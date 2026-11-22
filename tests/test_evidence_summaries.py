"""Hub answers and Agent summaries use the same reviewed data as their links."""
from copy import deepcopy
from pathlib import Path
import re
import tempfile
import unittest

import test_evaluation_overview as fixtures
from test_evaluation_overview import ROOT
from arena.reporting.overview import load_roster, make_catalog
from arena.reporting.overview_pages import Pages, render_pages
from arena.reporting.articles import render_article_body
from arena.reporting.bilingual import comparison, WORDS, OUTCOMES
from arena.reporting.detail import render_detail
from arena.reporting.site import report_navigation


class EvidenceSummaryTests(unittest.TestCase):
    record = fixtures.EvaluationOverviewTests.record
    save = fixtures.EvaluationOverviewTests.save

    def fixture(self, root, **kwargs):
        path, record = self.record(root, agent='codex-cli', scenario='camera-capture', **kwargs)
        for group in record['groups'].values():
            if group:
                group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high',
                    confirmationMode='capture-then-allow-once')
        record['presentation'] = {'testedOn': {'date': '2026-11-09', 'timezone': 'UTC+08:00'}}
        return path, path.relative_to(root), record

    def catalog(self, records):
        return make_catalog(records, load_roster(ROOT / 'profiles/coverage.json'))

    def test_case_answer_keeps_observations_conditions_and_original_links_in_both_languages(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(Path(folder))
            record = source[2]
            record['groups']['native']['interceptionAssessment']['reason'] = {
                'en': 'After Allow once, the controlled effect occurred <fixture>.',
                'zh-CN': 'Allow once之后发生受控效果<fixture>。'}
            record['groups']['finshield']['conditions']['approvalPolicy'] = None
            catalog = self.catalog([source])
            for language, observed, missing in [('en', 'After Allow once', 'Not recorded'),
                                                ('zh-CN', 'Allow once之后', '未记录')]:
                html = Pages(catalog, language).case(catalog['cases'][0])
                self.assertIn('id="recorded-answer"', html)
                self.assertIn(observed, html)
                self.assertIn('&lt;fixture&gt;', html)
                self.assertNotIn('occurred <fixture>', html)
                for text in ('2026-11-09', 'UTC+08:00', 'fixture-v2', 'deepseek-v4-pro',
                             'workspace-write', 'danger-full-access', 'capture-then-allow-once', missing):
                    self.assertIn(text, html)
                leaf = 'zh-CN.html' if language == 'zh-CN' else 'en.html'
                self.assertIn(source[1].parent.as_posix() + '/' + leaf, html)
                self.assertIn(source[1].parent.as_posix() + '/' + leaf + '#section-2', html)

    def test_missing_date_and_absent_track_stay_unknown_and_do_not_borrow_conditions(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(Path(folder), paired=False)
            source[2].pop('presentation')
            source[2]['groups']['native']['conditions']['agentVersion'] = None
            catalog = self.catalog([source])
            page = Pages(catalog, 'en')
            html = page.case(catalog['cases'][0])
            self.assertIn('Test date: Not recorded', html)
            self.assertIn('FinShield: Not run', html)
            self.assertNotIn('2026-11-09', html)
            agent = next(a for a in catalog['coverage'] if a['id'] == 'codex-cli')
            summary = page.agent_overview(agent)
            self.assertIn('Not recorded', summary)
            self.assertIn('Not tested', summary)

    def test_agent_summary_uses_conservative_scorer_and_its_contributing_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = self.fixture(root)
            second = self.fixture(root, identity='second')
            second[2]['groups']['native']['interceptionAssessment'] = deepcopy(
                second[2]['groups']['finshield']['interceptionAssessment'])
            second[2]['presentation']['testedOn']['date'] = '2026-11-10'
            second[2]['groups']['native']['conditions']['agentVersion'] = 'fixture-v3'
            outside = self.fixture(root, identity='outside')
            for group in outside[2]['groups'].values():
                group['conditions']['model'] = 'other-model'
                group['conditions']['agentVersion'] = 'outside-version'
            catalog = self.catalog([first, second, outside])
            page = Pages(catalog, 'en')
            agent = next(a for a in catalog['coverage'] if a['id'] == 'codex-cli')
            summary = page.agent_overview(agent)
            self.assertIn('DeepSeek Pro', summary)
            self.assertIn('high', summary)
            self.assertIn('0 of 1', summary)
            self.assertIn('1 of 1', summary)
            self.assertIn('2026-11-09', summary)
            self.assertIn('2026-11-10', summary)
            self.assertIn('fixture-v2', summary)
            self.assertIn('fixture-v3', summary)
            self.assertNotIn('outside-version', summary)
            self.assertIn('href="#privacy"', summary)
            for row in (first, second):
                self.assertIn(row[1].parent.as_posix() + '/en.html', summary)
            empty = next(a for a in catalog['coverage'] if a['id'] == 'workbuddy')
            self.assertNotIn('0 of 1', page.agent_overview(empty))

    def test_articles_link_to_localized_camera_hub_and_keep_original_citations(self):
        for slug in ('chrome-windows-sandbox', 'agent-privacy'):
            for language, prefix in [('en', ''), ('zh-CN', 'zh-cn/')]:
                text = (ROOT / f'articles/{slug}.{language}.md').read_text('utf8')
                self.assertIn(f'https://safety.finaios.ai/{prefix}cases/camera-capture/', text)
                self.assertIn('codex-python-file-v2-20261109/en.html', text)
                self.assertIn('workbuddy-python-file-v1-20261108/en.html', text)
                html = render_article_body(text, language, 'Summary', '')
                visible = re.sub(r'<details.*?</details>', '', html, flags=re.S)
                self.assertIn(f'https://safety.finaios.ai/{prefix}cases/camera-capture/', visible)

    def test_explanations_follow_visible_results_and_are_collapsed_on_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            catalog = self.catalog([self.fixture(Path(folder))])
            agent = next(a for a in catalog['coverage'] if a['id'] == 'codex-cli')
            for language in ('en', 'zh-CN'):
                page = Pages(catalog, language)
                for html, table, contents in [
                    (page.case(catalog['cases'][0]), 'class="scene-list"', 'id="recorded-answer"'),
                    (page.agent_score(agent), 'class="coverage-table agent-score-table"', 'id="recorded-overview"')]:
                    marker = '<details class="evidence-notes">'
                    self.assertTrue(marker in html, 'Explanations need a disclosure closed by default')
                    self.assertLess(html.index(table), html.index(marker))
                    self.assertLess(html.index(marker), html.index(contents))
                    self.assertLess(html.index(marker), html.index('class="scope-note"'))
                    self.assertIn('fixture-v2', html[html.index(marker):])

    def test_home_and_detail_scope_notes_follow_results_in_closed_disclosures(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(Path(folder))
            fixtures.EvaluationOverviewTests.attach_gif(self, source[0], source[2])
            source[2]['presentation']['dense'] = True
            catalog = self.catalog([source])
            navigation = report_navigation(catalog, source[1], source[2])
            for language in ('en', 'zh-CN'):
                home = Pages(catalog, language).home()
                marker = '<details class="evidence-notes">'
                with self.subTest(page='home', language=language):
                    self.assertTrue(marker in home, 'Homepage counting notes need a closed disclosure')
                    self.assertLess(home.index('id="real-tests"'), home.index(marker))
                    self.assertLess(home.index(marker), home.index('class="footnote"'))
                detail = render_detail(source[2], language, 'fixture-hash', comparison(source[2]),
                                       WORDS[language], OUTCOMES, navigation[language])
                with self.subTest(page='detail', language=language):
                    self.assertTrue(marker in detail, 'Full-site scope note needs a closed disclosure')
                    self.assertLess(detail.index('id="section-6"'), detail.index(marker))
                    self.assertLess(detail.index(marker), detail.index('class="evaluation-scope"'))
                standalone = render_detail(source[2], language, 'fixture-hash', comparison(source[2]),
                                           WORDS[language], OUTCOMES)
                self.assertNotIn('evaluation-scope', standalone)
                self.assertNotIn('class="evidence-notes"', standalone)

    def test_shared_templates_cover_all_cases_agents_and_category_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sources = [self.fixture(root)]
            for scenario in ('protected-directory-delete', 'window-flood'):
                path, record = self.record(root, scenario=scenario, agent='workbuddy')
                for group in record['groups'].values():
                    if group:
                        group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
                sources.append((path, path.relative_to(root), record))
            catalog = self.catalog(sources)
            pages = render_pages(catalog)
            for language in ('en', 'zh-CN'):
                renderer = Pages(catalog, language)
                routes = [renderer.case_path(case['id']) for case in catalog['cases']]
                for agent in catalog['coverage']:
                    routes.append(renderer.agent_page(agent['id']))
                    routes.extend(renderer.agent_page(agent['id'], category['id'])
                                  for category in catalog['categories'])
                for route in routes:
                    self.assertIn('<details class="evidence-notes">', pages[route], route)


if __name__ == '__main__':
    unittest.main()
