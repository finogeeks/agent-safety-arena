"""Fixed display-resolution worker. Importing this file has no desktop effects."""

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
    original = None
    stage = 'prepare'
    try:
        api.prepare()
        original = api.get_mode()
        emit(event='start', original=list(original), target=[1920, 1080])
        stage = 'effect'
        deadline = monotonic() + 25
        step = 0
        while monotonic() < deadline:
            if step % 2 == 0:
                api.set_mode(1920, 1080)
            else:
                api.set_mode(*original)
            step += 1
            remaining = deadline - monotonic()
            if remaining > 0:
                sleep(min(2, remaining))
        emit(event='effectComplete', steps=step)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if original is not None:
            try:
                api.set_mode(*original)
            except Exception as error:
                detail = dict(stage='restore', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        try:
            api.close()
        except Exception as error:
            detail = dict(stage='releaseResources', type=type(error).__name__, message=str(error))
            cleanup_errors.append(detail)
            emit(event='cleanupFailure', **detail)
    return summarize(emit, failure, cleanup_errors)

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ('dmDeviceName', wintypes.WCHAR * 32),
        ('dmSpecVersion', wintypes.WORD),
        ('dmDriverVersion', wintypes.WORD),
        ('dmSize', wintypes.WORD),
        ('dmDriverExtra', wintypes.WORD),
        ('dmFields', wintypes.DWORD),
        ('dmPositionX', wintypes.LONG),
        ('dmPositionY', wintypes.LONG),
        ('dmDisplayOrientation', wintypes.DWORD),
        ('dmDisplayFixedOutput', wintypes.DWORD),
        ('dmColor', wintypes.SHORT),
        ('dmDuplex', wintypes.SHORT),
        ('dmYResolution', wintypes.SHORT),
        ('dmTTOption', wintypes.SHORT),
        ('dmCollate', wintypes.SHORT),
        ('dmFormName', wintypes.WCHAR * 32),
        ('dmLogPixels', wintypes.WORD),
        ('dmBitsPerPel', wintypes.DWORD),
        ('dmPelsWidth', wintypes.DWORD),
        ('dmPelsHeight', wintypes.DWORD),
        ('dmDisplayFlags', wintypes.DWORD),
        ('dmDisplayFrequency', wintypes.DWORD),
        ('dmICMMethod', wintypes.DWORD),
        ('dmICMIntent', wintypes.DWORD),
        ('dmMediaType', wintypes.DWORD),
        ('dmDitherType', wintypes.DWORD),
        ('dmReserved1', wintypes.DWORD),
        ('dmReserved2', wintypes.DWORD),
        ('dmPanningWidth', wintypes.DWORD),
        ('dmPanningHeight', wintypes.DWORD),
    ]


class NativeAdapter:
    def __init__(self, emit):
        self.emit = emit
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.SetProcessDPIAware.argtypes = []
        self.user32.SetProcessDPIAware.restype = wintypes.BOOL
        self.user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.user32.GetSystemMetrics.restype = ctypes.c_int
        self.user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.POINTER(DEVMODEW)]
        self.user32.EnumDisplaySettingsW.restype = wintypes.BOOL
        self.user32.ChangeDisplaySettingsExW.argtypes = [wintypes.LPCWSTR,
            ctypes.POINTER(DEVMODEW), wintypes.HWND, wintypes.DWORD, ctypes.c_void_p]
        self.user32.ChangeDisplaySettingsExW.restype = ctypes.c_long

    def _blank(self):
        mode = DEVMODEW()
        mode.dmSize = ctypes.sizeof(DEVMODEW)
        return mode

    def prepare(self):
        result = self.user32.SetProcessDPIAware()
        self.emit(event='nativeResult', api='SetProcessDPIAware', result=int(result))
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def get_mode(self):
        mode = self._blank()
        ok = self.user32.EnumDisplaySettingsW(None, 0xFFFFFFFF, ctypes.byref(mode))
        self.emit(event='nativeResult', api='EnumDisplaySettingsW', result=int(ok),
                  width=int(mode.dmPelsWidth), height=int(mode.dmPelsHeight))
        if not ok:
            raise RuntimeError('EnumDisplaySettingsW failed')
        return int(mode.dmPelsWidth), int(mode.dmPelsHeight)

    def _find(self, width, height):
        best = None
        best_score = 10 ** 9
        for index in range(400):
            mode = self._blank()
            if not self.user32.EnumDisplaySettingsW(None, index, ctypes.byref(mode)):
                break
            score = abs(int(mode.dmPelsWidth) - width) + abs(int(mode.dmPelsHeight) - height)
            if best is None or score < best_score or (
                    score == best_score and mode.dmDisplayFrequency > best.dmDisplayFrequency):
                best = mode
                best_score = score
        if best is None:
            raise RuntimeError('No display mode is available')
        return best

    def set_mode(self, width, height):
        mode = self._find(width, height)
        code = self.user32.ChangeDisplaySettingsExW(None, ctypes.byref(mode), None, 0, None)
        self.emit(event='nativeResult', api='ChangeDisplaySettingsExW', result=int(code),
                  width=int(mode.dmPelsWidth), height=int(mode.dmPelsHeight))
        if code != 0:
            raise RuntimeError('ChangeDisplaySettingsExW returned ' + str(code))

    def close(self):
        return None

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
