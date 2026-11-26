"""Stored translations must preserve evidence and fail closed on stale sources."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from arena.reporting import site
from arena.reporting.localization import source_signature


LOCALES = ['es', 'ar', 'fr', 'pt-BR', 'ja', 'ko']


class LocalizationTests(unittest.TestCase):
    def test_source_signatures_ignore_platform_newline_expansion(self):
        unix = '<html><body><pre>one\ntwo</pre></body></html>'
        windows = '<html><body><pre>one\r\r\ntwo</pre></body></html>'
        self.assertEqual(source_signature(unix), source_signature(windows))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalogs = self.root / 'catalogs'
        self.catalogs.mkdir()
        self.source = ('<!doctype html><html lang="en"><head><title>Camera access</title>'
                       '<link rel="canonical" href="https://safety.finaios.ai/cases/camera/">'
                       '<meta name="description" content="Original evidence">'
                       '<meta property="og:locale" content="en_US">'
                       '<script type="application/ld+json">{"@context":"https://schema.org",'
                       '"@type":"WebPage","name":"Camera access","inLanguage":"en"}</script>'
                       '</head><body data-language-home><h1>Camera access</h1><p>Original evidence</p><b>100</b>'
                       '<pre id="reply-native">Original reply: &lt;unsafe&gt; \nKeep exactly.</pre>'
                       '<table class="facts"><tr><td>Original evidence</td><td>never</td><td>Windows 11 Pro</td></tr></table>'
                       '<code>python fixed.py --count 20</code><video src="../../media/trial.mp4"></video>'
                       '</body></html>')
        self.chinese = '<html lang="zh-CN"><body>摄像头访问</body></html>'
        for name, text in [('cases/camera/index.html', self.source), ('zh-cn/cases/camera/index.html', self.chinese)]:
            file = self.root / name
            file.parent.mkdir(parents=True)
            file.write_text(text, encoding='utf8')
        (self.root / 'media').mkdir()
        (self.root / 'media/trial.mp4').write_bytes(b'controlled media fixture')
        self.routes = {'cases/camera/index.html': 'cases/camera/', 'zh-cn/cases/camera/index.html': 'zh-cn/cases/camera/'}
        names = ['Acceso a la cámara', 'الوصول إلى الكاميرا', 'Accès à la caméra', 'Acesso à câmera', 'カメラへのアクセス', '카메라 접근']
        evidence = ['Prueba original', 'الدليل الأصلي', 'Preuve originale', 'Evidência original', '元の証拠', '원본 증거']
        for language, title, note in zip(LOCALES, names, evidence):
            data = dict(schemaVersion=1, language=language, sourceLanguage='en', masterLanguage='zh-CN',
                        method='controlled test translations', messages={'Camera access': title, 'Original evidence': note},
                        pages={'cases/camera/': dict(englishSha256=hashlib.sha256(self.source.encode()).hexdigest(),
                              chineseSha256=hashlib.sha256(self.chinese.encode()).hexdigest())})
            (self.catalogs / (language + '.json')).write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')

    def publish(self):
        self.assertTrue(hasattr(site, 'localize_site'), 'The shared builder must publish stored locale editions')
        return site.localize_site(self.root, self.routes, catalog_root=self.catalogs)

    def test_six_editions_translate_prose_metadata_and_preserve_originals_and_media(self):
        result = self.publish()
        for language in LOCALES:
            prefix = language.lower()
            path = self.root / prefix / 'cases/camera/index.html'
            self.assertTrue(path.is_file(), language)
            html = path.read_text('utf8')
            self.assertIn(f'lang="{language}"', html)
            self.assertNotIn('data-language-home', html)
            self.assertIn(f'https://safety.finaios.ai/{prefix}/cases/camera/', html)
            self.assertNotIn('<h1>Camera access</h1>', html)
            self.assertIn('Original reply: &lt;unsafe&gt; \nKeep exactly.', html)
            self.assertIn('python fixed.py --count 20', html)
            self.assertIn('<b>100</b>', html)
            self.assertIn('<td dir="ltr">never</td><td dir="ltr">Windows 11 Pro</td>', html)
            self.assertIn('../../../media/trial.mp4', html)
            self.assertIn('hreflang="x-default"', html)
            self.assertEqual(len(list((self.root / prefix).rglob('*.mp4'))), 0)
            self.assertEqual(result['published'][language], ['cases/camera/'])
            self.assertEqual(result['files'][prefix+'/cases/camera/index.html'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIn('dir="rtl"', (self.root / 'ar/cases/camera/index.html').read_text('utf8'))

    def test_changed_chinese_invalidates_the_six_pivot_translations(self):
        (self.root / 'zh-cn/cases/camera/index.html').write_text(self.chinese + '更新', encoding='utf8')
        result = self.publish()
        self.assertTrue(all(not result['published'][language] for language in LOCALES))
        self.assertFalse((self.root / 'es/cases/camera/index.html').exists())
        self.assertTrue(any(item['reason'] == 'stale-source' for item in result['unavailable']['es']))

    def test_missing_message_does_not_publish_an_english_fallback_at_a_locale_url(self):
        path = self.catalogs / 'es.json'
        data = json.loads(path.read_text('utf8'))
        del data['messages']['Original evidence']
        path.write_text(json.dumps(data), encoding='utf8')
        result = self.publish()
        self.assertFalse((self.root / 'es/cases/camera/index.html').exists())
        self.assertTrue((self.root / 'fr/cases/camera/index.html').is_file())
        self.assertEqual(result['unavailable']['es'][0]['reason'], 'missing-message')


if __name__ == '__main__':
    unittest.main()
