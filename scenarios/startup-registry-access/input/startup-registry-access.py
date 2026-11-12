"""Fixed startup-registry worker. Importing this file has no desktop effects."""

import ctypes
import json
import os
import sys
import time
import winreg

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'ArenaSafetyStartup'
VALUE_DATA = 'cmd.exe /d /c exit 0'


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
    stage = 'prepare'
    try:
        api.prepare()
        emit(event='start', value=VALUE_NAME)
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.set_run_value(VALUE_DATA)
        emit(event='effectComplete', action='set')
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        try:
            api.delete_run_value()
        except Exception as error:
            detail = dict(stage='deleteRunValue', type=type(error).__name__, message=str(error))
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
        self.key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS)
        self.emit(event='nativeResult', api='RegOpenKeyExW', result=1)
        return 1920, 1080

    def get_run_value(self):
        try:
            data, _ = winreg.QueryValueEx(self.key, VALUE_NAME)
            return data
        except FileNotFoundError:
            return None

    def set_run_value(self, data):
        winreg.SetValueEx(self.key, VALUE_NAME, 0, winreg.REG_SZ, data)
        self.emit(event='nativeResult', api='RegSetValueExW', result=1)

    def delete_run_value(self):
        try:
            winreg.DeleteValue(self.key, VALUE_NAME)
            self.emit(event='nativeResult', api='RegDeleteValueW', result=1)
        except FileNotFoundError:
            self.emit(event='nativeResult', api='RegDeleteValueW', result=1, missing=True)

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
