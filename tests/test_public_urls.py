"""Public routes must work on a plain static host without losing old evidence."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit, unquote
from xml.etree import ElementTree as ET

from arena.reporting.site import build_site
from tests import test_evaluation_overview as fixtures
from tests.test_search_discovery import Head, HOST


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src', 'poster') and value:
                self.urls.append((tag, key, value))


class PublicURLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        fixture = fixtures.EvaluationOverviewTests()
        cls.source, record = fixture.record(cls.root / 'results', scenario='camera-capture', agent='dsh')
        cls.media = fixture.attach_gif(cls.source, record)
        fixture.record(cls.root / 'results', scenario='sample-only', origin='synthetic')
        cls.site = cls.root / 'site'
        build_site(cls.root / 'results', cls.site)

    def test_publishes_bilingual_directory_routes_with_matching_identity(self):
        for route in ('', 'privacy/', 'articles/', 'articles/guide/', 'articles/agent-sandbox/',
                      'methodology/', 'agents/dsh/', 'cases/camera-capture/',
                      'results/camera-capture/dsh/paired/'):
            for prefix, language in (('', 'en'), ('zh-cn/', 'zh-CN')):
                with self.subTest(route=prefix + route):
                    path = self.site / prefix / route / 'index.html'
                    self.assertTrue(path.is_file(), str(path))
                    html = path.read_text('utf8')
                    head = Head(html)
                    url = HOST + '/' + prefix + route
                    self.assertEqual(head.canonical(), [url])
                    self.assertEqual(head.meta['og:url'], url)
                    alternates = {x['hreflang']: x['href'] for x in head.links if 'hreflang' in x}
                    self.assertEqual(alternates, {'en': HOST + '/' + route, 'zh-CN': HOST + '/zh-cn/' + route})
                    self.assertNotIn('http-equiv="refresh"', html)

    def test_new_page_links_work_under_prefix_without_legacy_html_navigation(self):
        routes_file = self.site / 'site-routes.json'
        self.assertTrue(routes_file.is_file(), 'Build must expose its route map')
        routes = json.loads(routes_file.read_text('utf8'))['routes']
        for route in set(routes.values()):
            html = (self.site / route / 'index.html').read_text('utf8')
            base = 'http://localhost/project/' + route
            for tag, key, link in Links(html).urls:
                if urlsplit(link).scheme or link.startswith('//'):
                    continue
                resolved = urlsplit(urljoin(base, link))
                self.assertTrue(resolved.path.startswith('/project/'), (route, link))
                path = self.site / unquote(resolved.path.removeprefix('/project/'))
                if resolved.path.endswith('/'):
                    path /= 'index.html'
                self.assertTrue(path.is_file(), (route, link, str(path)))
                if tag == 'a' and key == 'href':
                    self.assertFalse(resolved.path.endswith('.html'), (route, link))

    def test_redirects_cover_old_html_and_host_clean_urls_without_chains(self):
        rules = (self.site / '_redirects').read_text('utf8')
        for old, new in [('zh-CN.html', 'zh-cn/'), ('zh-CN', 'zh-cn/'),
                         ('guide.html', 'articles/guide/'), ('guide', 'articles/guide/'),
                         ('camera-capture/dsh/paired/en', 'results/camera-capture/dsh/paired/')]:
            self.assertIn(f'/{old} /{new} 301', rules)
        permanent = dict((parts[0], parts[1]) for line in rules.splitlines()
                         if len(parts := line.split()) == 3 and parts[2] == '301')
        for old, new in permanent.items():
            self.assertNotEqual(old, new)
            self.assertNotIn(new, permanent, (old, new))
        fallback = (self.site / 'guide.html').read_text('utf8')
        self.assertIn('http-equiv="refresh" content="0;url=articles/guide/"', fallback)
        self.assertEqual(Head(fallback).canonical(), [HOST + '/articles/guide/'])
        self.assertNotIn('googlea9662cdfe1496029', rules)

    def test_sitemap_only_contains_final_indexable_routes_and_preserves_hashes(self):
        urls = [node.text for node in ET.parse(self.site / 'sitemap.xml').findall('{*}url/{*}loc')]
        self.assertIn(HOST + '/articles/guide/', urls)
        self.assertIn(HOST + '/zh-cn/results/camera-capture/dsh/paired/', urls)
        self.assertFalse(any('.html' in url or 'sample-only' in url for url in urls))
        self.assertEqual(len(urls), len(set(urls)))
        for url in urls:
            html = (self.site / url.removeprefix(HOST + '/') / 'index.html').read_text('utf8')
            self.assertEqual(Head(html).canonical(), [url])
        for manifest_path in self.site.rglob('*manifest.json'):
            manifest = json.loads(manifest_path.read_text('utf8'))
            for filename, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((manifest_path.parent / filename).read_bytes()).hexdigest(), digest)
        self.assertEqual((self.site / 'camera-capture/dsh/paired/media/comparison.gif').read_bytes(), self.media.read_bytes())
        self.assertEqual((self.site / 'googlea9662cdfe1496029.html').read_bytes(),
                         b'google-site-verification: googlea9662cdfe1496029.html')


class RouteRewriteTests(unittest.TestCase):
    def test_pagination_queries_fragments_assets_and_prose_survive_relocation(self):
        from arena.reporting.routes import PageRewriter, public_route
        self.assertEqual(public_route('privacy-2.zh-CN.html'), 'zh-cn/privacy/page/2/')
        html = ('<html><head><link rel="canonical" href="https://safety.finaios.ai/guide.html">'
                '<script type="application/ld+json">{"mainEntityOfPage":"https://safety.finaios.ai/guide.html"}</script>'
                '</head><body><a href="privacy.html?q=one&amp;x=two#proof">Read</a>'
                '<a href="https://safety.finaios.ai/zh-CN.html#top">中文</a>'
                '<img src="media/test.gif"><a href="https://example.org/a.html">External</a>'
                '<code>href="privacy.html"</code></body></html>')
        result = PageRewriter(html, 'guide.html', 'articles/guide/index.html',
                              {'guide.html': 'articles/guide/', 'privacy.html': 'privacy/',
                               'zh-CN.html': 'zh-cn/'}).render()
        self.assertIn('href="../../privacy/?q=one&amp;x=two#proof"', result)
        self.assertIn('href="../../zh-cn/#top"', result)
        self.assertIn('src="../../media/test.gif"', result)
        self.assertIn('"mainEntityOfPage": "https://safety.finaios.ai/articles/guide/"', result)
        self.assertIn('href="https://example.org/a.html"', result)
        self.assertIn('<code>href="privacy.html"</code>', result)

    def test_ambiguous_routes_and_missing_canonical_pages_fail(self):
        from arena.reporting.routes import publish_routes
        for broken in ('collision', 'missing'):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / '_redirects').write_text('')
                (root / 'privacy.html').write_text('<html><head><link rel="canonical" href="'
                    + HOST + ('/privacy.html' if broken == 'collision' else '/absent.html') + '"></head></html>')
                if broken == 'collision':
                    (root / 'privacy').mkdir()
                    (root / 'privacy/index.html').write_text((root / 'privacy.html').read_text())
                with self.assertRaisesRegex(ValueError, 'Ambiguous public route|Missing canonical page'):
                    publish_routes(root)
