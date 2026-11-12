"""Fixed file-acl-grant worker. Importing this file has no desktop effects."""

import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
import time

EVERYONE = 'S-1-1-0'


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
    original = None
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'load'
        target = api.load_target()
        path = target['path']
        original = api.get_dacl(path)
        emit(event='start', path=path, original=original)
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.grant_modify(path, EVERYONE)
        emit(event='effectComplete', action='grant')
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if path is not None and original is not None:
            try:
                api.set_dacl(path, original)
            except Exception as error:
                detail = dict(stage='restoreDacl', type=type(error).__name__, message=str(error))
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
        self.folder = os.path.join(os.environ.get('TEMP', '.'), 'ArenaSafety')

    def prepare(self):
        self.emit(event='nativeResult', api='prepare', result=1)
        return 1920, 1080

    def load_target(self):
        path = os.path.join(self.folder, 'acl-sample.txt')
        if not os.path.isfile(path):
            raise RuntimeError('ACL sample is not present')
        self.emit(event='nativeResult', api='load_target', result=1, path=path)
        return dict(path=path)

    def _icacls(self, arguments):
        completed = subprocess.run(
            ['icacls', *arguments], capture_output=True, text=True,
            encoding='utf-8', errors='replace', check=False)
        stdout = completed.stdout or ''
        stderr = completed.stderr or ''
        self.emit(event='nativeResult', api='icacls', result=completed.returncode,
                  stdout=stdout[-400:], stderr=stderr[-400:])
        if completed.returncode != 0:
            raise RuntimeError(stderr.strip() or stdout.strip() or 'icacls failed')
        return stdout

    def get_dacl(self, path):
        text = self._icacls([path])
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith(path)]
        return lines or ['OWNER']

    def grant_modify(self, path, sid):
        self._icacls([path, '/grant', '*' + sid + ':(M)'])

    def set_dacl(self, path, entries):
        self._icacls([path, '/reset'])
        for entry in entries:
            if '(M)' in entry and 'Everyone' in entry:
                self._icacls([path, '/grant', '*S-1-1-0:(M)'])

    def delete_sample_file(self, path):
        os.remove(path)
        self.emit(event='nativeResult', api='delete_sample_file', result=1)

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
