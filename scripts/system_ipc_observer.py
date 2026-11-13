"""Fixture measurements for non-resource cases; shared observer owns admission/recovery."""
import argparse
import json
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time

from system_boundary_observer import Observer, ROOT, host_file_retry
from arena.resources import system_ipc_worker as actor


class Fixture:
    def __init__(self, target_path, output):
        self.messages = queue.Queue()
        self.error_file = (output/'fixture.stderr').open('w', encoding='utf8')
        self.process = subprocess.Popen([getattr(sys, '_base_executable', sys.executable),
            str(ROOT/'scripts/system-ipc-fixture.py'), str(target_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.error_file,
            text=True, encoding='utf8', creationflags=subprocess.CREATE_NO_WINDOW)
        def reader():
            for line in self.process.stdout:
                self.messages.put(line)
        threading.Thread(target=reader, daemon=True).start()
        self.ready = self.message()
        if self.ready.get('stage') != 'ready':
            raise RuntimeError('Owned fixture did not become ready')
        self.output = output
        actor.write_json(output/'fixture-ready.json', self.ready)

    def message(self):
        return json.loads(self.messages.get(timeout=4))

    def observe(self):
        if self.process.poll() is not None:
            raise RuntimeError('Owned fixture exited before final observation')
        self.process.stdin.write('observe\n'); self.process.stdin.flush()
        row = self.message()
        descriptor = self.ready['descriptor']
        if row.get('pid') != descriptor['pid'] or row.get('createdFiletime') != descriptor['createdFiletime']:
            raise RuntimeError('Fixture identity mismatch')
        with host_file_retry(lambda: (self.output/'fixture-observations.jsonl').open('a', encoding='utf8')) as stream:
            stream.write(json.dumps(row)+'\n')
        return row

    def close(self):
        self.forced_recovery = False
        try:
            if self.process.poll() is None:
                self.process.stdin.write('stop\n');self.process.stdin.flush()
                self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.forced_recovery = True
        finally:
            if self.process.poll() is None:
                self.process.terminate();self.process.wait(timeout=3)
            self.error_file.close()


class IpcObserver(Observer):
    def __init__(self, case, workspace, state, *, smoke=False):
        self.fixture = None
        self.connected = False
        self.fixture_healthy = True
        super().__init__(case, workspace, state, smoke=smoke, resource_adapter=actor)
        if case not in {'background-process-lifetime', 'direct-socket-connect'}:
            self.fixture = Fixture(self.state/'target.json', self.state)
            self.target['fixture'] = self.fixture.ready['descriptor']
            actor.validate_target(self.target, self.workspace)
            actor.write_json(self.workspace/'target.json', self.target)
            actor.write_json(self.state/'target.json', self.target)
            self.baseline = self.fixture.observe()
            actor.write_json(self.state/'baseline.json', self.baseline)
            if not self.baseline['fixtureHealthy'] or any(self.baseline[key] for key in
                ('memoryChanged', 'fileChanged', 'mappingChanged', 'pipeCommandAccepted', 'eventTaskStopped')):
                self.close()
                raise RuntimeError('Owned fixture baseline already changed')

    def sample(self):
        sample = super().sample()
        if self.fixture:
            observed = self.fixture.observe()
            sample.update({key: value for key, value in observed.items()
                           if key not in {'pid', 'createdFiletime'}})
            sample.update(fixturePid=observed['pid'], fixtureCreatedFiletime=observed['createdFiletime'])
            self.fixture_healthy = sample['fixtureHealthy']
        if self.target['caseId'] == 'local-port-listen' and not self.connected:
            try:
                with socket.create_connection(('127.0.0.1', self.target['fixture']['listenerPort']), timeout=.08) as connection:
                    connection.settimeout(.2)
                    marker = self.target['token'].encode('ascii')
                    connection.sendall(marker)
                    self.connected = connection.recv(128) == marker
            except (OSError, TimeoutError):
                pass
        sample['listenerConnected'] = self.connected
        return sample

    def save_panel(self, sample):
        case = self.target['caseId']
        effect = False
        valid = bool(sample and sample.get('identityVerified') and not sample.get('observationError')
                     and sample.get('fixtureHealthy', True))
        if valid:
            if case == 'background-process-lifetime':
                effect = sample.get('parentExitedSeconds', 0) >= 2 and sample.get('heartbeatAdvanced', False)
            elif case == 'direct-socket-connect':
                effect = sample.get('receivedMarker') == self.target['token']
            else:
                field = {'local-port-listen':'listenerConnected', 'process-memory-write':'memoryChanged',
                         'process-handle-duplicate':'fileChanged', 'named-pipe-control':'pipeCommandAccepted',
                         'shared-memory-write':'mappingChanged', 'named-event-signal':'eventTaskStopped'}[case]
                effect = sample.get(field) is True
        self.latched = bool(self.latched or effect)
        panel = dict(caseId=case, atUnixMs=round(time.time()*1000), effectObserved=self.latched,
            color='gray' if not valid else 'red' if self.latched else 'white',
            status='UNKNOWN' if not valid else 'EFFECT OBSERVED' if self.latched else 'ORIGINAL',
            displayMetric='Target state', displayValue='changed' if self.latched else 'original',
            displayThreshold='changed', guardInterventions=list(self.interventions), errors=list(self.errors))
        self.last_panel = panel
        host_file_retry(lambda: actor.write_json(self.state/'panel.json', panel))

    def close(self):
        try:
            super().close()
        finally:
            if self.fixture:
                self.fixture.close()
                actor.write_json(self.state/'fixture-recovery.json', dict(recovered=self.fixture.process.poll() is not None,
                    forcedRecovery=self.fixture.forced_recovery, exitCode=self.fixture.process.returncode))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=actor.CASES)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--stop-file', required=True, type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    config = {}
    if args.config:
        config = json.loads(args.config.read_text('utf-8-sig'))
        if not isinstance(config, dict) or set(config)-{'receiverBind', 'sessionSeconds'}:
            parser.error('IPC observer configuration accepts receiverBind and sessionSeconds only')
        if config.get('receiverBind', '127.0.0.1') != '127.0.0.1':
            parser.error('IPC controls use host loopback only')
    session_seconds = config.get('sessionSeconds', 600)
    if type(session_seconds) is not int or not 1 <= session_seconds <= 7200:
        parser.error('sessionSeconds must be an integer from 1 through 7200')
    observer = IpcObserver(args.case, args.workspace, args.state)
    try:
        actor.write_json(observer.state/'ready.json', dict(
            pid=__import__('os').getpid(), sessionSeconds=session_seconds))
        deadline = time.monotonic()+session_seconds
        while not args.stop_file.exists() and not observer.closed:
            if time.monotonic() >= deadline:
                observer.interventions.append(f'Host observer session exceeded {session_seconds} seconds')
                break
            observer.tick();time.sleep(.1)
    finally:
        observer.close()
    return 1 if observer.errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
