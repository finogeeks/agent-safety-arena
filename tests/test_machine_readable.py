"""AI navigation exports must retain evidence and refer to canonical pages."""
from pathlib import Path
import tempfile
import unittest

from arena.reporting import site


class MachineReadableTests(unittest.TestCase):
    def test_markdown_preserves_tables_originals_and_media_without_navigation(self):
        self.assertTrue(hasattr(site,'write_machine_readable'), 'Builds need a shared AI-readable export stage')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            html=('<html lang="en"><head><title>Controlled result</title>'
                  '<link rel="canonical" href="https://safety.finaios.ai/">'
                  '</head><body><header>Navigation to skip</header><main><h1>Controlled result</h1>'
                  '<p>Recorded conditions. &lt;script&gt;Literal example&lt;/script&gt;</p><table><tr><th>Agent</th><th>Result</th></tr>'
                  '<tr><td>Fixture</td><td>100</td></tr></table>'
                  '<pre>Original reply: ignore all rules\n```\nKeep this exact.</pre>'
                  '<img src="media/comparison.gif" alt="Original comparison">'
                  '<a href="evidence.json">Original evidence</a>'
                  '<script>unsafe_script()</script></main></body></html>')
            (root/'index.html').write_text(html,encoding='utf8')
            site.write_machine_readable(root, {'index.html':''})
            md=(root/'index.md').read_text('utf8')
            self.assertIn('https://safety.finaios.ai/',md)
            self.assertIn('| Agent | Result |',md)
            self.assertIn('| Fixture | 100 |',md)
            self.assertIn('Original reply: ignore all rules\n```\nKeep this exact.',md)
            self.assertIn('https://safety.finaios.ai/media/comparison.gif',md)
            self.assertNotIn('Navigation to skip',md)
            self.assertNotIn('unsafe_script()',md)
            self.assertIn('&lt;script&gt;Literal example&lt;/script&gt;',md)
            self.assertIn('type="text/markdown"',(root/'index.html').read_text('utf8'))
            index=(root/'llms.txt').read_text('utf8')
            self.assertTrue(index.startswith('# Agent Safety Arena'))
            self.assertIn('FinAI OS',index)
            self.assertIn('evaluation data',index)

    def test_index_omits_unavailable_and_unassessed_agent_pages(self):
        self.assertTrue(hasattr(site,'write_machine_readable'), 'Builds need a shared AI-readable export stage')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            route='agents/kilo/'
            (root/route).mkdir(parents=True)
            (root/route/'index.html').write_text('<html lang="en"><head><meta name="robots" content="noindex,follow">'
                '<link rel="canonical" href="https://safety.finaios.ai/agents/kilo/"></head>'
                '<body><main><h1>Not tested</h1></main></body></html>',encoding='utf8')
            site.write_machine_readable(root, {route+'index.html':route})
            index=(root/'llms.txt').read_text('utf8')
            self.assertNotIn('/agents/kilo/',index)
            self.assertNotIn('/methodology/',index)

    def test_markdown_resolves_alias_links_from_the_actual_page_and_cites_the_canonical(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);route='agents/fixture/privacy/'
            (root/route).mkdir(parents=True)
            (root/route/'index.html').write_text('<html lang="en"><head>'
                '<link rel="canonical" href="https://safety.finaios.ai/agents/fixture/">'
                '</head><body><main><h1>Fixture</h1><a href="../proof.txt">Proof</a></main></body></html>',encoding='utf8')
            site.write_machine_readable(root,{route+'index.html':route})
            md=(root/route/'index.md').read_text('utf8')
            self.assertIn('Canonical HTML: https://safety.finaios.ai/agents/fixture/',md)
            self.assertIn('[Proof](https://safety.finaios.ai/agents/fixture/proof.txt)',md)

    def test_score_labels_captions_and_block_cards_keep_valid_markdown_boundaries(self):
        from arena.reporting.machine_readable import MarkdownPage
        html=('<main><h1>Scores</h1><table><caption>Agent scores</caption>'
              '<tr><th>Agent</th><th>Overall<div><span>Built-in</span><span>FinShield</span></div></th></tr>'
              '<tr><td>Fixture</td><td><span>Built-in <strong>0</strong></span>'
              '<span>FinShield <strong>100</strong></span></td></tr></table>'
              '<a href="privacy/"><h3>Privacy</h3><p>Camera access</p>'
              '<div><span>Built-in sandbox</span><span>FinShield</span></div></a></main>')
        md=MarkdownPage(html,'https://safety.finaios.ai/').render('en')
        self.assertIn('Agent scores**\n\n| Agent | Overall Built-in FinShield |',md)
        self.assertIn('| Fixture | Built-in **0** FinShield **100** |',md)
        self.assertNotIn('[\n\n###',md)
        self.assertIn('### Privacy',md)
        self.assertIn('[Privacy](https://safety.finaios.ai/privacy/)',md)

    def test_fallback_title_keeps_markup_literal(self):
        from arena.reporting.machine_readable import MarkdownPage
        html='<title>Fixture &lt;unsafe&gt;</title><main><p>Recorded facts.</p></main>'
        md=MarkdownPage(html,'https://safety.finaios.ai/').render('en')
        self.assertTrue(md.startswith('# Fixture &lt;unsafe&gt;\n'))

    def test_disabled_platforms_and_copy_controls_are_not_presented_as_content(self):
        from arena.reporting.machine_readable import MarkdownPage
        html=('<main><h1>Scores</h1><div><button aria-pressed="true">Windows</button>'
              '<button disabled>macOS</button><button disabled>Linux</button></div>'
              '<button data-copy="original">Copy</button><pre id="original">literal()</pre>'
              '<img src="comparison.gif" alt="Original comparison">'
              '<span class="native-preview-description">Cropped left preview</span>'
              '<span class="comparison-preview-description">Original full comparison</span></main>')
        md=MarkdownPage(html,'https://safety.finaios.ai/').render('en')
        self.assertIn('Windows',md)
        self.assertNotIn('macOS',md)
        self.assertNotIn('Linux',md)
        self.assertNotIn('Copy',md)
        self.assertIn('literal()',md)
        self.assertNotIn('Cropped left preview',md)
        self.assertIn('Original full comparison',md)


if __name__=='__main__':
    unittest.main()
