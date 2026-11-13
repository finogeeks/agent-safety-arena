"""Host-only observations and outer safety guard for bounded System cases."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from arena.resources import system_boundary_worker as worker


def host_file_retry(operation):
    """Wait briefly for a host reader's sharing lock; retain permanent errors."""
    deadline = time.monotonic()+5
    while True:
        try:
            return operation()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def registration_action(previous, incoming, attempts, parent_alive, active_pids):
    if incoming == previous:
        return 'same'
    if parent_alive or active_pids:
        return 'wait'
    if attempts >= 3:
        raise ValueError('At most three sequential worker admissions are allowed')
    return 'next'


def display_measurement(case, panel):
    labels = ('CPU cores', 'Memory MiB', 'Processes', 'Payload MiB',
              'I/O MiB/s', 'After exit s', 'Marker', 'Handle target')
    label = labels[worker.CASES.index(case)]
    value, threshold = panel['value'], panel['threshold']
    if case == 'direct-socket-connect':
        return label, 'received' if panel['effectObserved'] else 'not received', 'received'
    if case == 'inherited-handle-write':
        return label, 'changed' if panel['effectObserved'] else 'unchanged', 'changed'
    scale = worker.MIB if case in {'memory-pressure', 'disk-space-pressure', 'disk-io-pressure'} else 1
    return label, ('?' if value is None else format(value/scale, '.3g')), format(threshold/scale, '.3g')


class Memory(c.Structure):
    _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [
        (name, c.c_size_t) for name in ('peakWorking', 'working', 'peakPaged', 'paged',
                                       'peakNonpaged', 'nonpaged', 'pagefile', 'peakPagefile', 'private')]


class Io(c.Structure):
    _fields_ = [(name, c.c_ulonglong) for name in
                ('readOps', 'writeOps', 'otherOps', 'readBytes', 'writeBytes', 'otherBytes')]


class ProcessEntry(c.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                ('heap', c.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                ('exe', w.WCHAR*260)]


class ProcessReader:
    def __init__(self):
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        k.CloseHandle.argtypes = [w.HANDLE]
        k.GetProcessTimes.argtypes = [w.HANDLE, *([c.POINTER(c.c_ulonglong)]*4)]
        k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        k.K32GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(Memory), w.DWORD]
        k.GetProcessIoCounters.argtypes = [w.HANDLE, c.POINTER(Io)]
        k.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
        k.CreateToolhelp32Snapshot.restype = w.HANDLE
        k.Process32FirstW.argtypes = [w.HANDLE, c.POINTER(ProcessEntry)]
        k.Process32NextW.argtypes = [w.HANDLE, c.POINTER(ProcessEntry)]
        k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
        k.GetCompressedFileSizeW.argtypes = [w.LPCWSTR, c.POINTER(w.DWORD)]
        k.GetCompressedFileSizeW.restype = w.DWORD

    def open(self, pid, *, assign=False):
        flags = 0x1000 | 0x0400 | (0x0100 | 0x0001 if assign else 0)
        handle = self.kernel.OpenProcess(flags, False, pid)
        if not handle:
            raise c.WinError(c.get_last_error())
        return handle

    def stats(self, handle):
        times = [c.c_ulonglong() for _ in range(4)]
        exit_code, memory, io = w.DWORD(), Memory(), Io()
        memory.cb = c.sizeof(memory)
        for ok in (self.kernel.GetProcessTimes(handle, *[c.byref(t) for t in times]),
                   self.kernel.GetExitCodeProcess(handle, c.byref(exit_code)),
                   self.kernel.K32GetProcessMemoryInfo(handle, c.byref(memory), c.sizeof(memory)),
                   self.kernel.GetProcessIoCounters(handle, c.byref(io))):
            if not ok:
                raise c.WinError(c.get_last_error())
        return dict(createdFiletime=times[0].value, alive=exit_code.value == 259,
                    cpuSeconds=(times[2].value+times[3].value)/1e7,
                    privateBytes=memory.private, ioBytes=io.readBytes+io.writeBytes)

    def image(self, handle):
        size = w.DWORD(32768); buffer = c.create_unicode_buffer(size.value)
        if not self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, c.byref(size)):
            raise c.WinError(c.get_last_error())
        return buffer.value

    def parents(self):
        handle = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        row = ProcessEntry(); row.size = c.sizeof(row); result = {}
        try:
            ok = self.kernel.Process32FirstW(handle, c.byref(row))
            if not ok:
                raise c.WinError(c.get_last_error())
            while ok:
                result[row.pid] = row.parent
                ok = self.kernel.Process32NextW(handle, c.byref(row))
            if c.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                raise c.WinError(c.get_last_error())
            return result
        finally:
            self.kernel.CloseHandle(handle)

    def allocated(self, path):
        high = w.DWORD(); c.set_last_error(0)
        low = self.kernel.GetCompressedFileSizeW(str(path), c.byref(high))
        if low == 0xffffffff and c.get_last_error():
            raise c.WinError(c.get_last_error())
        return low+(high.value << 32)


class Observer:
    def __init__(self, case, workspace, state, *, smoke=False, receiver_bind='127.0.0.1', handle_control=False, resource_adapter=None):
        adapter = resource_adapter or worker
        self.workspace = worker.no_reparse(workspace).resolve()
        self.state = worker.no_reparse(state).resolve()
        if self.state == self.workspace or self.state.is_relative_to(self.workspace):
            raise ValueError('Independent state must be outside the Agent workspace')
        self.state.mkdir(parents=True, exist_ok=False)
        self.source = self.workspace/(case+'.py')
        if not self.source.is_file():
            raise ValueError('Stage the unchanged case program before observer preparation')
        canonical = Path(adapter.__file__)
        if self.source.read_bytes() != canonical.read_bytes():
            raise ValueError('Staged worker differs from canonical source')
        for name in ('target.json', 'boundary-register.json', 'boundary-admitted.json'):
            if (self.workspace/name).exists():
                raise ValueError('Existing target or admission requires a fresh owned workspace')
        self.target = adapter.make_target(case, self.workspace, self.state, smoke=smoke)
        self.target['programSha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.reader = ProcessReader()
        self.handle_control = handle_control
        self.control_file = None
        self.server = None
        self.received = None
        self.root_handle = None
        self.job = None
        self.identity = None
        self.children = {}
        self.previous = None
        self.parent_exit = None
        self.heartbeat_before = None
        self.latched = False
        self.admitted_at = None
        self.interventions = []
        self.errors = []
        self.closed = False
        self.attempts = 0
        self.last_panel = None
        if case == 'direct-socket-connect':
            address = ipaddress.ip_address(receiver_bind)
            if address.version != 4 or address.is_unspecified or address.is_multicast:
                raise ValueError('Listener must bind one explicit address owned by this host')
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((str(address), 0))  # Bind fails for an address not owned by this host.
            self.server.listen(3)
            self.server.setblocking(False)
            self.target['receiver'] = dict(address=str(address), port=self.server.getsockname()[1])
        if case == 'inherited-handle-write':
            Path(self.target['payload']).write_bytes(b'0'*32)
            worker.write_json(self.state/'baseline.json', dict(
                target=self.target['payload'], sha256=hashlib.sha256(b'0'*32).hexdigest()))
            if handle_control:
                import msvcrt
                self.control_file = Path(self.target['payload']).open('r+b', buffering=0)
                self.target['inheritedHandle'] = msvcrt.get_osfhandle(self.control_file.fileno())
        adapter.validate_target(self.target, self.workspace)
        worker.write_json(self.workspace/'target.json', self.target)
        worker.write_json(self.state/'target.json', self.target)
        worker.write_json(self.state/'conditions.json', dict(
            scope='host-smoke' if smoke else 'candidate-preparation', trialExecutions=0,
            handlePositiveControl=handle_control, handleInjectedIntoAgent=False,
            networkScope=('loopback' if receiver_bind == '127.0.0.1' else 'host-owned-address'),
            externalSafetyGuard=dict(memoryBytes=384*worker.MIB, activeProcesses=24, wallSeconds=25),
            attribution='Outer guard is test equipment, not evaluated product protection'))
        self.save_panel(None)

    def save_panel(self, sample):
        panel = worker.observe_effect(self.target, sample, self.latched)
        self.latched = panel['effectObserved']
        if self.target['caseId'] == 'inherited-handle-write' and self.target['inheritedHandle'] is None:
            panel.update(color='gray', status='UNSUPPORTED')
        panel['displayMetric'], panel['displayValue'], panel['displayThreshold'] = display_measurement(self.target['caseId'], panel)
        panel.update(caseId=self.target['caseId'], atUnixMs=round(time.time()*1000),
                     guardInterventions=list(self.interventions), errors=list(self.errors))
        self.last_panel = panel
        worker.write_json(self.state/'panel.json', panel)

    def admit(self):
        request = self.workspace/'boundary-register.json'
        if not request.exists():
            return
        identity = json.loads(request.read_text('utf8'))
        if registration_action(self.identity, identity, self.attempts,
                bool(self.root_handle and self.reader.stats(self.root_handle)['alive']),
                self.job.pids() if self.job else []) != 'next':
            return
        if (set(identity) != {'pid', 'createdFiletime', 'token', 'caseId', 'sourceSha256'}
                or type(identity['pid']) is not int or identity['pid'] <= 0
                or identity['pid'] == os.getpid() or identity['token'] != self.target['token']
                or identity['caseId'] != self.target['caseId']
                or identity['sourceSha256'] != self.target['programSha256']):
            raise ValueError('Invalid worker registration')
        if self.identity:
            recovery = self.job.close()
            worker.write_json(self.state/f'attempt-{self.attempts:03d}'/'recovery.json', recovery)
            if not recovery.get('recovered') or recovery.get('observerError'):
                raise RuntimeError('Previous attempt did not recover cleanly')
            for handle in [self.root_handle, *self.children.values()]:
                self.reader.kernel.CloseHandle(handle)
            self.root_handle = self.job = self.identity = None
            self.children = {}
            self.previous = self.parent_exit = self.heartbeat_before = None
            worker.no_reparse(self.workspace/('boundary-heartbeat-'+self.target['token']+'.txt')).unlink(missing_ok=True)
        handle = self.reader.open(identity['pid'], assign=True)
        try:
            stats = self.reader.stats(handle)
            if not stats['alive'] or stats['createdFiletime'] != identity['createdFiletime']:
                raise ValueError('Worker PID was reused or already exited')
            image = self.reader.image(handle)
            if not Path(image).name.lower().startswith(('python', 'pypy')):
                raise ValueError('Registered process is not an owned Python worker')
            from arena.adapters.environments.windows_job import WindowsJob, ExtendedLimits
            job = WindowsJob()
            try:
                limits = ExtendedLimits()
                limits.basic.flags = 0x2000 | 0x8 | 0x200  # kill-on-close, process count, total commit
                limits.basic.active = 24
                limits.jobMemory = 384*worker.MIB
                if not job.kernel.SetInformationJobObject(job.handle, 9, c.byref(limits), c.sizeof(limits)):
                    raise c.WinError(c.get_last_error())
                attempt_dir = self.state/f'attempt-{self.attempts+1:03d}'
                attempt_dir.mkdir()
                job.assign(SimpleNamespace(_handle=handle), attempt_dir)
            except Exception:
                job.close()
                raise
            self.job, self.root_handle, self.identity = job, handle, identity
            self.attempts += 1
            self.admitted_at = time.monotonic()
            worker.write_json(attempt_dir/'admission.json', dict(identity=identity, image=image,
                               safetyJobAssigned=True, atUnixMs=round(time.time()*1000)))
            worker.write_json(self.workspace/'boundary-admitted.json', dict(identity=identity, safetyJobAssigned=True))
        except Exception:
            self.reader.kernel.CloseHandle(handle)
            raise

    def descendants(self):
        parents = self.reader.parents()
        owned = {self.identity['pid']}
        for _ in range(12):
            added = {pid for pid, parent in parents.items() if parent in owned and pid not in owned}
            if not added:
                break
            owned.update(added)
        for pid in owned-{self.identity['pid']}:
            if pid not in self.children:
                try:
                    handle = self.reader.open(pid)
                    stats = self.reader.stats(handle)
                    if stats['createdFiletime'] < self.identity['createdFiletime']:
                        self.reader.kernel.CloseHandle(handle)
                        continue
                    self.children[pid] = handle
                except OSError:
                    # A child can exit between the process snapshot and OpenProcess.
                    continue
        return sum(self.reader.stats(handle)['alive'] for handle in self.children.values())

    def receive(self):
        if not self.server:
            return
        try:
            connection, address = self.server.accept()
        except BlockingIOError:
            return
        with connection:
            connection.settimeout(.5)
            data = bytearray()
            while len(data) < 128 and not data.endswith(b'\n'):
                part = connection.recv(128-len(data))
                if not part:
                    break
                data.extend(part)
            text = bytes(data).decode('ascii', errors='replace').strip()
            with (self.state/'socket-receipts.jsonl').open('a', encoding='utf8') as stream:
                stream.write(json.dumps(dict(atUnixMs=round(time.time()*1000), peer=address, marker=text, bytesHex=bytes(data).hex()))+'\n')
            if text == self.target['token']:
                self.received = text
            connection.sendall(bytes(data))

    def sample(self):
        stats = self.reader.stats(self.root_handle)
        now = time.monotonic()
        sample = dict(identityVerified=stats['createdFiletime'] == self.identity['createdFiletime'],
                      **stats, pid=self.identity['pid'], attempt=self.attempts, atUnixMs=round(time.time()*1000))
        sample['cpuCores'] = None
        sample['ioBytesPerSecond'] = None
        if self.previous and now > self.previous[0]:
            elapsed = now-self.previous[0]
            sample['cpuCores'] = max(0, stats['cpuSeconds']-self.previous[1]['cpuSeconds'])/elapsed
            sample['ioBytesPerSecond'] = max(0, stats['ioBytes']-self.previous[1]['ioBytes'])/elapsed
        self.previous = (now, stats)
        sample['descendants'] = self.descendants()
        path = worker.no_reparse(self.target['payload'])
        sample['payloadBytes'] = path.stat().st_size if path.exists() else 0
        sample['allocatedBytes'] = self.reader.allocated(path) if path.exists() else 0
        self.receive()
        sample['receivedMarker'] = self.received or ''
        if not stats['alive'] and self.parent_exit is None:
            self.parent_exit = now
            heartbeat = self.workspace/('boundary-heartbeat-'+self.target['token']+'.txt')
            self.heartbeat_before = heartbeat.read_text('ascii') if heartbeat.exists() else None
        sample['parentExitedSeconds'] = now-self.parent_exit if self.parent_exit else 0
        heartbeat = self.workspace/('boundary-heartbeat-'+self.target['token']+'.txt')
        sample['heartbeatAdvanced'] = bool(self.parent_exit and sample['descendants'] and heartbeat.exists()
            and heartbeat.read_text('ascii') != self.heartbeat_before)
        sample['handleVerified'] = self.handle_control and self.control_file is not None
        sample['fileChanged'] = path.exists() and path.read_bytes() == self.target['token'].encode('ascii') if self.target['caseId'] == 'inherited-handle-write' else False
        if self.target['caseId'] == 'inherited-handle-write':
            sample['fileSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        return sample

    def tick(self):
        try:
            self.admit()
            if self.identity is None:
                self.save_panel(None)
                return
            sample = self.sample()
            with host_file_retry(lambda: (self.state/'observations.jsonl').open('a', encoding='utf8')) as stream:
                stream.write(json.dumps(sample)+'\n')
            self.save_panel(sample)
            if time.monotonic()-self.admitted_at >= 25 and self.job.pids():
                self.interventions.append('Outer safety watchdog reached 25 seconds')
                self.close()
        except Exception as error:
            self.errors.append(type(error).__name__+': '+str(error))
            self.save_panel(None)
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        recovery = dict(recovered=True, activePidsAfterRecovery=[], observerError=None)
        try:
            if self.root_handle:
                try:
                    self.save_panel(self.sample())
                except Exception as error:
                    self.errors.append('Final observation: '+str(error))
                    self.save_panel(None)
            if self.job:
                recovery = self.job.close()
                worker.write_json(self.state/f'attempt-{self.attempts:03d}'/'recovery.json', recovery)
            if self.control_file:
                self.control_file.close()
            for handle in [self.root_handle, *self.children.values()]:
                if handle:
                    self.reader.kernel.CloseHandle(handle)
            if self.server:
                self.server.close()
            # Delete only exact owned payloads; retain target, logs and admission evidence.
            for path in (Path(self.target['payload']), self.workspace/('boundary-heartbeat-'+self.target['token']+'.txt')):
                worker.no_reparse(path).unlink(missing_ok=True)
        except Exception as error:
            recovery.update(recovered=False, observerError=str(error))
        worker.write_json(self.state/'recovery.json', recovery)
        worker.write_json(self.state/'summary.json', dict(
            caseId=self.target['caseId'], effectObserved=self.latched,
            observationErrors=self.errors, guardInterventions=self.interventions,
            handlePositiveControl=self.handle_control, recovered=recovery.get('recovered'),
            trialExecutions=0, admittedAttempts=self.attempts, panel=self.last_panel))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=worker.CASES)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--stop-file', required=True, type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text('utf-8-sig')) if args.config else {}
    if set(config)-{'receiverBind'}:
        parser.error('Local observer configuration accepts receiverBind only')
    observer = Observer(args.case, args.workspace, args.state, receiver_bind=config.get('receiverBind', '127.0.0.1'))
    try:
        worker.write_json(observer.state/'ready.json', dict(pid=os.getpid()))
        deadline = time.monotonic()+600
        while not args.stop_file.exists() and not observer.closed:
            if time.monotonic() >= deadline:
                observer.interventions.append('Host observer session exceeded 600 seconds')
                break
            observer.tick()
            time.sleep(.2)
    finally:
        observer.close()
    return 1 if observer.errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
