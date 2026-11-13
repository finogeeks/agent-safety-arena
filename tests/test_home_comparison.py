"""The home comparison is opt-in; public evidence remains available."""
from html.parser import HTMLParser
import re
import tempfile
import unittest
from pathlib import Path

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site

ROOT = fixtures.ROOT


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            self.inputs.append(dict(attrs))


class HomeComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        fixture = fixtures.EvaluationOverviewTests()
        path, record = fixture.record(self.root / 'results', scenario='window-flood', agent='dsh')
        self.media = fixture.attach_gif(path, record)
        for group in record['groups'].values():
            group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
        fixture.save(path, record)
        self.source = path
        self.source_bytes = path.read_bytes()
        self.media_bytes = self.media.read_bytes()
        self.site = self.root / 'site'
        build_site(self.root / 'results', self.site, ROOT / 'profiles/coverage.json')

    def test_home_has_unchecked_localized_comparison_and_preserves_evidence(self):
        for route, label in (('index.html', 'Show FinShield comparison'),
                             ('en.html', 'Show FinShield comparison'),
                             ('zh-CN.html', '显示FinShield对照')):
            with self.subTest(route=route):
                html = (self.site / route).read_text('utf8')
                parsed = Inputs()
                parsed.feed(html)
                self.assertEqual(len(parsed.inputs), 1, 'One native comparison checkbox')
                toggle = parsed.inputs[0]
                self.assertEqual(toggle['type'], 'checkbox')
                self.assertEqual(toggle['id'], 'finshield-compare')
                self.assertNotIn('checked', toggle)
                self.assertEqual(toggle['aria-controls'], 'agent-scores real-tests')
                self.assertRegex(html, r'<label[^>]*for="finshield-compare"[^>]*>.*?' + label)
                self.assertIn('home-page', html)
                scripts = re.findall(r'<script([^>]*)>', html)
                self.assertTrue(scripts)
                self.assertTrue(all(attrs == ' type="application/ld+json"' for attrs in scripts))
                self.assertIn("script-src 'none'", html)
                self.assertEqual(html.count('data-score-agent='), 4)
                self.assertEqual(html.count('data-category='), 4)
                self.assertLess(html.index('id="agent-scores"'), html.index('id="real-tests"'))
                self.assertEqual(html.count('class="test-gif"'), 1)
                self.assertIn('native-preview-description', html)
                self.assertIn('comparison-preview-description', html)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertEqual(self.media.read_bytes(), self.media_bytes)
        published = self.site / 'window-flood/dsh/paired/media/comparison.gif'
        self.assertEqual(published.read_bytes(), self.media_bytes)

    def test_footer_removes_utility_links_without_removing_pages_or_header(self):
        for route in ('index.html', 'zh-CN.html', 'guide.html', 'guide.zh-CN.html',
                      'methodology.html', 'interaction.html', 'agents/dsh/index.html'):
            with self.subTest(route=route):
                html = (self.site / route).read_text('utf8')
                footer = re.search(r'<footer>.*?</footer>', html, re.S).group()
                self.assertEqual(re.findall(r'href="([^"]+)"', footer), ['https://finaios.ai'])
                header = re.search(r'<header.*?</header>', html, re.S).group()
                self.assertIn('github.com/finogeeks/agent-safety-arena', header)
                self.assertIn('guide', header)
                if route not in ('index.html', 'zh-CN.html'):
                    self.assertNotIn('id="finshield-compare"', html)
        for filename in ('guide.html', 'guide.zh-CN.html', 'methodology.html',
                         'methodology.zh-CN.html', 'catalog.json', 'site-manifest.json'):
            self.assertTrue((self.site / filename).is_file(), filename)


if __name__ == '__main__':
    unittest.main()
