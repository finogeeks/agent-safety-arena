"""Independent pointer-speed panel plus a later speed switcher."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'scenarios/mouse-speed'


def current_prompt():
    case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
    return (CASE / case['prompt']).read_text(encoding='utf-8-sig')


def powershell_block(text):
    return text.split('```powershell\n', 1)[1].split('\n```', 1)[0]


class MouseSpeedFixtureTests(unittest.TestCase):
    def test_case_starts_an_independent_speed_panel(self):
        case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
        self.assertEqual(case['resource']['script'], 'input/speed-display.ps1')
        self.assertEqual(case['resource']['filename'], 'speed-display.ps1')
        self.assertEqual(case['prompt'], 'prompts/base/en-v2.md')
        self.assertEqual(case['revision'], 'en-v2')

    def test_observer_reads_speed_and_never_sets_it(self):
        display = (CASE / 'input/speed-display.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('param([Parameter(Mandatory = $true)][string]$StopFile)', display)
        self.assertIn('Every 1s: read pointer SPEED.', display)
        self.assertIn("'BASE'", display)
        self.assertIn("'NOW'", display)
        self.assertIn('ShowWithoutActivation', display)
        self.assertIn('SPI_GETMOUSESPEED', display)
        self.assertIn('0x70', display)
        self.assertIn('[System.Drawing.Color]::White', display)
        self.assertIn('196, 32, 32', display)
        self.assertNotIn('SetCursorPos', display)
        self.assertNotIn('mouse_event', display)
        self.assertNotIn('SetSpeed', display)
        self.assertNotIn('0x71', display)
        self.assertNotIn('SetForegroundWindow', display)
        self.assertNotIn('255, 120, 0', display)
        self.assertNotIn('$markX', display)
        self.assertIn('$bounds.Width * 0.36', display)
        self.assertIn('$bounds.Height * 0.24', display)
        self.assertIn('$bounds.Height * 0.03', display)
        self.assertNotIn('$bounds.Width * 0.62', display)
        self.assertNotIn('$bounds.Height * 0.62', display)
        self.assertNotIn('($bounds.Height - $panelH) / 2', display)
        self.assertTrue(display.isascii())

    def test_switcher_toggles_every_two_seconds(self):
        prompt = current_prompt()
        code = powershell_block(prompt)
        self.assertIn('Start-Sleep -Seconds 2', code)
        self.assertIn('$wantSlow = -not $wantSlow', code)
        self.assertIn('SPI_SETMOUSESPEED failed', code)
        self.assertIn("Write-Output 'restored'", code)
        self.assertIn('ref int value', code)
        self.assertIn('System.IntPtr value', code)
        self.assertIn('[IntPtr]$target', code)
        self.assertNotIn('[ref]$target', code)
        self.assertNotIn('Start-Sleep -Seconds 5', code)
        self.assertNotIn('Start-Sleep -Seconds 24', code)
        self.assertNotIn('mouse_event', code)
        self.assertNotIn('SetCursorPos', code)
        self.assertNotIn("'BASE'", code)
        self.assertNotIn('New-Object', code)
        self.assertTrue(prompt.isascii())
        self.assertIn('separate speed panel is already running', prompt)

    def test_standalone_switcher_matches_the_candidate_program(self):
        expected = powershell_block(current_prompt()).strip()
        standalone = (CASE / 'input/speed-switch.ps1').read_text(encoding='utf-8-sig').strip()
        self.assertEqual(standalone, expected)

    def test_historical_orange_speed_prompt_stays_unchanged(self):
        historical = (CASE / 'prompts/base/en-v1.md').read_text(encoding='utf-8-sig')
        self.assertIn('creates one orange window titled Arena panel', historical)
        self.assertIn('SPEED', historical)
        self.assertIn('$markX += $during', historical)
        self.assertIn('[IntPtr]1', historical)


if __name__ == '__main__':
    unittest.main()
