"""Cleanup accepts the created fragment under Windows package virtualization."""
import os
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.adapters.agents.codex_terminal import NativeTerminalView


class FragmentCleanupTests(unittest.TestCase):
    def test_changed_title_still_closes_the_recorded_owned_handle(self):
        user = MagicMock()
        user.IsWindow.return_value = True
        def process(hwnd, pid):
            pid._obj.value = 45
            return 9
        user.GetWindowThreadProcessId.side_effect = process
        view = NativeTerminalView({}, None)
        view.title, view.handle, view.pid = 'old title', 123, 45
        with patch('arena.adapters.agents.codex_terminal.native_window', return_value=None), \
                patch('arena.adapters.agents.codex_terminal.c.WinDLL', return_value=user):
            view.close()
        user.PostMessageW.assert_called_once_with(123, 0x0010, 0, 0)

    def test_reused_handle_owned_by_another_process_is_not_closed(self):
        user = MagicMock()
        user.IsWindow.return_value = True
        def process(hwnd, pid):
            pid._obj.value = 46
            return 9
        user.GetWindowThreadProcessId.side_effect = process
        view = NativeTerminalView({}, None)
        view.title, view.handle, view.pid = 'old title', 123, 45
        with patch('arena.adapters.agents.codex_terminal.native_window', return_value=None), \
                patch('arena.adapters.agents.codex_terminal.c.WinDLL', return_value=user):
            view.close()
        user.PostMessageW.assert_not_called()

    def test_exact_owned_fragment_cleans_up_on_packaged_host(self):
        name = 'test-fragment-' + uuid.uuid4().hex
        root = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/Windows Terminal/Fragments'
        folder = root / ('Arena-' + name)
        folder.mkdir()
        fragment = folder / 'profile.json'
        fragment.write_text('{}', encoding='utf8')
        view = NativeTerminalView({}, None)
        view.directory = Path(name)
        view.fragment = fragment
        try:
            view.close()
            self.assertFalse(fragment.exists())
            self.assertFalse(folder.exists())
        finally:
            if fragment.exists():
                fragment.unlink()
            if folder.exists():
                folder.rmdir()

    def test_other_run_fragment_is_not_deleted(self):
        name = 'test-fragment-' + uuid.uuid4().hex
        root = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/Windows Terminal/Fragments'
        folder = root / ('Arena-' + name)
        folder.mkdir()
        fragment = folder / 'profile.json'
        fragment.write_text('{}', encoding='utf8')
        view = NativeTerminalView({}, None)
        view.directory = Path('different-run')
        view.fragment = fragment
        try:
            with self.assertRaises(RuntimeError):
                view.close()
            self.assertTrue(fragment.exists())
        finally:
            fragment.unlink()
            folder.rmdir()
