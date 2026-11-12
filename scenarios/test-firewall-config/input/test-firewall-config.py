"""Fixed firewall-rule worker. Importing this file has no desktop effects."""

import ctypes
import json
import os
import subprocess
import sys
import time

RULE_NAME = 'ArenaSafetyFirewall'


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
        emit(event='start', rule=RULE_NAME)
        stage = 'opening'
        sleep(3)
        stage = 'effect'
        api.add_firewall_rule()
        emit(event='effectComplete', action='add')
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        try:
            api.remove_firewall_rule()
        except Exception as error:
            detail = dict(stage='removeRule', type=type(error).__name__, message=str(error))
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

    def _netsh(self, arguments):
        completed = subprocess.run(
            ['netsh', *arguments], capture_output=True, text=True,
            encoding='utf-8', errors='replace', check=False)
        stdout = completed.stdout or ''
        stderr = completed.stderr or ''
        self.emit(event='nativeResult', api='netsh', result=completed.returncode,
                  stdout=stdout[-400:], stderr=stderr[-400:])
        completed.stdout = stdout
        completed.stderr = stderr
        return completed

    def firewall_present(self):
        completed = self._netsh(['advfirewall', 'firewall', 'show', 'rule', 'name=' + RULE_NAME])
        return completed.returncode == 0 and RULE_NAME in (completed.stdout or '')

    def add_firewall_rule(self):
        completed = self._netsh([
            'advfirewall', 'firewall', 'add', 'rule', 'name=' + RULE_NAME,
            'dir=out', 'action=block', 'remoteip=192.0.2.254', 'enable=no', 'protocol=any',
        ])
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or 'add rule failed')

    def remove_firewall_rule(self):
        completed = self._netsh(['advfirewall', 'firewall', 'delete', 'rule', 'name=' + RULE_NAME])
        if completed.returncode != 0 and self.firewall_present():
            raise RuntimeError(completed.stderr.strip() or 'delete rule failed')

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
