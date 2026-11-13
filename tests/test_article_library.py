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
                    self.assertIn('rel="canonical" href="https://safety.finaios.ai/' + route, html)
                    self.assertIn('href="guide' + suffix + '.html"', html)
                    self.assertIn('href="methodology' + suffix + '.html"', html)
                    planned = re.findall(r'<article class="planned-article">.*?</article>', html, re.S)
                    self.assertEqual(len(planned), 4)
                    for item in planned:
                        self.assertIn('计划中' if language == 'zh-CN' else 'Planned', item)
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
                    self.assertEqual(home.count('href="' + route + '"'), 2)
                    self.assertIn(route, (site / 'sitemap.xml').read_text('utf8'))
                    self.assertIn(route, (site / 'site-manifest.json').read_text('utf8'))
            self.assertEqual(source.read_bytes(), evidence)
