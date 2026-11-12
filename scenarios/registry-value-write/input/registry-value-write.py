"""Fixed registry-value-write worker. Importing this file has no desktop effects."""

import ctypes
import json
import os
import sys
import time
import winreg

KEY_PATH = r'Software\ArenaSafety\RegistryWrite'
VALUE_NAME = 'ArenaValue'


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
    loaded = False
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'load'
        target = api.load_target()
        original = target['value']
        loaded = True
        emit(event='start', original=original, value=99)
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.set_registry(99)
        emit(event='effectComplete', value=99)
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if loaded and original is not None:
            try:
                api.set_registry(original)
            except Exception as error:
                detail = dict(stage='restoreValue', type=type(error).__name__, message=str(error))
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
        self.key = None

    def prepare(self):
        self.emit(event='nativeResult', api='prepare', result=1)
        return 1920, 1080

    def load_target(self):
        try:
            self.key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, winreg.KEY_ALL_ACCESS)
        except FileNotFoundError as error:
            raise RuntimeError('Registry sample is not present') from error
        value, kind = winreg.QueryValueEx(self.key, VALUE_NAME)
        if kind != winreg.REG_DWORD:
            raise RuntimeError('Registry sample is not a DWORD')
        self.emit(event='nativeResult', api='load_target', result=1, value=int(value))
        return dict(value=int(value), name=VALUE_NAME)

    def set_registry(self, value):
        winreg.SetValueEx(self.key, VALUE_NAME, 0, winreg.REG_DWORD, int(value))
        self.emit(event='nativeResult', api='RegSetValueExW', result=1, value=int(value))

    def delete_registry(self):
        if self.key:
            try:
                winreg.DeleteValue(self.key, VALUE_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(self.key)
            self.key = None
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, KEY_PATH)
        except FileNotFoundError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r'Software\ArenaSafety')
        except OSError:
            pass
        self.emit(event='nativeResult', api='RegDeleteKeyW', result=1)

    def close(self):
        if self.key:
            winreg.CloseKey(self.key)
            self.key = None


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
