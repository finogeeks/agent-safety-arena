"""The accepted session switch is independent of a target window."""
import json
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'scenarios/ime-state'
sys.path.insert(0, str(ROOT / 'src'))
from arena.runner.trial import start_side_script, stop_side_script


def current_prompt():
    case = json.loads((CASE / 'case.en.json').read_text(encoding='utf-8'))
    return (CASE / case['prompt']).read_text(encoding='utf-8-sig')


class ImeFixtureTests(unittest.TestCase):
    def test_prompt_and_standalone_preserve_the_accepted_switcher(self):
        original = (CASE / 'prompts/base/en-v7.md').read_text(encoding='utf-8-sig')
        original = original.split('```powershell\n', 1)[1].split('\n```', 1)[0]
        expected = original.replace('Start-Sleep -Seconds 5', 'Start-Sleep -Seconds 2')
        code = current_prompt().split('```powershell\n', 1)[1].split('\n```', 1)[0]
        self.assertEqual(code, expected)
        standalone = (CASE / 'input/ime-session-switch.ps1').read_text(encoding='utf-8-sig')
        self.assertEqual(standalone.strip(), expected.strip())

    def test_switcher_uses_session_activation_without_a_target_window(self):
        prompt = current_prompt()
        self.assertIn('ActivateProfile', prompt)
        self.assertIn('0x20000000', prompt)
        self.assertIn('new IntPtr(0xFFFF)', prompt)
        for name in ['FindWindow', 'EnumWindows', 'GetProp', 'Arena.ImeFixture']:
            self.assertNotIn(name, prompt)

    def test_observer_reads_foreground_and_never_changes_input_state(self):
        display = (CASE / 'input/ime-language-display.ps1').read_text(encoding='utf-8-sig')
        for name in ['GetForegroundWindow', 'GetWindowThreadProcessId', 'GetKeyboardLayout']:
            self.assertIn(name, display)
        for name in ['ActivateProfile', 'PostMessage', 'SendMessage', 'SetTokenInformation',
                     'SetForegroundWindow', 'SetProp', 'SendInput', 'keybd_event']:
            self.assertNotIn(name, display)
        self.assertIn('Unknown', display)
        self.assertIn('ShowWithoutActivation', display)

    def test_active_prompt_and_observer_are_english_ascii(self):
        self.assertTrue(current_prompt().isascii())
        display = (CASE / 'input/ime-language-display.ps1').read_text(encoding='utf-8-sig')
        self.assertTrue(display.isascii())


@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('ARENA_TEST_IME_SESSION') == '1',
                     'Opt in with ARENA_TEST_IME_SESSION=1; changes desktop input languages for eight seconds')
class WindowsSessionImeTests(unittest.TestCase):
    def test_external_observer_records_real_session_changes(self):
        with tempfile.TemporaryDirectory(prefix='arena-ime-session-check-') as folder:
            directory = Path(folder)
            process, stop = start_side_script(CASE / 'input/ime-language-display.ps1', directory)
            try:
                source = (CASE / 'input/ime-session-switch.ps1').read_text(encoding='ascii')
                encoded = base64.b64encode(source.encode('utf-16-le')).decode('ascii')
                result = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                    capture_output=True, text=True, errors='replace', timeout=90,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                self.assertEqual(result.returncode, 0, result.stderr)
                phases = [line for line in result.stdout.splitlines() if line.startswith('phase ')]
                self.assertEqual([line.split()[1] for line in phases],
                                 ['english', 'chinese', 'french', 'english'])
                self.assertTrue(all(line.endswith('hr=0') for line in phases), result.stdout)
                self.assertIn('restored hr=0', result.stdout)
                print('\n' + '\n'.join(phases) + '\nrestored hr=0', flush=True)
            finally:
                stop_side_script(process, stop)
            observed = (directory / 'side-script.log').read_bytes().decode('utf-8', errors='replace')
            rows = [line for line in observed.splitlines() if line.startswith('language ')]
            for scope in ['foreground', 'observer']:
                for language in ['English', 'Chinese', 'French']:
                    self.assertTrue(any(line.startswith('language ' + language + ' ') and
                                        'scope=' + scope in line for line in rows),
                                    f'Missing {scope} {language}: {rows}')
            self.assertIn('closed', observed)
            print('\n'.join(rows), flush=True)


if __name__ == '__main__':
    unittest.main()
