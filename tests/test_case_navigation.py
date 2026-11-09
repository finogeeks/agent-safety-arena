"""Case discovery stays separate from Agent result and evidence navigation."""
import json
from html import escape
from pathlib import Path
import re
import tempfile
import unittest

import test_evaluation_overview as fixtures
from test_evaluation_overview import ROOT
from arena.reporting.overview import load_taxonomy
from arena.reporting.site import build_site


class CaseNavigationTests(unittest.TestCase):
    record = fixtures.EvaluationOverviewTests.record
    save = fixtures.EvaluationOverviewTests.save

    def fixed_record(self, results, **kwargs):
        path, record = self.record(results, **kwargs)
        for group in record['groups'].values():
            if group:
                group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
        return self.save(path, record)

    def metadata(self, root, scenarios):
        data = json.loads((ROOT / 'scenarios/catalog.json').read_text('utf8'))
        data['scenarios'] = scenarios
        path = root / 'taxonomy.json'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        return path

    def test_localized_cards_show_purpose_and_link_without_agent_scores_or_slug(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixed_record(root / 'results', scenario='window-flood', agent='dsh')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            for language, route, title, purpose, action in [
                ('zh-CN', 'interaction.zh-CN.html', '弹窗风暴', '把正在用的应用埋住', '查看详情'),
                ('en', 'interaction.html', 'Window Flood', 'working apps are buried', 'View case'),
            ]:
                html = (root / 'site' / route).read_text('utf8')
                for closed in re.findall(r'<details(?![^>]*\bopen\b)[^>]*>.*?</details>', html):
                    self.assertNotIn('class="coverage-table"', closed)
                self.assertLess(html.index('class="coverage-table"'), html.index('class="scenario-card-grid"'))
                card = re.search(r'<a class="scenario-card".*?</a>', html).group()
                self.assertIn(title, card)
                self.assertIn(purpose, card)
                data = json.loads((root / 'site/catalog.json').read_text('utf8'))
                description = next(case for case in data['cases'] if case['id'] == 'window-flood')['description'][language]
                self.assertIn('title="' + escape(description, quote=True) + '"', card)
                self.assertIn(action, card)
                self.assertNotIn('DSH', card)
                self.assertNotIn('score', card)
                self.assertNotIn('<small>window-flood', card)
                if language == 'en':
                    self.assertNotRegex(card, r'[\u4e00-\u9fff]')
                else:
                    self.assertNotIn('Window Flood', card)

    def test_case_cards_count_agents_once_and_keep_unresolved_and_untested_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixed_record(root / 'results', scenario='window-flood', agent='dsh')
            self.fixed_record(root / 'results', identity='duplicate', scenario='window-flood', agent='dsh')
            path, record = self.fixed_record(root / 'results', scenario='window-flood', agent='codex-cli', paired=False)
            record['groups']['native'].pop('interceptionAssessment')
            self.save(path, record)
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            html = (root / 'site/interaction.zh-CN.html').read_text('utf8')
            card = re.search(r'<a class="scenario-card".*?</a>', html).group()
            self.assertIn('data-protection="native"', card)
            self.assertIn('data-protection="finshield"', card)
            native = re.search(r'<div data-protection="native">.*?</div>', card).group()
            finshield = re.search(r'<div data-protection="finshield">.*?</div>', card).group()
            for value in ('失败1个', '待核实1个', '未测试3个'):
                self.assertIn(value, native)
            for value in ('成功1个', '未测试4个'):
                self.assertIn(value, finshield)
            self.assertNotIn('失败2个', native)
            self.assertNotIn('DSH', card)
            self.assertNotIn('Codex CLI', card)

    def test_category_intro_is_brief_without_model_or_effort_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixed_record(root / 'results', scenario='window-flood', agent='dsh')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            for route in ('interaction.html', 'interaction.zh-CN.html'):
                html = (root / 'site' / route).read_text('utf8')
                intro = re.search(r'<section class="page-intro">.*?</section>', html).group()
                self.assertNotIn('DeepSeek', intro)
                self.assertNotIn('High', intro)
                self.assertEqual(intro.count('<p'), 1)
                self.assertIn('class="coverage-table"', html)
                self.assertIn('0%', html)
                self.assertIn('100%', html)
                self.assertNotIn('class="phase-label"', html)
                self.assertNotIn('class="category-tabs"', html)
                self.assertNotIn('class="pagination"', html)
                self.assertNotIn('防护结果 · 智能体数量', html)
                self.assertNotIn('Protection results · Agent counts', html)
            for route in ('index.html', 'zh-CN.html'):
                self.assertNotIn('class="phase-label"', (root / 'site' / route).read_text('utf8'))

    def test_display_priority_applies_before_pagination_and_description_is_escaped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scenarios = {}
            for number in range(21):
                identity = f'case-{number:02d}'
                self.record(root / 'results', scenario=identity)
                scenarios[identity] = dict(category='interaction',
                    title={'en': identity, 'zh-CN': f'案例{number}'})
            scenarios['case-20'].update(displayOrder=0, description={
                'en': 'Controlled <b>effect</b>.', 'zh-CN': '受控 <b>效果</b>。'})
            config = self.metadata(root, scenarios)
            build_site(root / 'results', root / 'site', catalog_path=config)
            html = (root / 'site/interaction.html').read_text('utf8')
            identities = re.findall(r'data-case="([^"]+)"', html)
            self.assertEqual(identities, ['case-20'] + [f'case-{n:02d}' for n in range(19)])
            self.assertIn('Controlled &lt;b&gt;effect&lt;/b&gt;.', html)
            self.assertIn('A controlled &lt;script&gt;fixture&lt;/script&gt;.', html)
            self.assertIn('data-case="case-19"', (root / 'site/interaction-2.html').read_text('utf8'))
            self.assertIn('class="pagination"', html)
            self.assertNotIn('class="category-tabs"', html)

    def test_inner_pages_share_home_first_breadcrumb_and_compact_header(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixed_record(root / 'results', scenario='window-flood', agent='dsh')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/zh-CN.html').read_text('utf8')
            home_header = re.search(r'<header\b.*?</header>', home).group()
            self.assertIn('aria-label="主导航"', home_header)
            self.assertIn('GitHub ↗', home_header)
            self.assertIn('brand-mark', home_header)
            self.assertNotIn('class="report-breadcrumb"', home)
            self.assertNotIn('场景分类', home_header)
            self.assertNotIn('评测方法', home_header)
            pages = [
                (root / 'site/interaction.zh-CN.html', '交互安全',
                 [('zh-CN.html', '首页')]),
                (root / 'site/cases/window-flood/zh-CN.html', '弹窗风暴',
                 [('../../zh-CN.html', '首页'), ('../../interaction.zh-CN.html', '交互安全')]),
                (root / 'site/methodology.zh-CN.html', '评测方法',
                 [('zh-CN.html', '首页')]),
                (root / 'site/interaction.html', 'Interaction Safety',
                 [('index.html', 'Home')]),
                (root / 'site/cases/window-flood/index.html', 'Window Flood',
                 [('../../index.html', 'Home'), ('../../interaction.html', 'Interaction Safety')]),
            ]
            for path, current, parents in pages:
                html = path.read_text('utf8')
                header = re.search(r'<header\b.*?</header>', html).group()
                crumb = re.search(r'<nav class="report-breadcrumb".*?</nav>', html)
                self.assertIsNotNone(crumb, path.name)
                trail = crumb.group()
                links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', trail)
                self.assertEqual(links, parents, path.name)
                self.assertIn('aria-current="page">' + current + '</span>', trail)
                self.assertNotIn('← 总览', html)
                self.assertNotIn('← 场景列表', html)
                self.assertIn('GitHub ↗', header)
                self.assertIn('class="brand"', header)
                self.assertIn('class="locale"', header)
                if 'zh-CN' in path.name:
                    self.assertIn('aria-label="主导航"', header)
                    self.assertIn('隐私安全', header)
                    self.assertNotIn('场景分类', header)
                else:
                    self.assertIn('aria-label="Main navigation"', header)
                    self.assertIn('Privacy Safety', header)

    def test_single_case_hub_shows_combined_results_without_redundant_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixed_record(root / 'results', scenario='window-flood', agent='dsh')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            html = (root / 'site/cases/window-flood/zh-CN.html').read_text('utf8')
            table = re.search(r'<table class="case-table">.*?</table>', html).group()
            for value in ('未拦截', '已拦截', '未测试', '详情与证据'):
                self.assertIn(value, table)
            for value in ('开发评测', '条件有差异或缺项', '受控文件丢失'):
                self.assertNotIn(value, html)
            for value in ('%', '成功0 · 失败1', '成功1 · 失败0'):
                self.assertNotIn(value, table)
            self.assertIn('data-label="默认防护"', table)
            self.assertIn('data-label="FinShield"', table)
            self.assertIn('把正在用的应用埋住', html)
            self.assertIn('../../window-flood/dsh/paired/zh-CN.html', html)
            self.assertNotIn('每个 Agent', html)
            # A new unresolved repeat cannot become a verified block on the hub.
            path, record = self.fixed_record(root / 'results', identity='unresolved', scenario='window-flood', agent='dsh')
            record['groups']['finshield']['runId'] = 'different-run'
            record['groups']['finshield'].pop('interceptionAssessment')
            self.save(path, record)
            build_site(root / 'results', root / 'repeated', ROOT / 'profiles/coverage.json')
            html = (root / 'repeated/cases/window-flood/zh-CN.html').read_text('utf8')
            self.assertIn('待核实', html)
            self.assertNotIn('待核实1', html)
            self.assertNotIn('100%', html)

    def test_taxonomy_rejects_invalid_description_and_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            item = dict(category='interaction', title={'en': 'Case', 'zh-CN': '案例'})
            for key, value in [('displayOrder', True), ('displayOrder', -1),
                               ('description', {'en': 'Only English'})]:
                with self.subTest(key=key, value=value):
                    path = self.metadata(root, {'case': dict(item, **{key: value})})
                    with self.assertRaises(ValueError):
                        load_taxonomy(path)


if __name__ == '__main__':
    unittest.main()
