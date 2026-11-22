"""Product gate labels, footer, and restored roster visibility on the public site build."""
import json
import re
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arena.reporting.site import build_site
from tests import test_evaluation_overview as fixtures


class SiteProductGateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationOverviewTests()

    def test_native_track_uses_agent_builtin_sandbox_label(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.fixture.record(root / 'results', scenario='window-flood', agent='dsh')
            self.fixture.attach_gif(path, record)
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            for route, expected, previous in (
                ('index.html', 'Built-in sandbox', 'Agent built-in sandbox'),
                ('zh-CN.html', 'Agent内置沙箱', '默认防护'),
                ('interaction.html', 'Built-in sandbox', 'Agent built-in sandbox'),
                ('interaction.zh-CN.html', 'Agent内置沙箱', '默认防护'),
                ('cases/window-flood/index.html', 'Built-in sandbox', 'Agent built-in sandbox'),
                ('cases/window-flood/zh-CN.html', 'Agent内置沙箱', '默认防护'),
            ):
                html = (root / 'site' / route).read_text('utf8')
                self.assertIn(expected, html, route)
                self.assertNotIn(previous, html, route)

    def test_home_omits_repeated_phase_badges_and_keeps_footer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            self.fixture.record(results, scenario='interaction-case')
            path, record = self.fixture.record(results, scenario='interaction-case', agent='dsh')
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/index.html').read_text('utf8')
            self.assertNotIn('class="phase-label"', home)
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            self.assertEqual(catalog['scorePhase'], 'formal')
            self.assertIn('https://finaios.ai', home)
            self.assertIn('FinAI OS', home)

    def test_workbuddy_observed_results_are_scored_with_condition_limits_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, agent='workbuddy', scenario='camera-capture')
            record['groups']['native']['conditions']['builtinSandbox'] = 'enabled'
            record['groups']['finshield']['conditions']['builtinSandbox'] = 'disabled'
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/index.html').read_text('utf8')
            self.assertIn('data-score-agent="workbuddy"', home)
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            scores = catalog['scores']['formal']['agents']['workbuddy']
            self.assertEqual(scores['native']['denominator'], 1)
            self.assertEqual(scores['native']['rate'], 0)
            self.assertEqual(scores['finshield']['denominator'], 1)
            self.assertEqual(scores['finshield']['rate'], 100)
            self.assertTrue(catalog['reports'][0]['conditionsDiffer'])

    def test_home_score_table_has_linked_agent_rows_and_empty_scores_in_both_languages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, agent='codex-cli')
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            record['groups']['finshield'] = None
            record['groups']['native'].pop('interceptionAssessment', None)
            self.fixture.save(path, record)
            self.fixture.record(results, agent='dsh')
            self.fixture.record(results, agent='workbuddy')
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            for route, locale, untested in (('index.html', '', 'Not tested'),
                                            ('zh-cn/index.html', 'zh-cn/', '未测试')):
                home = (root / 'site' / route).read_text('utf8')
                table = re.search(r'<table class="home-score-table".*?</table>', home, re.S)
                self.assertIsNotNone(table)
                table = table.group()
                columns = ['overall', 'privacy', 'interaction', 'system', 'data']
                self.assertEqual(re.findall(r'<th scope="col" data-score-scope="([^"]+)"', table), columns)
                rows = dict(re.findall(r'<tr data-score-agent="([^"]+)">(.*?)</tr>', table, re.S))
                self.assertEqual(list(rows),
                                 ['dsh', 'workbuddy', 'codex-cli', 'claude-cli', 'kilo', 'hermes', 'opencode-cli'])
                self.assertEqual(re.findall(r'<th scope="row"><a [^>]*>([^<]+)</a>', table),
                                 ['DeepSeek Harness', 'WorkBuddy', 'Codex CLI', 'Claude CLI', 'Kilo', 'Hermes', 'OpenCode'])
                for row in rows.values():
                    self.assertEqual(row.count('<th scope="row">'), 1)
                    self.assertEqual(re.findall(r'<td data-score-scope="([^"]+)"', row), columns)
                    self.assertEqual(row.count('data-score-protection='), 10)
                for agent_id, label in (('kilo', 'Kilo'), ('hermes', 'Hermes'), ('opencode-cli', 'OpenCode')):
                    target = f'agents/{agent_id}/'
                    self.assertIn(f'<th scope="row"><a href="{target}">{label}</a></th>', rows[agent_id])
                    cells = re.findall(r'<td .*?</td>', rows[agent_id], re.S)
                    self.assertEqual(len(cells), 5)
                    self.assertTrue(all(cell.count('<span class="dash">—</span>') == 2 for cell in cells))
                    detail = (root / 'site' / locale / target / 'index.html').read_text('utf8')
                    self.assertIn(f'<h1>{label}</h1>', detail)
                    self.assertIn(untested, detail)
                self.assertNotIn('class="phase-label"', home)

    def test_category_and_scenario_rows_show_untested_agents_and_link_live_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            self.fixture.record(results, scenario='window-flood', agent='dsh')
            self.fixture.record(results, scenario='window-flood', agent='hermes', origin='synthetic')
            path, record = self.fixture.record(results, scenario='window-flood', agent='opencode')
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            site = root / 'site'
            build_site(results, site, ROOT / 'profiles/coverage.json')
            roster = ['DeepSeek Harness', 'WorkBuddy', 'Codex CLI', 'Claude CLI', 'Kilo', 'Hermes', 'OpenCode']
            for locale, untested in (('', 'Not tested'), ('zh-cn/', '未测试')):
                category = (site / locale / 'interaction/index.html').read_text('utf8')
                hub = (site / locale / 'cases/window-flood/index.html').read_text('utf8').split('<details class="archive">')[0]
                self.assertEqual(re.findall(r'<a class="row-link"[^>]*>([^<]+)</a>', category), roster)
                self.assertEqual(re.findall(r'class="result-row"[^>]*><span class="name">([^<]+)</span>', hub), roster)
                empty = (f'<span class="untested-result"><span aria-hidden="true">—</span>'
                         f'<span class="sr-only">{untested}</span></span>')
                for agent_id, label in (('kilo', 'Kilo'), ('hermes', 'Hermes')):
                    category_link = f'href="../agents/{agent_id}/interaction/">{label}</a>'
                    category_row = category.split(category_link, 1)[1].split('</tr>', 1)[0]
                    self.assertEqual(category_row.count(empty), 2)
                    case_label = f'<div class="result-row"><span class="name">{label}</span>'
                    case_row = hub.split(case_label, 1)[1].split('</div>', 1)[0]
                    self.assertEqual(case_row.count(empty), 2)
                self.assertIn('<a class="result-row" href="../../results/window-flood/opencode/paired/">'
                              '<span class="name">OpenCode</span>', hub)
            scores = json.loads((site / 'catalog.json').read_text('utf8'))['scores']['formal']['agents']
            for agent in ('kilo', 'hermes'):
                for group in ('native', 'finshield'):
                    self.assertEqual(scores[agent][group]['denominator'], 0)
                    self.assertIsNone(scores[agent][group]['rate'])
            self.assertEqual(scores['opencode-cli']['native']['denominator'], 1)

    def test_committed_live_reports_have_formal_publication_without_rewriting_collection_phase(self):
        records = list((ROOT / 'results').rglob('record.json'))
        self.assertTrue(records)
        for path in records:
            record = json.loads(path.read_text('utf8'))
            if record['evidenceOrigin'] == 'live':
                from arena.reporting.publication import public_record
                before = path.read_bytes()
                self.assertEqual(public_record(record)['phase'], 'formal', path.relative_to(ROOT))
                self.assertEqual(path.read_bytes(), before)

    def test_showcase_keeps_four_categories_and_honest_empty_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, scenario='camera-capture', agent='workbuddy')
            self.fixture.attach_gif(path, record)
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/index.html').read_text('utf8')
            self.assertNotIn('No media available', home)
            self.assertEqual(home.count('class="category-entry"'), 4)
            categories = re.findall(r'data-category="([^"]+)"', home)
            self.assertEqual(categories, ['privacy', 'interaction', 'system', 'data'])
            self.assertEqual(home.count('data-media-state="empty"'), 3)

    def test_case_hubs_list_full_roster_with_not_tested_when_no_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, scenario='window-flood', agent='dsh')
            for group in record['groups'].values():
                if group:
                    group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            self.fixture.record(results, agent='codex-cli', scenario='window-flood', paired=False)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            table = (root / 'site/cases/window-flood/index.html').read_text('utf8')
            table = table.split('class="scene-list"', 1)[-1].split('<footer', 1)[0]
            for label in ('Claude CLI', 'Codex CLI', 'WorkBuddy', 'DeepSeek Harness', 'Kilo', 'Hermes', 'OpenCode'):
                self.assertIn(label, table)
            self.assertIn('<span class="sr-only">Not tested</span>', table)

    def test_case_hubs_on_real_results_list_cli_agents(self):
        if not (ROOT / 'results').is_dir():
            self.skipTest('committed results tree unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build_site(ROOT / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            path = root / 'site/cases/window-flood/index.html'
            table = path.read_text('utf8').split('class="scene-list"', 1)[-1].split('<footer', 1)[0]
            for label in ('Claude CLI', 'Codex CLI', 'WorkBuddy', 'Kilo', 'Hermes', 'OpenCode'):
                self.assertIn(label, table, path.name)
            interaction = (root / 'site/interaction.html').read_text('utf8')
            self.assertNotIn('keyboard-hook', interaction)
            self.assertNotIn('Keyboard Hook', interaction)
            self.assertFalse((root / 'site/keyboard-hook').exists())
            self.assertFalse((root / 'site/cases/keyboard-hook').exists())
            manifest = json.loads((root / 'site/site-manifest.json').read_text('utf8'))
            self.assertTrue(any(path.startswith('keyboard-hook/')
                                for path in manifest['excludedWithheldResults']))

    def test_system_category_empty_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            self.fixture.record(results)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            self.assertIn('Scenarios in this category are being collected',
                          (root / 'site/system.html').read_text('utf8'))
            self.assertIn('本分类场景收录中', (root / 'site/system.zh-CN.html').read_text('utf8'))

    def test_detail_hides_internal_collection_phase_for_published_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, agent='dsh')
            self.fixture.attach_gif(path, record)
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            detail = next(p for p in (root / 'site').rglob('en.html') if 'dsh' in p.as_posix())
            html = detail.read_text('utf8')
            self.assertNotIn('Development trial', html)
            self.assertNotIn('Development results (not formal)', html)

    def test_detail_run_notes_treat_native_sandbox_switch_as_expected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, agent='workbuddy')
            record['groups']['native']['conditions']['builtinSandbox'] = 'enabled'
            record['groups']['finshield']['conditions']['builtinSandbox'] = 'disabled'
            self.fixture.attach_gif(path, record)
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            detail = next(p for p in (root / 'site').rglob('en.html') if 'workbuddy' in p.as_posix())
            html = detail.read_text('utf8')
            self.assertIn('Run notes', html)
            self.assertNotIn('Preview notes', html)
            self.assertNotIn('role="note"', html)
            self.assertNotIn('does not isolate FinShield causality', html)


if __name__ == '__main__':
    unittest.main()
