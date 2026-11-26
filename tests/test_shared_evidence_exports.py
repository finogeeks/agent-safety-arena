"""Canonical Markdown shares originals without changing human evidence or downloads."""
from html import escape
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.reporting.machine_readable import write_machine_readable


class SharedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.text = 'Original warning: controlled resource. <literal> `code` 中文\n' * 20

    def page(self, route, language='en', body=None):
        path = self.root / route / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        html = ('<html lang="' + language + '"><head><title>Fixture</title>'
                '<link rel="canonical" href="https://safety.finaios.ai/' + route + '"></head>'
                '<body><main><h1>Fixture</h1><p>Conditions and findings.</p>'
                + (body if body is not None else '<pre id="reply-native">' + escape(self.text) + '</pre>')
                + '</main></body></html>')
        path.write_text(html, encoding='utf8')
        return path

    def manifest(self):
        return json.loads((self.root / 'text-evidence-manifest.json').read_text('utf8'))

    def test_language_exports_reference_one_exact_shared_payload(self):
        a = self.page('results/fixture/')
        b = self.page('zh-cn/results/fixture/', 'zh-CN')
        write_machine_readable(self.root, {'a.html': 'results/fixture/', 'b.html': 'zh-cn/results/fixture/'})
        files = list((self.root / 'evidence-text').glob('*.txt'))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_text('utf8'), self.text)
        for html in (a, b):
            md = html.with_suffix('.md').read_text('utf8')
            self.assertIn('Conditions and findings.', md)
            self.assertNotIn(self.text, md)
            self.assertIn('https://safety.finaios.ai/evidence-text/', md)
            self.assertIn(escape(self.text), html.read_text('utf8'))
        self.assertEqual(len(self.manifest()['texts']), 1)
        self.assertEqual(self.manifest()['files'][files[0].relative_to(self.root).as_posix()],
                         hashlib.sha256(files[0].read_bytes()).hexdigest())
        self.assertEqual(len(self.manifest()['references']), 2)
        self.assertIn('/text-evidence-manifest.json', (self.root / 'llms.txt').read_text('utf8'))

    def test_existing_original_download_is_reused_byte_for_byte(self):
        source = self.root / 'case/agent/pair/native-tools.txt'
        source.parent.mkdir(parents=True)
        original = self.text.rstrip('\n').replace('\n', '\r\n').encode('utf8')
        source.write_bytes(original)
        self.page('', body='<pre>' + escape(self.text) + '</pre><pre>literal()</pre>'
                  '<a href="case/agent/pair/native-tools.txt" download>Tool log</a>')
        write_machine_readable(self.root, {'index.html': ''})
        self.assertEqual(source.read_bytes(), original)
        md = (self.root / 'index.md').read_text('utf8')
        self.assertIn('/case/agent/pair/native-tools.txt', md)
        self.assertIn('literal()', md)
        self.assertFalse(list((self.root / 'evidence-text').glob('*.txt')))
        item = next(iter(self.manifest()['texts'].values()))
        self.assertEqual(item['sha256'], hashlib.sha256(original).hexdigest())

    def test_legacy_reports_become_pointers_while_notes_and_downloads_stay(self):
        old = self.root / 'case/agent/pair'
        old.mkdir(parents=True)
        for name in ('en.md', 'zh-CN.md'):
            (old / name).write_text('Redundant full export\n' * 100, encoding='utf8')
        note = old / 'native-editing-notes.md'
        note.write_bytes(b'Original reviewed offsets and provenance.\n')
        self.page('results/case/agent/pair/')
        self.page('zh-cn/results/case/agent/pair/', 'zh-CN')
        routes = {'case/agent/pair/en.html': 'results/case/agent/pair/',
                  'case/agent/pair/zh-CN.html': 'zh-cn/results/case/agent/pair/'}
        write_machine_readable(self.root, routes)
        self.assertLess((old / 'en.md').stat().st_size, 1024)
        self.assertIn('/results/case/agent/pair/index.md', (old / 'en.md').read_text('utf8'))
        self.assertIn('/zh-cn/results/case/agent/pair/index.md', (old / 'zh-CN.md').read_text('utf8'))
        self.assertEqual(note.read_bytes(), b'Original reviewed offsets and provenance.\n')

    def test_article_markdown_link_uses_its_current_language(self):
        for name in ('demo.en.md', 'demo.zh-CN.md'):
            (self.root / name).write_text('Original source export\n' * 100)
        self.page('articles/demo/')
        self.page('zh-cn/articles/demo/', 'zh-CN')
        french = self.page('fr/articles/demo/', 'fr', '<a href="../../../demo.en.md">Markdown</a>')
        manifest = {'published': {'fr': ['articles/demo/']}, 'files': {'fr/articles/demo/index.html': 'old'}}
        (self.root / 'translation-manifest.json').write_text(json.dumps(manifest))
        write_machine_readable(self.root, {'demo.html': 'articles/demo/', 'demo.zh-CN.html': 'zh-cn/articles/demo/'})
        self.assertIn('href="index.md"', french.read_text('utf8'))
        self.assertIn('/fr/articles/demo/index.md', french.with_suffix('.md').read_text('utf8'))
        refreshed = json.loads((self.root / 'translation-manifest.json').read_text('utf8'))
        self.assertEqual(refreshed['files']['fr/articles/demo/index.html'], hashlib.sha256(french.read_bytes()).hexdigest())

    def test_repeat_export_keeps_bytes_and_discovery_tags_stable(self):
        page = self.page('')
        routes = {'index.html': ''}
        write_machine_readable(self.root, routes)
        tracked = ['index.md', 'index.html', 'llms.txt', 'text-evidence-manifest.json']
        first = {name: (self.root / name).read_bytes() for name in tracked}
        write_machine_readable(self.root, routes)
        self.assertEqual(first, {name: (self.root / name).read_bytes() for name in tracked})
        self.assertEqual(page.read_text('utf8').count('type="text/markdown"'), 1)

    def test_shared_text_collision_is_rejected_without_overwrite(self):
        key = hashlib.sha256(self.text.encode('utf8')).hexdigest()
        target = self.root / 'evidence-text' / (key + '.txt')
        target.parent.mkdir()
        target.write_bytes(b'Preserve this existing file')
        self.page('')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            write_machine_readable(self.root, {'index.html': ''})
        self.assertEqual(target.read_bytes(), b'Preserve this existing file')

    def test_legacy_export_hashes_are_refreshed_without_changing_source_identity(self):
        old = self.root / 'case/agent/pair'
        old.mkdir(parents=True)
        (old / 'en.md').write_text('Full report\n' * 100)
        (old / 'export-manifest.json').write_text(json.dumps({'sourceRecordSha256': 'preserve', 'files': {'en.md': 'old'}}))
        self.page('results/case/agent/pair/')
        write_machine_readable(self.root, {'case/agent/pair/en.html': 'results/case/agent/pair/'})
        result = json.loads((old / 'export-manifest.json').read_text('utf8'))
        self.assertEqual(result['sourceRecordSha256'], 'preserve')
        self.assertEqual(result['files']['en.md'], hashlib.sha256((old / 'en.md').read_bytes()).hexdigest())
