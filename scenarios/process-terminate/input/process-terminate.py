"""Fixed process-terminate worker. Importing this file has no desktop effects."""

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
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'load'
        child = api.load_target()
        emit(event='start', pid=child['pid'], created=child.get('created'))
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.terminate_process(child['pid'])
        sleep(10)
        alive = api.process_alive(child['pid'])
        emit(event='effectComplete', alive=alive)
        if alive:
            raise RuntimeError('Target process still running after TerminateProcess')
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if child is not None:
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
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateProcess.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.kernel32.GetExitCodeProcess.restype = wintypes.BOOL

    def prepare(self):
        self.emit(event='nativeResult', api='prepare', result=1)
        return 1920, 1080

    def load_target(self):
        path = heartbeat_path()
        if not os.path.isfile(path):
            raise RuntimeError('Heartbeat display is not running')
        data = read_heartbeat(path)
        pid = int(data['pid'])
        if not self.process_alive(pid):
            raise RuntimeError('Heartbeat process is not running')
        self.emit(event='nativeResult', api='load_target', result=1, pid=pid)
        return data

    def terminate_process(self, pid):
        handle = self.kernel32.OpenProcess(0x0001, False, int(pid))
        error = ctypes.get_last_error()
        self.emit(event='nativeResult', api='OpenProcess', result=int(bool(handle)), error=error or None)
        if not handle:
            raise ctypes.WinError(error)
        try:
            ctypes.set_last_error(0)
            result = self.kernel32.TerminateProcess(handle, 1)
            error = ctypes.get_last_error() if not result else None
            self.emit(event='nativeResult', api='TerminateProcess', result=int(result), error=error)
            if not result:
                raise ctypes.WinError(error)
        finally:
            self.kernel32.CloseHandle(handle)

    def process_alive(self, pid):
        handle = self.kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            self.emit(event='nativeResult', api='OpenProcess', result=0, pid=int(pid))
            return False
        code = wintypes.DWORD()
        self.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        self.kernel32.CloseHandle(handle)
        alive = code.value == 259
        self.emit(event='nativeResult', api='GetExitCodeProcess', result=int(code.value), alive=alive)
        return alive

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
