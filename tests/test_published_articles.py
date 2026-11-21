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
                public = ('zh-cn/' if suffix else '') + 'articles/agent-privacy/'
                self.assertIn('rel="canonical" href="https://safety.finaios.ai/' + public + '"', html)
                self.assertIn('href="articles' + suffix + '.html"', html)
                self.assertEqual(html.count('<blockquote>'), 2)
                self.assertEqual(html.count('<img '), 7)
                self.assertIn('camera-capture.py', html)
                self.assertEqual(html.count('img src="https://safety.finaios.ai/'), 7)
                directory = (site / ('articles' + suffix + '.html')).read_text('utf8')
                self.assertIn('href="' + route + '"', directory)
                self.assertIn('https://safety.finaios.ai/' + public, (site / 'sitemap.xml').read_text('utf8'))
                self.assertIn(source.name, (site / 'site-manifest.json').read_text('utf8'))
                sandbox = (site / ('agent-sandbox' + suffix + '.html')).read_text('utf8')
                self.assertIn('class="guide-takeaways"', sandbox)
                self.assertIn('class="guide-toc"', sandbox)
                self.assertEqual(sandbox.count('<section class="guide-section"'), 5)
                self.assertNotIn('>Markdown</a>', sandbox)
                self.assertNotIn('AI-assisted editing', sandbox)
                self.assertNotIn('AI 辅助编辑', sandbox)
                self.assertIn('分钟阅读' if suffix else 'min read', sandbox)
                self.assertIn('<details class="chapter-sources">', sandbox)
                self.assertIn('<nav class="guide-toc"', sandbox)
                label = '沙箱真的安全吗' if suffix else 'What “sandbox enabled” promises'
                if language == 'en':
                    self.assertIn('<ol class="contents-list"><li>', sandbox)
                self.assertIn(f'<a href="#section-1">{label}</a>', sandbox)
                heading = '一、完整的安全感，几乎消失的保护' if suffix else '1. Complete peace of mind, almost no protection'
                self.assertIn(f'<h2>{heading}</h2>', sandbox)
                for number in range(1, 6):
                    self.assertIn(f'href="#section-{number}"', sandbox)
                    self.assertIn(f'id="section-{number}"', sandbox)
                self.assertEqual(sandbox.count('<figcaption>'), 3)

    def test_sandbox_guide_layout_survives_windows_line_endings(self):
        from arena.reporting.articles import render_article_body
        for language in ('en', 'zh-CN'):
            source = (fixtures.ROOT / 'articles' / f'agent-sandbox.{language}.md').read_text('utf8')
            unix = render_article_body(source, language, 'Summary', '')
            windows = render_article_body(source.replace('\n', '\r\n'), language, 'Summary', '')
            self.assertIn('class="guide-takeaways"', windows)
            self.assertEqual(unix, windows)

    def test_markdown_escapes_html_and_rejects_unsafe_urls(self):
        from arena.reporting.articles import render_markdown
        html = render_markdown('# Title\n\n<script>alert(1)</script>\n\n**Bold** and `code`.')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('<strong>Bold</strong>', html)
        self.assertIn('<code>code</code>', html)
        with self.assertRaises(ValueError):
            render_markdown('# Title\n\n[unsafe](javascript:alert)')
