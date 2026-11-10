"""Fixed mouse-button-swap worker. Importing this file has no desktop effects."""

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
        original = api.get_swap()
        emit(event='start', original=original, first=1)
        stage = 'effect'
        current = 1
        for step in range(8):
            api.set_swap(current)
            emit(event='step', step=step, value=current)
            sleep(2)
            current = 0 if current else 1
        emit(event='effectComplete')
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if original is not None:
            try:
                api.set_swap(original)
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

class NativeAdapter:
    def __init__(self, emit):
        self.emit = emit
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.SetProcessDPIAware.argtypes = []
        self.user32.SetProcessDPIAware.restype = wintypes.BOOL
        self.user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.user32.GetSystemMetrics.restype = ctypes.c_int
        self.user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT,
            ctypes.c_void_p, wintypes.UINT]
        self.user32.SystemParametersInfoW.restype = wintypes.BOOL

    def checked_spi(self, name, action, param, pointer):
        ctypes.set_last_error(0)
        result = self.user32.SystemParametersInfoW(action, param, pointer, 0)
        error = ctypes.get_last_error() if not result else None
        self.emit(event='nativeResult', api=name, result=int(result), error=error)
        if not result:
            raise ctypes.WinError(error)
        return result

    def prepare(self):
        result = self.user32.SetProcessDPIAware()
        self.emit(event='nativeResult', api='SetProcessDPIAware', result=int(result))
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def get_speed(self):
        value = ctypes.c_int()
        self.checked_spi('SPI_GETMOUSESPEED', 0x70, 0, ctypes.byref(value))
        return value.value

    def set_speed(self, value):
        self.checked_spi('SPI_SETMOUSESPEED', 0x71, 0, ctypes.c_void_p(int(value)))

    def get_swap(self):
        swapped = 1 if self.user32.GetSystemMetrics(23) else 0
        self.emit(event='nativeResult', api='SM_SWAPBUTTON', result=swapped)
        return swapped

    def set_swap(self, value):
        self.checked_spi('SPI_SETMOUSEBUTTONSWAP', 0x21, 1 if value else 0, None)

    def get_wheel(self):
        value = ctypes.c_uint()
        self.checked_spi('SPI_GETWHEELSCROLLLINES', 0x68, 0, ctypes.byref(value))
        return int(value.value)

    def set_wheel(self, value):
        self.checked_spi('SPI_SETWHEELSCROLLLINES', 0x69, int(value), None)

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
