"""The project overview summarizes evidence without creating new trial results."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arena.reporting.site import build_site


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value and not value.startswith(('https:', '#')):
                self.paths.append(value.split('#')[0])


class EvaluationOverviewTests(unittest.TestCase):
    def record(self, results, identity='paired', *, agent='sample-agent', paired=True,
               origin='live', scenario='controlled-delete'):
        record = json.loads((ROOT / 'templates/reviewed-record.example.json').read_text('utf8'))
        record.update(agentId=agent, scenarioId=scenario, evidenceOrigin=origin)
        native = record['groups']['native']
        native['runId'] = agent + '-native-run'
        native['conditions']['agentId'] = agent
        native['conditions']['agentVersion'] = 'fixture-v2'
        native['conditions']['model'] = 'fixture-model'
        native['conditions']['builtinSandbox'] = 'workspace-write'
        native['conditions']['approvalPolicy'] = 'ask'
        native['interceptionAssessment'] = dict(status='not-blocked', basis='observed-effect',
            reason={'en': 'The controlled file disappeared.', 'zh-CN': '受控文件已消失。'},
            evidence=['controlled-observation'])
        native.pop('warningAssessment', None)
        record['groups']['finshield'] = deepcopy(native) if paired else None
        if paired:
            fs = record['groups']['finshield']
            fs.update(runId=agent + '-finshield-run', environmentVersion='FinShield fixture-7')
            fs['conditions']['builtinSandbox'] = 'danger-full-access'
            fs['interceptionAssessment'] = dict(status='blocked', basis='verified-postcondition',
                reason={'en': 'The controlled file remained present.', 'zh-CN': '受控文件仍然存在。'},
                evidence=['controlled-observation'], postcondition=dict(
                    effect={'en': 'loss of the controlled file', 'zh-CN': '受控文件丢失'},
                    attemptConfirmed=True, coverageConfirmed=True, baselineObserved=True,
                    observed=False, mechanism='unverified'))
        record['publicMedia'] = []
        for lang, title in [('en', 'Controlled deletion <fixture>'), ('zh-CN', '受控删除 <fixture>')]:
            record['narrative'][lang]['title'] = title
            record['narrative'][lang]['purpose'] = 'A controlled <script>fixture</script>.'
        path = results / scenario / agent / identity / 'record.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        return self.save(path, record)

    def save(self, path, record):
        path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf8')
        return path, record

    def attach_gif(self,path,record):
        record['presentation']=dict(layout='comparison-v1',agentLabel={'en':'Sample Agent','zh-CN':'样例 Agent'},
            groups={name:dict(title={'en':name,'zh-CN':name},configuration=['controlled fixture'],
                toolSummary={'en':'Controlled result.','zh-CN':'受控结果。'}) for name in ('native','finshield')},
            overview=dict(media='media/comparison.gif',results={name:{'en':'Reviewed result.','zh-CN':'已审阅结果。'} for name in ('native','finshield')}),
            reproduction={'en':'Follow the controlled fixture procedure.','zh-CN':'按受控流程复现。'})
        media=path.parent/'media/comparison.gif';media.parent.mkdir(exist_ok=True);media.write_bytes(b'controlled original GIF fixture')
        record['publicMedia']=[dict(kind='image',path='media/comparison.gif',group='comparison',
            caption={'en':'Edited excerpt; speed adjusted.','zh-CN':'节选；已调整速度。'})]
        self.save(path,record)
        return media

    def test_counts_unique_live_runs_and_separates_reused_and_synthetic_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            self.record(results, identity='earlier', paired=False)
            self.record(results, agent='another-agent', paired=False)
            self.record(results, origin='synthetic', scenario='sample-only')
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            counts = catalog['counts']
            self.assertEqual(catalog['schemaVersion'], 1)
            for key, expected in dict(liveScenarios=1, liveAgents=2, liveRuns=3,
                    pairedReports=1, formalReports=3, developmentReports=0,
                    languageStudyReports=0, syntheticReports=1, archivedReports=1).items():
                self.assertEqual(counts[key], expected, key)
            earlier = next(r for r in catalog['reports'] if r['path'].endswith('/earlier'))
            self.assertTrue(earlier['archived'])
            html = (root / 'site/methodology.html').read_text('utf8')
            self.assertIn('id="history"', html)
            self.assertIn('id="synthetic"', html)
            self.assertNotIn('100%', html)

    def test_preserves_scoped_assessments_unknowns_versions_and_mismatched_conditions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            path, record = self.record(results)
            record['groups']['native'].pop('interceptionAssessment')
            record['groups']['native']['warningAssessment'] = dict(level='unassessed',
                reason={'en': 'Incomplete observation.', 'zh-CN': '观察不完整。'}, evidence=None)
            self.save(path, record)
            self.record(results, agent='another-agent', paired=False)
            before = path.read_bytes()
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            paired = next(r for r in catalog['reports'] if r['paired'])
            fs = paired['assessments']['finshield']
            self.assertEqual(fs['label']['zh-CN'], '已阻止受控文件丢失')
            self.assertIsNone(fs['warningLevel'])
            self.assertEqual(paired['assessments']['native']['state'], 'unassessed')
            self.assertEqual(paired['versions']['finshield'], 'FinShield fixture-7')
            self.assertEqual(paired['conditionStatus'], 'incomplete')
            single = next(r for r in catalog['reports'] if not r['paired'])
            self.assertEqual(single['assessments']['finshield']['state'], 'not-run')
            self.assertEqual(path.read_bytes(), before)
            html = (root / 'site/cases/controlled-delete/zh-CN.html').read_text('utf8')
            self.assertNotIn('受控文件丢失', html)
            self.assertNotIn('弹窗', html)
            self.assertNotIn('0.10.9', html)
            self.assertNotIn('<script>fixture</script>', html)

    def test_does_not_archive_a_report_with_conflicting_conditions_for_the_same_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            path, single = self.record(results, identity='different-conditions', paired=False)
            single['groups']['native']['conditions']['model'] = 'different-model'
            self.save(path, single)
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            self.assertEqual(catalog['counts']['archivedReports'], 0)

    def test_both_languages_link_to_every_report_and_evidence_with_relative_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            self.record(results)
            self.record(results, identity='earlier', paired=False)
            build_site(results, site)
            for page in site.rglob('*.html'):
                html = page.read_text('utf8')
                parsed = Links(); parsed.feed(html)
                self.assertTrue(all((page.parent / p).is_file() for p in parsed.paths), (page, parsed.paths))
            self.assertIn('lang="en"', (site / 'index.html').read_text('utf8'))
            self.assertIn('lang="zh-CN"', (site / 'zh-CN.html').read_text('utf8'))
            self.assertIn('Earlier reports', (site / 'methodology.html').read_text('utf8'))
            manifest = json.loads((site / 'site-manifest.json').read_text('utf8'))
            for filename in ('catalog.json', 'catalog.css', 'en.html', 'zh-CN.html', 'interaction.html'):
                self.assertIn(filename, manifest['files'])

    def test_planned_agents_remain_visible_and_only_matching_model_enters_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            path, record = self.record(results, agent='codex-cli')
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-official/deepseek-v4-pro', reasoningEffort='high')
            record['groups']['finshield']['conditions']['reasoningEffort'] = 'low'
            self.save(path, record)
            self.record(results, agent='synthetic-only-agent', origin='synthetic', scenario='sample-only')
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            self.assertEqual(len(catalog['coverage']), 5)
            codex = next(r for r in catalog['coverage'] if r['id'] == 'codex-cli')
            self.assertEqual(codex['native']['scenarios'], 1)
            self.assertEqual(codex['native']['formalScenarios'], 1)
            self.assertEqual(codex['finshield']['scenarios'], 0)
            workbuddy = next(r for r in catalog['coverage'] if r['id'] == 'workbuddy')
            self.assertEqual(workbuddy['native']['reports'], [])
            html = (root / 'site/zh-CN.html').read_text('utf8')
            for label in ('WorkBuddy', 'OpenCode CLI', 'Claude CLI'):
                self.assertIn(label, html)
            for agent in ('workbuddy', 'claude-cli', 'opencode-cli', 'codex-cli'):
                self.assertIn(f'data-score-agent="{agent}"', html, agent)
            self.assertNotIn('不评测模型能力', html)
            self.assertNotIn('class="protocol"', html)
            self.assertNotIn('DeepSeek Pro', html)

    def test_home_stays_compact_with_100_cases_and_categories_paginate_by_scenario(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            taxonomy = json.loads((ROOT / 'scenarios/catalog.json').read_text('utf8'))
            taxonomy['scenarios'] = {}
            for number in range(100):
                scenario = f'case-{number:03d}'
                self.record(results, scenario=scenario, paired=False)
                taxonomy['scenarios'][scenario] = dict(category='interaction',
                    title={'en': f'Case {number:03d}', 'zh-CN': f'场景 {number:03d}'})
            # Another Agent's report does not add a second scenario row.
            self.record(results, scenario='case-000', agent='second-agent', paired=False)
            path = root / 'catalog.json'; path.write_text(json.dumps(taxonomy), encoding='utf8')
            build_site(results, site, ROOT / 'profiles/coverage.json', path)
            home = (site / 'index.html').read_text('utf8')
            self.assertEqual(re.findall(r'data-category="([^"]+)"', home),
                             ['privacy', 'interaction', 'system', 'data'])
            self.assertIn('class="agent-card-grid"', home)
            self.assertEqual(home.count('data-score-agent='), 5)
            self.assertNotIn('score-matrix', home)
            self.assertNotIn('data-case=', home)
            self.assertNotIn('<img', home)
            self.assertNotIn('Case 099', home)
            self.assertNotIn('domestic', home.lower())
            self.assertNotIn('international', home.lower())
            self.assertNotIn('Target:', home)
            self.assertNotIn('recorded scenario', home)
            seen = set()
            for number in range(1, 6):
                page = site / ('interaction' + (f'-{number}' if number > 1 else '') + '.html')
                text = page.read_text('utf8')
                ids = re.findall(r'data-case="([^"]+)"', text)
                self.assertEqual(len(ids), 20)
                self.assertEqual(text.count('class="scenario-card"'), 20)
                self.assertIn('class="scenario-card-grid"', text)
                self.assertNotIn('scenario-table', text)
                self.assertTrue(seen.isdisjoint(ids))
                seen.update(ids)
                self.assertTrue(page.with_suffix('.zh-CN.html').is_file())
            self.assertEqual(len(seen), 100)
            self.assertFalse((site / 'interaction-6.html').exists())
            self.assertIn('Scenarios in this category are being collected', (site / 'data.html').read_text('utf8'))
            catalog = json.loads((site / 'catalog.json').read_text('utf8'))
            self.assertEqual(next(c for c in catalog['categories'] if c['id']=='interaction')['scenarios'], 100)
            self.assertTrue(all('region' not in agent for agent in catalog['coverage']))

    def test_duplicate_roster_aliases_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            roster = json.loads((ROOT / 'profiles/coverage.json').read_text('utf8'))
            roster['agents'][1]['recordAgentIds'].append('dsh')
            path = root / 'coverage.json'; path.write_text(json.dumps(roster), encoding='utf8')
            with self.assertRaises(ValueError):
                build_site(results, root / 'site', path)
            self.assertFalse((root / 'site').exists())

    def test_home_showcase_whole_cards_link_to_categories_and_preserve_live_gif(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results';site=root/'site'
            path,record=self.record(results)
            media=self.attach_gif(path,record)
            taxonomy=json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))
            taxonomy['scenarios']['controlled-delete']=dict(category='data',title={'en':'Controlled deletion','zh-CN':'受控删除'})
            config=root/'taxonomy.json';config.write_text(json.dumps(taxonomy),encoding='utf8')
            before=path.read_bytes()
            build_site(results,site,catalog_path=config)
            html=(site/'index.html').read_text('utf8')
            prefix='controlled-delete/sample-agent/paired/'
            self.assertLess(html.index('id="real-tests"'),html.index('id="agent-scores"'))
            self.assertIn('<img',html)
            self.assertIn(prefix+'media/comparison.gif',html)
            showcase=html.split('id="real-tests"')[1].split('id="agent-scores"')[0]
            for filename, suffix in [('index.html', ''), ('zh-CN.html', '.zh-CN')]:
                localized = (site / filename).read_text('utf8')
                showcase_html = localized.split('id="real-tests"')[1].split('id="agent-scores"')[0]
                cards = re.findall(r'<a class="test-card scenario-card"[^>]*>.*?</a>', showcase_html, re.S)
                self.assertEqual(len(cards), 4, filename)
                self.assertEqual(showcase_html.count('<a '), 4, 'One native link per entire card')
                for category, whole_card in zip(('privacy', 'interaction', 'system', 'data'), cards):
                    self.assertIn(f'href="{category}{suffix}.html"', whole_card)
                    self.assertIn('<h3', whole_card)
                    self.assertIn('class="showcase-lead"', whole_card)
                    self.assertIn('class="category-entry"', whole_card)
                    self.assertNotIn('onclick=', whole_card)
                    if category == 'data':
                        self.assertIn('<img', whole_card)
                    else:
                        self.assertNotIn('<img', whole_card)
            card=re.search(r'<a class="test-card scenario-card"[^>]*data-category="data".*?</a>',showcase,re.S).group()
            self.assertIn('Data Safety',card)
            self.assertIn('Files are deleted, changed, or copied away in secret, and your important materials cannot be recovered or are leaked',card)
            self.assertIn('href="data.html"',card)
            self.assertLess(card.index('<h3'), card.index('<img'))
            self.assertNotIn('#section-3',card)
            self.assertNotIn('Controlled deletion',showcase)
            self.assertNotIn('>sample-agent<',showcase)
            self.assertNotIn('class="test-title"',html)
            self.assertNotIn('class="test-actions"',html)
            self.assertNotIn('class="showcase-note"',html)
            self.assertNotIn('Video comparison',html)
            self.assertNotIn('Original records',html)
            self.assertNotIn('evidence.json',html)
            self.assertNotIn('GIF excerpt',html)
            css=(site/'catalog.css').read_text('utf8')
            self.assertIn('.refined-page .showcase-grid{grid-template-columns:repeat(4,minmax(0,1fr))',css)
            self.assertEqual(re.findall(r'data-category="([^"]+)"', html),
                             ['privacy', 'interaction', 'system', 'data'])
            self.assertEqual(html.count('data-media-state="empty"'),3)
            self.assertNotIn('category-score-table',html)
            self.assertEqual(media.read_bytes(),(site/prefix/'media/comparison.gif').read_bytes())
            self.assertEqual(path.read_bytes(),before)
            catalog=json.loads((site/'catalog.json').read_text('utf8'))
            self.assertTrue(catalog['reports'][0]['hasReproduction'])

    def test_missing_or_synthetic_media_keeps_four_honest_empty_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results';site=root/'site'
            self.record(results)
            path,record=self.record(results,origin='synthetic',scenario='window-flood')
            self.attach_gif(path,record)
            build_site(results,site)
            html=(site/'index.html').read_text('utf8')
            self.assertIn('id="real-tests"',html)
            self.assertEqual(re.findall(r'data-category="([^"]+)"', html),
                             ['privacy', 'interaction', 'system', 'data'])
            self.assertEqual(html.count('data-media-state="empty"'),4)
            self.assertNotIn('<img',html)
            self.assertNotIn('href="#"',html)
            self.assertNotIn('No media available',html)
            self.assertEqual(html.count('class="category-entry"'),4)
            self.assertNotIn('class="test-actions"',html)

    def test_homepage_uses_the_same_type_as_inner_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.record(root / 'results')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            css = (root / 'site/catalog.css').read_text('utf8')
            block = css.split('.refined-page{', 1)[1].split('.refined-page ', 1)[0]
            self.assertIn('--text-size:14px', block)
            self.assertIn('--heading-size:20px', block)
            self.assertIn('Microsoft YaHei', block)
            for route in ('index.html', 'zh-CN.html'):
                html = (root / 'site' / route).read_text('utf8')
                self.assertIn('class="refined-page"', html)
                self.assertNotIn('Segoe UI', html)

    def test_site_headers_share_four_categories_and_github(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.record(root / 'results', scenario='camera-capture', agent='workbuddy')
            self.attach_gif(path, record)
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.save(path, record)
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            chinese = ['隐私安全', '交互安全', '系统安全', '数据安全']
            english = ['Privacy Safety', 'Interaction Safety', 'System Safety', 'Data Safety']
            home = (root / 'site/zh-CN.html').read_text('utf8')
            home_header = re.search(r'<header\b.*?</header>', home).group()
            for label in chinese:
                self.assertIn(label, home_header)
            self.assertIn('GitHub ↗', home_header)
            self.assertNotIn('场景分类', home_header)
            self.assertNotIn('评测方法', home_header)
            self.assertNotIn('不评测模型能力', home)
            self.assertNotIn('class="protocol"', home)
            self.assertIn('<section class="intro"><div><h1>', home)
            self.assertLess(home.index('Agent安全测评'), home.index('id="real-tests"'))
            pages = {
                root / 'site/zh-CN.html': chinese,
                root / 'site/privacy.zh-CN.html': chinese,
                root / 'site/cases/camera-capture/zh-CN.html': chinese,
                root / 'site/methodology.zh-CN.html': chinese,
                root / 'site/camera-capture/workbuddy/paired/zh-CN.html': chinese,
                root / 'site/index.html': english,
                root / 'site/interaction.html': english,
            }
            for path, labels in pages.items():
                html = path.read_text('utf8')
                header = re.search(r'<header\b.*?</header>', html).group()
                for label in labels:
                    self.assertIn(label, header)
                self.assertIn('GitHub ↗', header)
                self.assertNotIn('#categories', header)
            category_header = re.search(r'<header\b.*?</header>',
                                        (root / 'site/privacy.zh-CN.html').read_text('utf8')).group()
            self.assertIn('aria-current="page">隐私安全</a>', category_header)

    def test_privacy_safety_is_first_and_owns_camera_leak(self):
        taxonomy = json.loads((ROOT / 'scenarios/catalog.json').read_text('utf8'))
        self.assertEqual([item['id'] for item in taxonomy['categories']],
                         ['privacy', 'interaction', 'system', 'data'])
        self.assertEqual(taxonomy['categories'][0]['label'],
                         {'en': 'Privacy Safety', 'zh-CN': '隐私安全'})
        self.assertEqual(taxonomy['scenarios']['camera-capture']['category'], 'privacy')
        self.assertEqual(taxonomy['scenarios']['microphone-capture']['category'], 'privacy')
        self.assertEqual(taxonomy['scenarios']['microphone-capture']['title'],
                         {'en': 'Microphone Leak', 'zh-CN': '麦克风泄密'})
        self.assertEqual(taxonomy['scenarios']['screen-capture']['category'], 'privacy')
        self.assertEqual(taxonomy['scenarios']['screen-capture']['title'],
                         {'en': 'Screen Leak', 'zh-CN': '截屏泄密'})
        self.assertEqual(taxonomy['scenarios']['screen-capture']['displayOrder'], 2)
        self.assertNotIn('speaker-mute', taxonomy['scenarios'])
        descriptions = {item['id']: item['description'] for item in taxonomy['categories']}
        self.assertEqual(descriptions, {
            'privacy': {
                'en': 'The camera or microphone is turned on in secret, or a screenshot is taken, and your image, conversation or screen leak out',
                'zh-CN': '摄像头或麦克风被偷偷打开，或屏幕被偷偷截下，你的画面、谈话或屏幕内容会泄露出去',
            },
            'interaction': {
                'en': 'Pop-ups cover the screen, windows jump or disappear, and your computer feels like someone else is controlling it',
                'zh-CN': '弹窗盖住屏幕，窗口乱动或消失，你的电脑像被别人控制',
            },
            'system': {
                'en': 'Programs are shut down, permissions and system settings are changed, and your computer cannot be used',
                'zh-CN': '程序被关掉，权限和系统设置被改掉，你的电脑无法使用',
            },
            'data': {
                'en': 'Files are deleted, changed, or copied away in secret, and your important materials cannot be recovered or are leaked',
                'zh-CN': '文件被删改或偷偷拷走，你的重要资料找不回来或被泄露出去',
            },
        })
        for item in taxonomy['categories']:
            for text in item['description'].values():
                self.assertFalse(str(text).endswith(('。', '.')))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.record(root / 'results', scenario='camera-capture', agent='workbuddy')
            self.attach_gif(path, record)
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.save(path, record)
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/zh-CN.html').read_text('utf8')
            self.assertEqual(re.findall(r'data-category="([^"]+)"', home),
                             ['privacy', 'interaction', 'system', 'data'])
            self.assertLess(home.index('data-category="privacy"'), home.index('data-category="interaction"'))
            card = re.search(r'<article class="agent-card".*?</article>', home, re.S).group()
            self.assertLess(card.index('隐私安全'), card.index('交互安全'))
            html = (root / 'site/camera-capture/workbuddy/paired/zh-CN.html').read_text('utf8')
            crumb = re.search(r'<nav class="report-breadcrumb".*?</nav>', html).group()
            self.assertIn('隐私安全', crumb)
            self.assertIn('href="../../../privacy.zh-CN.html"', crumb)
            self.assertIn('摄像头泄密', crumb)
            self.assertNotIn('数据安全', crumb)
            category = (root / 'site/privacy.zh-CN.html').read_text('utf8')
            self.assertNotIn('class="category-tabs"', category)
            main = category.split('</header>', 1)[1]
            self.assertNotIn('交互安全', main)


if __name__ == '__main__':
    unittest.main()
