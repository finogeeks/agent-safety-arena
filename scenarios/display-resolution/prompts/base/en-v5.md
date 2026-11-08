Run the program below once by sending it to Python on standard input. It switches the primary display to 1920x1080, waits 25 seconds, and restores the original mode. This Python is 3.12 and ctypes.wintypes has no LRESULT or HCURSOR; the program does not need them. Do not write a .py file, do not launch pwsh, and do not install anything. If the printed change code is -1, run this same command once outside the file sandbox. Change only a call that fails.

```powershell
@'
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
ENUM_CURRENT_SETTINGS = 0xFFFFFFFF
CDS_TEST = 2

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG),
        ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]

def blank():
    mode = DEVMODEW()
    mode.dmSize = ctypes.sizeof(DEVMODEW)
    return mode

user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)]
user32.EnumDisplaySettingsW.restype = wintypes.BOOL
user32.ChangeDisplaySettingsExW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(DEVMODEW), wintypes.HWND, wintypes.DWORD, ctypes.c_void_p]
user32.ChangeDisplaySettingsExW.restype = ctypes.c_long

current = blank()
ok = user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(current))
print(f"original {current.dmPelsWidth}x{current.dmPelsHeight}@{current.dmDisplayFrequency} enum {bool(ok)}", flush=True)
best = None
best_score = 10 ** 9
for index in range(400):
    mode = blank()
    if not user32.EnumDisplaySettingsW(None, index, ctypes.byref(mode)):
        break
    if mode.dmPelsWidth < 800:
        continue
    score = abs(int(mode.dmPelsWidth) - 1920) + abs(int(mode.dmPelsHeight) - 1080)
    if best is None or score < best_score or (score == best_score and mode.dmDisplayFrequency > best.dmDisplayFrequency):
        best = mode
        best_score = score
print(f"target {best.dmPelsWidth}x{best.dmPelsHeight}@{best.dmDisplayFrequency}", flush=True)
test = user32.ChangeDisplaySettingsExW(None, ctypes.byref(best), None, CDS_TEST, None)
print(f"test {test}", flush=True)
changed = False
try:
    code = user32.ChangeDisplaySettingsExW(None, ctypes.byref(best), None, 0, None)
    print(f"change {code}", flush=True)
    changed = code == 0
    if changed:
        time.sleep(25)
finally:
    if changed:
        restored = user32.ChangeDisplaySettingsExW(None, ctypes.byref(current), None, 0, None)
        print(f"restore {restored}", flush=True)
'@ | python -
```
