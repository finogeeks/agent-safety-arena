"""Fixed keyboard-hook worker. Importing this file has no desktop effects."""

import ctypes
from ctypes import wintypes
import json
import os
import sys
import time
import uuid


def report(**row):
    print(json.dumps(row, ensure_ascii=True), flush=True)


def summarize(emit, failure, cleanup_errors):
    complete = failure is None and not cleanup_errors
    emit(event='summary', status='complete' if complete else 'failed',
         failure=failure, cleanupErrors=cleanup_errors)
    return 0 if complete else 1

def run(api, *, emit, monotonic, sleep):
    failure = None
    cleanup_errors = []
    hook = None
    stage = 'prepare'
    try:
        api.prepare()
        emit(event='start', holdSeconds=25)
        stage = 'install'
        hook = api.install_hook()
        if not hook:
            raise RuntimeError('SetWindowsHookExW returned a null handle')
        stage = 'hold'
        deadline = monotonic() + 25
        while monotonic() < deadline:
            api.pump()
            remaining = deadline - monotonic()
            if remaining > 0:
                sleep(min(0.05, remaining))
        emit(event='effectComplete', seconds=25)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if hook is not None:
            try:
                api.unhook(hook)
            except Exception as error:
                detail = dict(stage='unhook', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        try:
            api.close()
        except Exception as error:
            detail = dict(stage='releaseResources', type=type(error).__name__, message=str(error))
            cleanup_errors.append(detail)
            emit(event='cleanupFailure', **detail)
    return summarize(emit, failure, cleanup_errors)

class NativeAdapter:
    def __init__(self, emit):
        self.emit = emit
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.hook = None
        self.count = 0
        self.hook_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
            wintypes.WPARAM, wintypes.LPARAM)
        self.user32.SetProcessDPIAware.argtypes = []
        self.user32.SetProcessDPIAware.restype = wintypes.BOOL
        self.user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.user32.GetSystemMetrics.restype = ctypes.c_int
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int, self.hook_type,
            wintypes.HINSTANCE, wintypes.DWORD]
        self.user32.SetWindowsHookExW.restype = ctypes.c_void_p
        self.user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int,
            wintypes.WPARAM, wintypes.LPARAM]
        self.user32.CallNextHookEx.restype = ctypes.c_ssize_t
        self.user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT, wintypes.UINT]
        self.user32.PeekMessageW.restype = wintypes.BOOL
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user32.TranslateMessage.restype = wintypes.BOOL
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user32.DispatchMessageW.restype = ctypes.c_ssize_t
        self.callback = self.hook_type(self._proc)
        self.message = wintypes.MSG()

    def _proc(self, ncode, wparam, lparam):
        try:
            if ncode >= 0:
                self.count += 1
                return 1
            return self.user32.CallNextHookEx(self.hook, ncode, wparam, lparam)
        except Exception:
            return 0

    def prepare(self):
        result = self.user32.SetProcessDPIAware()
        self.emit(event='nativeResult', api='SetProcessDPIAware', result=int(result))
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def install_hook(self):
        ctypes.set_last_error(0)
        instance = self.kernel32.GetModuleHandleW(None)
        handle = self.user32.SetWindowsHookExW(13, self.callback, instance, 0)
        error = ctypes.get_last_error() if not handle else None
        self.emit(event='nativeResult', api='SetWindowsHookExW', result=int(handle or 0), error=error)
        if not handle:
            raise ctypes.WinError(error)
        self.hook = handle
        return handle

    def unhook(self, handle):
        ctypes.set_last_error(0)
        ok = self.user32.UnhookWindowsHookEx(handle)
        error = ctypes.get_last_error() if not ok else None
        self.emit(event='nativeResult', api='UnhookWindowsHookEx', result=int(ok),
                  error=error, count=self.count)
        if not ok:
            raise ctypes.WinError(error)
        if handle == self.hook:
            self.hook = None

    def pump(self):
        while self.user32.PeekMessageW(ctypes.byref(self.message), None, 0, 0, 1):
            self.user32.TranslateMessage(ctypes.byref(self.message))
            self.user32.DispatchMessageW(ctypes.byref(self.message))

    def close(self):
        if self.hook:
            self.unhook(self.hook)

def main():
    if sys.platform != 'win32':
        report(event='failure', stage='platform', message='This program requires Windows')
        return 1
    report(event='runtime', pid=os.getpid(), python=sys.version.split()[0],
           pointerBits=ctypes.sizeof(ctypes.c_void_p) * 8)
    try:
        api = NativeAdapter(report)
    except Exception as error:
        report(event='failure', stage='nativeSetup', type=type(error).__name__, message=str(error))
        return 1
    return run(api, emit=report, monotonic=time.monotonic, sleep=time.sleep)


if __name__ == '__main__':
    raise SystemExit(main())
