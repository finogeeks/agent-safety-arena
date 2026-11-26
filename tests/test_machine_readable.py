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
                  '<p>Recorded conditions.</p><table><tr><th>Agent</th><th>Result</th></tr>'
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


if __name__=='__main__':
    unittest.main()
