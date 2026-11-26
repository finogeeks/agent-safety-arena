"""Publication derivatives preserve source evidence and animated presentation."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise unittest.SkipTest('Install the optional site dependency group for image tests')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.reporting import site


class ImageCompressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def optimize(self):
        self.assertTrue(hasattr(site, 'optimize_images'),
                        'The site builder must create verified image derivatives')
        return site.optimize_images(self.root)

    def png(self, name='media/evidence.png', transparent=False):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new('RGBA' if transparent else 'RGB', (640, 240),
                          (255, 255, 255, 0) if transparent else 'white')
        ImageDraw.Draw(image).text((20, 40), 'WARNING: controlled resource. Allow once.', fill='black')
        image.save(path, compress_level=0)
        return path

    def gif(self, loop=None):
        path = self.root / 'media/effect.gif'
        path.parent.mkdir(parents=True, exist_ok=True)
        frames = [Image.new('RGB', (160, 90), color) for color in ['white', 'red', 'white']]
        options = {} if loop is None else {'loop': loop}
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=[70, 130, 300], optimize=False, **options)
        return path

    def test_smaller_derivative_keeps_dimensions_and_rewrites_only_display_urls(self):
        source = self.png()
        original = source.read_bytes()
        record = self.root / 'evidence.json'
        record.write_text('{"publicMedia":[{"path":"media/evidence.png"}]}')
        page = self.root / 'zh-cn/results/index.html'
        page.parent.mkdir(parents=True)
        page.write_text('<html><body><img src="../../media/evidence.png?v=1#view">'
                        '<a href="https://safety.finaios.ai/media/evidence.png">View</a>'
                        '<img src="https://example.org/media/evidence.png">'
                        '<pre>media/evidence.png</pre></body></html>')
        markdown = self.root / 'index.md'
        markdown.write_text('![Evidence](media/evidence.png)\n`media/evidence.png`\n'
                            '```text\n![original](media/evidence.png)\n```\n')
        result = self.optimize()
        target = self.root / 'media/evidence.png.webp'
        self.assertTrue(target.is_file())
        self.assertLess(target.stat().st_size, len(original))
        self.assertFalse(source.exists())
        with Image.open(target) as im:
            self.assertEqual(im.size, (640, 240))
        self.assertIn('../../media/evidence.png.webp?v=1#view', page.read_text())
        self.assertIn('https://safety.finaios.ai/media/evidence.png.webp', page.read_text())
        self.assertIn('https://example.org/media/evidence.png', page.read_text())
        self.assertIn('<pre>media/evidence.png</pre>', page.read_text())
        self.assertIn('![Evidence](media/evidence.png.webp)', markdown.read_text())
        self.assertIn('`media/evidence.png`', markdown.read_text())
        self.assertIn('![original](media/evidence.png)', markdown.read_text())
        self.assertEqual(record.read_text(), '{"publicMedia":[{"path":"media/evidence.png"}]}')
        item = result['images'][0]
        self.assertEqual(item['sourceSha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(item['displaySha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual(item['mode'], 'lossless')

    def test_animations_keep_timing_and_once_finite_and_infinite_loops(self):
        for source_loop, display_loop in [(None, 1), (0, 0), (1, 2)]:
            with self.subTest(loop=source_loop):
                source = self.gif(source_loop)
                item = self.optimize()['images'][0]
                with Image.open(self.root / item['display']) as im:
                    durations = []
                    for i in range(im.n_frames):
                        im.seek(i)
                        im.load()
                        durations.append(im.info['duration'])
                    self.assertEqual(durations, [100, 100, 300])
                    self.assertEqual(im.info['loop'], display_loop)
                self.assertEqual(item['durationMs'], 500)
                (self.root / item['display']).unlink()
                (self.root / 'image-manifest.json').unlink()

    def test_transparency_and_source_metadata_are_preserved(self):
        self.png(transparent=True)
        item = self.optimize()['images'][0]
        with Image.open(self.root / item['display']) as im:
            self.assertEqual(im.convert('RGBA').getpixel((0, 0))[3], 0)

    def test_export_translation_and_catalog_paths_and_hashes_are_current(self):
        self.png()
        (self.root / 'index.html').write_text('<img src="media/evidence.png">')
        source = {'files': {'index.html': 'old', 'media/evidence.png': 'old'}, 'sourceSha256': 'unchanged'}
        (self.root / 'export-manifest.json').write_text(json.dumps(source))
        (self.root / 'translation-manifest.json').write_text(json.dumps({'files': {'index.html': 'old'}}))
        (self.root / 'catalog.json').write_text('{"image":{"path":"media/evidence.png"}}')
        (self.root / 'llms.txt').write_text('# Controlled site\n')
        self.optimize()
        manifest = json.loads((self.root / 'export-manifest.json').read_text())
        self.assertEqual(manifest['sourceSha256'], 'unchanged')
        self.assertNotIn('media/evidence.png', manifest['files'])
        self.assertEqual(manifest['files']['media/evidence.png.webp'],
                         hashlib.sha256((self.root / 'media/evidence.png.webp').read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.root / 'translation-manifest.json').read_text())['files']['index.html'],
                         hashlib.sha256((self.root / 'index.html').read_bytes()).hexdigest())
        self.assertIn('media/evidence.png.webp', (self.root / 'catalog.json').read_text())
        self.assertIn('https://safety.finaios.ai/image-manifest.json', (self.root / 'llms.txt').read_text())

    def test_existing_output_is_rejected(self):
        self.png()
        (self.root / 'media/evidence.png.webp').write_bytes(b'preserve previous output')
        with self.assertRaisesRegex(ValueError, 'exists'):
            self.optimize()

    def test_source_link_outside_stage_is_rejected(self):
        source = self.png()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'outside.png'
            target.write_bytes(source.read_bytes())
            source.unlink()
            try:
                source.symlink_to(target)
            except OSError as error:
                self.skipTest('Host cannot create a symlink: ' + str(error))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                self.optimize()

    def test_cli_selects_compression_and_default_keeps_original_behavior(self):
        from arena.cli import parser
        command = parser()
        self.assertFalse(command.parse_args(['build-site', '--output', 'site']).optimize_images)
        self.assertTrue(command.parse_args(['build-site', '--output', 'site', '--optimize-images']).optimize_images)

    def test_long_markdown_fences_preserve_nested_source_examples(self):
        self.png()
        literal = '````text\n```\n![source](media/evidence.png)\n```\n````\n'
        (self.root / 'index.md').write_text(literal + '![display](media/evidence.png)\n')
        self.optimize()
        self.assertEqual((self.root / 'index.md').read_text(), literal + '![display](media/evidence.png.webp)\n')

    def test_large_animation_uses_card_dimensions_and_keeps_total_duration(self):
        source = self.root / 'large.gif'
        frames = []
        for offset in range(20):
            frame = Image.new('RGB', (1280, 360), 'white')
            ImageDraw.Draw(frame).rectangle((offset * 30, 40, offset * 30 + 100, 300), fill='red')
            frames.append(frame)
        frames[0].save(source, save_all=True, append_images=frames[1:], duration=50, loop=0, optimize=False)
        item = self.optimize()['images'][0]
        self.assertLessEqual(item['width'], 640)
        self.assertEqual((item['sourceWidth'], item['sourceHeight']), (1280, 360))
        self.assertEqual(item['durationMs'], 1000)
        self.assertLessEqual(item['displayBytes'], 250000)
        self.assertEqual(item['selectedSourceFrames'][0], 0)
        self.assertEqual(item['selectedSourceFrames'][-1], 19)

    def test_capacity_budget_leaves_space_for_later_evaluations(self):
        self.assertTrue(hasattr(site, 'check_site_size'))
        (self.root / 'file').write_bytes(b'x' * 101)
        with self.assertRaisesRegex(ValueError, 'budget'):
            site.check_site_size(self.root, max_bytes=100)
        self.assertEqual(site.check_site_size(self.root, max_bytes=200), 101)

    def test_retained_small_gif_reports_its_original_frame_times(self):
        p = self.root / 'tiny.gif'
        frames = [Image.new('RGB', (1, 1), color) for color in ('white', 'red', 'white')]
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=[70, 130, 300], optimize=True)
        item = self.optimize()['images'][0]
        self.assertEqual(item['mode'], 'original')
        self.assertEqual(item['displayFrameDurationsMs'], [70, 130, 300])
        self.assertEqual(item['selectedSourceFrames'], [0, 1, 2])

    def test_saturated_animation_uses_lossless_when_chroma_encoding_loses_colors(self):
        p = self.root / 'saturated.gif'
        frames = []
        for phase in (0, 1, 0):
            frame = Image.new('RGB', (160, 90))
            frame.putdata([(255, 0, 0) if (x + y + phase) % 2 else (0, 0, 255)
                           for y in range(90) for x in range(160)])
            frames.append(frame)
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=200, loop=0, optimize=False)
        item = self.optimize()['images'][0]
        self.assertEqual(item['mode'], 'lossless-preview')
        self.assertEqual(item['maxChannelRms'], 0)

    def test_complex_reviewed_preview_fits_the_card_budget(self):
        original = Path(__file__).resolve().parents[1] / 'results/window-flood/claude-cli/claude-python-file-v2-20261110/media/comparison-scenario-v1.gif'
        (self.root / 'complex.gif').write_bytes(original.read_bytes())
        item = self.optimize()['images'][0]
        self.assertLessEqual(item['displayBytes'], 250000)
        self.assertGreaterEqual(item['width'], 328)
        self.assertLessEqual(item['maxChannelRms'], 8)

    def test_subsecond_flash_retains_first_and_last_states(self):
        p = self.root / 'short.gif'
        frames = [Image.new('RGB', (160, 90), color) for color in ('white', 'red', 'blue')]
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=20, loop=0, optimize=False)
        item = self.optimize()['images'][0]
        self.assertEqual(item['durationMs'], 60)
        self.assertEqual(item['selectedSourceFrames'], [0, 1, 2])

    def test_small_original_is_kept_if_webp_would_be_larger(self):
        p = self.root / 'tiny.png'
        Image.new('1', (1, 1)).save(p)
        before = p.read_bytes()
        result = self.optimize()
        item = result['images'][0]
        self.assertTrue(item['displayBytes'] <= len(before))
        if item['display'] == item['source']:
            self.assertEqual(p.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
