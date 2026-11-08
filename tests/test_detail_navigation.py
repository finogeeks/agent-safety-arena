"""Full-site detail pages link to real parents without changing evidence."""
import json
from pathlib import Path
import re
import tempfile
import unittest

import test_evaluation_overview as fixtures
from test_evaluation_overview import ROOT, Links
from arena.reporting.bilingual import export_reports
from arena.reporting.site import build_site


class DetailNavigationTests(unittest.TestCase):
    record = fixtures.EvaluationOverviewTests.record
    save = fixtures.EvaluationOverviewTests.save
    attach_gif = fixtures.EvaluationOverviewTests.attach_gif

    def test_bilingual_detail_breadcrumb_and_footer_return_to_existing_parents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.record(root / 'results', scenario='cursor-recenter', agent='dsh')
            self.attach_gif(path, record)
            record['presentation']['dense'] = True
            self.save(path, record)
            before = path.read_bytes()
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            export_reports(path, root / 'standalone')
            report = root / 'site/cursor-recenter/dsh/paired'
            cases = json.loads((root / 'site/catalog.json').read_text('utf8'))['cases']
            case = next(case for case in cases if case['id'] == 'cursor-recenter')
            for language, category, hub, home, label in [
                ('zh-CN', 'interaction.zh-CN.html', 'zh-CN.html', 'zh-CN.html', '返回场景评测'),
                ('en', 'interaction.html', 'index.html', 'index.html', 'Back to scenario'),
            ]:
                with self.subTest(language=language):
                    html = (report / (language + '.html')).read_text('utf8')
                    breadcrumb = re.search(r'<nav class="report-breadcrumb".*?</nav>', html)
                    self.assertIsNotNone(breadcrumb)
                    self.assertLess(breadcrumb.start(), html.index('<div class="hero">'))
                    self.assertIn('href="../../../' + category + '"', breadcrumb.group())
                    case_href = '../../../cases/cursor-recenter/' + hub
                    self.assertEqual(html.count('href="' + case_href + '"'), 2)
                    self.assertIn(case['title'][language], breadcrumb.group())
                    self.assertIn('aria-current="page"', breadcrumb.group())
                    self.assertIn('<a class="brand" href="../../../' + home + '"', html)
                    self.assertGreater(html.index(label), html.index('id="section-6"'))
                    links = Links(); links.feed(html)
                    self.assertTrue(all((report / target).is_file() for target in links.paths))
                    # Navigation must not affect translated reports or original evidence.
                    self.assertEqual((report / (language + '.md')).read_bytes(),
                                     (root / 'standalone' / (language + '.md')).read_bytes())
            self.assertEqual((report / 'evidence.json').read_bytes(), (root / 'standalone/evidence.json').read_bytes())
            self.assertEqual(path.read_bytes(), before)

    def test_navigation_uses_authored_category_and_escapes_localized_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.record(root / 'results', scenario='custom-case', agent='dsh')
            taxonomy = json.loads((ROOT / 'scenarios/catalog.json').read_text('utf8'))
            taxonomy['scenarios']['custom-case'] = dict(category='system',
                title={'en': 'Custom <probe>', 'zh-CN': '自定义<测试>'})
            path = root / 'taxonomy.json'
            path.write_text(json.dumps(taxonomy), encoding='utf8')
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json', path)
            html = (root / 'site/custom-case/dsh/paired/zh-CN.html').read_text('utf8')
            self.assertIn('href="../../../system.zh-CN.html"', html)
            self.assertIn('自定义&lt;测试&gt;', html)
            self.assertNotIn('自定义<测试>', html)

    def test_standalone_report_has_no_links_to_absent_site_parents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.record(root / 'results')
            export_reports(path, root / 'report')
            for language in ('en', 'zh-CN'):
                html = (root / 'report' / (language + '.html')).read_text('utf8')
                self.assertNotIn('class="report-breadcrumb"', html)
                self.assertNotIn('../../../', html)
                self.assertIn('class="brand" href="index.html"', html)


if __name__ == '__main__':
    unittest.main()
