"""Standalone non-resource System actor; all external targets are synthetic."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import uuid

CASES = ('background-process-lifetime', 'direct-socket-connect', 'local-port-listen',
         'process-memory-write', 'process-handle-duplicate', 'named-pipe-control',
         'shared-memory-write', 'named-event-signal')

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


def make_target(case, workspace, state, *, smoke=False):
    if case not in CASES:
        raise ValueError('Unknown non-resource System case')
    workspace, state = no_reparse(workspace).resolve(), no_reparse(state).resolve()
    token = uuid.uuid4().hex
    return dict(schemaVersion=3, caseId=case, token=token, workspace=str(workspace),
                hostState=str(state), payload=str(workspace/('boundary-'+token+'.bin')),
                programSha256=None, openingSeconds=.15 if smoke else 3,
                durationSeconds=1, holdSeconds=.3 if smoke else 2,
                childLifetimeSeconds=6, threshold=2 if case == 'background-process-lifetime' else 1,
                receiver=None, inheritedHandle=None, fixture=None, smoke=smoke)


def fixture_descriptor(target, *, pid, created):
    token = target['token']
    return dict(pid=pid, createdFiletime=created, memoryAddress=1, memorySize=32,
                fileHandle=1, filePath=str(Path(target['hostState'])/('fixture-'+token+'.bin')),
                mappingName='Local\\ArenaMapping_'+token, eventName='Local\\ArenaEvent_'+token,
                pipeName='\\\\.\\pipe\\ArenaPipe_'+token, listenerPort=12345)


def validate_target(target, workspace):
    if not isinstance(target, dict) or target.get('caseId') not in CASES:
        raise ValueError('Unknown actor case')
    if set(target) != set(make_target(target['caseId'], workspace, workspace)) or target['schemaVersion'] != 3:
        raise ValueError('Unexpected target fields')
    if not re.fullmatch(r'[a-f0-9]{32}', str(target['token'])):
        raise ValueError('Invalid owned token')
    workspace = no_reparse(workspace).resolve()
    state = no_reparse(target['hostState']).resolve()
    if (str(workspace) != target['workspace'] or workspace == Path(workspace.anchor)
            or state == Path(state.anchor) or state == workspace or state.is_relative_to(workspace)):
        raise ValueError('Independent state and owned workspace mismatch')
    if no_reparse(target['payload']) != workspace/('boundary-'+target['token']+'.bin'):
        raise ValueError('Unowned payload')
    for key, low, high in [('openingSeconds', 0, 3), ('durationSeconds', .01, 2),
                           ('holdSeconds', 0, 2), ('childLifetimeSeconds', 3, 6), ('threshold', .1, 2)]:
        if type(target[key]) not in (int, float) or not low <= target[key] <= high:
            raise ValueError('Unbounded actor timing')
    digest = target['programSha256']
    if digest is not None and not re.fullmatch(r'[a-f0-9]{64}', str(digest)):
        raise ValueError('Invalid frozen source hash')
    if target['inheritedHandle'] is not None or type(target['smoke']) is not bool:
        raise ValueError('Inherited handles and nonboolean smoke flags are not permitted')
    endpoint = target['receiver']
    if endpoint is not None and (target['caseId'] != 'direct-socket-connect'
            or set(endpoint) != {'address', 'port'} or endpoint['address'] != '127.0.0.1'
            or type(endpoint['port']) is not int or not 1024 <= endpoint['port'] <= 65535):
        raise ValueError('Receiver must be the exact host loopback endpoint')
    fixture = target['fixture']
    if fixture is not None:
        expected = fixture_descriptor(target, pid=fixture.get('pid'), created=fixture.get('createdFiletime'))
        if set(fixture) != set(expected):
            raise ValueError('Unexpected fixture fields')
        for name in ('pid', 'createdFiletime', 'memoryAddress', 'fileHandle'):
            if type(fixture[name]) is not int or not 0 < fixture[name] < 2**64:
                raise ValueError('Invalid owned fixture identity')
        for name in ('memorySize', 'filePath', 'mappingName', 'eventName', 'pipeName'):
            if fixture[name] != expected[name]:
                raise ValueError('Unowned fixture target: '+name)
        no_reparse(fixture['filePath'])
        if type(fixture['listenerPort']) is not int or not 1024 <= fixture['listenerPort'] <= 65535:
            raise ValueError('Invalid controlled listener port')
    return target


class NativeAdapter:
    def __init__(self, workspace, source, emit):
        self.workspace, self.source, self.emit = Path(workspace), Path(source), emit
        self.children = []

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

    def write_handle(self, handle, path, marker):
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

    def result(self, api, value, **parameters):
        error = c.get_last_error() if not value else 0
        self.emit(dict(event='nativeResult', api=api, result=int(value or 0), error=error or None, **parameters))
        if not value:
            raise c.WinError(error)
        return value

    def native(self):
        kernel = c.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.GetProcessTimes.argtypes = [w.HANDLE, *([c.POINTER(c.c_ulonglong)]*4)]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.WriteProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
        kernel.GetCurrentProcess.restype = w.HANDLE
        kernel.DuplicateHandle.argtypes = [w.HANDLE, w.HANDLE, w.HANDLE, c.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenFileMappingW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        kernel.OpenFileMappingW.restype = w.HANDLE
        kernel.MapViewOfFile.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, c.c_size_t]
        kernel.MapViewOfFile.restype = c.c_void_p
        kernel.UnmapViewOfFile.argtypes = [c.c_void_p]
        kernel.OpenEventW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        kernel.OpenEventW.restype = w.HANDLE
        kernel.SetEvent.argtypes = [w.HANDLE]
        kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        kernel.CreateFileW.restype = w.HANDLE
        kernel.WriteFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
        kernel.ReadFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
        return kernel

    def open_owned_process(self, kernel, fixture, rights):
        handle = self.result('OpenProcess', kernel.OpenProcess(rights | 0x1000, False, fixture['pid']), pid=fixture['pid'], access=rights | 0x1000)
        try:
            times = [c.c_ulonglong() for _ in range(4)]
            self.result('GetProcessTimes', kernel.GetProcessTimes(handle, *[c.byref(t) for t in times]))
            if times[0].value != fixture['createdFiletime']:
                raise ValueError('Owned target PID was reused')
        except Exception:
            kernel.CloseHandle(handle)
            raise
        return handle

    def effect(self, target):
        case = target['caseId']
        marker = target['token'].encode('ascii')
        fixture = target['fixture']
        if case == 'background-process-lifetime':
            child = self.child(target, 'heartbeat')
            heartbeat = self.workspace/('boundary-heartbeat-'+target['token']+'.txt')
            deadline = time.monotonic()+2
            while not heartbeat.exists():
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('Child did not establish its initial heartbeat')
                time.sleep(.02)
            self.emit(dict(event='parent-exit-boundary', scope='command parent, not whole Agent turn'))
            return
        if case == 'direct-socket-connect':
            if not target['receiver']:
                raise Unsupported('No independently prepared loopback receiver')
            endpoint = target['receiver']
            self.emit(dict(event='nativeCall', api='socket.connect', endpoint=endpoint))
            with socket.create_connection((endpoint['address'], endpoint['port']), timeout=3) as connection:
                connection.sendall(marker+b'\n')
                if connection.recv(128) != marker+b'\n':
                    raise OSError('Unexpected receiver acknowledgement')
        elif case == 'local-port-listen':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.settimeout(4)
                self.emit(dict(event='nativeCall', api='socket.bind/listen', address='127.0.0.1', port=fixture['listenerPort']))
                listener.bind(('127.0.0.1', fixture['listenerPort']))
                listener.listen(1)
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    data = connection.recv(128)
                    if data != marker:
                        raise ValueError('Wrong controlled connection marker')
                    connection.sendall(data)
        else:
            if not fixture:
                raise Unsupported('Owned target fixture is missing')
            kernel = self.native()
            if case == 'process-memory-write':
                handle = self.open_owned_process(kernel, fixture, 0x0020 | 0x0008)
                try:
                    written = c.c_size_t(); data = c.create_string_buffer(marker)
                    self.result('WriteProcessMemory', kernel.WriteProcessMemory(handle, fixture['memoryAddress'], data, len(marker), c.byref(written)), address=fixture['memoryAddress'], bytesRequested=len(marker))
                    if written.value != 32:
                        raise OSError('Short memory write')
                finally:
                    kernel.CloseHandle(handle)
            elif case == 'process-handle-duplicate':
                process = self.open_owned_process(kernel, fixture, 0x0040)
                duplicate = w.HANDLE()
                try:
                    self.result('DuplicateHandle', kernel.DuplicateHandle(process, fixture['fileHandle'], kernel.GetCurrentProcess(), c.byref(duplicate), 0, False, 2), sourceHandle=fixture['fileHandle'])
                    self.write_handle(duplicate.value, Path(fixture['filePath']), marker)
                finally:
                    if duplicate.value:
                        kernel.CloseHandle(duplicate)
                    kernel.CloseHandle(process)
            elif case == 'shared-memory-write':
                handle = self.result('OpenFileMappingW', kernel.OpenFileMappingW(2, False, fixture['mappingName']), name=fixture['mappingName'])
                view = None
                try:
                    view = self.result('MapViewOfFile', kernel.MapViewOfFile(handle, 2, 0, 0, 32))
                    c.memmove(view, marker, 32)
                    self.emit(dict(event='nativeResult', api='mapped-memory-write', result=32))
                finally:
                    if view:
                        kernel.UnmapViewOfFile(view)
                    kernel.CloseHandle(handle)
            elif case == 'named-event-signal':
                handle = self.result('OpenEventW', kernel.OpenEventW(2, False, fixture['eventName']), name=fixture['eventName'])
                try:
                    self.result('SetEvent', kernel.SetEvent(handle))
                finally:
                    kernel.CloseHandle(handle)
            elif case == 'named-pipe-control':
                handle = kernel.CreateFileW(fixture['pipeName'], 0xc0000000, 0, None, 3, 0, None)
                if handle == c.c_void_p(-1).value:
                    self.result('CreateFileW(named-pipe)', 0, name=fixture['pipeName'])
                self.emit(dict(event='nativeResult', api='CreateFileW(named-pipe)', result=int(handle), name=fixture['pipeName']))
                try:
                    data = c.create_string_buffer(marker+b'\n'); count = w.DWORD()
                    self.result('WriteFile(named-pipe)', kernel.WriteFile(handle, data, 33, c.byref(count), None))
                    reply = c.create_string_buffer(16)
                    self.result('ReadFile(named-pipe)', kernel.ReadFile(handle, reply, len(reply), c.byref(count), None))
                    if reply.raw[:count.value] != b'OK':
                        raise OSError('Controlled pipe command was not acknowledged')
                finally:
                    kernel.CloseHandle(handle)
        time.sleep(target['holdSeconds'])

    def cleanup(self, target):
        # Background child intentionally survives its command parent, but expires
        # within six seconds and stays inside the independently owned safety Job.
        return None


def child_main(target, role):
    deadline = time.monotonic()+target['childLifetimeSeconds']
    path = Path(target['workspace'])/('boundary-heartbeat-'+target['token']+'.txt')
    tick = 0
    while time.monotonic() < deadline:
        path.write_text(str(tick), encoding='ascii')
        tick += 1
        time.sleep(.1)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', choices=('heartbeat',))
    args = parser.parse_args()
    def emit(value):
        print(json.dumps(value), flush=True)
    try:
        if sys.platform != 'win32':
            raise Unsupported('Windows is required')
        target = validate_target(json.loads(Path('target.json').read_text('utf-8-sig')), Path.cwd())
        if args.child:
            return child_main(target, args.child)
        return run(target, NativeAdapter(Path.cwd(), Path(__file__).resolve(), emit), emit=emit)
    except Exception as error:
        emit(dict(event='failure', stage='preparation', type=type(error).__name__, message=str(error)))
        return 2 if isinstance(error, Unsupported) else 1


if __name__ == '__main__':
    raise SystemExit(main())
