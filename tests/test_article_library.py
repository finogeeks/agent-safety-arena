"""The article directory distinguishes published reading from planned topics."""
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site
from arena.reporting.guide import load_guide, render_guide


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href', ''))


class ArticleLibraryTests(unittest.TestCase):
    def test_article_directory_routes_and_publication_states(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture = fixtures.EvaluationOverviewTests()
            source, _ = fixture.record(root / 'results', scenario='camera-capture', agent='dsh')
            evidence = source.read_bytes()
            site = root / 'site'
            build_site(root / 'results', site, fixtures.ROOT / 'profiles/coverage.json')
            for language, suffix in [('en', ''), ('zh-CN', '.zh-CN')]:
                with self.subTest(language=language):
                    route = 'articles' + suffix + '.html'
                    self.assertTrue((site / route).is_file(), 'Article directory must exist')
                    html = (site / route).read_text('utf8')
                    self.assertIn('CollectionPage', html)
                    public = ('zh-cn/' if suffix else '') + 'articles/'
                    self.assertIn('rel="canonical" href="https://safety.finaios.ai/' + public + '"', html)
                    self.assertIn('href="guide' + suffix + '.html"', html)
                    featured = re.search(r'<article class="featured-article".*?</article>', html, re.S)[0]
                    self.assertIn('href="chrome-windows-sandbox' + suffix + '.html"', featured)
                    self.assertNotIn('href="guide' + suffix + '.html"', featured)
                    cards = re.findall(r'<article class="published-article">.*?</article>', html, re.S)
                    self.assertIn('href="guide' + suffix + '.html"', cards[0])
                    self.assertIn('href="agent-sandbox' + suffix + '.html"', cards[1])
                    self.assertFalse(any('href="chrome-windows-sandbox' + suffix + '.html"' in card for card in cards))
                    self.assertIn('href="methodology' + suffix + '.html"', html)
                    disclosure = re.search(r'<details class="planned-topics">.*?</details>', html, re.S)[0]
                    planned = re.findall(r'<li class="planned-article">.*?</li>', disclosure, re.S)
                    self.assertEqual(len(planned), 4)
                    for item in planned:
                        self.assertNotIn('<a ', item)
                        self.assertNotIn('<time', item)
                    links = Links()
                    links.feed(html)
                    for href in links.hrefs:
                        url = urlsplit(href)
                        if not url.scheme:
                            self.assertTrue((site / url.path).is_file(), href)
                    guide = (site / ('guide' + suffix + '.html')).read_text('utf8')
                    self.assertIn(render_guide(load_guide(), language, '', ''), guide)
                    self.assertIn('href="' + route + '"', guide)
                    home = (site / ('zh-CN.html' if suffix else 'index.html')).read_text('utf8')
                    self.assertEqual(home.count('href="' + (route if suffix else 'articles/') + '"'), 2)
                    self.assertIn('https://safety.finaios.ai/' + public, (site / 'sitemap.xml').read_text('utf8'))
                    self.assertIn(route, (site / 'site-manifest.json').read_text('utf8'))
            self.assertEqual(source.read_bytes(), evidence)
