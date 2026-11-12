"""CDP view over the owned WorkBuddy renderer. Do not launch a second Chrome."""
import base64
import json
from pathlib import Path
import subprocess
import threading

from arena.adapters.agents.dsh import hidden_process_options
from arena.adapters.agents.workbuddy import maximize_owned_windows, running_workbuddy_pids


class WorkBuddyView:
    def __init__(self, node, desktop=None, window_size=(1200, 800), window_state='maximized'):
        self.node = str(node)
        self.desktop = desktop
        self.window_size = window_size
        self.window_state = window_state
        self.bridge = None
        self.pid = None
        self.command_lock = threading.Lock()

    def connect(self, websocket_url, process_id):
        if not isinstance(websocket_url, str) or not websocket_url.startswith('ws://127.0.0.1:'):
            raise RuntimeError('WorkBuddy CDP must use the owned loopback listener')
        self.pid = process_id
        self.bridge = subprocess.Popen(
            [self.node, str(Path(__file__).with_suffix('.cjs'))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf8', **hidden_process_options())
        self.command('connect', url=websocket_url)
        if self.desktop and self.pid:
            self.desktop.move(self.pid)
        self.layout()

    def command(self, action, **fields):
        with self.command_lock:
            if self.bridge is None or self.bridge.poll() is not None:
                raise RuntimeError('The WorkBuddy observer is not running')
            self.bridge.stdin.write(json.dumps({'action': action, **fields}) + '\n')
            self.bridge.stdin.flush()
            line = self.bridge.stdout.readline()
        if not line:
            raise RuntimeError('The WorkBuddy observer exited')
        response = json.loads(line)
        if not response['ok']:
            raise RuntimeError(response['error'])
        return response.get('value')

    def layout(self):
        pids = set(running_workbuddy_pids())
        if self.pid:
            pids.add(int(self.pid))
        if self.window_state == 'maximized':
            maximize_owned_windows(pids)

    def prepare(self):
        self.command('prepare')
        self.hide_account()
        self.layout()
        if self.desktop and self.pid:
            self.desktop.verify(self.pid)

    def hide_account(self):
        self.command('hide-account')

    def fill(self, prompt):
        self.layout()
        self.command('fill', text=prompt)

    def prepare_session(self, workspace, model_id, require_native_sandbox=True):
        return self.command('hook-prepare', workspace=str(workspace), modelId=model_id,
                            requireNativeSandbox=require_native_sandbox)

    def hook_submit(self, prompt, request_id):
        return self.command('hook-submit', text=prompt, requestId=request_id)

    def hook_output(self):
        return self.command('hook-output')

    def hook_cancel(self):
        return self.command('hook-cancel')

    def send(self):
        self.command('send')

    def cancel(self):
        try:
            self.command('cancel')
        except RuntimeError:
            pass

    def snapshot(self):
        return self.command('snapshot')

    def view_state(self):
        return self.command('view')

    def verify_presentation(self):
        self.hide_account()
        self.layout()
        if self.desktop and self.pid:
            return self.desktop.verify(self.pid)
        return {}

    def choose_once(self, key, text, label=None):
        return self.command('choose-once', key=key, text=text, label=label)

    def screenshot(self, path, key=None):
        screenshot = self.command('screenshot', key=key)
        if screenshot is False:
            return False
        Path(path).write_bytes(base64.b64decode(screenshot['data'], validate=True))
        return {'at': screenshot['at']}

    def close(self):
        if not self.bridge:
            return
        try:
            if self.bridge.poll() is None:
                self.command('close')
        except (RuntimeError, OSError):
            pass
        finally:
            try:
                self.bridge.stdin.close()
            except OSError:
                pass
            try:
                self.bridge.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.bridge.kill()
                self.bridge.wait(timeout=5)
            try:
                self.bridge.stdout.close()
            except OSError:
                pass
            self.bridge = None
