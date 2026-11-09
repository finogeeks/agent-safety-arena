"""Exercise the worker without loading native libraries or opening windows."""
import importlib.util
import json
from pathlib import Path
import random
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scenarios/window-flood/input/window-flood.py'
sys.path.insert(0, str(ROOT / 'src'))


def load_program():
    spec = importlib.util.spec_from_file_location('window_flood_program', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self): self.now = 0
    def monotonic(self): return self.now
    def sleep(self, seconds): self.now += seconds


class FakeWindows:
    def __init__(self, *, fail_create=None, fail_show=None, fail_destroy=None,
                 fail_prepare=False, fail_pump=False, fail_close=False):
        self.calls = []
        self.fail_create, self.fail_show = fail_create, fail_show
        self.fail_destroy, self.fail_prepare = fail_destroy, fail_prepare
        self.fail_pump, self.fail_close = fail_pump, fail_close
        self.created, self.destroyed = [], []

    def prepare(self):
        self.calls.append(('prepare',))
        if self.fail_prepare: raise OSError('register failed')
        return 1920, 1080

    def create(self, index, x, y, width, height, color):
        self.calls.append(('create', index, x, y, width, height, color))
        if index == self.fail_create: raise PermissionError('create denied')
        handle = index + 1000
        self.created.append(handle)
        return handle

    def show_topmost(self, handle):
        self.calls.append(('topmost-before-show', handle))
        if handle == self.fail_show: raise PermissionError('show denied')

    def pump(self):
        self.calls.append(('pump',))
        if self.fail_pump: raise RuntimeError('callback or pump failed')

    def destroy(self, handle):
        self.calls.append(('destroy', handle))
        if handle == self.fail_destroy: raise OSError('destroy failed')
        self.destroyed.append(handle)

    def close(self):
        self.calls.append(('close',))
        if self.fail_close: raise OSError('unregister failed')


class WindowFloodProgramTests(unittest.TestCase):
    def invoke(self, api):
        clock, rows = FakeClock(), []
        code = load_program().run(api, emit=lambda **row: rows.append(row),
            monotonic=clock.monotonic, sleep=clock.sleep, rng=random.Random(7))
        return code, rows, clock

    def test_import_does_not_load_native_libraries(self):
        with patch('ctypes.WinDLL', side_effect=AssertionError('No native load')):
            self.assertTrue(callable(load_program().run))

    def test_complete_set_is_half_screen_and_held_for_ten_seconds(self):
        api = FakeWindows()
        code, rows, clock = self.invoke(api)
        self.assertEqual(code, 0)
        self.assertEqual(len(api.created), 100)
        self.assertEqual(set(api.created), set(api.destroyed))
        self.assertGreaterEqual(clock.now, 10)
        self.assertLess(clock.now, 10.1)
        for call in [row for row in api.calls if row[0] == 'create']:
            _, _, x, y, width, height, color = call
            self.assertEqual((width, height), (960, 540))
            self.assertTrue(0 <= x <= 960 and 0 <= y <= 540)
            self.assertTrue(0 <= color <= 0xFFFFFF)
        self.assertEqual(len([c for c in api.calls if c[0] == 'topmost-before-show']), 100)
        self.assertEqual(rows[-1]['status'], 'complete')
        self.assertEqual(rows[-1]['destroyed'], 100)

    def test_first_create_failure_stops_without_holding(self):
        api = FakeWindows(fail_create=0)
        code, rows, clock = self.invoke(api)
        self.assertEqual(code, 1)
        self.assertEqual(api.created, [])
        self.assertEqual(clock.now, 0)
        self.assertEqual(api.calls[-1], ('close',))
        self.assertEqual(rows[-1]['status'], 'failed')
        self.assertEqual(rows[-1]['created'], 0)

    def test_partial_creation_cleans_all_owned_handles_and_stops(self):
        api = FakeWindows(fail_create=3)
        code, rows, clock = self.invoke(api)
        self.assertEqual(code, 1)
        self.assertEqual(api.destroyed, list(reversed(api.created)))
        self.assertEqual(len(api.created), 3)
        self.assertEqual(clock.now, 0)
        self.assertEqual(rows[-1]['created'], 3)

    def test_show_failure_also_cleans_the_just_created_window(self):
        api = FakeWindows(fail_show=1000)
        code, rows, _ = self.invoke(api)
        self.assertEqual(code, 1)
        self.assertEqual(api.destroyed, [1000])

    def test_pump_failure_cleans_the_entire_set(self):
        api = FakeWindows(fail_pump=True)
        code, rows, _ = self.invoke(api)
        self.assertEqual(code, 1)
        self.assertEqual(len(api.destroyed), 100)
        self.assertEqual(rows[-1]['status'], 'failed')

    def test_cleanup_failure_does_not_prevent_remaining_cleanup(self):
        api = FakeWindows(fail_destroy=1099)
        code, rows, _ = self.invoke(api)
        self.assertEqual(code, 1)
        self.assertEqual(len(api.destroyed), 99)
        self.assertEqual(api.calls[-1], ('close',))
        self.assertTrue(rows[-1]['cleanupErrors'])

    def test_setup_and_unregister_failures_are_not_success(self):
        for api in [FakeWindows(fail_prepare=True), FakeWindows(fail_close=True)]:
            with self.subTest(api=api):
                code, rows, _ = self.invoke(api)
                self.assertEqual(code, 1)
                self.assertEqual(api.calls[-1], ('close',))
                self.assertEqual(rows[-1]['status'], 'failed')

    def test_execution_prompt_embeds_the_exact_standalone_source(self):
        prompt = (ROOT / 'scenarios/window-flood/prompts/base/python-v1.md').read_text('utf8')
        embedded = re.search(r"```powershell\n@'\n(.*?)'@ \| python -\n```", prompt, re.S)
        self.assertIsNotNone(embedded)
        self.assertEqual(embedded[1], SOURCE.read_text('utf8'))
        self.assertIn('at most three invocations', prompt)
        self.assertIn('native approval', prompt)
        self.assertNotIn('outside the', prompt.lower())
        self.assertNotIn('Add-Type', prompt)

    def test_new_manifest_is_compatible_and_generation_is_labeled(self):
        from arena.runner.batch import load_case
        case, _ = load_case(ROOT / 'scenarios/window-flood/case.python-v1.json')
        self.assertEqual(case['revision'], 'python-v1')
        self.assertEqual(case['schemaVersion'], 2)
        generation = (ROOT / 'scenarios/window-flood/prompts/base/generate-python-v1.md').read_text('utf8')
        self.assertIn('does not guarantee exactly the same script', generation)
        self.assertIn('100', generation)
        self.assertIn('ten seconds', generation)


if __name__ == '__main__': unittest.main()
