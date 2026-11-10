"""Published evaluations stay consistent across source collection phases."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site
from arena.reporting.publication import public_record
from copy import deepcopy

ROOT = fixtures.ROOT


class PublishedResultTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationOverviewTests()

    def record(self, results, scenario, *, phase='development', assessed=True):
        path, record = self.fixture.record(results, scenario=scenario, agent='dsh')
        self.fixture.attach_gif(path, record)
        record['phase'] = phase
        for group in record['groups'].values():
            group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            if not assessed:
                group.pop('interceptionAssessment', None)
        self.fixture.save(path, record)
        return path, record

    def test_reviewed_new_case_updates_home_category_hub_and_detail_without_rewriting_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.record(root / 'results', 'microphone-capture', phase='formal')
            path, record = self.record(root / 'results', 'camera-capture')
            before = path.read_bytes()
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            score = catalog['scores'][catalog['scorePhase']]
            self.assertEqual(score['agents']['dsh']['native']['denominator'], 2)
            self.assertEqual(score['categories']['privacy']['dsh']['finshield']['passed'], 2)
            self.assertEqual(catalog['counts']['formalReports'], 2)
            hub = (root / 'site/cases/camera-capture/zh-CN.html').read_text('utf8')
            row = re.search(r'<a class="result-row"[^>]*>.*?DeepSeek Harness.*?</a>', hub, re.S).group()
            self.assertIn('未拦截', row)
            self.assertIn('已拦截', row)
            self.assertNotIn('未测试', row)
            prefix = root / 'site/camera-capture/dsh/paired'
            for language in ('en', 'zh-CN'):
                html = (prefix / (language + '.html')).read_text('utf8')
                self.assertNotIn('class="phase-label"', html)
                self.assertNotIn('Development trial', html)
                self.assertNotIn('开发试录', html)
            evidence = json.loads((prefix / 'evidence.json').read_text('utf8'))
            self.assertEqual(evidence['phase'], 'development')
            self.assertEqual(evidence['groups'], record['groups'])
            self.assertEqual(path.read_bytes(), before)

    def test_home_keeps_gifs_and_compact_category_links_with_new_titles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.record(root / 'results', 'camera-capture')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            for route, title, results, previous in (
                ('zh-CN.html', 'Agent安全测评', '测评结果', '真实测试'),
                ('index.html', 'Agent Safety Evaluation', 'Evaluation results', 'Real tests'),
            ):
                html = (root / 'site' / route).read_text('utf8')
                self.assertIn('<h1>' + title + '</h1>', html)
                self.assertIn('<h2>' + results + '</h2>', html)
                self.assertNotIn(previous, html)
                self.assertIn('class="test-gif"', html)
                self.assertEqual(re.findall(r'data-category="([^"]+)"', html),
                                 ['privacy', 'interaction', 'system', 'data'])
                self.assertNotIn('showcase-blank', html)
                for card in re.findall(r'<article class="test-card"[^>]*data-media-state="empty".*?</article>', html):
                    self.assertIn('class="category-entry"', card)

    def test_recorded_unknown_stays_unassessed_in_publication_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.record(root / 'results', 'camera-capture', phase='formal')
            self.record(root / 'results', 'microphone-capture', assessed=False)
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            score = catalog['scores'][catalog['scorePhase']]['agents']['dsh']['native']
            self.assertEqual((score['denominator'], score['unassessed']), (1, 1))

    def test_synthetic_and_language_studies_do_not_become_public_evaluations(self):
        with tempfile.TemporaryDirectory() as folder:
            _, record = self.record(Path(folder) / 'results', 'camera-capture')
            synthetic = deepcopy(record)
            synthetic['evidenceOrigin'] = 'synthetic'
            study = deepcopy(record)
            study['phase'] = 'language-study'
            self.assertEqual(public_record(synthetic)['phase'], 'development')
            self.assertEqual(public_record(study)['phase'], 'language-study')

    def test_native_sandbox_switch_is_expected_but_model_difference_is_disclosed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.record(root / 'results', 'camera-capture')
            record['groups']['native']['conditions']['builtinSandbox'] = 'enabled'
            record['groups']['finshield']['conditions']['builtinSandbox'] = 'disabled'
            self.fixture.save(path, record)
            build_site(root / 'results', root / 'expected', ROOT / 'profiles/coverage.json')
            detail = Path('camera-capture/dsh/paired/en.html')
            self.assertNotIn('role="note"', (root / 'expected' / detail).read_text('utf8'))
            record['groups']['finshield']['conditions']['model'] = 'other-model'
            self.fixture.save(path, record)
            build_site(root / 'results', root / 'different', ROOT / 'profiles/coverage.json')
            self.assertIn('role="note"', (root / 'different' / detail).read_text('utf8'))


if __name__ == '__main__':
    unittest.main()
