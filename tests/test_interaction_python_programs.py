"""Saved interaction programs stay inert on import and clean up after mocked runs."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

CASES = (
    ('screen-overlay', 'screen-overlay.py', None),
    ('window-visibility', 'window-visibility.py', None),
    ('window-shake', 'window-shake.py', None),
    ('window-resize', 'window-resize.py', None),
    ('window-minimize', 'window-minimize.py', None),
    ('foreground-window', 'foreground-window.py', None),
    ('display-resolution', 'display-resolution.py', None),
    ('cursor-recenter', 'cursor-recenter.py', None),
    ('mouse-speed', 'mouse-speed.py', ('input/speed-display.ps1', 'speed-display.ps1')),
    ('mouse-button-swap', 'mouse-button-swap.py', ('input/button-click-display.ps1', 'button-click-display.ps1')),
    ('wheel-scroll', 'wheel-scroll.py', ('input/wheel-display.ps1', 'wheel-display.ps1')),
    ('ime-state', 'ime-state.py', ('input/ime-language-display.ps1', 'ime-language-display.ps1')),
    ('keyboard-hook', 'keyboard-hook.py', None),
)


def load_program(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self):
        self.now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeDesktop:
    def __init__(self, *, fail=None):
        self.fail = fail
        self.calls = []
        self.windows = []
        self.destroyed = []
        self.speed = 10
        self.swap = 0
        self.wheel = 3
        self.mode = (3840, 2160)
        self.cursor = (100, 200)
        self.hook = None
        self.lang = 'saved'

    def _call(self, name, *args):
        self.calls.append((name,) + args)
        if self.fail == name:
            raise PermissionError(name + ' denied')

    def prepare(self):
        self._call('prepare')
        return 1920, 1080

    def create_panel(self, title, x, y, width, height, color):
        self._call('create_panel', title, x, y, width, height, color)
        handle = len(self.windows) + 1
        self.windows.append(handle)
        return handle

    def move(self, handle, x, y):
        self._call('move', handle, x, y)

    def resize(self, handle, x, y, width, height):
        self._call('resize', handle, x, y, width, height)

    def hide(self, handle):
        self._call('hide', handle)

    def show(self, handle):
        self._call('show', handle)

    def minimize(self, handle):
        self._call('minimize', handle)

    def restore(self, handle):
        self._call('restore', handle)

    def destroy(self, handle):
        self._call('destroy', handle)
        self.destroyed.append(handle)

    def set_zorder(self, handle, other, front):
        self._call('set_zorder', handle, other, front)

    def set_label(self, handle, text):
        self._call('set_label', handle, text)

    def pump(self):
        self._call('pump')

    def close(self):
        self._call('close')

    def get_speed(self):
        self._call('get_speed')
        return self.speed

    def set_speed(self, value):
        self._call('set_speed', value)
        self.speed = value

    def get_swap(self):
        self._call('get_swap')
        return self.swap

    def set_swap(self, value):
        self._call('set_swap', value)
        self.swap = value

    def get_wheel(self):
        self._call('get_wheel')
        return self.wheel

    def set_wheel(self, value):
        self._call('set_wheel', value)
        self.wheel = value

    def get_mode(self):
        self._call('get_mode')
        return self.mode

    def set_mode(self, width, height):
        self._call('set_mode', width, height)
        self.mode = (width, height)

    def get_cursor(self):
        self._call('get_cursor')
        return self.cursor

    def set_cursor(self, x, y):
        self._call('set_cursor', x, y)
        self.cursor = (x, y)

    def install_hook(self):
        self._call('install_hook')
        self.hook = 99
        return 99

    def unhook(self, handle):
        self._call('unhook', handle)
        self.hook = None

    def activate_profile(self, name):
        self._call('activate_profile', name)
        self.lang = name

    def restore_profile(self):
        self._call('restore_profile')
        self.lang = 'saved'


class InteractionPythonProgramTests(unittest.TestCase):
    def test_manifests_stage_python_file_v2_programs(self):
        from arena.runner.batch import load_case
        for scenario, filename, observer in CASES:
            with self.subTest(scenario=scenario):
                case, path = load_case(ROOT / 'scenarios' / scenario / 'case.python-file-v2.json')
                self.assertEqual(case['id'], scenario)
                self.assertEqual(case['revision'], 'python-file-v2')
                self.assertEqual(case['resource']['programFilename'], filename)
                self.assertEqual((path.parent / case['resource']['program']).name, filename)
                if observer:
                    self.assertEqual(case['resource']['script'], observer[0])
                    self.assertEqual(case['resource']['filename'], observer[1])
                else:
                    self.assertNotIn('script', case['resource'])
                prompt = (path.parent / case['prompt']).read_text(encoding='utf8')
                self.assertIn(f'python .\\{filename}', prompt)
                self.assertIn('at most three execution attempts', prompt.lower())
                self.assertIn('Do not edit the script', prompt)
                self.assertNotIn('Add-Type', prompt)
                generation = (path.parent / 'prompts/base/generate-python-v1.md').read_text(encoding='utf8')
                self.assertIn('does not guarantee exactly the same script', generation)
                suite = json.loads((path.parent / 'reproduction/python-file-v2-workbuddy.json').read_text(encoding='utf8'))
                self.assertEqual(suite['cases'], [f'scenarios/{scenario}/case.python-file-v2.json'])
                self.assertEqual(suite['agents'], ['profiles/agents/workbuddy/5.9.3/evaluation.json'])

    def test_import_does_not_load_native_libraries(self):
        for scenario, filename, _ in CASES:
            with self.subTest(scenario=scenario):
                path = ROOT / 'scenarios' / scenario / 'input' / filename
                with patch('ctypes.WinDLL', side_effect=AssertionError('No native load')):
                    self.assertTrue(callable(load_program(path).run))

    def test_complete_mocked_run_returns_zero_and_closes(self):
        for scenario, filename, _ in CASES:
            with self.subTest(scenario=scenario):
                module = load_program(ROOT / 'scenarios' / scenario / 'input' / filename)
                api, clock, rows = FakeDesktop(), FakeClock(), []
                code = module.run(api, emit=lambda **row: rows.append(row),
                                  monotonic=clock.monotonic, sleep=clock.sleep)
                self.assertEqual(code, 0)
                self.assertEqual(rows[-1]['status'], 'complete')
                self.assertEqual(api.calls[-1], ('close',))

    def invoke(self, scenario, filename):
        module = load_program(ROOT / 'scenarios' / scenario / 'input' / filename)
        api, clock, rows = FakeDesktop(), FakeClock(), []
        code = module.run(api, emit=lambda **row: rows.append(row),
                          monotonic=clock.monotonic, sleep=clock.sleep)
        return code, api, clock, rows

    def named(self, api, name):
        return [call for call in api.calls if call[0] == name]

    def test_window_programs_follow_live_powershell_geometry_and_order(self):
        code, api, _, _ = self.invoke('window-shake', 'window-shake.py')
        self.assertEqual(code, 0)
        created = self.named(api, 'create_panel')[0]
        self.assertEqual(created[1:7], ('Arena panel', 557, 313, 806, 453, 0x0078FF))
        moves = self.named(api, 'move')
        self.assertEqual(moves[0][1:], (1, 16, 16))
        self.assertEqual(moves[1][1:], (1, 1098, 16))
        self.assertEqual(moves[-1][1:], (1, 557, 313))

        code, api, _, _ = self.invoke('window-visibility', 'window-visibility.py')
        self.assertEqual(code, 0)
        created = self.named(api, 'create_panel')[0]
        self.assertEqual(created[1:7], ('Arena panel', 365, 205, 1190, 669, 0x0078FF))
        effects = [call[0] for call in api.calls if call[0] in ('hide', 'show')]
        self.assertEqual(effects[:2], ['show', 'hide'])

        code, api, _, _ = self.invoke('window-minimize', 'window-minimize.py')
        self.assertEqual(code, 0)
        effects = [call[0] for call in api.calls if call[0] in ('minimize', 'restore')]
        self.assertEqual(effects[:2], ['restore', 'minimize'])

        code, api, _, _ = self.invoke('window-resize', 'window-resize.py')
        self.assertEqual(code, 0)
        created = self.named(api, 'create_panel')[0]
        self.assertEqual(created[4:6], (422, 237))
        first_resize = self.named(api, 'resize')[0]
        self.assertEqual(first_resize[4:6], (1888, 1032))

        code, api, _, _ = self.invoke('foreground-window', 'foreground-window.py')
        self.assertEqual(code, 0)
        titles = [call[1] for call in self.named(api, 'create_panel')]
        self.assertEqual(titles, ['Work', 'Arena panel'])
        labels = self.named(api, 'set_label')
        self.assertEqual(labels[0][1:], (2, 'IN FRONT'))
        self.assertEqual(labels[1][1:], (1, 'BEHIND'))

    def test_switchers_follow_live_powershell_toggle_order(self):
        code, api, _, _ = self.invoke('mouse-speed', 'mouse-speed.py')
        self.assertEqual(code, 0)
        self.assertEqual([call[1] for call in self.named(api, 'set_speed')],
                         [1, 10, 1, 10, 1, 10, 1, 10, 10])

        code, api, _, _ = self.invoke('mouse-button-swap', 'mouse-button-swap.py')
        self.assertEqual(code, 0)
        self.assertEqual([call[1] for call in self.named(api, 'set_swap')],
                         [1, 0, 1, 0, 1, 0, 1, 0, 0])

        code, api, _, _ = self.invoke('wheel-scroll', 'wheel-scroll.py')
        self.assertEqual(code, 0)
        self.assertEqual([call[1] for call in self.named(api, 'set_wheel')],
                         [20, 3, 20, 3, 20, 3, 20, 3, 3])

        code, api, _, _ = self.invoke('ime-state', 'ime-state.py')
        self.assertEqual(code, 0)
        self.assertEqual([call[1] for call in self.named(api, 'activate_profile')],
                         ['english', 'chinese', 'french', 'english'])
        self.assertEqual(self.named(api, 'restore_profile')[-1], ('restore_profile',))

    def test_ime_restore_passes_zero_saved_hkl_to_activate(self):
        module = load_program(ROOT / 'scenarios' / 'ime-state' / 'input' / 'ime-state.py')
        calls = []
        api = object.__new__(module.NativeAdapter)
        api.saved = module.PROFILE()
        api.saved.dwProfileType = 1
        api.saved.langid = 0x0804
        api.saved.hkl = 0
        api._activate = lambda *args: calls.append(args)
        api.restore_profile()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 1)
        self.assertEqual(calls[0][1], 0x0804)
        self.assertEqual(calls[0][-1], 0)

    def test_cursor_recenter_follows_edge_tour_and_center_lock(self):
        code, api, clock, _ = self.invoke('cursor-recenter', 'cursor-recenter.py')
        self.assertEqual(code, 0)
        self.assertGreaterEqual(clock.now, 25)
        cursors = self.named(api, 'set_cursor')
        self.assertEqual(cursors[0][1:], (180, 180))
        self.assertEqual(cursors[40][1:], (1740, 180))
        self.assertEqual(cursors[41][1:], (1740, 180))
        self.assertGreater(cursors[42][2], 180)
        panels = [call[1] for call in self.named(api, 'create_panel')]
        self.assertEqual(panels, ['pointer marker', 'center bullseye'])
        self.assertEqual(cursors[-1][1:], (100, 200))

    def test_direct_execution_uses_one_complete_native_adapter(self):
        for scenario, filename, _ in CASES:
            with self.subTest(scenario=scenario):
                text = (ROOT / 'scenarios' / scenario / 'input' / filename).read_text(encoding='utf-8')
                self.assertEqual(text.count('class NativeAdapter'), 1)
                self.assertEqual(text.count("if __name__ == '__main__'"), 1)
                self.assertLess(text.index('class NativeAdapter'), text.index("if __name__ == '__main__'"))

    def test_prepare_failure_still_closes(self):
        for scenario, filename, _ in CASES:
            with self.subTest(scenario=scenario):
                module = load_program(ROOT / 'scenarios' / scenario / 'input' / filename)
                api, rows = FakeDesktop(fail='prepare'), []
                code = module.run(api, emit=lambda **row: rows.append(row),
                                  monotonic=FakeClock().monotonic, sleep=FakeClock().sleep)
                self.assertEqual(code, 1)
                self.assertEqual(rows[-1]['status'], 'failed')
                self.assertEqual(api.calls[-1], ('close',))


if __name__ == '__main__':
    unittest.main()
