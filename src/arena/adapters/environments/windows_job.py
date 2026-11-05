"""Bound recovery and observe windows of one trial-owned Windows process tree."""
import ctypes as c
from ctypes import wintypes as w
import json
import threading
import time


class BasicLimits(c.Structure):
    _fields_ = [('processTime',c.c_longlong),('jobTime',c.c_longlong),('flags',w.DWORD),
                ('minimum',c.c_size_t),('maximum',c.c_size_t),('active',w.DWORD),
                ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]


class ExtendedLimits(c.Structure):
    _fields_ = [('basic',BasicLimits),('io',c.c_ulonglong*6),('processMemory',c.c_size_t),
                ('jobMemory',c.c_size_t),('peakProcess',c.c_size_t),('peakJob',c.c_size_t)]


class WindowsJob:
    def __init__(self):
        self.kernel = c.WinDLL('kernel32',use_last_error=True)
        self.user = c.WinDLL('user32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [c.c_void_p,w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE,w.HANDLE]
        self.kernel.QueryInformationJobObject.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p]
        self.kernel.TerminateJobObject.argtypes = [w.HANDLE,w.UINT]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.OpenProcess.argtypes = [w.DWORD,w.BOOL,w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.GetProcessTimes.argtypes = [w.HANDLE,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p]
        self.user.GetWindowThreadProcessId.argtypes = [w.HWND,c.POINTER(w.DWORD)]
        self.user.IsWindowVisible.argtypes = [w.HWND]
        self.user.GetWindowRect.argtypes = [w.HWND,c.POINTER(w.RECT)]
        self.handle = self.kernel.CreateJobObjectW(None,None)
        if not self.handle:
            raise c.WinError(c.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.kernel.SetInformationJobObject(self.handle,9,c.byref(limits),c.sizeof(limits)):
            self.kernel.CloseHandle(self.handle)
            raise c.WinError(c.get_last_error())
        self.halt = threading.Event()
        self.reader = None
        self.error = None

    def pids(self):
        # QueryInformationJobObject JobObjectBasicProcessIdList, pointer-sized IDs.
        for capacity in (256,4096):
            raw = c.create_string_buffer(8 + capacity*c.sizeof(c.c_size_t))
            if self.kernel.QueryInformationJobObject(self.handle,3,raw,len(raw),None):
                count = w.DWORD.from_buffer(raw,4).value
                return list((c.c_size_t*count).from_buffer(raw,8))
            if c.get_last_error() != 234:
                raise c.WinError(c.get_last_error())
        raise RuntimeError('Owned process list exceeded observation capacity')

    def snapshot(self):
        pids = self.pids()
        identities = []
        for pid in pids:
            process = self.kernel.OpenProcess(0x1000,False,pid)
            if process:
                times = [c.c_ulonglong() for _ in range(4)]
                try:
                    if self.kernel.GetProcessTimes(process,*[c.byref(value) for value in times]):
                        identities.append(dict(pid=pid,createdFiletime=times[0].value))
                finally:
                    self.kernel.CloseHandle(process)
        windows = []
        callback_type = c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        @callback_type
        def collect(hwnd, ignored):
            pid = w.DWORD()
            self.user.GetWindowThreadProcessId(hwnd,c.byref(pid))
            if pid.value in pids:
                rect = w.RECT()
                if self.user.GetWindowRect(hwnd,c.byref(rect)):
                    windows.append(dict(handle=int(hwnd),pid=pid.value,
                        visible=bool(self.user.IsWindowVisible(hwnd)),
                        bounds=[rect.left,rect.top,rect.right,rect.bottom]))
            return True
        self.user.EnumWindows.argtypes = [callback_type,w.LPARAM]
        if not self.user.EnumWindows(collect,0):
            raise c.WinError(c.get_last_error())
        return dict(atUnixMs=round(time.time()*1000),processes=identities,windows=windows)

    def assign(self, process, directory):
        if not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
            raise c.WinError(c.get_last_error())
        path = directory/'native-window-observations.jsonl'
        def observe():
            try:
                with path.open('w',encoding='utf8') as stream:
                    while not self.halt.is_set():
                        stream.write(json.dumps(self.snapshot())+'\n')
                        stream.flush()
                        self.halt.wait(.25)
            except Exception as error:
                self.error = str(error)
        self.reader = threading.Thread(target=observe,daemon=True)
        self.reader.start()

    def close(self):
        if not self.handle:
            return dict(alreadyClosed=True)
        self.halt.set()
        if self.reader:
            self.reader.join(timeout=5)
        before = self.snapshot()
        try:
            if not self.kernel.TerminateJobObject(self.handle,0):
                raise c.WinError(c.get_last_error())
            deadline = time.monotonic()+10
            remaining = self.pids()
            while remaining and time.monotonic()<deadline:
                time.sleep(.05)
                remaining = self.pids()
            return dict(boundary='Windows Job Object, kill-on-close, no breakaway',
                        beforeRecovery=before,activePidsAfterRecovery=remaining,
                        recovered=not remaining,observerError=self.error)
        finally:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
