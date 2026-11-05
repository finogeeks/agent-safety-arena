"""Windows-only integration checks use disposable owned processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


@unittest.skipUnless(sys.platform=='win32','Windows process boundary')
class WindowsJobTests(unittest.TestCase):
    def test_observer_records_only_the_owned_native_window(self):
        from arena.adapters.environments.windows_job import WindowsJob
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gate = root/'start'
            code = ('import ctypes,time,pathlib; from ctypes import wintypes as w; '
                    f'gate=pathlib.Path({str(gate)!r}); '
                    'exec("while not gate.exists(): time.sleep(.02)"); '
                    'u=ctypes.WinDLL("user32"); '
                    'u.CreateWindowExW.restype=w.HWND; '
                    'u.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]; '
                    'h=u.CreateWindowExW(0,"STATIC","Arena owned hidden fixture",0x00CF0000,20,20,240,160,None,None,None,None); '
                    'assert h; time.sleep(30)')
            job = WindowsJob()
            parent = subprocess.Popen([sys.executable,'-c',code],creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                job.assign(parent,root)
                gate.touch()
                deadline = time.monotonic()+10
                snapshot = job.snapshot()
                while not snapshot['windows'] and time.monotonic()<deadline:
                    time.sleep(.1)
                    snapshot = job.snapshot()
                # Windows may also create owned hidden IME helper windows.
                self.assertTrue(any(window['bounds']==[20,20,260,180] for window in snapshot['windows']))
                self.assertTrue(all(window['pid']==parent.pid for window in snapshot['windows']))
                self.assertTrue(all(not window['visible'] for window in snapshot['windows']))
                self.assertTrue(job.close()['recovered'])
                parent.wait(timeout=5)
            finally:
                job.close()
                if parent.poll() is None:
                    parent.terminate()
                    parent.wait(timeout=5)

    def test_job_recovers_owned_parent_and_child(self):
        from arena.adapters.environments.windows_job import WindowsJob
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = WindowsJob()
            parent = subprocess.Popen([sys.executable,'-c',
                'import subprocess,sys,time; time.sleep(.5); '
                'subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); time.sleep(30)'],
                creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                job.assign(parent,root)
                deadline = time.monotonic()+10
                while len(job.pids())<2 and time.monotonic()<deadline:
                    time.sleep(.1)
                self.assertEqual(len(job.pids()),2)
                self.assertNotIn(os.getpid(),job.pids())
                recovery = job.close()
                self.assertTrue(recovery['recovered'])
                self.assertIsNone(recovery['observerError'])
                parent.wait(timeout=5)
                rows = [json.loads(line) for line in (root/'native-window-observations.jsonl').read_text().splitlines()]
                self.assertTrue(any(row['processes'] for row in rows))
            finally:
                job.close()
                if parent.poll() is None:
                    parent.terminate()
                    parent.wait(timeout=5)


if __name__=='__main__':
    unittest.main()
