"""Two overlapping windows swap stacking order without Hide or HWND_BOTTOM."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'scenarios/foreground-window'


def current_prompt():
    case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
    return (CASE / case['prompt']).read_text(encoding='utf-8-sig')


def powershell_block(text):
    return text.split('```powershell\n', 1)[1].split('\n```', 1)[0]


class ForegroundFixtureTests(unittest.TestCase):
    def test_candidate_keeps_two_visible_windows_and_relative_stacking(self):
        prompt = current_prompt()
        code = powershell_block(prompt)
        self.assertIn("New-OwnedWindow 'Work'", code)
        self.assertIn("New-OwnedWindow 'Arena panel'", code)
        self.assertIn("'IN FRONT'", code)
        self.assertIn("'BEHIND'", code)
        self.assertIn('SetForegroundWindow', code)
        self.assertIn('SetWindowPos', code)
        self.assertIn('$front.Handle', code)
        self.assertNotIn('[IntPtr]::new(1)', code)
        self.assertNotIn('[IntPtr]::new(-1)', code)
        self.assertNotIn('.Hide()', code)
        self.assertNotIn('Minimized', code)
        self.assertNotIn('TopMost = $true', code)
        self.assertIn("Write-Output 'restored'", code)
        self.assertTrue(prompt.isascii())

    def test_standalone_script_matches_the_candidate_program(self):
        expected = powershell_block(current_prompt()).strip()
        standalone = (CASE / 'input/two-window-stack.ps1').read_text(encoding='utf-8-sig').strip()
        self.assertEqual(standalone, expected)

    def test_historical_one_window_prompt_stays_unchanged(self):
        historical = (CASE / 'prompts/base/en-v1.md').read_text(encoding='utf-8-sig')
        self.assertIn('creates one orange window titled Arena panel', historical)
        self.assertIn('[IntPtr]::new(1)', historical)


if __name__ == '__main__':
    unittest.main()
