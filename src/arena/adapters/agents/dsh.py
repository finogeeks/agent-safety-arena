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


def new_blank_sessions(sessions, workspace, previous_ids):
    return [item for item in sessions if item.get("cwd")
            and Path(item["cwd"]).resolve() == Path(workspace).resolve()
            and item.get("sessionId") not in previous_ids
            and item.get("blank") and not item.get("running")]


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(request.full_url).netloc:
            raise ValueError("DSH authentication redirected outside its loopback listener")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class DshAgent:
    """Start one installed DSH Web server and use only its owned session."""

    METHODS = {"workspace/create", "session/list", "session/projections", "session/page",
               "session/prompt", "session/cancel", "session/rename"}

    def __init__(self, node, entry):
        self.node, self.entry = str(node), Path(entry)
        self.process = None
        self.session_id = None
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), LocalRedirect(),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _read_output(self, stream, output, ready):
        with output.open("w", encoding="utf8") as log:
            for line in stream:
                match = re.search(r"http://127\.0\.0\.1:\d+/\?token=[^\s\x1b]+", line)
                if match:
                    ready.put(match.group())
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
            [self.node, str(self.entry), "web", "--host", "127.0.0.1", "--port", "0", "--no-open"],
            cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf8", errors="replace", **hidden_process_options())
        self.reader = threading.Thread(target=self._read_output,
                                       args=(self.process.stdout, evidence_directory / "dsh.log", ready), daemon=True)
        self.reader.start()
        deadline = time.monotonic() + 120
        while True:
            try:
                authenticated_url = ready.get(timeout=.2)
                break
            except queue.Empty:
                if self.process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("DSH startup failed or timed out; inspect the private dsh.log")
        parsed = urllib.parse.urlsplit(authenticated_url)
        if parsed.hostname != "127.0.0.1" or parsed.scheme != "http" or not parsed.port:
            raise ValueError("DSH must use its owned loopback listener")
        self.base = f"http://127.0.0.1:{parsed.port}"
        try:
            with self.opener.open(authenticated_url, timeout=15) as response:
                response.read()
        except (urllib.error.URLError, OSError) as error:
            raise RuntimeError(f"DSH authentication failed: {scrub(error)}") from None
        self.rpc("workspace/create", {"request": {"path": str(workspace)}})
        browser.open(authenticated_url, self.base)
        browser.wait_ready()
        existing = self.rpc("session/list", {"_request": {}})["items"]
        previous_ids = {item["sessionId"] for item in existing}
        browser.prepare(workspace.name)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            sessions = self.rpc("session/list", {"_request": {}})["items"]
            candidates = new_blank_sessions(sessions, workspace, previous_ids)
            if len(candidates) == 1:
                self.session_id = candidates[0]["sessionId"]
                break
            if len(candidates) > 1:
                raise RuntimeError("More than one blank DSH session exists in the owned workspace")
            time.sleep(.2)
        if not self.session_id:
            raise RuntimeError("The visible owned DSH conversation was not found")
        title = "Arena " + workspace.name
        self.rpc("session/rename", {"request": {"sessionId": self.session_id, "title": title}})
        browser.verify_title(title)
        projection = self.rpc("session/projections", {"request": {"sessionId": self.session_id}})
        values = (projection or {}).get("values", {})
        package = json.loads((self.entry.parent.parent / "package.json").read_text("utf8"))
        return {"sessionId": self.session_id, "agent": "DSH", "agentVersion": package["version"],
                "model": values.get("modelSelection"), "permissions": values.get("permissions"),
                "captureWindowTitle": browser.capture_title(title),
                "addedProtection": False}

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
