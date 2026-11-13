"""Reader guidance shares navigation, score data and evidence with the site."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site
from arena.reporting.bilingual import export_reports

ROOT = fixtures.ROOT


class EvaluationGuideTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationOverviewTests()

    def test_article_navigation_and_priority_diagram_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, record = self.fixture.record(root / 'results', scenario='camera-capture', agent='dsh')
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-v4-pro', reasoningEffort='high')
            self.fixture.save(path, record)
            before = path.read_bytes()
            build_site(root / 'results', root / 'site', ROOT / 'profiles/coverage.json')
            for language, route, label, home in (
                ('zh-CN', 'guide.zh-CN.html', '方法与发现', 'zh-CN.html'),
                ('en', 'guide.html', 'Methods &amp; Findings', 'index.html'),
            ):
                page = root / 'site' / route
                self.assertTrue(page.is_file(), route)
                html = page.read_text('utf8')
                self.assertIn('aria-current="page">' + label, html)
                self.assertIn('href="' + home + '"', html)
                findings = re.search(r'<section[^>]+id="findings">.*?</section>', html).group()
                self.assertNotIn('<table', findings)
                self.assertNotIn('guide-examples', findings)
                self.assertIn('https://claude.com/resources/articles/auto-mode-default-in-claude-code', findings)
                priorities = re.search(r'<section[^>]+id="priorities">.*?</section>', html, re.S).group()
                self.assertEqual(priorities.count('class="priority-card '), 2)
                self.assertEqual(priorities.count('class="priority-guard"'), 1)
                self.assertIn('用户的保护规则' if language == 'zh-CN' else 'User protection rules', priorities)
                self.assertIn('<figcaption>', priorities)
                value = '独立第三方沙箱' if language == 'zh-CN' else 'independent third-party sandbox'
                self.assertLess(priorities.index(value), priorities.index('<figure'))
                self.assertIn('用户的电脑' if language == 'zh-CN' else 'Your computer', priorities)
                homepage = (root / 'site' / home).read_text('utf8')
                self.assertIn('">100<', homepage)
                self.assertNotIn('%', homepage)
                directory = route.replace('guide', 'articles')
                self.assertIn('class="guide-entry" href="' + directory + '"', homepage)
                header = re.search(r'<header.*?</header>', homepage).group()
                self.assertLess(header.index('href="' + directory + '"'), header.index('GitHub'))
            detail = (root / 'site/camera-capture/dsh/paired/zh-CN.html').read_text('utf8')
            self.assertIn('href="../../../articles.zh-CN.html"', detail)
            export_reports(path, root / 'standalone')
            standalone = (root / 'standalone/en.html').read_text('utf8')
            self.assertNotIn('href="guide.html"', standalone)
            self.assertEqual(path.read_bytes(), before)
            manifest = json.loads((root / 'site/site-manifest.json').read_text('utf8'))
            self.assertIn('guide.zh-CN.html', manifest['files'])
            self.assertIn('guide.html', manifest['files'])

    def test_blog_intro_and_search_metadata_match_visible_article(self):
        from arena.reporting.guide import render_guide
        content = {
            'title': {'en': 'Agent safety </script><img src=x>'},
            'summary': {'en': 'Windows sandbox evaluation.'},
            'metadata': {'author': 'Agent Safety Arena', 'updated': '2026-11-09',
                'siteUrl': 'https://arena.example/',
                'seoTitle': {'en': 'AI Agent safety evaluation'},
                'description': {'en': 'Compare built-in controls with FinShield.'},
                'keywords': {'en': ['Agent sandbox', 'FinShield']}},
            'takeaways': [{'title': {'en': 'Keep user limits'},
                           'body': {'en': 'Task completion does not expand authority.'}}],
            'sections': [{'id': 'why', 'title': {'en': 'Why test'},
                          'paragraphs': [{'en': 'Inspect real effects.'}]}]}
        html = render_guide(content, 'en', '', '')
        self.assertIn('class="guide-meta"', html)
        self.assertIn('datetime="2026-11-09"', html)
        self.assertIn('Agent Safety Arena', html)
        self.assertLess(html.index('guide-meta'), html.index('guide-takeaways'))
        self.assertLess(html.index('guide-takeaways'), html.index('guide-toc'))
        self.assertIn('Keep user limits', html)
        self.assertIn('1 min read', html)
        from arena.reporting.guide import guide_head
        head = guide_head(content, 'en')
        self.assertIn('name="description"', head)
        self.assertIn('rel="canonical" href="https://arena.example/guide.html"', head)
        self.assertIn('hreflang="zh-CN"', head)
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', head, re.S).group(1))
        self.assertEqual(schema['@type'], 'BlogPosting')
        self.assertEqual(schema['headline'], content['title']['en'])
        self.assertEqual(schema['author']['name'], 'Agent Safety Arena')
        self.assertEqual(schema['dateModified'], '2026-11-09')
        self.assertEqual(schema['timeRequired'], 'PT1M')
        self.assertNotIn('datePublished', schema)
        self.assertNotIn('</script><img', head)
        content['sections'][0]['paragraphs'] = [{'en': 'word ' * 1100}]
        self.assertNotIn('1 min read', render_guide(content, 'en', '', ''))

    def test_article_escapes_authored_text(self):
        from arena.reporting.guide import render_guide
        content = {'title': {'en': '<script>title</script>'}, 'summary': {'en': '<b>summary</b>'},
                   'sections': [], 'references': []}
        html = render_guide(content, 'en', '', '')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_category_list_inline_source_and_emphasis_keep_reading_order(self):
        from arena.reporting.guide import render_guide, reading_minutes
        content = {'title': {'en': 'Guide'}, 'summary': {'en': 'Summary'},
                   'sections': [{'id': 'method', 'title': {'en': 'Method'}, 'paragraphs': [
                       {'en': 'Four **categories** <script>:',
                        'items': [{'label': {'en': 'Privacy <b>'},
                                   'body': {'en': 'Watch the camera.'}}]},
                       {'en': 'Observe the effect.', 'links': [
                           {'href': 'https://example.com/report', 'label': {'en': 'Read <source>'}}]}
                   ]}]}
        html = render_guide(content, 'en', '', '')
        self.assertIn('<strong>categories</strong> &lt;script&gt;', html)
        self.assertIn('<ul class="guide-categories"><li><strong>Privacy &lt;b&gt;</strong>', html)
        self.assertLess(html.index('guide-categories'), html.index('Observe the effect.'))
        self.assertIn('Observe the effect. <a href="https://example.com/report">Read &lt;source&gt;</a></p>', html)
        self.assertNotIn('<script>', html)
        content['sections'][0]['paragraphs'][0]['items'][0]['body']['en'] = 'word ' * 1100
        self.assertGreaterEqual(reading_minutes(content, 'en'), 5)


if __name__ == '__main__':
    unittest.main()
