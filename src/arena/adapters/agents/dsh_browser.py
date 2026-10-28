"""A visible Chrome window owned by one DSH trial; no personal browser profile."""

import base64
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request

from arena.adapters.agents.dsh import hidden_process_options


class DshBrowser:
    def __init__(self, node, chrome, region=None):
        self.node, self.chrome, self.region = str(node), str(chrome), region
        self.chrome_process = None
        self.bridge = None
        self.profile = None
        self.command_lock = threading.Lock()

    def open(self, url, origin):
        self.profile = Path(tempfile.mkdtemp(prefix="arena-dsh-chrome-"))
        x, y, width, height = self.region or (0, 0, 1200, 900)
        self.chrome_process = subprocess.Popen(
            [self.chrome, "--user-data-dir=" + str(self.profile), "--remote-debugging-port=0",
             "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
             "--force-device-scale-factor=1",
             "--disable-session-crashed-bubble", f"--window-position={x},{y}", f"--window-size={width},{height}",
             "--app=" + url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 30
        port_file = self.profile / "DevToolsActivePort"
        while not port_file.exists():
            if self.chrome_process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Dedicated Chrome failed to start")
            time.sleep(.1)
        port = int(port_file.read_text("utf8").splitlines()[0])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        target = None
        while time.monotonic() < deadline:
            with opener.open(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                targets = json.load(response)
            target = next((item for item in targets if item.get("type") == "page"
                           and item.get("url", "").startswith(origin + "/")), None)
            if target:
                break
            time.sleep(.1)
        if not target:
            raise RuntimeError("Owned DSH page was not found in the dedicated browser")
        self.bridge = subprocess.Popen([self.node, str(Path(__file__).with_suffix(".cjs"))],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding="utf8", **hidden_process_options())
        self.command("connect", url=target["webSocketDebuggerUrl"])

    def command(self, action, **fields):
        with self.command_lock:
            self.bridge.stdin.write(json.dumps({"action": action, **fields}) + "\n")
            self.bridge.stdin.flush()
            line = self.bridge.stdout.readline()
        if not line:
            raise RuntimeError("The dedicated Chrome observer exited")
        response = json.loads(line)
        if not response["ok"]:
            raise RuntimeError(response["error"])
        return response.get("value")

    def prepare(self, workspace):
        self.command("prepare", workspace=workspace)

    def wait_ready(self):
        self.command("ready")

    def verify_title(self, title):
        self.command("verify-title", title=title)
        self.command("layout", region=self.region or (0, 0, 1200, 900))

    def capture_title(self, expected):
        """Resolve the visible native title only from the Chrome process we started."""
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        matches = []

        @callback_type
        def visit(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == self.chrome_process.pid and user32.IsWindowVisible(hwnd):
                text = ctypes.create_unicode_buffer(2048)
                user32.GetWindowTextW(hwnd, text, len(text))
                if text.value.startswith(expected):
                    matches.append(text.value)
            return True

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            matches.clear()
            user32.EnumWindows(visit, 0)
            if len(matches) == 1:
                return matches[0]
            time.sleep(.1)
        raise RuntimeError("Could not identify one visible native window for the owned DSH Chrome process")

    def snapshot(self):
        return self.command("snapshot")

    def screenshot(self, path, key=None):
        screenshot = self.command("screenshot", key=key)
        if screenshot is False:
            return False
        Path(path).write_bytes(base64.b64decode(screenshot["data"], validate=True))
        return {"at": screenshot["at"]}

    def frame(self):
        screenshot = self.command("screenshot")
        return base64.b64decode(screenshot["data"], validate=True)

    def close(self):
        if self.bridge:
            try:
                if self.bridge.poll() is None:
                    self.command("close")
            except (RuntimeError, OSError):
                pass
            finally:
                self.bridge.stdin.close()
                try:
                    self.bridge.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.bridge.kill()
                    self.bridge.wait(timeout=5)
                self.bridge.stdout.close()
        if self.chrome_process and self.chrome_process.poll() is None:
            try:
                self.chrome_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    # The live Popen handle still identifies this trial's root process.
                    subprocess.run(["taskkill", "/PID", str(self.chrome_process.pid), "/T", "/F"],
                                   capture_output=True, timeout=10, **hidden_process_options())
                else:
                    self.chrome_process.kill()
                self.chrome_process.wait(timeout=5)
        if self.profile:
            # Only remove the unique temporary profile that this instance created.
            temporary_root = Path(tempfile.gettempdir()).resolve()
            target = self.profile.resolve()
            if target.parent != temporary_root or not target.name.startswith("arena-dsh-chrome-"):
                raise RuntimeError("Temporary Chrome profile is outside the owned cleanup boundary")
            for attempt in range(20):
                try:
                    shutil.rmtree(target)
                    break
                except FileNotFoundError:
                    break
                except OSError:
                    if attempt == 19:
                        raise RuntimeError("Temporary browser profile could not be removed") from None
                    time.sleep(.2)
