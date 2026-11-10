"""Fixed ime-state worker. Importing this file has no desktop effects."""

import ctypes
from ctypes import wintypes
import json
import os
import sys
import time
import uuid


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
    original = None
    stage = 'prepare'
    try:
        api.prepare()
        original = 'saved'
        emit(event='start', order=['english', 'chinese', 'french', 'english'])
        stage = 'effect'
        for name in ('english', 'chinese', 'french', 'english'):
            api.activate_profile(name)
            emit(event='phase', name=name)
            sleep(2)
        emit(event='effectComplete')
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if original is not None:
            try:
                api.restore_profile()
            except Exception as error:
                detail = dict(stage='restore', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        try:
            api.close()
        except Exception as error:
            detail = dict(stage='releaseResources', type=type(error).__name__, message=str(error))
            cleanup_errors.append(detail)
            emit(event='cleanupFailure', **detail)
    return summarize(emit, failure, cleanup_errors)

class GUID(ctypes.Structure):
    _fields_ = [('Data1', ctypes.c_uint32), ('Data2', ctypes.c_uint16),
                ('Data3', ctypes.c_uint16), ('Data4', ctypes.c_ubyte * 8)]

    def __init__(self, text='00000000-0000-0000-0000-000000000000'):
        super().__init__()
        parts = text.split('-')
        self.Data1 = int(parts[0], 16)
        self.Data2 = int(parts[1], 16)
        self.Data3 = int(parts[2], 16)
        rest = parts[3] + parts[4]
        for index in range(8):
            self.Data4[index] = int(rest[index * 2:index * 2 + 2], 16)


class PROFILE(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('dwProfileType', ctypes.c_uint32),
        ('langid', ctypes.c_uint16),
        ('pad0', ctypes.c_uint16),
        ('clsid', GUID),
        ('guidProfile', GUID),
        ('catid', GUID),
        ('hklSubstitute', ctypes.c_void_p),
        ('dwCaps', ctypes.c_uint32),
        ('pad1', ctypes.c_uint32),
        ('hkl', ctypes.c_void_p),
        ('dwFlags', ctypes.c_uint32),
        ('pad2', ctypes.c_uint32),
    ]


class VTBL(ctypes.Structure):
    _fields_ = [
        ('QueryInterface', ctypes.c_void_p),
        ('AddRef', ctypes.c_void_p),
        ('Release', ctypes.c_void_p),
        ('ActivateProfile', ctypes.c_void_p),
        ('DeactivateProfile', ctypes.c_void_p),
        ('GetProfile', ctypes.c_void_p),
        ('EnumProfiles', ctypes.c_void_p),
        ('ReleaseInputProcessor', ctypes.c_void_p),
        ('RegisterProfile', ctypes.c_void_p),
        ('UnregisterProfile', ctypes.c_void_p),
        ('GetActiveProfile', ctypes.c_void_p),
    ]


class COM(ctypes.Structure):
    _fields_ = [('lpVtbl', ctypes.POINTER(VTBL))]


ACTIVATE = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_uint, ctypes.c_ushort,
    ctypes.POINTER(GUID), ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_uint)
GET_ACTIVE = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.c_void_p)
RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)


class NativeAdapter:
    CLSID = '33C53A50-F456-4884-B049-85FD643ECFED'
    IID = '71c6e74c-0f28-11d8-a82a-00065b84435c'
    CAT = '34745C63-B2F0-4784-8B67-5E12C8701A31'
    PINYIN = '81D4E9C9-1D3B-41BC-9E6C-4B40BF79E35E'
    PINYIN_PROFILE = 'FA550B04-5AD7-411F-A5AC-CA038EC515D7'

    def __init__(self, emit):
        self.emit = emit
        self.ole32 = ctypes.WinDLL('ole32', use_last_error=True)
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        self.ole32.CoInitialize.restype = ctypes.HRESULT
        self.ole32.CoUninitialize.argtypes = []
        self.ole32.CoUninitialize.restype = None
        self.ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p,
            ctypes.c_uint, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        self.ole32.CoCreateInstance.restype = ctypes.HRESULT
        self.user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
            wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p)]
        self.user32.SendMessageTimeoutW.restype = ctypes.c_void_p
        self.user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.user32.GetSystemMetrics.restype = ctypes.c_int
        self.initialized = False
        self.ptr = None
        self.saved = None

    def _mgr(self):
        if self.ptr:
            return self.ptr
        clsid, iid, ptr = GUID(self.CLSID), GUID(self.IID), ctypes.c_void_p()
        hr = self.ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid),
                                         ctypes.byref(ptr))
        self.emit(event='nativeResult', api='CoCreateInstance', result=int(hr))
        if hr < 0 or not ptr.value:
            raise ctypes.WinError(hr & 0xFFFFFFFF)
        self.ptr = ptr
        return ptr

    def _vtbl(self):
        obj = ctypes.cast(self.ptr, ctypes.POINTER(COM))
        return obj.contents.lpVtbl.contents

    def prepare(self):
        hr = self.ole32.CoInitialize(None)
        self.emit(event='nativeResult', api='CoInitialize', result=int(hr))
        if hr < 0:
            raise ctypes.WinError(hr & 0xFFFFFFFF)
        self.initialized = True
        self._mgr()
        profile = PROFILE()
        cat = GUID(self.CAT)
        hr = GET_ACTIVE(self._vtbl().GetActiveProfile)(self.ptr, ctypes.byref(cat),
                                                       ctypes.byref(profile))
        self.emit(event='nativeResult', api='GetActiveProfile', result=int(hr),
                  langid=int(profile.langid))
        if hr < 0:
            raise ctypes.WinError(hr & 0xFFFFFFFF)
        self.saved = profile
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def _activate(self, profile_type, langid, clsid, guid_profile, hkl):
        hr = ACTIVATE(self._vtbl().ActivateProfile)(
            self.ptr, profile_type, langid, ctypes.byref(clsid), ctypes.byref(guid_profile),
            ctypes.c_void_p(hkl), 0x20000000)
        self.emit(event='nativeResult', api='ActivateProfile', result=int(hr), langid=int(langid))
        if hr < 0:
            raise ctypes.WinError(hr & 0xFFFFFFFF)
        ignored = ctypes.c_void_p()
        broadcast = hkl & 0xFFFFFFFF
        if broadcast == 0:
            broadcast = 0x08040804
        self.user32.SendMessageTimeoutW(wintypes.HWND(0xFFFF), 0x50, 1, broadcast,
                                        2, 200, ctypes.byref(ignored))

    def activate_profile(self, name):
        empty = GUID()
        if name == 'english':
            self._activate(2, 0x0409, empty, empty, 0x04090409)
        elif name == 'french':
            self._activate(2, 0x040C, empty, empty, 0x040C040C)
        elif name == 'chinese':
            self._activate(1, 0x0804, GUID(self.PINYIN), GUID(self.PINYIN_PROFILE), 0)
        else:
            raise ValueError(name)

    def restore_profile(self):
        if self.saved is None:
            return
        hkl = int(self.saved.hkl or 0) & 0xFFFFFFFF
        self._activate(self.saved.dwProfileType, self.saved.langid, self.saved.clsid,
                       self.saved.guidProfile, hkl)

    def close(self):
        errors = []
        if self.ptr:
            try:
                RELEASE(self._vtbl().Release)(self.ptr)
            except Exception as error:
                errors.append(str(error))
            self.ptr = None
        if self.initialized:
            try:
                self.ole32.CoUninitialize()
            except Exception as error:
                errors.append(str(error))
            self.initialized = False
        if errors:
            raise RuntimeError('; '.join(errors))

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
