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
                ('index.html', 'Agent built-in sandbox', 'Default protection'),
                ('zh-CN.html', 'Agent内置沙箱', '默认防护'),
                ('interaction.html', 'Agent built-in sandbox', 'Default protection'),
                ('interaction.zh-CN.html', 'Agent内置沙箱', '默认防护'),
                ('cases/window-flood/index.html', 'Agent built-in sandbox', 'Default protection'),
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

    def test_recorded_agents_visible_and_only_unrecorded_roster_entries_folded(self):
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
            for route in ('index.html', 'zh-CN.html'):
                home = (root / 'site' / route).read_text('utf8')
                self.assertIn('<details class="unrecorded-agents">', home)
                visible, folded = home.split('<details class="unrecorded-agents">', 1)
                self.assertEqual(re.findall(r'data-score-agent="([^"]+)"', visible),
                                 ['dsh', 'workbuddy', 'codex-cli'])
                self.assertEqual(re.findall(r'<h3>([^<]+)</h3>', visible)[-3:],
                                 ['DeepSeek Harness', 'WorkBuddy', 'Codex CLI'])
                self.assertEqual(re.findall(r'data-score-agent="([^"]+)"', folded),
                                 ['claude-cli', 'opencode-cli'])
                for agent in ('claude-cli', 'opencode-cli'):
                    self.assertIn(f'data-score-agent="{agent}"', home, agent)
                self.assertNotIn('<details class="unrecorded-agents" open', home)
                self.assertNotIn('agent-archive', home)
                for card in re.findall(r'<article class="agent-card".*?</article>', home, re.S):
                    self.assertEqual(re.findall(r'class="agent-scope ([^"]+)"', card),
                                     ['overall', 'privacy', 'interaction', 'system', 'data'])
                    self.assertEqual(card.count('data-score-protection='), 10)
                self.assertNotIn('class="phase-label"', home)

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
            self.assertEqual(home.count('class="category-entry"'), 3)
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
            table = table.split('class="case-table"', 1)[-1].split('</table>', 1)[0]
            for label in ('Claude CLI', 'OpenCode CLI', 'Codex CLI', 'WorkBuddy', 'DeepSeek Harness'):
                self.assertIn(label, table)
            self.assertIn('Not tested', table)

    def test_case_hubs_on_real_results_list_cli_agents(self):
        if not (ROOT / 'results').is_dir():
            self.skipTest('committed results tree unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build_site(ROOT / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            path = root / 'site/cases/window-flood/index.html'
            table = path.read_text('utf8').split('class="case-table"', 1)[-1].split('</table>', 1)[0]
            for label in ('Claude CLI', 'OpenCode CLI', 'Codex CLI', 'WorkBuddy'):
                self.assertIn(label, table, path.name)

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
