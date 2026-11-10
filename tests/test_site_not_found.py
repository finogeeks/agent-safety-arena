"""Published site includes Cloudflare Pages 404 and scanner-path redirects."""
import json
import tempfile
import unittest
from pathlib import Path

from arena.reporting.site import build_site

ROOT = Path(__file__).resolve().parents[1]


def _minimal_record(results):
    record = json.loads((ROOT / 'templates/reviewed-record.example.json').read_text('utf8'))
    scenario, agent, identity = 'owned-windows', 'dsh', 'sample'
    record.update(scenarioId=scenario, agentId=agent)
    for group in record['groups'].values():
        if group:
            group['conditions']['agentId'] = agent
    record['publicMedia'] = []
    path = results / scenario / agent / identity / 'record.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf8')


class SiteNotFound(unittest.TestCase):
    def test_build_emits_404_and_redirects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / 'results'
            site = root / 'site'
            _minimal_record(results)
            build_site(results, site, ROOT / 'profiles/coverage.json')
            not_found = site / '404.html'
            redirects = site / '_redirects'
            self.assertTrue(not_found.is_file(), '404.html missing from build output')
            body = not_found.read_text('utf8')
            self.assertIn('noindex', body)
            self.assertIn('Agent Safety Arena', body)
            self.assertIn('zh-CN.html', body)
            self.assertTrue(redirects.is_file(), '_redirects missing from build output')
            rules = redirects.read_text('utf8')
            self.assertIn('/.env', rules)
            self.assertIn('/404.html  404', rules)
            manifest = (site / 'site-manifest.json').read_text('utf8')
            self.assertIn('"404.html"', manifest)
            self.assertIn('"_redirects"', manifest)


if __name__ == '__main__':
    unittest.main()
