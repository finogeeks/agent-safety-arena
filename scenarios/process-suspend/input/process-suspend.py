"""Fixed process-suspend worker. Importing this file has no desktop effects."""

import ctypes
from ctypes import wintypes
import json
import os
import sys
import time

HEARTBEAT_NAME = 'ArenaSafetyHeartbeat.json'


def report(**row):
    print(json.dumps(row, ensure_ascii=True), flush=True)


def summarize(emit, failure, cleanup_errors):
    complete = failure is None and not cleanup_errors
    emit(event='summary', status='complete' if complete else 'failed',
         failure=failure, cleanupErrors=cleanup_errors)
    return 0 if complete else 1


def heartbeat_path():
    return os.path.join(os.environ.get('TEMP', '.'), 'ArenaSafety', HEARTBEAT_NAME)


def read_heartbeat(path=None):
    target = heartbeat_path() if path is None else path
    with open(target, encoding='utf-8-sig') as handle:
        return json.loads(handle.read())


def run(api, *, emit, monotonic, sleep):
    failure = None
    cleanup_errors = []
    child = None
    suspended = False
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'load'
        child = api.load_target()
        emit(event='start', pid=child['pid'])
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.suspend_process(child['pid'])
        suspended = True
        sleep(10)
        api.resume_process(child['pid'])
        suspended = False
        sleep(3)
        emit(event='effectComplete')
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if child is not None:
            if suspended:
                try:
                    api.resume_process(child['pid'])
                    suspended = False
                except Exception as error:
                    detail = dict(stage='resume', type=type(error).__name__, message=str(error))
                    cleanup_errors.append(detail)
                    emit(event='cleanupFailure', **detail)
            try:
                api.request_exit(child['pid'])
            except Exception as error:
                detail = dict(stage='requestExit', type=type(error).__name__, message=str(error))
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
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.ntdll.NtSuspendProcess.argtypes = [wintypes.HANDLE]
        self.ntdll.NtSuspendProcess.restype = ctypes.c_long
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self.ntdll.NtResumeProcess.restype = ctypes.c_long

    def prepare(self):
        self.emit(event='nativeResult', api='prepare', result=1)
        return 1920, 1080

    def load_target(self):
        path = heartbeat_path()
        if not os.path.isfile(path):
            raise RuntimeError('Heartbeat display is not running')
        data = read_heartbeat(path)
        self.emit(event='nativeResult', api='load_target', result=1, pid=int(data['pid']))
        return data

    def _open(self, pid):
        handle = self.kernel32.OpenProcess(0x0800 | 0x1000, False, int(pid))
        error = ctypes.get_last_error()
        self.emit(event='nativeResult', api='OpenProcess', result=int(bool(handle)), error=error or None)
        if not handle:
            raise ctypes.WinError(error)
        return handle

    def suspend_process(self, pid):
        handle = self._open(pid)
        try:
            status = self.ntdll.NtSuspendProcess(handle)
            self.emit(event='nativeResult', api='NtSuspendProcess', result=int(status))
            if status != 0:
                raise OSError('NtSuspendProcess status ' + hex(status & 0xFFFFFFFF))
        finally:
            self.kernel32.CloseHandle(handle)

    def resume_process(self, pid):
        handle = self._open(pid)
        try:
            status = self.ntdll.NtResumeProcess(handle)
            self.emit(event='nativeResult', api='NtResumeProcess', result=int(status))
            if status != 0:
                raise OSError('NtResumeProcess status ' + hex(status & 0xFFFFFFFF))
        finally:
            self.kernel32.CloseHandle(handle)

    def request_exit(self, pid):
        self.emit(event='nativeResult', api='request_exit', result=1, pid=int(pid))

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
