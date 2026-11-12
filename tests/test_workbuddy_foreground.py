"""Actual desktop focus is required; a CDP screenshot is not sufficient."""
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.adapters.agents.workbuddy import maximize_owned_windows


class WorkBuddyForegroundTests(unittest.TestCase):
    def test_owned_window_moves_to_recording_desktop_before_focus(self):
        from arena.adapters.agents.workbuddy_view import WorkBuddyView
        calls = []
        desktop = MagicMock()
        desktop.move.side_effect = lambda pid: calls.append('move')
        view = WorkBuddyView('node', desktop)
        view.command = MagicMock()
        view.layout = lambda: calls.append('focus')
        with patch('arena.adapters.agents.workbuddy_view.subprocess.Popen'):
            view.connect('ws://127.0.0.1:9333/devtools/page/owned', 999)
        self.assertEqual(calls, ['move', 'focus'])

    def invoke(self, allow):
        user, kernel = MagicMock(), MagicMock()
        state = {'foreground': 202}
        user.EnumWindows.side_effect = lambda callback, unused: callback(101, 0)
        def thread(hwnd, pid):
            if pid is not None:
                pid._obj.value = 999
            return int(hwnd) + 10
        user.GetWindowThreadProcessId.side_effect = thread
        user.IsWindowVisible.return_value = True
        user.GetWindowTextLengthW.return_value = 9
        user.GetForegroundWindow.side_effect = lambda: state['foreground']
        def foreground(hwnd):
            if allow:
                state['foreground'] = int(hwnd)
            return allow
        user.SetForegroundWindow.side_effect = foreground
        kernel.GetCurrentThreadId.return_value = 1
        times = iter(range(100))
        with patch('arena.adapters.agents.workbuddy.ctypes.WinDLL',
                   side_effect=lambda name, **kwargs: user if name == 'user32' else kernel), \
                patch('arena.adapters.agents.workbuddy.time.monotonic', side_effect=lambda: next(times)), \
                patch('arena.adapters.agents.workbuddy.time.sleep'):
            result = maximize_owned_windows({999})
        return result, user

    def test_failed_foreground_activation_cannot_pass_preparation(self):
        with self.assertRaisesRegex(RuntimeError, 'foreground'):
            self.invoke(False)

    def test_owned_foreground_is_verified_after_activation(self):
        result, user = self.invoke(True)
        self.assertEqual(result, [101])
        self.assertGreaterEqual(user.GetForegroundWindow.call_count, 2)
