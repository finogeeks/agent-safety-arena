"""Optional real-Chrome capture check against a synthetic local page, not DSH."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from arena.adapters.agents.dsh_browser import DshBrowser
from arena.evidence.recording import BrowserRecorder


PAGE = b'''<!doctype html><html><title>Synthetic capture fixture</title><body>
<h1>Synthetic capture fixture, not a DSH result</h1>
<div data-approval-key="approval:test-1">
  <p>This deletes the disposable test note. The deletion cannot be undone.</p>
  <button onclick="document.querySelector('[data-approval-key]').setAttribute('data-approval-key','approval:test-2')">Allow once</button>
  <button>Reject</button>
</div></body></html>'''


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


@unittest.skipUnless(os.environ.get("ARENA_TEST_CHROME") and shutil.which("node"),
                     "Set ARENA_TEST_CHROME to run the local real-Chrome capture check")
class BrowserCaptureTests(unittest.TestCase):
    def test_native_panel_screenshot_repeated_request_and_passive_click_observation(self):
        chrome = Path(os.environ["ARENA_TEST_CHROME"])
        server = ThreadingHTTPServer(("127.0.0.1", 0), PageHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        origin = f"http://127.0.0.1:{server.server_port}"
        browser = DshBrowser(shutil.which("node"), chrome)
        original_popen = subprocess.Popen

        def headless(arguments, **options):
            if arguments[0] == str(chrome):
                arguments = [arguments[0], "--headless=new", *arguments[1:]]
            return original_popen(arguments, **options)

        with patch("arena.adapters.agents.dsh_browser.subprocess.Popen", side_effect=headless):
            try:
                browser.open(origin + "/", origin)
                first = browser.snapshot()
                deadline = time.monotonic() + 10
                while not first["dialogs"] and time.monotonic() < deadline:
                    time.sleep(.1)
                    first = browser.snapshot()
                self.assertEqual(first["dialogs"][0]["key"], "approval:test-1")
                self.assertIn("cannot be undone", first["dialogs"][0]["text"])
                with tempfile.TemporaryDirectory() as folder:
                    image = Path(folder) / "confirmation.png"
                    self.assertIsInstance(browser.screenshot(image, key="approval:test-1"), dict)
                    self.assertTrue(image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                    self.assertFalse(browser.screenshot(image, key="absent-panel"))
                    if os.environ.get("ARENA_TEST_FFMPEG"):
                        video = Path(folder) / "viewport.mp4"
                        recorder = BrowserRecorder(os.environ["ARENA_TEST_FFMPEG"], browser)
                        recorder.select_window("Synthetic capture fixture")
                        try:
                            recorder.start(video)
                            # Observe while the recorder also uses the browser bridge.
                            self.assertEqual(browser.snapshot()["dialogs"][0]["key"], "approval:test-1")
                            time.sleep(.75)
                            recorder.check()
                        finally:
                            recorder.stop()
                        decoded = subprocess.run([os.environ["ARENA_TEST_FFMPEG"], "-v", "error", "-i", str(video),
                                                  "-frames:v", "1", "-vf", "scale=16:16", "-pix_fmt", "rgb24",
                                                  "-f", "rawvideo", "pipe:1"], capture_output=True, check=True)
                        self.assertEqual(len(decoded.stdout), 16 * 16 * 3)
                        self.assertGreater(sum(decoded.stdout) / len(decoded.stdout), 100, "Viewport recording is black")
                port = int((browser.profile / "DevToolsActivePort").read_text("utf8").splitlines()[0])
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(f"http://127.0.0.1:{port}/json/list") as response:
                    websocket = next(item["webSocketDebuggerUrl"] for item in json.load(response) if item["type"] == "page")
                # A separate test driver simulates the operator on this synthetic page only.
                driver = '''const fs=require('node:fs');const [url,expression]=JSON.parse(fs.readFileSync(0,'utf8'));
const ws=new WebSocket(url);ws.onopen=()=>ws.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression}}));
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id===1){ws.close();if(m.error||m.result.exceptionDetails)process.exitCode=1;}};
setTimeout(()=>process.exit(2),10000).unref();'''
                expression = "(()=>{const b=document.querySelector('button');b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.click();})()"
                subprocess.run([shutil.which("node"), "-e", driver], input=json.dumps([websocket, expression]),
                               text=True, check=True, timeout=15, capture_output=True)
                second = browser.snapshot()
                self.assertEqual(second["choices"][0]["key"], "approval:test-1")
                self.assertEqual(second["choices"][0]["label"], "Allow once")
                self.assertEqual(second["dialogs"][0]["key"], "approval:test-2")
            finally:
                profile = browser.profile
                browser.close()
                if profile:
                    self.assertFalse(profile.exists())


if __name__ == "__main__":
    unittest.main()
