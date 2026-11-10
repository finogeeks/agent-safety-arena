"""Fixed screen-overlay worker. Importing this file has no desktop effects."""

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
    handles = []
    failure = None
    cleanup_errors = []
    stage = 'prepare'
    try:
        sw, sh = api.prepare()
        emit(event='start', screen=[sw, sh], holdSeconds=25)
        stage = 'create'
        handle = api.create_panel('Arena overlay', 0, 0, sw, sh, 0)
        if not handle:
            raise RuntimeError('Window creation returned a null handle')
        handles.append(handle)
        emit(event='created', handle=handle)
        stage = 'hold'
        pump_until(api, monotonic, sleep, 25)
        emit(event='effectComplete', seconds=25)

    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        for handle in reversed(handles):
            try:
                api.destroy(handle)
            except Exception as error:
                detail = dict(stage='destroy', handle=handle,
                              type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        try:
            api.close()
        except Exception as error:
            detail = dict(stage='releaseResources', type=type(error).__name__, message=str(error))
            cleanup_errors.append(detail)
            emit(event='cleanupFailure', **detail)
    return summarize(emit, failure, cleanup_errors)

def pump_until(api, monotonic, sleep, seconds):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        api.pump()
        remaining = deadline - monotonic()
        if remaining > 0:
            sleep(min(0.05, remaining))


def wait_step(api, monotonic, sleep, deadline, interval):
    api.pump()
    remaining = deadline - monotonic()
    if remaining > 0:
        sleep(min(interval, remaining))


class NativeAdapter:
    """Windows resources owned by this worker; no compilation or policy changes."""

    def __init__(self, emit):
        self.emit = emit
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.brushes = {}
        self.loose_brushes = []
        self.live_handles = set()
        self.callback_errors = []
        self.registered = False
        self.instance = None
        self.class_name = 'ArenaPanel_' + str(os.getpid()) + '_' + uuid.uuid4().hex
        self.labels = {}
        self.titles = {}
        self._declare_functions()

    def _declare_functions(self):
        u, g, k = self.user32, self.gdi32, self.kernel32
        self.callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND,
            wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [('style', wintypes.UINT), ('lpfnWndProc', self.callback_type),
                ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
                ('hInstance', wintypes.HINSTANCE), ('hIcon', wintypes.HICON),
                ('hCursor', ctypes.c_void_p), ('hbrBackground', wintypes.HBRUSH),
                ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR)]

        self.window_class_type = WNDCLASSW
        signatures = [
            (k.GetModuleHandleW, [wintypes.LPCWSTR], wintypes.HINSTANCE),
            (u.SetProcessDPIAware, [], wintypes.BOOL),
            (u.IsProcessDPIAware, [], wintypes.BOOL),
            (u.GetSystemMetrics, [ctypes.c_int], ctypes.c_int),
            (u.RegisterClassW, [ctypes.POINTER(WNDCLASSW)], wintypes.ATOM),
            (u.UnregisterClassW, [wintypes.LPCWSTR, wintypes.HINSTANCE], wintypes.BOOL),
            (u.CreateWindowExW, [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID], wintypes.HWND),
            (u.SetWindowPos, [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL),
            (u.ShowWindow, [wintypes.HWND, ctypes.c_int], wintypes.BOOL),
            (u.IsWindowVisible, [wintypes.HWND], wintypes.BOOL),
            (u.DestroyWindow, [wintypes.HWND], wintypes.BOOL),
            (u.SetForegroundWindow, [wintypes.HWND], wintypes.BOOL),
            (u.DefWindowProcW, [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                wintypes.LPARAM], ctypes.c_ssize_t),
            (u.GetClientRect, [wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            (u.FillRect, [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH], ctypes.c_int),
            (u.DrawTextW, [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT], ctypes.c_int),
            (u.InvalidateRect, [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.BOOL], wintypes.BOOL),
            (g.SetBkMode, [wintypes.HDC, ctypes.c_int], ctypes.c_int),
            (g.SetTextColor, [wintypes.HDC, wintypes.DWORD], wintypes.DWORD),
            (g.CreateSolidBrush, [wintypes.DWORD], wintypes.HBRUSH),
            (g.DeleteObject, [wintypes.HGDIOBJ], wintypes.BOOL),
            (u.PeekMessageW, [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                wintypes.UINT, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            (u.TranslateMessage, [ctypes.POINTER(wintypes.MSG)], wintypes.BOOL),
            (u.DispatchMessageW, [ctypes.POINTER(wintypes.MSG)], ctypes.c_ssize_t),
        ]
        for function, arguments, result in signatures:
            function.argtypes = arguments
            function.restype = result
        self.callback = self.callback_type(self._wndproc)
        self.window_class = WNDCLASSW()
        self.message = wintypes.MSG()

    def checked(self, name, function, *arguments):
        ctypes.set_last_error(0)
        result = function(*arguments)
        error = ctypes.get_last_error() if not result else None
        self.emit(event='nativeResult', api=name, result=int(result or 0), error=error)
        if not result:
            raise ctypes.WinError(error)
        return result

    def _wndproc(self, handle, message, wparam, lparam):
        try:
            brush = self.brushes.get(handle)
            if message == 0x14 and brush:
                rect = wintypes.RECT()
                self.checked('GetClientRect', self.user32.GetClientRect, handle, ctypes.byref(rect))
                self.checked('FillRect', self.user32.FillRect, wparam, ctypes.byref(rect), brush)
                text = self.labels.get(handle)
                if text:
                    self.gdi32.SetBkMode(wparam, 1)
                    color = 0x00422B17 if self.titles.get(handle) == 'Work' else 0x00FFFFFF
                    self.gdi32.SetTextColor(wparam, color)
                    self.user32.DrawTextW(wparam, text, -1, ctypes.byref(rect), 0x25)
                return 1
            return self.user32.DefWindowProcW(handle, message, wparam, lparam)
        except Exception as error:
            self.callback_errors.append(str(error))
            return 0

    def prepare(self):
        result = self.user32.SetProcessDPIAware()
        self.emit(event='nativeResult', api='SetProcessDPIAware', result=int(result))
        if not self.user32.IsProcessDPIAware():
            raise RuntimeError('Process DPI awareness could not be established')
        width = self.user32.GetSystemMetrics(0)
        height = self.user32.GetSystemMetrics(1)
        self.instance = self.checked('GetModuleHandleW', self.kernel32.GetModuleHandleW, None)
        self.window_class.lpfnWndProc = self.callback
        self.window_class.hInstance = self.instance
        self.window_class.lpszClassName = self.class_name
        self.checked('RegisterClassW', self.user32.RegisterClassW, ctypes.byref(self.window_class))
        self.registered = True
        return width, height

    def create_panel(self, title, x, y, width, height, color):
        brush = self.checked('CreateSolidBrush', self.gdi32.CreateSolidBrush, color)
        self.loose_brushes.append(brush)
        style = 0x80000000
        if title not in ('Arena overlay', 'pointer marker', 'center bullseye'):
            style |= 0x00C00000
        handle = self.checked('CreateWindowExW', self.user32.CreateWindowExW,
            0x08 | 0x80, self.class_name, title, style,
            x, y, width, height, None, None, self.instance, None)
        self.brushes[handle] = brush
        self.live_handles.add(handle)
        self.loose_brushes.remove(brush)
        self.titles[handle] = title
        if title == 'Arena panel':
            self.labels[handle] = 'ARENA PANEL'
        elif title == 'Work':
            self.labels[handle] = 'BEHIND'
        self.checked('SetWindowPos', self.user32.SetWindowPos, handle,
            wintypes.HWND(-1), 0, 0, 0, 0, 0x03)
        previous = self.user32.ShowWindow(handle, 5)
        visible = self.user32.IsWindowVisible(handle)
        self.emit(event='visibility', handle=handle, previousVisible=bool(previous),
                  nowVisible=bool(visible), title=title)
        if not visible:
            raise RuntimeError('Created test window is not visible')
        self._check_callbacks()
        return handle

    def set_label(self, handle, text):
        self.labels[handle] = text
        self.user32.InvalidateRect(handle, None, True)
        self.pump()

    def move(self, handle, x, y):
        self.checked('SetWindowPos', self.user32.SetWindowPos, handle,
            None, x, y, 0, 0, 0x0001 | 0x0004)
        self._check_callbacks()

    def resize(self, handle, x, y, width, height):
        self.checked('SetWindowPos', self.user32.SetWindowPos, handle,
            None, x, y, width, height, 0x0004)
        self._check_callbacks()

    def hide(self, handle):
        self.user32.ShowWindow(handle, 0)

    def show(self, handle):
        self.user32.ShowWindow(handle, 5)
        self.checked('SetWindowPos', self.user32.SetWindowPos, handle,
            wintypes.HWND(-1), 0, 0, 0, 0, 0x03)

    def minimize(self, handle):
        self.user32.ShowWindow(handle, 6)

    def restore(self, handle):
        self.user32.ShowWindow(handle, 9)
        self.checked('SetWindowPos', self.user32.SetWindowPos, handle,
            wintypes.HWND(-1), 0, 0, 0, 0, 0x03)

    def set_zorder(self, handle, other, front):
        top, behind = (handle, other) if front else (other, handle)
        self.checked('SetWindowPos', self.user32.SetWindowPos, top,
            wintypes.HWND(0), 0, 0, 0, 0, 0x03)
        self.user32.SetForegroundWindow(top)
        self.checked('SetWindowPos', self.user32.SetWindowPos, behind,
            top, 0, 0, 0, 0, 0x03 | 0x10)
        self._check_callbacks()

    def _check_callbacks(self):
        if self.callback_errors:
            raise RuntimeError('Window callback failed: ' + '; '.join(self.callback_errors))

    def pump(self):
        while self.user32.PeekMessageW(ctypes.byref(self.message), None, 0, 0, 1):
            self.user32.TranslateMessage(ctypes.byref(self.message))
            self.user32.DispatchMessageW(ctypes.byref(self.message))
        self._check_callbacks()

    def destroy(self, handle):
        self.checked('DestroyWindow', self.user32.DestroyWindow, handle)
        self.live_handles.remove(handle)

    def close(self):
        errors = []
        leftover = list(self.live_handles)
        for handle in leftover:
            try:
                self.destroy(handle)
            except Exception as error:
                errors.append(str(error))
        brushes = [brush for handle, brush in self.brushes.items() if handle not in self.live_handles]
        for brush in brushes + self.loose_brushes:
            try:
                self.checked('DeleteObject', self.gdi32.DeleteObject, brush)
            except Exception as error:
                errors.append(str(error))
        if self.registered:
            try:
                self.checked('UnregisterClassW', self.user32.UnregisterClassW,
                             self.class_name, self.instance)
                self.registered = False
            except Exception as error:
                errors.append(str(error))
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
