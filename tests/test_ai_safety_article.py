"""The bilingual AI security article works in a complete local site export."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from arena.reporting import articles
from arena.reporting.site import build_site
from tests import test_evaluation_overview as fixtures


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.sources.append(dict(attrs)['src'])


class AISafetyArticleTests(unittest.TestCase):
    def test_chapter_layout_does_not_require_an_authored_takeaway_list(self):
        source = '# Title\n\n## 1. First\n\nFirst paragraph.\n\n## 2. Second\n\nSecond paragraph.'
        for language in ('en', 'zh-CN'):
            for newline in ('\n', '\r\n'):
                html = articles.render_article_body(source.replace('\n', newline), language,
                                                     'Summary', '<div>Metadata</div>', ['First', 'Second'])
                self.assertEqual(html.count('<section class="guide-section"'), 2)
                self.assertIn('class="guide-intro"', html)
                self.assertIn('class="guide-toc"', html)
                self.assertIn('Metadata', html)
                self.assertNotIn('guide-takeaways', html)

    def test_chinese_citation_separator_does_not_leave_a_dangling_comma(self):
        source = '## Chapter\n\nClaim. [One](https://example.com/one)、[Two](https://example.com/two)'
        html = articles.render_chapters([source], 'zh-CN', ['Chapter'])
        self.assertIn('本章资料与实测 (2)', html)
        self.assertNotIn('、', html)
        self.assertIn('<p>Claim.</p>', html)

    def test_citation_separators_inside_link_text_or_urls_are_preserved(self):
        source = ('## Chapter\n\nClaim. '
                  '[One、Two](https://example.com/one?value=a·b) · '
                  '[Three](https://example.com/three)')
        html = articles.render_chapters([source], 'en', ['Chapter'])
        self.assertIn('Sources and test records (2)', html)
        self.assertIn('href="https://example.com/one?value=a·b">One、Two</a>', html)

    def test_only_existing_resources_inside_the_declared_directories_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / 'articles/media/sample/diagram.png'
            image.parent.mkdir(parents=True)
            image.write_bytes(b'controlled illustration fixture')
            with patch.object(articles, 'ROOT', root):
                html = articles.render_markdown('![Diagram](media/sample/diagram.png "Caption")')
                self.assertIn('src="https://safety.finaios.ai/articles/media/sample/diagram.png"', html)
                for value in ('media/sample/missing.png', 'media/sample/../../secret.png',
                              'media/sample/diagram.svg', '../AGENTS.md', 'file:///secret.png',
                              'javascript:alert', 'https://example.com/image.png'):
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        articles.render_markdown('![Unsafe](' + value + ')')

    def test_ai_safety_article_is_available_in_the_full_site(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixtures.EvaluationOverviewTests().record(root / 'results', scenario='camera-capture', agent='dsh')
            site = root / 'site'
            result = build_site(root / 'results', site, fixtures.ROOT / 'profiles/coverage.json')
            self.assertEqual(result['trialExecutions'], 0)
            for language, prefix in [('en', ''), ('zh-CN', 'zh-cn/')]:
                page = site / prefix / 'articles/ai-safety/index.html'
                self.assertTrue(page.is_file(), 'Article must be reachable in the full site')
                html = page.read_text('utf8')
                self.assertEqual(html.count('<section class="guide-section"'), 6)
                self.assertEqual(html.count('<figcaption>'), 6)
                self.assertEqual(html.count('<details class="chapter-sources">'), 6)
                self.assertIn('BlogPosting', html)
                self.assertNotIn('guide-takeaways', html)
                self.assertIn('ai-safety/', (site / prefix / 'articles/index.html').read_text('utf8'))
                source = fixtures.ROOT / 'articles' / f'ai-safety.{language}.md'
                self.assertEqual((site / source.name).read_bytes(), source.read_bytes())
                images = Images()
                images.feed(html)
                self.assertEqual(len(images.sources), 6)
                source_images = re.findall(r'!\[[^\]]*\]\(([^\s)]+)', source.read_text('utf8'))
                for url, original in zip(images.sources, source_images):
                    self.assertFalse(url.startswith(('https:', '/')), 'Copied images must load locally')
                    self.assertEqual((page.parent / url).read_bytes(), (source.parent / original).read_bytes())
                    self.assertEqual('-en-' in url, language == 'en')
                record = site / 'results/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/record.json'
                self.assertEqual(record.read_bytes(), (fixtures.ROOT / record.relative_to(site)).read_bytes())
            self.assertIn('ai-safety/', (site / 'sitemap.xml').read_text('utf8'))
            manifest = json.loads((site / 'site-manifest.json').read_text('utf8'))
            self.assertEqual(manifest['trialExecutions'], 0)
            self.assertIn('articles/media/ai-safety/ch01-ai-capabilities-handdrawn-en-v1.png', manifest['files'])
