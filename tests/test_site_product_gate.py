"""Product gate labels, roster filtering, and footer on the public site build."""
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

    def test_development_phase_label_on_home_and_scored_cells(self):
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
            self.assertIn('Development results (not formal)', home)
            self.assertGreaterEqual(home.count('class="phase-label"'), 2)
            self.assertIn('https://finaios.ai', home)
            self.assertIn('FinAI OS', home)

    def test_workbuddy_mismatch_excluded_from_home_scores(self):
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
            self.assertNotIn('data-score-agent="workbuddy"', home)
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            scores = catalog['scores']['development']['agents'].get('workbuddy', {})
            self.assertEqual(scores.get('native', {}).get('denominator'), 0)

    def test_untested_roster_agents_hidden_and_codex_archived(self):
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
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            home = (root / 'site/index.html').read_text('utf8')
            self.assertNotIn('data-score-agent="claude-cli"', home)
            self.assertNotIn('data-score-agent="opencode-cli"', home)
            main_scores = home.split('id="agent-scores"', 1)[1].split('agent-archive', 1)[0]
            self.assertNotIn('data-score-agent="codex-cli"', main_scores)
            self.assertIn('agent-archive', home)
            self.assertIn('data-score-agent="codex-cli"', home.split('agent-archive', 1)[1])

    def test_showcase_omits_empty_categories_and_no_media_copy(self):
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
            categories = re.findall(r'data-category="([^"]+)"', home)
            self.assertEqual(categories, ['privacy'])

    def test_case_hubs_omit_unpaired_roster_agents_and_not_tested_badges(self):
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
            for path in (root / 'site/cases').rglob('index.html'):
                table = path.read_text('utf8').split('class="case-table"', 1)[-1].split('</table>', 1)[0]
                for label in ('Claude CLI', 'OpenCode CLI', 'Codex CLI', 'WorkBuddy'):
                    self.assertNotIn(label, table, path.name)
                self.assertNotIn('Not tested', table, path.name)
                self.assertNotIn('未测试', table, path.name)

    def test_case_hub_lists_only_assessed_agents_on_real_results(self):
        site = ROOT / 'results'
        if not site.is_dir():
            self.skipTest('committed results tree unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build_site(ROOT / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            hubs = list((root / 'site/cases').glob('*/index.html'))
            self.assertGreaterEqual(len(hubs), 16)
            for path in hubs:
                html = path.read_text('utf8')
                table = html.split('class="case-table"', 1)[-1].split('</table>', 1)[0]
                for label in ('Claude CLI', 'OpenCode CLI', 'Codex CLI'):
                    self.assertNotIn(label, table, path.name)
                self.assertNotIn('Not tested', table, path.name)

    def test_system_category_empty_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            self.fixture.record(results)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            self.assertIn('Scenarios in this category are being collected',
                          (root / 'site/system.html').read_text('utf8'))
            self.assertIn('本分类场景收录中', (root / 'site/system.zh-CN.html').read_text('utf8'))

    def test_detail_shows_development_phase_beside_track(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            path, record = self.fixture.record(results, agent='dsh')
            self.fixture.attach_gif(path, record)
            self.fixture.save(path, record)
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            detail = next(p for p in (root / 'site').rglob('en.html') if 'dsh' in p.as_posix())
            html = detail.read_text('utf8')
            self.assertIn('Development trial', html)
            self.assertIn('Development results (not formal)', html)

    def test_detail_run_notes_and_condition_banner(self):
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
            self.assertIn('condition-banner', html)
            self.assertIn('does not isolate FinShield causality', html)


if __name__ == '__main__':
    unittest.main()
