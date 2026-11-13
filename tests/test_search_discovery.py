"""Search identities and summaries must match the same reviewed evidence."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site
from arena.reporting.bilingual import export_reports

HOST = 'https://safety.finaios.ai'


class Head(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.meta = {}
        self.feed(html.split('</head>')[0])

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'link':
            self.links.append(values)
        if tag == 'meta':
            self.meta[values.get('name', values.get('property'))] = values.get('content')

    def canonical(self):
        return [x['href'] for x in self.links if x.get('rel') == 'canonical']


class SearchDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = fixtures.EvaluationOverviewTests()
        self.source, self.record = self.fixture.record(self.root / 'results', scenario='camera-capture', agent='dsh')
        self.fixture.attach_gif(self.source, self.record)
        for group in self.record['groups'].values():
            group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
        self.fixture.save(self.source, self.record)
        self.fixture.record(self.root / 'results', scenario='sample-only', origin='synthetic')
        self.original = self.source.read_bytes()
        self.site = self.root / 'site'
        build_site(self.root / 'results', self.site)

    def html(self, route):
        return (self.site / route).read_text('utf8')

    def test_canonical_pairs_cover_home_categories_agents_cases_and_details(self):
        for en, zh in [('index.html', 'zh-CN.html'), ('privacy.html', 'privacy.zh-CN.html'),
                       ('agents/dsh/index.html', 'agents/dsh/zh-CN.html'),
                       ('cases/camera-capture/index.html', 'cases/camera-capture/zh-CN.html'),
                       ('camera-capture/dsh/paired/en.html', 'camera-capture/dsh/paired/zh-CN.html'),
                       ('guide.html', 'guide.zh-CN.html'), ('methodology.html', 'methodology.zh-CN.html')]:
            for language, route in [('en', en), ('zh-CN', zh)]:
                with self.subTest(route=route):
                    html = self.html(route)
                    head = Head(html)
                    self.assertEqual(head.canonical(), [HOST + '/' + route])
                    self.assertTrue(head.meta.get('description'))
                    self.assertEqual(head.meta['og:url'], HOST + '/' + route)
                    alternates = {x['hreflang']: x['href'] for x in head.links if 'hreflang' in x}
                    self.assertEqual(alternates['en'], HOST + '/' + en)
                    self.assertEqual(alternates['zh-CN'], HOST + '/' + zh)
                    schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])
                    self.assertEqual(schema['inLanguage'], language)
                    self.assertNotIn('aggregateRating', schema)
                    self.assertNotIn('datePublished', schema)
        self.assertEqual(Head(self.html('en.html')).canonical(), [HOST + '/index.html'])
        self.assertEqual(Head(self.html('agents/dsh/privacy.html')).canonical(), [HOST + '/agents/dsh/index.html'])

    def test_sitemap_only_lists_indexable_canonical_pages_and_is_manifested(self):
        path = self.site / 'sitemap.xml'
        self.assertTrue(path.exists(), 'The build must provide a canonical sitemap')
        tree = ET.fromstring(path.read_text('utf8'))
        urls = [node.text for node in tree.findall('{*}url/{*}loc')]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn(HOST + '/camera-capture/dsh/paired/en.html', urls)
        self.assertIn(HOST + '/cases/camera-capture/zh-CN.html', urls)
        self.assertNotIn(HOST + '/en.html', urls)
        self.assertNotIn(HOST + '/agents/dsh/privacy.html', urls)
        self.assertFalse(any('sample-only' in url or '404' in url for url in urls))
        self.assertFalse(tree.findall('{*}url/{*}lastmod'), 'Do not fake content dates using build time')
        for url in urls:
            route = url.removeprefix(HOST + '/')
            self.assertEqual(Head(self.html(route)).canonical(), [url])
        manifest = json.loads((self.site / 'site-manifest.json').read_text('utf8'))
        self.assertEqual(manifest['files']['sitemap.xml'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIn('robots.txt', manifest['files'])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_robots_allows_search_bots_without_changing_training_policy(self):
        path = self.site / 'robots.txt'
        self.assertTrue(path.exists(), 'Public crawl policy must be included in the artifact')
        parser = RobotFileParser()
        parser.parse(path.read_text('utf8').splitlines())
        for bot in ('Googlebot', 'bingbot', 'Baiduspider', 'OAI-SearchBot', 'Claude-SearchBot', 'PerplexityBot', 'GPTBot'):
            self.assertTrue(parser.can_fetch(bot, HOST + '/zh-CN.html'), bot)
        self.assertEqual(parser.site_maps(), [HOST + '/sitemap.xml'])

    def test_current_findings_and_visible_caption_use_catalog_not_fixed_claims(self):
        guide = self.html('guide.html')
        self.assertIn('current-findings', guide)
        self.assertIn('0/1', guide)
        self.assertIn('1/1', guide)
        self.assertIn('href="agents/dsh/index.html"', guide)
        self.assertIn('also develops FinShield', guide)
        self.assertIn('real executions', guide)
        self.assertIn('href="methodology.html"', guide)
        home = self.html('zh-CN.html')
        self.assertIn('公开测评', home)
        self.assertIn('AI Agent', home)
        self.assertIn('showcase-caption', home)
        self.assertIn('内置防护：未拦截', home)
        # A changed assessed outcome must update article figures on the next build.
        self.record['groups']['native']['interceptionAssessment'] = self.record['groups']['finshield']['interceptionAssessment']
        self.fixture.save(self.source, self.record)
        build_site(self.root / 'results', self.root / 'updated')
        changed = (self.root / 'updated/guide.html').read_text('utf8')
        summary = re.search(r'<aside class="current-findings".*?</aside>', changed, re.S)[0]
        self.assertNotIn('0/1', summary)
        self.assertIn('1/1', summary)

    def test_detail_scope_is_visible_and_standalone_has_no_invented_url(self):
        detail = self.html('camera-capture/dsh/paired/en.html')
        self.assertRegex(detail, r'class="[^"]*\bevaluation-scope\b')
        self.assertIn('recorded approvals', detail)
        self.assertIn('<title>Controlled deletion &lt;fixture&gt; · Agent Safety Arena</title>', detail)
        self.assertIn('recorded approvals', Head(detail).meta['description'])
        export_reports(self.source, self.root / 'standalone')
        self.assertEqual(Head((self.root / 'standalone/en.html').read_text('utf8')).canonical(), [])
        packet = self.site / 'camera-capture/dsh/paired/evidence.json'
        standalone = self.root / 'standalone/evidence.json'
        self.assertEqual(packet.read_bytes(), standalone.read_bytes())

    def test_public_pages_welcome_citations_with_real_permanent_evidence_links(self):
        guide = self.html('guide.zh-CN.html')
        self.assertIn('id="cite"', guide)
        self.assertIn('欢迎读者、研究者和AI搜索引用', guide)
        detail = self.html('camera-capture/dsh/paired/en.html')
        citation = re.search(r'<p class="citation".*?</p>', detail, re.S)
        self.assertIsNotNone(citation, 'Every published comparison needs a citation link')
        self.assertIn('href="' + HOST + '/camera-capture/dsh/paired/en.html"', citation[0])
        self.assertIn('href="evidence.json"', citation[0])
        self.assertNotIn('noindex', detail)
        self.assertNotIn('nosnippet', detail)

    def test_page_metadata_escapes_markup_and_pagination_keeps_its_identity(self):
        from arena.reporting.search import page_head
        title = 'Test </script><img src=x>'
        head = page_head(title, 'A "quoted" result <unsafe>', 'en',
                         {'en':'privacy-2.html', 'zh-CN':'privacy-2.zh-CN.html'})
        self.assertNotIn('</script><img', head)
        self.assertEqual(Head(head).canonical(), [HOST + '/privacy-2.html'])
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', head)[1])
        self.assertEqual(schema['name'], title)


if __name__ == '__main__':
    unittest.main()
