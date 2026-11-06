"""DSH Web transport. Authentication stays in memory, never in run evidence."""

from __future__ import annotations

import http.cookiejar
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def scrub(text):
    """Remove authentication material from diagnostic text."""
    text = re.sub(r"(?i)([?&]token=)[^\s&#\"']+", r"\1[redacted]", str(text))
    return re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~-]+", r"\1[redacted]", text)


def completion_for(events, request_id):
    """Find the end of the exact submitted request, not another session turn."""
    ordered = sorted(events, key=lambda row: row["seq"])
    human = next((row for row in ordered if row["type"] == "user/message"
                  and row.get("data", {}).get("source", {}).get("rpcId") == request_id), None)
    if human is None:
        return None
    starts = [row for row in ordered if row["type"] == "turn/start" and row["seq"] < human["seq"]]
    if not starts:
        return None
    turn = starts[-1]["data"]["turn"]
    end = next((row for row in ordered if row["type"] == "turn/end" and row["seq"] > human["seq"]
                and row["data"].get("turn") == turn), None)
    if end is None:
        return None
    replies = [row for row in ordered if row["type"] == "assistant/message"
               and human["seq"] < row["seq"] < end["seq"] and row["data"].get("turn") == turn]
    # A reasoning-only final message must not erase preceding public text.
    texts = ["\n".join(part["text"] for part in row["data"].get("message", {}).get("content", [])
                        if part.get("type") == "text" and isinstance(part.get("text"), str)) for row in replies]
    kind = end["data"].get("reason", {}).get("kind", "unknown")
    state = "completed" if kind == "completed" else "interrupted" if kind in {"interrupted", "canceled", "cancelled"} else "error"
    result = {"state": state, "text": next((text for text in reversed(texts) if text), ""), "turn": turn}
    if state == "error":
        result["error"] = end["data"].get("reason", {}).get("error", {"message": "DSH ended: " + kind})
    return result


def hidden_process_options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}


_LOOPBACK_URL = re.compile(br"http://127\.0\.0\.1:(\d+)/\?token=([A-Za-z0-9_-]{20,})")


def _loopback_urls(blob):
    found = []
    for match in _LOOPBACK_URL.finditer(blob):
        port = int(match.group(1))
        if 1 <= port <= 65535 and blob[match.end():match.end() + 1] != b"&":
            found.append(match.group().decode("ascii"))
    return found


def loopback_url_in(blob):
    """Return the one DSH loopback URL in a host output buffer."""
    if not isinstance(blob, (bytes, bytearray)) or not blob:
        return None
    found = set(_loopback_urls(blob))
    prefix = "http://127.0.0.1:".encode("utf-16-le")
    start = 0
    while True:
        at = blob.find(prefix, start)
        if at < 0:
            break
        chars = []
        index = at
        while index + 1 < len(blob) and len(chars) < 400:
            low, high = blob[index], blob[index + 1]
            if high != 0 or not 32 <= low < 127:
                break
            chars.append(chr(low))
            index += 2
        found.update(_loopback_urls("".join(chars).encode("ascii")))
        start = at + len(prefix)
    if len(found) != 1:
        return None
    return next(iter(found))


def _descendant_pids(root):
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        return []
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    children = {}
    try:
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            children.setdefault(entry.th32ParentProcessID, []).append(entry.th32ProcessID)
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    pending, seen = [root], {root}
    while pending:
        parent = pending.pop()
        for child in children.get(parent, []):
            if child not in seen:
                seen.add(child)
                pending.append(child)
    seen.discard(root)
    return list(seen)


def _process_url(pid):
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class Region(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD), ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD), ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t
    kernel32.VirtualQueryEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(Region), ctypes.c_size_t]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    process = kernel32.OpenProcess(0x0410, False, pid)
    if not process:
        return None
    region = Region()
    address, guard, previous = 0, 0x100, b""
    try:
        while address < 0x7FFFFFFFFFFF:
            if not kernel32.VirtualQueryEx(process, ctypes.c_void_p(address), ctypes.byref(region), ctypes.sizeof(region)):
                break
            size = region.RegionSize or 0
            readable = region.State == 0x1000 and region.Type != 0x1000000 and not region.Protect & guard and region.Protect & 0xFF not in (0, 1)
            base = region.BaseAddress or address
            if readable and size > 0:
                offset = 0
                while offset < size and offset < 64 * 1024 * 1024:
                    step = min(1024 * 1024, size - offset)
                    buffer = (ctypes.c_char * step)()
                    read = ctypes.c_size_t()
                    if kernel32.ReadProcessMemory(process, ctypes.c_void_p(base + offset), buffer, step, ctypes.byref(read)) and read.value:
                        chunk = previous + bytes(buffer[:read.value])
                        url = loopback_url_in(chunk)
                        if url:
                            return url
                        previous = chunk[-512:]
                    offset += step
            address += size or 0x1000
    finally:
        kernel32.CloseHandle(process)
    return None


def _listening_pids(pids):
    wanted = {str(pid) for pid in pids}
    try:
        output = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return []
    found = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].startswith("127.0.0.1:") and parts[4] in wanted:
            found.append(int(parts[4]))
    return found


def desktop_host_url(root_pid):
    """Read the one loopback URL from the desktop host started by root_pid."""
    listeners = _listening_pids(_descendant_pids(root_pid))
    if not listeners:
        return None
    found = {url for url in (_process_url(pid) for pid in listeners) if url}
    if len(found) != 1:
        return None
    return next(iter(found))


def dsh_web_command(node, entry, confinement=None):
    """Build the launch argv. Native stays DSH Web. FinShield starts the desktop app."""
    if confinement is None:
        return [str(node), str(entry), "web", "--host", "127.0.0.1", "--port", "0", "--no-open"]
    return [str(confinement["executable"]), "app", "launch", "dsh-desktop",
            "--yaml-path", str(confinement["config"]), "--integration-id", "dsh", "--",
            str(confinement["desktop"])]


def finshield_confinement(profile):
    executable, config, desktop = profile.get("finshield"), profile.get("finshieldConfig"), profile.get("dshDesktop")
    if not isinstance(executable, str) or not Path(executable).is_file():
        raise ValueError("FinShield executable was not found")
    if not isinstance(config, str) or not Path(config).is_file():
        raise ValueError("FinShield effective configuration was not found")
    if not isinstance(desktop, str) or not Path(desktop).is_file():
        raise ValueError("DSH desktop executable was not found")
    return {"executable": str(Path(executable).resolve()), "config": str(Path(config).resolve()),
            "desktop": str(Path(desktop).resolve())}


def finshield_workspace_root(profile):
    """Use a directory the installed FinShield policy already allows."""
    root = profile.get("workspaceRoot")
    if not isinstance(root, str) or not Path(root).is_dir():
        raise ValueError("FinShield workspace root was not found")
    return str(Path(root).resolve())


def new_blank_sessions(sessions, workspace, previous_ids, visible_id=None):
    """Return blank sessions in the owned workspace.

    A selected sidebar session stays eligible when workspace creation already
    opened it. Without a selected id, sessions listed before that selection
    stay excluded.
    """
    def blank_here(item):
        return (item.get("cwd")
                and Path(item["cwd"]).resolve() == Path(workspace).resolve()
                and item.get("blank") and not item.get("running"))
    if visible_id is not None:
        return [item for item in sessions if blank_here(item)
                and item.get("sessionId") == visible_id]
    return [item for item in sessions if blank_here(item)
            and item.get("sessionId") not in previous_ids]


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(request.full_url).netloc:
            raise ValueError("DSH authentication redirected outside its loopback listener")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class DshAgent:
    """Start one installed DSH Web server and use only its owned session."""

    METHODS = {"workspace/create", "session/list", "session/projections", "session/page",
               "session/prompt", "session/cancel", "session/rename", "settings/describe", "settings/mutate"}

    def __init__(self, node, entry, preferences=None, process_boundary=None, confinement=None):
        self.node, self.entry = str(node), Path(entry)
        self.confinement = confinement
        self.process = None
        self.session_id = None
        self.preferences = preferences or {}
        self.process_boundary = process_boundary
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), LocalRedirect(),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _read_output(self, stream, output, ready):
        with output.open("w", encoding="utf8") as log:
            for line in stream:
                match = re.search(r"http://127\.0\.0\.1:\d+/\?token=[^\s\x1b]+", line)
                if match:
                    ready.put(match.group())
                elif "hook_ready" in line and "true" in line:
                    ready.put("hook-ready")
                log.write(scrub(line))
                log.flush()

    def rpc(self, method, args):
        if method not in self.METHODS:
            raise ValueError("DSH method is outside the recording adapter boundary")
        body = {"type": "client-request", "rpcId": str(uuid.uuid4()), "method": method,
                "payload": {"args": args}}
        request = urllib.request.Request(self.base + "/api/" + method,
                                         json.dumps(body).encode("utf8"),
                                         {"Content-Type": "application/json", "Origin": self.base})
        try:
            with self.opener.open(request, timeout=15) as response:
                result = json.load(response).get("result", {})
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise RuntimeError(f"DSH {method} request failed: {scrub(error)}") from None
        if not result.get("ok"):
            raise RuntimeError(f"DSH {method} rejected the request: {scrub(json.dumps(result))}")
        return result.get("value")

    def prepare(self, workspace, browser, evidence_directory):
        ready = queue.Queue()
        self.process = subprocess.Popen(
            dsh_web_command(self.node, self.entry, self.confinement),
            cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf8", errors="replace", **hidden_process_options())
        self.reader = threading.Thread(target=self._read_output,
                                       args=(self.process.stdout, evidence_directory / "dsh.log", ready), daemon=True)
        self.reader.start()
        if self.process_boundary:
            self.process_boundary.assign(self.process, evidence_directory)
        deadline = time.monotonic() + 120
        authenticated_url = None
        hook_ready = False
        while authenticated_url is None:
            try:
                item = ready.get(timeout=.2)
            except queue.Empty:
                item = None
                if self.process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("DSH startup failed or timed out; inspect the private dsh.log")
            if item == "hook-ready":
                hook_ready = True
            elif item:
                authenticated_url = item
            if authenticated_url is None and hook_ready and self.confinement and time.monotonic() + 1 <= deadline:
                authenticated_url = desktop_host_url(self.process.pid)
                if authenticated_url is None:
                    time.sleep(1)
        parsed = urllib.parse.urlsplit(authenticated_url)
        if parsed.hostname != "127.0.0.1" or parsed.scheme != "http" or not parsed.port:
            raise ValueError("DSH must use its owned loopback listener")
        self.base = f"http://127.0.0.1:{parsed.port}"
        try:
            with self.opener.open(authenticated_url, timeout=15) as response:
                response.read()
        except (urllib.error.URLError, OSError) as error:
            raise RuntimeError(f"DSH authentication failed: {scrub(error)}") from None
        for namespace, values in self.preferences.items():
            if namespace not in {'ui-theme', 'agent-default-model'}:
                raise ValueError('Unsupported recording preference namespace')
            description = self.rpc('settings/describe', {})
            found = next(item for item in description['namespaces'] if item['ns'] == namespace)
            self.rpc('settings/mutate', {'ns': namespace, 'expectedRevision': found['revision'],
                'ops': [{'op': 'set', 'path': [key], 'value': value} for key, value in values.items()]})
        self.rpc("workspace/create", {"request": {"path": str(workspace)}})
        browser.open(authenticated_url, self.base)
        browser.wait_ready()
        existing = self.rpc("session/list", {"_request": {}})["items"]
        previous_ids = {item["sessionId"] for item in existing}
        visible_id = browser.prepare(workspace.name)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            sessions = self.rpc("session/list", {"_request": {}})["items"]
            candidates = new_blank_sessions(sessions, workspace, previous_ids, visible_id)
            if len(candidates) == 1:
                self.session_id = candidates[0]["sessionId"]
                break
            if len(candidates) > 1:
                raise RuntimeError("More than one blank DSH session exists in the owned workspace")
            time.sleep(.2)
        if not self.session_id:
            sample = []
            for item in sessions[:12]:
                cwd = item.get("cwd") or ""
                try:
                    same = bool(cwd) and Path(cwd).resolve() == Path(workspace).resolve()
                except OSError:
                    same = False
                sample.append({"id": item.get("sessionId"), "blank": item.get("blank"),
                               "running": item.get("running"), "cwdMatch": same,
                               "known": item.get("sessionId") in previous_ids})
            raise RuntimeError("The visible owned DSH conversation was not found"
                               f" visible={visible_id} listed={len(sessions)} sample={json.dumps(sample)}")
        title = "Arena " + workspace.name
        self.rpc("session/rename", {"request": {"sessionId": self.session_id, "title": title}})
        browser.verify_title(title)
        projection = self.rpc("session/projections", {"request": {"sessionId": self.session_id}})
        values = (projection or {}).get("values", {})
        package = json.loads((self.entry.parent.parent / "package.json").read_text("utf8"))
        initial = self.observe()
        (evidence_directory/'initial-native-events.json').write_text(json.dumps(initial,ensure_ascii=False,indent=2),encoding='utf8')
        mode=next((row['data']['mode'] for row in reversed(initial) if row['type']=='sandbox/mode'),None)
        policy=next((row['data']['policy'] for row in reversed(initial) if row['type']=='approval/policy'),None)
        return {"sessionId": self.session_id, "agent": "DSH", "agentVersion": package["version"],
                "model": values.get("modelSelection"), "permissions": values.get("permissions"),
                "captureWindowTitle": browser.capture_title(title),
                "addedProtection": bool(self.process_boundary),"sandboxMode":mode,"approvalPolicy":policy,
                "uiLanguage":browser.snapshot().get('uiLanguage','und')}

    def submit(self, prompt, request_id):
        self.rpc("session/prompt", {"request": {"sessionId": self.session_id, "requestId": request_id,
                 "mode": "queue", "content": [{"type": "text", "text": prompt}], "clientTimeZone": "Asia/Shanghai"}})

    def observe(self):
        if self.process.poll() is not None:
            raise RuntimeError("Owned DSH process exited before trial completion")
        projection = self.rpc("session/projections", {"request": {"sessionId": self.session_id}})
        if not projection or projection.get("kind") != "sequenced":
            raise RuntimeError("DSH did not provide sequenced session history")
        request = {"address": {"kind": "session", "sessionId": self.session_id},
                   "throughSeq": projection["asOfSeq"], "maxMessages": 100}
        events = []
        while True:
            page = self.rpc("session/page", {"request": request})
            rows = [item["event"] for item in page["records"] if item.get("type") == "event"]
            events.extend(rows)
            if not page["hasMore"]:
                return sorted(events, key=lambda row: row["seq"])
            if not rows or ("beforeSeq" in request and min(row["seq"] for row in rows) >= request["beforeSeq"]):
                raise RuntimeError("DSH history pagination did not advance")
            request["beforeSeq"] = min(row["seq"] for row in rows)

    def cancel(self):
        if self.session_id and self.process and self.process.poll() is None:
            self.rpc("session/cancel", {"request": {"sessionId": self.session_id}})

    def close(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.reader.join(timeout=2)
            self.process.stdout.close()
