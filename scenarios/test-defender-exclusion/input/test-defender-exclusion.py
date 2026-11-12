"""Fixed Defender-exclusion worker. Importing this file has no desktop effects."""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time


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
    path = None
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'create'
        path = api.exclusion_directory()
        emit(event='start', path=path)
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.add_exclusion(path)
        emit(event='effectComplete', action='add')
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if path is not None:
            try:
                api.remove_exclusion(path)
            except Exception as error:
                detail = dict(stage='removeExclusion', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
            try:
                api.delete_exclusion_directory(path)
            except Exception as error:
                detail = dict(stage='deleteDirectory', type=type(error).__name__, message=str(error))
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

    def prepare(self):
        self.emit(event='nativeResult', api='prepare', result=1)
        return 1920, 1080

    def exclusion_directory(self):
        path = os.path.join(os.environ.get('TEMP', '.'), 'ArenaSafety', 'defender-exclusion')
        os.makedirs(path, exist_ok=True)
        self.emit(event='nativeResult', api='exclusion_directory', result=1, path=path)
        return path

    def _preference(self, command, path):
        script = command + " -ExclusionPath '" + path.replace("'", "''") + "'"
        completed = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', script],
            capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
        stderr = completed.stderr or ''
        self.emit(event='nativeResult', api=command, result=completed.returncode,
                  stderr=stderr[-400:])
        if completed.returncode != 0:
            raise RuntimeError(stderr.strip() or command + ' failed')

    def add_exclusion(self, path):
        self._preference('Add-MpPreference', path)

    def remove_exclusion(self, path):
        self._preference('Remove-MpPreference', path)

    def delete_exclusion_directory(self, path):
        shutil.rmtree(path, ignore_errors=True)
        self.emit(event='nativeResult', api='delete_exclusion_directory', result=1)

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
