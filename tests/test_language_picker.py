"""Language controls must open real equivalents without changing evidence."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urljoin, urlsplit

from arena.reporting.bilingual import export_reports
from arena.reporting.site import build_site
from tests import test_evaluation_overview as fixtures


class Picker(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.options = {}
        self.assets = []
        self.pickers = 0
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'details' and 'language-picker' in attrs.get('class', '').split():
            self.pickers += 1
        if 'data-language' in attrs:
            self.options[attrs['data-language']] = (tag, attrs)
        if tag == 'script' and attrs.get('src', '').split('?')[0].endswith('language.js'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('href', '').split('?')[0].endswith('language.css'):
            self.assets.append(attrs['href'])


class LanguagePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        fixture = fixtures.EvaluationOverviewTests()
        cls.source, record = fixture.record(cls.root / 'results', scenario='camera-capture', agent='dsh')
        cls.media = fixture.attach_gif(cls.source, record)
        cls.source_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()
        cls.site = cls.root / 'site'
        build_site(cls.root / 'results', cls.site)
        export_reports(cls.source, cls.root / 'standalone')

    def resolve(self, source, href):
        base = 'http://localhost/project/' + source
        path = unquote(urlsplit(urljoin(base, href)).path)
        self.assertTrue(path.startswith('/project/'), (source, href))
        relative = path.removeprefix('/project/')
        target = self.site / relative
        return target / 'index.html' if path.endswith('/') else target

    def test_shared_dropdown_lists_eight_languages_and_only_published_destinations(self):
        order = ['en', 'zh-CN', 'es', 'ar', 'fr', 'pt-BR', 'ja', 'ko']
        for language, prefix in [('en', ''), ('zh-CN', 'zh-cn/')]:
            for route in ['', 'privacy/', 'articles/', 'articles/guide/',
                          'methodology/', 'agents/dsh/', 'agents/dsh/privacy/',
                          'cases/camera-capture/', 'results/camera-capture/dsh/paired/']:
                with self.subTest(language=language, route=route):
                    source = prefix + route + 'index.html'
                    picker = Picker((self.site / source).read_text('utf8'))
                    self.assertEqual(picker.pickers, 1, 'Every public page needs the shared language dropdown')
                    self.assertEqual(list(picker.options), order)
                    for locale, (tag, attrs) in picker.options.items():
                        if locale in ('en', 'zh-CN'):
                            self.assertEqual(tag, 'a')
                            self.assertTrue(self.resolve(source, attrs['href']).is_file())
                            if locale != language:
                                expected = ('' if locale == 'en' else 'zh-cn/') + route + 'index.html'
                                self.assertEqual(self.resolve(source, attrs['href']), self.site / expected)
                        else:
                            self.assertEqual(attrs.get('aria-disabled'), 'true')
                            self.assertNotIn('href', attrs)
                    self.assertEqual(picker.options[language][1].get('aria-current'), 'true')

    def test_first_party_assets_resolve_under_a_prefix_and_keep_csp_narrow(self):
        for route in ['index.html', 'zh-cn/articles/guide/index.html',
                      'results/camera-capture/dsh/paired/index.html',
                      'camera-capture/dsh/paired/index.html']:
            html = (self.site / route).read_text('utf8')
            picker = Picker(html)
            self.assertEqual(len(picker.assets), 2, 'Pages need one stylesheet and one preference script')
            for href in picker.assets:
                self.assertTrue(self.resolve(route, href).is_file(), (route, href))
            self.assertIn("script-src 'self'", html)
            self.assertNotIn("'unsafe-inline'", html)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_hash)
        manifest = json.loads((self.site / 'site-manifest.json').read_text('utf8'))
        self.assertEqual(manifest['trialExecutions'], 0)
        self.assertEqual((self.site / 'camera-capture/dsh/paired/media/comparison.gif').read_bytes(), self.media.read_bytes())

    def test_automatic_entry_has_real_no_script_links_and_is_not_indexed(self):
        entry = self.site / 'visit/index.html'
        self.assertTrue(entry.is_file(), 'Static builds need a usable automatic-language entry')
        html = entry.read_text('utf8')
        self.assertIn('data-language-entry', html)
        self.assertIn('noindex,follow', html)
        self.assertNotIn('rel="canonical"', html)
        self.assertNotIn('/visit/', (self.site / 'sitemap.xml').read_text('utf8'))
        for _, attrs in Picker(html).options.values():
            if 'href' in attrs:
                self.assertTrue(self.resolve('visit/index.html', attrs['href']).is_file())

    def test_standalone_reports_keep_local_language_navigation_and_assets(self):
        for language in ('en', 'zh-CN'):
            html = (self.root / 'standalone' / (language + '.html')).read_text('utf8')
            picker = Picker(html)
            self.assertEqual(picker.pickers, 1)
            self.assertEqual(len(picker.assets), 2)
            for href in picker.assets:
                self.assertTrue((self.root / 'standalone' / href.split('?')[0]).is_file())
            self.assertNotIn('../../../', html)
            for locale in ('en', 'zh-CN'):
                _, attrs = picker.options[locale]
                if locale != language:
                    self.assertEqual(attrs['href'], locale + '.html')


if __name__ == '__main__':
    unittest.main()
