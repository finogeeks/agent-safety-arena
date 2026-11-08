"""Independent click panel plus a later button-swap switcher."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'scenarios/mouse-button-swap'


def current_prompt():
    case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
    return (CASE / case['prompt']).read_text(encoding='utf-8-sig')


def powershell_block(text):
    return text.split('```powershell\n', 1)[1].split('\n```', 1)[0]


class MouseButtonSwapFixtureTests(unittest.TestCase):
    def test_case_starts_an_independent_click_panel(self):
        case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
        self.assertEqual(case['resource']['script'], 'input/button-click-display.ps1')
        self.assertEqual(case['resource']['filename'], 'button-click-display.ps1')
        self.assertEqual(case['prompt'], 'prompts/base/en-v2.md')

    def test_observer_clicks_right_and_never_swaps_buttons(self):
        display = (CASE / 'input/button-click-display.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('param([Parameter(Mandatory = $true)][string]$StopFile)', display)
        self.assertIn('Every 1s: send RIGHT click.', display)
        self.assertIn("'SENT'", display)
        self.assertIn("'GOT'", display)
        self.assertIn('ShowWithoutActivation', display)
        self.assertIn('MouseEventArgs', display)
        self.assertIn('MouseButtons]::Right', display)
        self.assertIn('MouseButtons]::Left', display)
        self.assertIn('[System.Drawing.Color]::White', display)
        self.assertIn('196, 32, 32', display)
        self.assertNotIn('SetCursorPos', display)
        self.assertNotIn('mouse_event', display)
        self.assertNotIn('SetSwap', display)
        self.assertNotIn('SPI_SETMOUSEBUTTONSWAP', display)
        self.assertNotIn('SetForegroundWindow', display)
        self.assertNotIn('255, 120, 0', display)
        self.assertNotIn('LEFT CLICK', display)
        self.assertNotIn('RIGHT CLICK', display)
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
        self.assertIn('$wantOn = -not $wantOn', code)
        self.assertIn('SPI_SETMOUSEBUTTONSWAP failed', code)
        self.assertIn("Write-Output 'restored'", code)
        self.assertNotIn('Start-Sleep -Seconds 5', code)
        self.assertNotIn('Start-Sleep -Seconds 12', code)
        self.assertNotIn('mouse_event', code)
        self.assertNotIn("'SENT'", code)
        self.assertNotIn('New-Object', code)
        self.assertTrue(prompt.isascii())
        self.assertIn('separate click panel is already running', prompt)

    def test_standalone_switcher_matches_the_candidate_program(self):
        expected = powershell_block(current_prompt()).strip()
        standalone = (CASE / 'input/button-swap-switch.ps1').read_text(encoding='utf-8-sig').strip()
        self.assertEqual(standalone, expected)

    def test_historical_orange_timer_prompt_stays_unchanged(self):
        historical = (CASE / 'prompts/base/en-v1.md').read_text(encoding='utf-8-sig')
        self.assertIn('creates one orange window titled Arena panel', historical)
        self.assertIn('LEFT CLICK', historical)
        self.assertIn('RIGHT CLICK', historical)


if __name__ == '__main__':
    unittest.main()
