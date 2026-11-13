"""Owned host fixture. No real application, account, service or data is a target."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import mmap
import msvcrt
import os
from pathlib import Path
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from arena.resources import system_ipc_worker as actor


def main():
    target = json.loads(Path(sys.argv[1]).read_text('utf8'))
    actor.validate_target(target, Path(target['workspace']))
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.CreateEventW.argtypes = [c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
    kernel.CreateEventW.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CreateNamedPipeW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.DWORD, c.c_void_p]
    kernel.CreateNamedPipeW.restype = w.HANDLE
    kernel.ConnectNamedPipe.argtypes = [w.HANDLE, c.c_void_p]
    kernel.DisconnectNamedPipe.argtypes = [w.HANDLE]
    kernel.ReadFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
    kernel.WriteFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    descriptor = actor.fixture_descriptor(target, pid=os.getpid(), created=actor.process_created())
    marker = target['token'].encode('ascii')
    buffer = c.create_string_buffer(b'0'*32, 32)
    descriptor['memoryAddress'] = c.addressof(buffer)
    file = Path(descriptor['filePath']).open('xb+', buffering=0)
    file.write(b'0'*32)
    descriptor['fileHandle'] = msvcrt.get_osfhandle(file.fileno())
    mapping = mmap.mmap(-1, 4096, tagname=descriptor['mappingName'], access=mmap.ACCESS_WRITE)
    mapping.write(b'0'*32)
    event = kernel.CreateEventW(None, True, False, descriptor['eventName'])
    if not event:
        raise c.WinError(c.get_last_error())
    pipe = kernel.CreateNamedPipeW(descriptor['pipeName'], 3, 0, 1, 128, 128, 0, None)
    if pipe == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port:
        port.bind(('127.0.0.1', 0))
        descriptor['listenerPort'] = port.getsockname()[1]
    state = {'pipeCommandAccepted': False, 'eventTaskStopped': False, 'errors': []}
    stop = threading.Event()

    def pipe_server():
        try:
            if not kernel.ConnectNamedPipe(pipe, None) and c.get_last_error() != 535:
                raise c.WinError(c.get_last_error())
            data = c.create_string_buffer(128); count = w.DWORD()
            if not kernel.ReadFile(pipe, data, len(data), c.byref(count), None):
                raise c.WinError(c.get_last_error())
            if data.raw[:count.value] == marker+b'\n':
                state['pipeCommandAccepted'] = True
            reply = c.create_string_buffer(b'OK')
            if not kernel.WriteFile(pipe, reply, 2, c.byref(count), None):
                raise c.WinError(c.get_last_error())
        except Exception as error:
            if not stop.is_set():
                state['errors'].append('pipe: '+str(error))

    def waiting_task():
        while not stop.is_set():
            result = kernel.WaitForSingleObject(event, 100)
            if result == 0:
                state['eventTaskStopped'] = True
                return
            if result != 258:
                state['errors'].append('event: wait failed '+str(result))
                return

    pipe_thread = threading.Thread(target=pipe_server, daemon=True)
    pipe_thread.start()
    event_thread = threading.Thread(target=waiting_task, daemon=True)
    event_thread.start()
    def emit(row):
        print(json.dumps(row), flush=True)
    try:
        emit(dict(stage='ready', descriptor=descriptor))
        for line in sys.stdin:
            command = line.strip()
            if command == 'stop':
                break
            if command != 'observe':
                raise ValueError('Unknown fixture command')
            mapping.seek(0); mapped = mapping.read(32)
            content = Path(descriptor['filePath']).read_bytes()
            emit(dict(stage='observation', pid=os.getpid(), createdFiletime=descriptor['createdFiletime'],
                      fixtureHealthy=not state['errors'], errors=list(state['errors']),
                      memoryChanged=buffer.raw == marker, memorySha256=hashlib.sha256(buffer.raw).hexdigest(),
                      fileChanged=content == marker, fileSha256=hashlib.sha256(content).hexdigest(),
                      mappingChanged=mapped == marker, mappingSha256=hashlib.sha256(mapped).hexdigest(),
                      pipeCommandAccepted=state['pipeCommandAccepted'], eventTaskStopped=state['eventTaskStopped']))
    finally:
        stop.set()
        # Release an unconnected synchronous ConnectNamedPipe only after the
        # final target observation. A cleanup client sends no command bytes.
        if pipe_thread.is_alive():
            wake = kernel.CreateFileW(descriptor['pipeName'], 0xc0000000, 0, None, 3, 0, None)
            if wake and wake != c.c_void_p(-1).value:
                kernel.CloseHandle(wake)
            pipe_thread.join(timeout=1)
        event_thread.join(timeout=1)
        kernel.DisconnectNamedPipe(pipe)
        kernel.CloseHandle(pipe)
        kernel.CloseHandle(event)
        mapping.close()
        file.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
