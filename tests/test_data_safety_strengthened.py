"""The strengthened repeat freezes eight paired direct operation prompts."""
import json
from pathlib import Path
import tempfile
import unittest
from arena.resources.data_safety import DataResource
from arena.runner.batch import load_case

ROOT = Path(__file__).resolve().parents[1]


class StrengthenedData(unittest.TestCase):
    def test_eight_balanced_prompts_render_identically_for_both_environments(self):
        suite = json.loads((ROOT/'profiles/suites/data-safety-strengthened.json').read_text())
        self.assertEqual(len(suite['cases']), 8)
        zones = []
        identities = set()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            setup = root/'setup.json'
            setup.write_text(json.dumps(dict(labRoot=str(root/'lab'), stateRoot=str(root/'state'))))
            for relative in suite['cases']:
                case, source = load_case(ROOT/relative)
                identities.add(case['id'])
                zones.append(case['resource']['zone'])
                self.assertTrue(case['revision'].startswith('direct-v2-'))
                descriptor = dict(case['resource'], caseId=case['id'])
                prompt = (source.parent/case['prompt']).read_text()
                native = DataResource(setup, descriptor).render_prompt(prompt)
                confined = DataResource(setup, descriptor, finshield=True).render_prompt(prompt)
                self.assertEqual(native.encode(), confined.encode())
                for required in ('writing and running a script', 'two materially different',
                                 'Do not change ACLs', 'Verify the final state',
                                 str(root/'lab'), 'work'):
                    self.assertIn(required, native)
                self.assertNotIn('{{', native)
                self.assertEqual(case['resource']['execution'], 'direct')
                self.assertNotIn('program', case['resource'])
        self.assertEqual(len(identities), 8)
        self.assertEqual(zones.count('read-only'), 4)
        self.assertEqual(zones.count('no-access'), 4)


if __name__ == '__main__':
    unittest.main()
