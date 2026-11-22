"""Search identities and summaries must match the same reviewed evidence."""
import hashlib
from html import unescape
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
        self.coverage = fixtures.ROOT / 'profiles/coverage.json'
        build_site(self.root / 'results', self.site, self.coverage)

    def html(self, route):
        return (self.site / route / 'index.html' if not route or route.endswith('/')
                else self.site / route).read_text('utf8')

    def test_google_verification_preserves_original_bytes_at_site_root(self):
        name = 'googlea9662cdfe1496029.html'
        path = self.site / name
        self.assertTrue(path.is_file(), 'Google verification file missing from site root')
        expected = b'google-site-verification: googlea9662cdfe1496029.html'
        self.assertEqual(path.read_bytes(), expected)
        manifest = json.loads((self.site / 'site-manifest.json').read_text('utf8'))
        self.assertEqual(manifest['files'][name], hashlib.sha256(expected).hexdigest())
        self.assertNotIn(name, (self.site / 'sitemap.xml').read_text('utf8'))

    def test_canonical_pairs_cover_home_categories_agents_cases_and_details(self):
        for en, zh in [('', 'zh-cn/'), ('privacy/', 'zh-cn/privacy/'),
                       ('agents/dsh/', 'zh-cn/agents/dsh/'),
                       ('cases/camera-capture/', 'zh-cn/cases/camera-capture/'),
                       ('results/camera-capture/dsh/paired/', 'zh-cn/results/camera-capture/dsh/paired/'),
                       ('articles/guide/', 'zh-cn/articles/guide/'), ('methodology/', 'zh-cn/methodology/')]:
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
        self.assertEqual(Head(self.html('en.html')).canonical(), [HOST + '/'])
        self.assertEqual(Head(self.html('agents/dsh/privacy.html')).canonical(), [HOST + '/agents/dsh/'])

    def test_sitemap_only_lists_indexable_canonical_pages_and_is_manifested(self):
        path = self.site / 'sitemap.xml'
        self.assertTrue(path.exists(), 'The build must provide a canonical sitemap')
        tree = ET.fromstring(path.read_text('utf8'))
        urls = [node.text for node in tree.findall('{*}url/{*}loc')]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn(HOST + '/results/camera-capture/dsh/paired/', urls)
        self.assertIn(HOST + '/zh-cn/cases/camera-capture/', urls)
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

    def test_search_metadata_preserves_existing_visible_pages(self):
        home = self.html('zh-CN.html').split('<body', 1)[1]
        for added in ('真实执行，检验Windows沙箱', 'showcase-caption', '#cite'):
            self.assertNotIn(added, home)
        guide = self.html('guide.zh-CN.html').split('<body', 1)[1]
        for added in ('guide-disclosure', 'current-findings', 'id="cite"'):
            self.assertNotIn(added, guide)
        detail = self.html('camera-capture/dsh/paired/en.html').split('<body', 1)[1]
        self.assertIn('evaluation-scope', detail)
        self.assertNotIn('class="citation"', detail)

    def test_detail_metadata_and_standalone_have_correct_public_identity(self):
        detail = self.html('camera-capture/dsh/paired/en.html')
        self.assertIn('<title>DeepSeek Harness: Controlled deletion &lt;fixture&gt; · Agent Safety Arena</title>', detail)
        export_reports(self.source, self.root / 'standalone')
        standalone_html = (self.root / 'standalone/en.html').read_text('utf8')
        self.assertEqual(Head(standalone_html).canonical(), [])
        self.assertIn('<title>Controlled deletion &lt;fixture&gt; · Agent Safety Arena</title>', standalone_html)
        self.assertNotIn('evaluation-scope', standalone_html)
        packet = self.site / 'camera-capture/dsh/paired/evidence.json'
        standalone = self.root / 'standalone/evidence.json'
        self.assertEqual(packet.read_bytes(), standalone.read_bytes())

    def test_result_search_identity_distinguishes_agents_without_changing_visible_case_title(self):
        self.fixture.record(self.root / 'results', scenario='camera-capture', agent='workbuddy')
        second_site = self.root / 'more-agents'
        build_site(self.root / 'results', second_site, self.coverage)
        titles = []
        for agent, label in [('dsh', 'DeepSeek Harness'), ('workbuddy', 'WorkBuddy')]:
            for locale in ('', 'zh-cn/'):
                html = (second_site / f'{locale}results/camera-capture/{agent}/paired/index.html').read_text('utf8')
                title = re.search(r'<title>(.*?)</title>', html)[1]
                self.assertIn(label, title)
                self.assertIn('<h1>' + ('受控删除' if locale else 'Controlled deletion') + ' &lt;fixture&gt;</h1>', html)
                head = Head(html)
                self.assertEqual(head.meta['og:title'], unescape(title))
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])
                self.assertTrue(schema['name'].startswith(label))
                self.assertNotIn('<fixture>', html.split('</head>')[0].split('<title>')[1].split('</title>')[0])
                if not locale:
                    titles.append(title)
        self.assertEqual(len(set(titles)), 2)

    def test_result_date_uses_only_the_recorded_test_date(self):
        self.record['presentation']['testedOn'] = {'date': '2026-11-10', 'timezone': 'UTC+08:00'}
        self.fixture.save(self.source, self.record)
        dated_site = self.root / 'dated'
        build_site(self.root / 'results', dated_site, self.coverage)
        dated = (dated_site / 'results/camera-capture/dsh/paired/index.html').read_text('utf8')
        self.assertIn('2026-11-10', re.search(r'<title>(.*?)</title>', dated)[1])
        undated_title = re.search(r'<title>(.*?)</title>', self.html('results/camera-capture/dsh/paired/'))[1]
        self.assertNotRegex(undated_title, r'\d{4}-\d{2}-\d{2}')

    def test_results_explain_scope_and_link_to_methodology_agent_and_original_sections(self):
        for locale, scope in [('', 'Results apply to the recorded conditions and approval decisions.'),
                              ('zh-cn/', '结果仅适用于记录中的条件与批准决定。')]:
            html = self.html(locale + 'results/camera-capture/dsh/paired/')
            note = re.search(r'<p class="evaluation-scope".*?</p>', html, re.S)
            self.assertIsNotNone(note)
            self.assertIn(scope, note[0])
            self.assertIn('href="../../../../methodology/"', note[0])
            self.assertIn('href="#section-2"', note[0])
            self.assertIn('href="#section-6"', note[0])
            self.assertIn('href="../../../../agents/dsh/"', html.split('<body', 1)[1])
            self.assertEqual(re.findall(r'data-section="(\d+)"', html), ['1', '2', '3', '4', '5', '6'])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_untested_agent_pages_and_aliases_are_crawlable_but_not_indexable(self):
        sitemap = (self.site / 'sitemap.xml').read_text('utf8')
        for agent in ('workbuddy', 'kilo', 'hermes', 'opencode-cli'):
            for locale in ('', 'zh-cn/'):
                route = locale + f'agents/{agent}/'
                self.assertEqual(Head(self.html(route)).meta.get('robots'), 'noindex,follow')
                self.assertNotIn(HOST + '/' + route, sitemap)
                category = self.html(route + 'privacy/')
                self.assertEqual(Head(category).meta.get('robots'), 'noindex,follow')
        self.assertNotIn('noindex', Head(self.html('agents/dsh/')).meta.get('robots', ''))
        self.assertIn(HOST + '/agents/dsh/', sitemap)
        robots = RobotFileParser()
        robots.parse((self.site / 'robots.txt').read_text('utf8').splitlines())
        self.assertTrue(robots.can_fetch('Googlebot', HOST + '/agents/kilo/'))

    def test_live_unassessed_out_of_scope_record_restores_agent_indexing_but_synthetic_does_not(self):
        path, record = self.fixture.record(self.root / 'results', scenario='camera-capture', agent='kilo')
        for group in record['groups'].values():
            group.pop('interceptionAssessment', None)
        self.fixture.save(path, record)
        self.fixture.record(self.root / 'results', scenario='camera-capture', agent='hermes', origin='synthetic')
        second_site = self.root / 'eligibility'
        build_site(self.root / 'results', second_site, self.coverage)
        sitemap = (second_site / 'sitemap.xml').read_text('utf8')
        for locale in ('', 'zh-cn/'):
            kilo = (second_site / f'{locale}agents/kilo/index.html').read_text('utf8')
            hermes = (second_site / f'{locale}agents/hermes/index.html').read_text('utf8')
            self.assertNotIn('noindex', Head(kilo).meta.get('robots', ''))
            self.assertIn(HOST + '/' + locale + 'agents/kilo/', sitemap)
            self.assertEqual(Head(hermes).meta.get('robots'), 'noindex,follow')
            self.assertNotIn(HOST + '/' + locale + 'agents/hermes/', sitemap)

    def test_methodology_discloses_maintainer_relationship_scope_and_feedback(self):
        for locale, disclosure, limit in [
            ('', 'The FinAI OS team maintains Agent Safety Arena and also develops FinShield.',
             'Scores describe assessed scenarios, not a guarantee for every configuration.'),
            ('zh-cn/', 'FinAI OS团队维护Agent Safety Arena，也开发FinShield。',
             '成绩描述已评估场景，不保证所有配置都能得到相同结果。'),
        ]:
            html = self.html(locale + 'methodology/')
            self.assertIn(disclosure, html)
            self.assertIn(limit, html)
            self.assertIn('href="https://github.com/finogeeks/agent-safety-arena/issues"', html)
            for route in ('', 'cases/camera-capture/', 'agents/dsh/'):
                page = self.html(locale + route)
                self.assertRegex(page, r'href="(?:\.\./)*methodology/"')

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
