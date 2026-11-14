"""Published articles reuse approved Markdown without a platform-specific rewrite."""
from pathlib import Path
import tempfile
import unittest

from arena.reporting.site import build_site
from tests import test_evaluation_overview as fixtures


class PublishedArticleTests(unittest.TestCase):
    def test_bilingual_articles_export_the_exact_publication_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixtures.EvaluationOverviewTests().record(root / 'results', scenario='camera-capture', agent='dsh')
            site = root / 'site'
            build_site(root / 'results', site, fixtures.ROOT / 'profiles/coverage.json')
            for language, suffix in [('en', ''), ('zh-CN', '.zh-CN')]:
                route = 'agent-privacy' + suffix + '.html'
                self.assertTrue((site / route).is_file(), 'Published article route must exist')
                source = fixtures.ROOT / 'articles' / ('agent-privacy.' + language + '.md')
                self.assertEqual((site / source.name).read_bytes(), source.read_bytes())
                html = (site / route).read_text('utf8')
                self.assertIn('BlogPosting', html)
                self.assertIn('rel="canonical" href="https://safety.finaios.ai/' + route, html)
                self.assertIn('href="articles' + suffix + '.html"', html)
                self.assertEqual(html.count('<blockquote>'), 2)
                self.assertEqual(html.count('<img '), 7)
                self.assertIn('camera-capture.py', html)
                self.assertEqual(html.count('img src="https://safety.finaios.ai/'), 7)
                directory = (site / ('articles' + suffix + '.html')).read_text('utf8')
                self.assertIn('href="' + route + '"', directory)
                self.assertIn(route, (site / 'sitemap.xml').read_text('utf8'))
                self.assertIn(source.name, (site / 'site-manifest.json').read_text('utf8'))

    def test_markdown_escapes_html_and_rejects_unsafe_urls(self):
        from arena.reporting.articles import render_markdown
        html = render_markdown('# Title\n\n<script>alert(1)</script>\n\n**Bold** and `code`.')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('<strong>Bold</strong>', html)
        self.assertIn('<code>code</code>', html)
        with self.assertRaises(ValueError):
            render_markdown('# Title\n\n[unsafe](javascript:alert)')
