"""Fixed service-stop worker. Importing this file has no desktop effects."""

import json
import os
import subprocess
import sys
import time

SERVICE_NAME = 'ArenaStopSvc'


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
    loaded = False
    stop_ok = False
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'load'
        name = api.load_target()
        loaded = True
        emit(event='start', service=name, status=api.query_service())
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.stop_service()
        stop_ok = True
        emit(event='effectComplete', status='STOPPED')
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if loaded:
            if not stop_ok:
                emit(event='leftoverService', service=SERVICE_NAME,
                     reason='every evaluated stop failed; host recovery may stop and delete later')
            else:
                try:
                    if api.query_service() != 'RUNNING':
                        api.start_service()
                except Exception as error:
                    detail = dict(stage='restoreRunning', type=type(error).__name__, message=str(error))
                    cleanup_errors.append(detail)
                    emit(event='cleanupFailure', **detail)
                try:
                    api.stop_service()
                    api.delete_service()
                except Exception as error:
                    detail = dict(stage='teardownService', type=type(error).__name__, message=str(error))
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

    def _schtasks(self, arguments):
        completed = subprocess.run(
            ['schtasks.exe', *arguments], capture_output=True, text=True,
            encoding='utf-8', errors='replace', check=False)
        stdout = completed.stdout or ''
        stderr = completed.stderr or ''
        self.emit(event='nativeResult', api='schtasks', result=completed.returncode,
                  args=arguments, stdout=stdout[-400:], stderr=stderr[-400:])
        if completed.returncode != 0:
            raise RuntimeError((stderr.strip() or stdout.strip() or 'schtasks failed'))
        return stdout

    def load_target(self):
        status = self.query_service()
        self.emit(event='nativeResult', api='load_target', result=1, service=SERVICE_NAME, status=status)
        if status != 'RUNNING':
            raise RuntimeError('ArenaStopSvc is not running')
        return SERVICE_NAME

    def query_service(self):
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        completed = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command',
             "[string]((Get-ScheduledTask -TaskName '" + SERVICE_NAME +
             "' -ErrorAction SilentlyContinue).State)"],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            check=False, creationflags=flags)
        state = (completed.stdout or '').strip()
        self.emit(event='nativeResult', api='Get-ScheduledTask', result=completed.returncode,
                  state=state, stderr=(completed.stderr or '')[-400:])
        if state == 'Running':
            return 'RUNNING'
        if not state:
            return 'ABSENT'
        return 'STOPPED'

    def stop_service(self):
        self._schtasks(['/End', '/TN', SERVICE_NAME])

    def start_service(self):
        self._schtasks(['/Run', '/TN', SERVICE_NAME])

    def delete_service(self):
        self._schtasks(['/Delete', '/TN', SERVICE_NAME, '/F'])

    def close(self):
        return None


def main():
    if sys.platform != 'win32':
        report(event='failure', stage='platform', message='This program requires Windows')
        return 1
    report(event='runtime', pid=os.getpid(), python=sys.version.split()[0])
    try:
        api = NativeAdapter(report)
    except Exception as error:
        report(event='failure', stage='nativeSetup', type=type(error).__name__, message=str(error))
        return 1
    return run(api, emit=report, monotonic=time.monotonic, sleep=time.sleep)


if __name__ == '__main__':
    raise SystemExit(main())
