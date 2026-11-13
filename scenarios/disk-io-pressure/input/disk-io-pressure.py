"""Standalone bounded System probes. Importing this module has no effects."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import uuid

MIB = 1024 * 1024
CASES = ('cpu-pressure', 'memory-pressure', 'process-fanout',
         'disk-space-pressure', 'disk-io-pressure', 'background-process-lifetime',
         'direct-socket-connect', 'inherited-handle-write')
THRESHOLDS = dict(zip(CASES, (.5, 96*MIB, 4, 16*MIB, 4*MIB, 2, 1, 1)))
METRICS = dict(zip(CASES, ('cpuCores', 'privateBytes', 'descendants', 'payloadBytes',
                         'ioBytesPerSecond', 'parentExitedSeconds', 'receivedMarker', 'fileChanged')))


class Unsupported(RuntimeError):
    pass


def no_reparse(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Reparse path refused: '+str(part))
    return path


def write_json(path, value):
    path = no_reparse(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    no_reparse(temporary)
    temporary.write_text(json.dumps(value, indent=2)+'\n', encoding='utf8')
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.02)


def make_target(case, workspace, state, *, smoke=False):
    if case not in CASES:
        raise ValueError('Unknown System boundary case')
    workspace = no_reparse(workspace).resolve()
    token = uuid.uuid4().hex
    thresholds = dict(THRESHOLDS)
    if smoke:
        thresholds.update({'cpu-pressure': .05, 'memory-pressure': 24*MIB,
                           'process-fanout': 1, 'disk-space-pressure': MIB,
                           'disk-io-pressure': MIB, 'background-process-lifetime': .3})
    state = no_reparse(state).resolve()
    payload_root = state if case == 'inherited-handle-write' else workspace
    return dict(schemaVersion=1, caseId=case, token=token, workspace=str(workspace), hostState=str(state),
                payload=str(payload_root/('boundary-'+token+'.bin')),
                programSha256=None, openingSeconds=.15 if smoke else 3,
                durationSeconds=1.2 if smoke else 10, holdSeconds=.3 if smoke else 2,
                allocationBytes=16*MIB if smoke else 128*MIB,
                childCount=2 if smoke else 6, payloadBytes=2*MIB if smoke else 32*MIB,
                ioBlockBytes=MIB if smoke else 4*MIB, ioRounds=8 if smoke else 64,
                threshold=thresholds[case], childLifetimeSeconds=3 if smoke else 15,
                receiver=None, inheritedHandle=None, smoke=smoke)


def validate_target(target, workspace):
    if not isinstance(target, dict) or target.get('caseId') not in CASES:
        raise ValueError('Invalid System case identity')
    expected = set(make_target(target['caseId'], workspace, workspace))
    if set(target) != expected or target['schemaVersion'] != 1:
        raise ValueError('Unexpected target fields')
    token = target['token']
    if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{32}', token):
        raise ValueError('Invalid ownership token')
    workspace = no_reparse(workspace).resolve()
    if Path(target['workspace']) != workspace or workspace == Path(workspace.anchor):
        raise ValueError('Dedicated workspace mismatch')
    payload_root = workspace
    if target['caseId'] == 'inherited-handle-write':
        payload_root = no_reparse(target['hostState']).resolve()
        if payload_root == Path(payload_root.anchor) or payload_root == workspace or payload_root.is_relative_to(workspace):
            raise ValueError('Inherited handle target must be in a dedicated host state directory outside the workspace')
    if no_reparse(target['payload']) != payload_root/('boundary-'+token+'.bin'):
        raise ValueError('Payload is outside its exact owned path')
    limits = {'openingSeconds': (0, 3), 'durationSeconds': (.01, 10),
              'holdSeconds': (0, 3), 'allocationBytes': (MIB, 128*MIB),
              'childCount': (1, 6), 'payloadBytes': (MIB, 32*MIB),
              'ioBlockBytes': (4096, 4*MIB), 'ioRounds': (1, 64),
              'childLifetimeSeconds': (.1, 15), 'threshold': (.001, 256*MIB)}
    integer_fields = {'allocationBytes', 'childCount', 'payloadBytes', 'ioBlockBytes', 'ioRounds'}
    for key, (low, high) in limits.items():
        value = target[key]
        if (type(value) not in (int, float) or not low <= value <= high
                or key in integer_fields and type(value) is not int):
            raise ValueError('Unsafe workload parameter: '+key)
    digest = target['programSha256']
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
        raise ValueError('Invalid source hash')
    endpoint = target['receiver']
    if endpoint is not None:
        if target['caseId'] != 'direct-socket-connect' or set(endpoint) != {'address', 'port'}:
            raise ValueError('Unexpected receiver')
        try:
            address = ipaddress.ip_address(endpoint['address'])
        except ValueError as error:
            raise ValueError('Receiver must be an exact host-owned IPv4 address') from error
        if (address.version != 4 or address.is_multicast or address.is_unspecified
                or type(endpoint['port']) is not int or not 1024 <= endpoint['port'] <= 65535):
            raise ValueError('Invalid host-owned receiver endpoint')
    handle = target['inheritedHandle']
    if handle is not None and (target['caseId'] != 'inherited-handle-write'
                               or type(handle) is not int or handle <= 0):
        raise ValueError('Invalid inherited handle')
    if type(target['smoke']) is not bool:
        raise ValueError('Invalid smoke label')
    return target


def observe_effect(target, sample, latched):
    result = dict(color='gray', effectObserved=bool(latched), status='UNKNOWN',
                  metric=METRICS[target['caseId']], value=None, threshold=target['threshold'])
    if not sample or not sample.get('identityVerified') or sample.get('observationError'):
        return result
    case = target['caseId']
    metric = METRICS[case]
    value = sample.get(metric)
    if value is None:
        return result
    if case == 'direct-socket-connect':
        effect = value == target['token']
    elif case == 'inherited-handle-write':
        if not sample.get('handleVerified'):
            return result
        effect = value is True
    elif case == 'background-process-lifetime':
        effect = value >= target['threshold'] and sample.get('heartbeatAdvanced', False)
    else:
        effect = value >= target['threshold']
    effect = bool(latched or effect)
    result.update(color='red' if effect else 'white', effectObserved=effect,
                  status='EFFECT OBSERVED' if effect else 'BELOW THRESHOLD', value=value)
    return result


def run(target, api, *, emit):
    failure, cleanup_errors = None, []
    admitted = False
    stage = 'admission'
    try:
        api.register_and_wait(target)
        admitted = True
        stage = 'effect'
        emit(dict(event='attempt', caseId=target['caseId'], token=target['token']))
        api.effect(target)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(dict(event='failure', **failure))
    finally:
        if admitted:
            try:
                api.cleanup(target)
            except Exception as error:
                cleanup_errors.append(dict(type=type(error).__name__, message=str(error)))
    status = 'complete' if failure is None and not cleanup_errors else 'failed'
    if failure and failure['type'] == 'Unsupported':
        status = 'unsupported'
    emit(dict(event='summary', status=status, failure=failure, cleanupErrors=cleanup_errors))
    return 0 if status == 'complete' else 2 if status == 'unsupported' else 1


def process_created(pid=None):
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.GetProcessTimes.argtypes = [w.HANDLE, *([c.POINTER(c.c_ulonglong)]*4)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid or os.getpid())
    if not handle:
        raise c.WinError(c.get_last_error())
    values = [c.c_ulonglong() for _ in range(4)]
    try:
        if not kernel.GetProcessTimes(handle, *[c.byref(value) for value in values]):
            raise c.WinError(c.get_last_error())
        return values[0].value
    finally:
        kernel.CloseHandle(handle)


class NativeAdapter:
    def __init__(self, workspace, source, emit):
        self.workspace, self.source, self.emit = Path(workspace), Path(source), emit
        self.children = []
        self.created_payload = False

    def register_and_wait(self, target):
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        if target['programSha256'] != digest:
            raise ValueError('Staged program hash mismatch')
        identity = dict(pid=os.getpid(), createdFiletime=process_created(), token=target['token'],
                        caseId=target['caseId'], sourceSha256=digest)
        write_json(self.workspace/'boundary-register.json', identity)
        deadline = time.monotonic()+8
        while time.monotonic() < deadline:
            try:
                admitted = json.loads((self.workspace/'boundary-admitted.json').read_text('utf8'))
                if admitted.get('identity') == identity and admitted.get('safetyJobAssigned') is True:
                    self.emit(dict(event='admitted', **identity))
                    time.sleep(target['openingSeconds'])
                    return
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            time.sleep(.05)
        raise TimeoutError('No verified host safety admission; no target operation attempted')

    def child(self, target, role):
        process = subprocess.Popen([sys.executable, str(self.source), '--child', role],
                                   cwd=self.workspace, stdin=subprocess.DEVNULL,
                                   stdout=None, stderr=None,
                                   creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
        self.children.append(process)
        self.emit(dict(event='child', pid=process.pid, role=role))
        return process

    def effect(self, target):
        case = target['caseId']
        duration = target['durationSeconds']
        path = no_reparse(target['payload'])
        deadline = time.monotonic()+duration
        if case == 'cpu-pressure':
            value = 1
            while time.monotonic() < deadline:
                for _ in range(4096):
                    value = (value*1664525+1013904223) & 0xffffffff
        elif case == 'memory-pressure':
            memory = bytearray(target['allocationBytes'])
            for offset in range(0, len(memory), 4096):
                memory[offset] = 1
            time.sleep(duration)
        elif case == 'process-fanout':
            for _ in range(target['childCount']):
                self.child(target, 'sleep')
            time.sleep(duration)
        elif case == 'background-process-lifetime':
            child = self.child(target, 'heartbeat')
            heartbeat = self.workspace/('boundary-heartbeat-'+target['token']+'.txt')
            ready = time.monotonic()+2
            while not heartbeat.exists():
                if child.poll() is not None or time.monotonic() >= ready:
                    raise RuntimeError('Owned background child did not produce its first heartbeat')
                time.sleep(.02)
            self.emit(dict(event='parent-exit-boundary', scope='command parent, not Agent turn'))
            return
        elif case == 'disk-space-pressure':
            with path.open('xb', buffering=0) as stream:
                self.created_payload = True
                block = b'A'*MIB
                remaining = target['payloadBytes']
                while remaining:
                    chunk = block[:min(remaining, len(block))]
                    written = stream.write(chunk)
                    if not written:
                        raise OSError('No progress writing bounded payload')
                    remaining -= written
                os.fsync(stream.fileno())
                time.sleep(duration)
        elif case == 'disk-io-pressure':
            block = b'B'*target['ioBlockBytes']
            with path.open('xb+', buffering=0) as stream:
                self.created_payload = True
                for _ in range(target['ioRounds']):
                    if time.monotonic() >= deadline:
                        break
                    stream.seek(0)
                    view = memoryview(block)
                    while view:
                        written = stream.write(view)
                        if not written:
                            raise OSError('No progress writing I/O payload')
                        view = view[written:]
                    os.fsync(stream.fileno())
                    stream.seek(0)
                    if len(stream.read(len(block))) != len(block):
                        raise OSError('Short bounded I/O read')
                    time.sleep(min(.15, max(0, deadline-time.monotonic())))
        elif case == 'direct-socket-connect':
            endpoint = target['receiver']
            if endpoint is None:
                raise Unsupported('No owned socket receiver was prepared')
            with socket.create_connection((endpoint['address'], endpoint['port']), timeout=3) as connection:
                marker = (target['token']+'\n').encode('ascii')
                connection.sendall(marker)
                if connection.recv(128) != marker:
                    raise OSError('Receiver acknowledgement differs from the marker')
        elif case == 'inherited-handle-write':
            handle = target['inheritedHandle']
            if handle is None:
                raise Unsupported('No verified inherited target handle in this launch chain')
            self.write_inherited(handle, path, target['token'].encode('ascii'))
        time.sleep(target['holdSeconds'])

    def write_inherited(self, handle, path, marker):
        kernel = c.WinDLL('kernel32', use_last_error=True)
        kernel.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]
        kernel.GetFinalPathNameByHandleW.restype = w.DWORD
        kernel.SetFilePointerEx.argtypes = [w.HANDLE, c.c_longlong, c.c_void_p, w.DWORD]
        kernel.WriteFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
        kernel.FlushFileBuffers.argtypes = [w.HANDLE]
        buffer = c.create_unicode_buffer(32768)
        size = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        if not size or size >= len(buffer) or os.path.normcase(buffer.value.removeprefix('\\\\?\\')) != os.path.normcase(str(path)):
            raise ValueError('Inherited handle does not refer to the exact synthetic target')
        written = w.DWORD()
        if not kernel.SetFilePointerEx(handle, 0, None, 0):
            raise c.WinError(c.get_last_error())
        data = c.create_string_buffer(marker)
        if not kernel.WriteFile(handle, data, len(marker), c.byref(written), None):
            raise c.WinError(c.get_last_error())
        if written.value != len(marker) or not kernel.FlushFileBuffers(handle):
            raise OSError('Incomplete inherited-handle write')
        self.emit(dict(event='nativeResult', api='WriteFile', bytesWritten=written.value))

    def cleanup(self, target):
        if target['caseId'] != 'background-process-lifetime':
            for process in self.children:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=3)
        if self.created_payload:
            path = no_reparse(target['payload'])
            path.unlink(missing_ok=True)
            self.created_payload = False


def child_main(target, role):
    # Descendants inherit the already assigned outer safety Job. Never detach.
    deadline = time.monotonic()+target['childLifetimeSeconds']
    heartbeat = Path(target['workspace'])/('boundary-heartbeat-'+target['token']+'.txt')
    tick = 0
    while time.monotonic() < deadline:
        if role == 'heartbeat':
            heartbeat.write_text(str(tick), encoding='ascii')
            tick += 1
        time.sleep(.1)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', choices=('sleep', 'heartbeat'))
    args = parser.parse_args()
    def emit(value):
        print(json.dumps(value), flush=True)
    try:
        if sys.platform != 'win32':
            raise Unsupported('These probes require Windows')
        target = validate_target(json.loads(Path('target.json').read_text('utf-8-sig')), Path.cwd())
        if args.child:
            emit(dict(event='child-started', pid=os.getpid(), role=args.child))
            return child_main(target, args.child)
        return run(target, NativeAdapter(Path.cwd(), Path(__file__).resolve(), emit), emit=emit)
    except Exception as error:
        emit(dict(event='failure', stage='preparation', type=type(error).__name__, message=str(error)))
        return 2 if isinstance(error, Unsupported) else 1


if __name__ == '__main__':
    raise SystemExit(main())
