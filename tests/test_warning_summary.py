"""Existing warning evidence stays separate from effect prevention scores."""
import json
from pathlib import Path
import re
import tempfile
import unittest

import test_evaluation_overview as fixtures
from test_evaluation_overview import ROOT
from arena.reporting.site import build_site


class WarningSummaryTests(unittest.TestCase):
    record = fixtures.EvaluationOverviewTests.record
    save = fixtures.EvaluationOverviewTests.save

    def warning_record(self, root, level=None, basis='dialog-wording', identity='paired', model='deepseek-v4-pro'):
        path, record = self.record(root / 'results', scenario='window-flood', agent='dsh', identity=identity)
        for group in record['groups'].values():
            group['conditions'].update(model=model, reasoningEffort='high')
        native = record['groups']['native']
        native['runId'] += '-' + identity
        if level:
            image = path.parent / 'media/native-warning.png'
            image.parent.mkdir(exist_ok=True)
            image.write_bytes(b'controlled original still fixture')
            record['publicMedia'].append(dict(kind='image', path='media/native-warning.png', group='native',
                caption={'en': 'Controlled still.', 'zh-CN': '受控截图。'}))
            native['warningAssessment'] = dict(level=level, basis=basis,
                reason={'en': 'Reviewed fixture warning.', 'zh-CN': '已审阅的测试提示。'},
                evidence=None if level == 'unassessed' else 'media/native-warning.png')
        self.save(path, record)
        return path

    def build(self, root):
        build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
        html = (root / 'site/cases/window-flood/zh-CN.html').read_text('utf8')
        native = re.search(r'<td data-label="Agent内置沙箱">(.*?)</td>', html).group(1)
        protected = re.search(r'<td data-label="FinShield">(.*?)</td>', html).group(1)
        return native, protected, json.loads((root / 'site/catalog.json').read_text('utf8'))

    def test_existing_warning_presence_and_grades_are_visible_without_changing_scores(self):
        for level, basis, label in [
            ('adequate', 'dialog-wording', '告警充分'),
            ('partial', 'dialog-wording', '告警不全'),
            ('insufficient', 'dialog-wording', '告警不足'),
            ('insufficient', 'confirmed-no-warning', '无告警'),
            ('unassessed', 'dialog-wording', None),
            (None, 'dialog-wording', None),
        ]:
            with self.subTest(level=level, basis=basis), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                path = self.warning_record(root, level, basis)
                before = path.read_bytes()
                native, protected, catalog = self.build(root)
                if label:
                    self.assertIn(label, native)
                else:
                    self.assertNotIn('data-warning-level=', native)
                self.assertIn('未拦截', native)
                self.assertIn('无需评估告警', protected)
                detail = (root / 'site' / path.relative_to(root / 'results').parent / 'zh-CN.html').read_text('utf8')
                summary = detail.split('id="section-2"')[1].split('</section>')[0]
                if label:
                    self.assertIn(label, summary)
                else:
                    self.assertNotIn('data-warning-level=', summary)
                self.assertNotRegex(native + summary, '告警待核实|待评估|Pending review')
                self.assertIn('无需评估告警', summary)
                self.assertNotRegex(summary, r'[ABCU] ·|（[ABCU]）')
                visible = summary.split('<details')[0]
                self.assertIn('未拦截', visible)
                if label:
                    self.assertIn(label, visible)
                english = (root / 'site' / path.relative_to(root / 'results').parent / 'en.html').read_text('utf8')
                english_summary = english.split('id="section-2"')[1].split('</section>')[0]
                english_labels = {'告警充分': 'Warning sufficient', '告警不全': 'Warning incomplete',
                                  '告警不足': 'Warning insufficient', '无告警': 'No warning'}
                if label:
                    self.assertIn(english_labels[label], english_summary)
                self.assertNotIn('Pending review', english_summary)
                self.assertIn('Warning review not required', english_summary)
                self.assertNotRegex(english_summary, r'[ABCU] ·|\([ABCU]\)')
                if basis == 'confirmed-no-warning':
                    self.assertIn('warning-absent', native)
                    self.assertIn('warning-absent', summary)
                else:
                    self.assertNotIn('warning-absent', native)
                self.assertEqual(catalog['scores']['development']['cases']['window-flood']['dsh']['native']['rate'], 0)
                self.assertEqual(path.read_bytes(), before)
                if level:
                    self.assertEqual(catalog['reports'][0]['assessments']['native']['warningBasis'], basis)

    def test_repeat_warning_presence_is_not_claimed_for_all_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.warning_record(root, 'adequate', identity='first')
            self.warning_record(root, 'insufficient', 'confirmed-no-warning', identity='second')
            native, _, _ = self.build(root)
            self.assertIn('告警不足', native)
            self.assertNotIn('无告警', native)

    def test_warning_summary_uses_same_model_scope_as_the_scored_item(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.warning_record(root, 'adequate', identity='first')
            self.warning_record(root, 'insufficient', 'confirmed-no-warning', identity='second', model='other-model')
            native, _, _ = self.build(root)
            self.assertIn('告警充分', native)
            self.assertNotIn('无告警', native)

    def test_unknown_repeat_does_not_receive_an_adequate_warning_grade(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.warning_record(root, 'adequate', identity='first')
            self.warning_record(root, identity='second')
            native, _, _ = self.build(root)
            self.assertNotIn('data-warning-level=', native)
            self.assertNotIn('告警充分', native)

    def test_unexposed_effort_keeps_observed_result_and_warning_visible_without_scoring(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = self.warning_record(root, 'unassessed')
            record = json.loads(path.read_text('utf8'))
            for group in record['groups'].values():
                group['conditions']['reasoningEffort'] = 'not-exposed'
            self.save(path, record)
            before = path.read_bytes()
            native, protected, catalog = self.build(root)
            self.assertIn('未拦截', native)
            self.assertNotIn('data-warning-level=', native)
            self.assertIn('推理强度未公开', native)
            self.assertIn('已拦截', protected)
            self.assertIn('无需评估告警', protected)
            score = catalog['scores']['development']['cases']['window-flood']['dsh']['native']
            self.assertEqual(score['denominator'], 0)
            self.assertEqual(score['failed'], 0)
            self.assertEqual(score['excluded'], 1)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
