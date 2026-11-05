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

LOCALIZED_PAGE = '''<!doctype html><html><meta charset="utf-8">
<title>Chinese workspace fixture</title><body>
<button aria-label="打开侧边栏" onclick="this.setAttribute('aria-label','收起侧边栏');document.querySelector('section').hidden=false">Sidebar</button>
<section hidden>
<button aria-label="在“another-workspace”中新建会话" onclick="document.title='Wrong workspace'">Other</button>
<button aria-label="在“fixture-owned”中新建会话" onclick="document.title='Selected fixture-owned';document.querySelector('main').innerHTML='<div contenteditable=true></div>';document.querySelector('[data-row-key]').setAttribute('data-row-key','session:selected-in-ui')">Owned</button>
<div role="treeitem" aria-selected="true" data-row-key="session:automatic-blank">Blank</div>
</section><main></main></body></html>'''.encode('utf8')


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(LOCALIZED_PAGE if self.path == '/localized' else PAGE)

    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which("node"), "Node.js is required for the browser command check")
class BrowserLayoutTests(unittest.TestCase):
    def test_background_layout_preserves_foreground_desktop(self):
        driver = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const methods = [];
class Socket {
  constructor() { queueMicrotask(() => this.onopen()); }
  send(raw) {
    const request = JSON.parse(raw);
    methods.push({method: request.method, params: request.params});
    const result = request.method === 'Browser.getWindowForTarget' ? {windowId: 1} : {};
    queueMicrotask(() => this.onmessage({data: JSON.stringify({id: request.id, result})}));
  }
}
const context = vm.createContext({
  require: () => ({createInterface: () => ({on() {return this;}})}),
  WebSocket: Socket, URL, setTimeout, clearTimeout, process: {stdin: {}},
});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8') + '\nthis.command = dispatch;', context);
(async () => {
  await context.command({action: 'connect', url: 'ws://127.0.0.1:1234'});
  methods.length = 0;
  await context.command({action: 'layout', region: [0, 0, 1200, 800], activate: false});
  const background = [...methods];
  methods.length = 0;
  await context.command({action: 'layout', region: [0, 0, 1200, 800]});
  const foreground = [...methods];
  methods.length = 0;
  await context.command({action: 'layout', region: [0, 0, 1200, 800], windowState: 'maximized', activate: false});
  console.log(JSON.stringify({background, foreground, maximized: methods}));
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
        bridge = Path(__file__).resolve().parents[1] / "src/arena/adapters/agents/dsh_browser.cjs"
        result = subprocess.run([shutil.which("node"), "-e", driver, str(bridge)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = json.loads(result.stdout)
        self.assertNotIn("Page.bringToFront", [row['method'] for row in calls["background"]])
        self.assertEqual([row['method'] for row in calls["background"]].count("Browser.setWindowBounds"), 2)
        self.assertIn("Page.bringToFront", [row['method'] for row in calls["foreground"]])
        bounds=[row['params']['bounds'] for row in calls['maximized'] if row['method']=='Browser.setWindowBounds']
        self.assertEqual(bounds[-1], {'windowState':'maximized'})
        self.assertNotIn("Page.bringToFront", [row['method'] for row in calls['maximized']])


@unittest.skipUnless(os.environ.get("ARENA_TEST_CHROME") and shutil.which("node"),
                     "Set ARENA_TEST_CHROME to run the local real-Chrome capture check")
class BrowserCaptureTests(unittest.TestCase):
    def test_real_browser_applies_maximized_window_and_larger_scale(self):
        chrome=Path(os.environ['ARENA_TEST_CHROME'])
        server=ThreadingHTTPServer(('127.0.0.1',0),PageHandler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        origin=f'http://127.0.0.1:{server.server_port}'
        browser=DshBrowser(shutil.which('node'),chrome,window_state='maximized',scale_factor=2)
        original_popen=subprocess.Popen
        translation_preferences=[]
        def headless(arguments,**options):
            if arguments[0]==str(chrome):
                profile=Path(next(value.partition('=')[2] for value in arguments if value.startswith('--user-data-dir=')))
                preferences=profile/'Default/Preferences'
                values=json.loads(preferences.read_text('utf8')) if preferences.exists() else {}
                translation_preferences.append(values.get('translate',{}).get('enabled'))
                arguments=[arguments[0],'--headless=new',*arguments[1:]]
            return original_popen(arguments,**options)
        with patch('arena.adapters.agents.dsh_browser.subprocess.Popen',side_effect=headless):
            try:
                browser.open(origin+'/',origin)
                browser.verify_title('Synthetic capture fixture')
                port=int((browser.profile/'DevToolsActivePort').read_text('utf8').splitlines()[0])
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://127.0.0.1:{port}/json/list') as response:
                    url=next(row['webSocketDebuggerUrl'] for row in json.load(response) if row['type']=='page')
                driver='''const ws=new WebSocket(process.argv[1]);let scale;
ws.onopen=()=>ws.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression:'devicePixelRatio',returnByValue:true}}));
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id===1){scale=m.result.result.value;ws.send(JSON.stringify({id:2,method:'Browser.getWindowForTarget'}));}
else if(m.id===2){ws.send(JSON.stringify({id:3,method:'Browser.getWindowBounds',params:{windowId:m.result.windowId}}));}
else if(m.id===3){console.log(JSON.stringify({scale,state:m.result.bounds.windowState}));ws.close();}};
setTimeout(()=>process.exit(2),10000).unref();'''
                result=subprocess.run([shutil.which('node'),'-e',driver,url],capture_output=True,text=True,check=True,timeout=15)
                self.assertEqual(json.loads(result.stdout),dict(scale=2,state='maximized'))
                self.assertTrue(browser.frame().startswith(b'\x89PNG'))
                self.assertEqual(translation_preferences,[False])
            finally:
                browser.close()

    def test_chinese_shell_is_ready_before_workspace_composer_exists(self):
        chrome = Path(os.environ["ARENA_TEST_CHROME"])
        server = ThreadingHTTPServer(("127.0.0.1", 0), PageHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
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
                browser.open(origin + "/localized", origin)
                browser.wait_ready()
                self.assertEqual(browser.prepare("fixture-owned"), "selected-in-ui")
                self.assertEqual(browser.snapshot()["title"], "Selected fixture-owned")
            finally:
                browser.close()

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
                            self.assertGreater(recorder.checkpoint(), recorder.started_at)
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
                with self.assertRaisesRegex(RuntimeError, 'changed'):
                    browser.choose_once('approval:test-2', 'different panel text')
                self.assertEqual(browser.snapshot()['dialogs'][0]['key'], 'approval:test-2')
                chosen = browser.choose_once('approval:test-2', second['dialogs'][0]['text'])
                self.assertEqual(chosen['label'], 'Allow once')
            finally:
                profile = browser.profile
                browser.close()
                if profile:
                    self.assertFalse(profile.exists())


if __name__ == "__main__":
    unittest.main()
