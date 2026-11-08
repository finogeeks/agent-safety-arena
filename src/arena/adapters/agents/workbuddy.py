"""WorkBuddy desktop launch helpers and owned-process adapter."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import re
import queue
from pathlib import Path
import subprocess
import time
import threading
import urllib.error
import urllib.request

from arena.adapters.agents.dsh import hidden_process_options, _descendant_pids


ACCOUNT_HIDE_SELECTORS = (
    '.user-menu-trigger',
    '.user-menu-trigger-miniprogram',
    '.conversation-list-invite-friends',
    '.conversation-list-invite-friends__card',
    '.msg-center-bell-btn',
)
ACCOUNT_TEXT = re.compile(
    r'(?i)[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}|Credits Up|Invite friends to WorkBuddy')
COMPOSER_PLACEHOLDERS = (
    'Plan, @ for context, / for commands',
)
PROBE_URL = 'http://127.0.0.1:18488/workbuddy/probe'


def launch_command(profile, workspace, confinement=None):
    port = profile['debugPort']
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('WorkBuddy debug port must be 1 to 65535')
    entry = profile.get('workbuddyEntry')
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError('WorkBuddy recording profile requires workbuddyEntry')
    command = [entry, '--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={port}', str(workspace)]
    if confinement:
        command = [confinement['executable'], 'app', 'launch', 'workbuddy',
                   '--yaml-path', confinement['config'], '--integration-id', 'workbuddy', '--', *command]
    return command


def workbuddy_confinement(profile):
    result = {}
    for field, key in [('finshield', 'executable'), ('finshieldConfig', 'config')]:
        path = profile.get(field)
        if not isinstance(path, str) or not Path(path).is_file():
            raise ValueError('WorkBuddy FinSafe launch file not found: ' + field)
        result[key] = str(Path(path).resolve())
    return result


def finshield_main_pid(line):
    try:
        value = json.loads(line)
    except (ValueError, TypeError):
        return None
    if (isinstance(value, dict) and value.get('hook_ready') is True
            and type(value.get('main_pid')) is int and value['main_pid'] > 0):
        return value['main_pid']
    return None


def wait_finshield_main(process, directory, timeout=60):
    ready = queue.Queue()
    def drain(stream, filename, inspect):
        from arena.runner.trial import scrub
        with (Path(directory) / filename).open('w', encoding='utf8') as output:
            for line in stream:
                output.write(scrub(line)); output.flush()
                pid = finshield_main_pid(line) if inspect else None
                if pid:
                    ready.put(pid)
        stream.close()
    for stream, filename, inspect in [(process.stdout, 'finsafe-launch.stdout.log', True),
                                     (process.stderr, 'finsafe-launch.stderr.log', False)]:
        threading.Thread(target=drain, args=(stream, filename, inspect), daemon=True).start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            pid = ready.get(timeout=.2)
        except queue.Empty:
            if process.poll() is not None:
                raise RuntimeError('FinSafe launcher exited before hook readiness; see saved launch logs')
            continue
        if pid not in _descendant_pids(process.pid):
            raise RuntimeError('FinSafe ready Main is not a child of the owned launcher')
        return pid
    raise RuntimeError('FinSafe launcher did not report original hook readiness')


def protected_daemon_pids(rows):
    by_pid = {row['pid']: row for row in rows}
    def basename(value):
        return str(value).replace('\\', '/').rsplit('/', 1)[-1].lower()
    return [row['pid'] for row in rows if row.get('appContainer') is True
            and basename(row.get('image')) in {'workbuddy.exe', 'workbuddyai.exe'}
            and basename(by_pid.get(row.get('parentId'), {}).get('image')) == 'finsafe.exe']


def execution_identities(main_pid):
    """Read image, parent and token flag in the owned subtree; omit arguments."""
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
        'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=15, check=True, **hidden_process_options())
    all_rows = json.loads(result.stdout)
    owned = {main_pid, *_descendant_pids(main_pid)}
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    rows = []
    for item in all_rows:
        if item['ProcessId'] not in owned:
            continue
        row = dict(pid=item['ProcessId'], parentId=item['ParentProcessId'], image=item['Name'], appContainer=None)
        process = kernel.OpenProcess(0x1000, False, row['pid'])
        token = wintypes.HANDLE()
        try:
            if not process or not advapi.OpenProcessToken(process, 8, ctypes.byref(token)):
                raise ctypes.WinError(ctypes.get_last_error())
            value, length = wintypes.DWORD(), wintypes.DWORD()
            if not advapi.GetTokenInformation(token, 29, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(length)):
                raise ctypes.WinError(ctypes.get_last_error())
            row['appContainer'] = bool(value.value)
        except OSError as error:
            row['tokenError'] = str(error)
        finally:
            if token.value: kernel.CloseHandle(token)
            if process: kernel.CloseHandle(process)
        rows.append(row)
    return rows


def presentation_has_account(text):
    return bool(ACCOUNT_TEXT.search(text or ''))


def composer_is_empty(text):
    value = (text or '').strip()
    return (not value) or value in COMPOSER_PLACEHOLDERS


def same_prompt(actual, expected):
    def plain(value):
        return re.sub(r'[ \t]+\n', '\n', str(value or '').replace('\r\n', '\n')).strip()
    return plain(actual) == plain(expected)


def events_from_view(view):
    request_id = view['requestId']
    prompt = view.get('prompt') or ''
    events = [
        {'seq': 0, 'type': 'turn/start', 'data': {'turn': 1}},
        {'seq': 1, 'type': 'user/message', 'data': {
            'content': [{'type': 'text', 'text': prompt}],
            'source': {'kind': 'user', 'rpcId': request_id}}},
    ]
    assistant = view.get('assistantText') or ''
    if assistant:
        events.append({'seq': 2, 'type': 'assistant/message', 'data': {
            'turn': 1, 'message': {'content': [{'type': 'text', 'text': assistant}]}}})
    if view.get('completed') and not view.get('running'):
        events.append({'seq': 3, 'type': 'turn/end', 'data': {
            'turn': 1, 'reason': {'kind': 'completed'}}})
    return events


def events_from_hook(output, prompt):
    """Normalize one owned native request without inferring an end from the UI."""
    request_id = output['requestId']
    events = []
    def add(kind, data):
        events.append(dict(seq=len(events), type=kind, data=data))
    add('turn/start', {'turn': 1})
    add('user/message', {'content': [{'type': 'text', 'text': prompt}],
                         'source': {'kind': 'user', 'rpcId': request_id}})
    text = []
    for row in output.get('events', []):
        if row.get('sessionId') != output['sessionId']:
            continue
        event = row['event']
        add('workbuddy/native', event)
        if row.get('topic') == 'sandbox:interceptRequest':
            add('approval/asked', {'id': event['requestId'], 'source': 'WorkBuddy native sandbox',
                'toolName': event.get('toolName') or 'sandbox', 'command': event.get('command'),
                'reason': event})
        update = event.get('update', {})
        kind = update.get('sessionUpdate')
        if kind == 'agent_message_chunk' and update.get('content', {}).get('type') == 'text':
            text.append(update['content']['text'])
        if kind == 'tool_call':
            arguments = update.get('rawInput') or {}
            add('tool/call', {'callId': update.get('toolCallId'),
                'toolName': update.get('name') or update.get('title'),
                'arguments': json.dumps(arguments, ensure_ascii=False)})
        if event.get('type') == 'permissionRequest':
            request = event.get('request') or {}
            call = request.get('toolCall') or {}
            arguments = call.get('rawInput') or {}
            add('approval/asked', {'id': event['requestId'], 'source': 'WorkBuddy native approval',
                'toolName': call.get('name') or call.get('title'),
                'callId': call.get('toolCallId'), 'command': arguments.get('command'),
                'reason': request})
    result = output.get('result') or {}
    native = result.get('nativeRequest') or {}
    meta = result.get('_meta') or {}
    final_text = native.get('assistantText') or (meta.get('codebuddy.ai') or {}).get('lastAssistantText') or ''.join(text)
    if final_text:
        add('assistant/message', {'turn': 1, 'message': {'content': [{'type': 'text', 'text': final_text}]}})
    if output.get('status') == 'error':
        add('turn/end', {'turn': 1, 'reason': {'kind': 'error', 'error': {'message': output.get('error')}}})
    elif output.get('status') == 'finished':
        stop = ({'completed': 'end_turn', 'cancelled': 'cancelled', 'error': 'error'}.get(native.get('state'))
                if native else result.get('stopReason'))
        kind = 'completed' if stop == 'end_turn' else 'cancelled' if stop in {'cancelled', 'canceled'} else 'error'
        reason = {'kind': kind, 'nativeStopReason': stop}
        if kind == 'error':
            reason['error'] = {'message': meta.get('codebuddy.ai/errorMessage') or str(stop)}
        add('turn/end', {'turn': 1, 'reason': reason})
    return events


class WorkBuddyDesktopGuard:
    """Pause capture on another desktop while the native task continues."""
    def __init__(self, desktop, recorder, agent, sleep=time.sleep):
        self.desktop, self.recorder, self.agent, self.sleep = desktop, recorder, agent, sleep

    def check(self):
        if self.desktop.current() == self.desktop.number:
            return
        from arena.runner.trial import save
        path = self.agent.directory / 'recording-interruptions.json'
        rows = json.loads(path.read_text(encoding='utf8')) if path.exists() else []
        item = dict(pausedAtUnixMs=round(time.time()*1000), resumeAtUnixMs=None,
                    reason='Operator desktop changed', approvalInputWhilePaused=False,
                    observation='Native task continues; capture interval is missing')
        rows.append(item)
        self.recorder.set_paused(True)
        save(path, rows)
        while self.desktop.current() != self.desktop.number:
            if (self.agent.directory / 'stop').exists():
                self.desktop.switch(self.desktop.number)
                self.recorder.set_paused(False)
                raise RuntimeError('Operator stopped the recording while capture was paused')
            self.sleep(.2)
        self.recorder.set_paused(False)
        item['resumeAtUnixMs'] = round(time.time()*1000)
        save(path, rows)


def loopback_json(url, timeout=2):
    request = urllib.request.Request(url, method='GET')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def debug_port_open(port):
    try:
        version = loopback_json(f'http://127.0.0.1:{port}/json/version')
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None
    browser = str(version.get('Browser') or '')
    if 'Chrome/' not in browser and 'Chromium/' not in browser:
        return None
    return version


def running_workbuddy_pids():
    result = subprocess.run(
        ['tasklist', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True, timeout=10, **hidden_process_options())
    pids = []
    for line in result.stdout.splitlines():
        parts = [item.strip().strip('"') for item in line.split(',')]
        if len(parts) >= 2 and parts[0].lower() in {'workbuddyai.exe', 'workbuddy.exe'}:
            try:
                pids.append(int(parts[1]))
            except ValueError:
                continue
    return pids


def stop_owned_debug_instance(port):
    if running_workbuddy_pids() or debug_port_open(port) is not None:
        raise RuntimeError('Another WorkBuddy instance owns the process lock; will not attach to an unknown session')
    return {'stoppedExisting': False}


def wait_for_probe(timeout=60):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = loopback_json(PROBE_URL)
            if last.get('ok') is True and last.get('app') == 'workbuddy-desktop':
                return last
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            last = None
        time.sleep(.2)
    raise RuntimeError('WorkBuddy loopback probe did not become ready')


def maximize_owned_windows(process_ids):
    """Maximize visible windows of the owned WorkBuddy process tree. Do not move the pointer."""
    pids = {int(pid) for pid in process_ids}
    if not pids:
        raise RuntimeError('WorkBuddy process id is missing')
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    found = []

    @callback_type
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            found.append(hwnd)
        return True

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        found.clear()
        user32.EnumWindows(visit, 0)
        if found:
            for hwnd in found:
                user32.ShowWindow(hwnd, 3)
                user32.SetForegroundWindow(hwnd)
            return [int(hwnd) for hwnd in found]
        time.sleep(.2)
    raise RuntimeError('Could not maximize a visible WorkBuddy window')


def wait_for_page(port, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            pages = loopback_json(f'http://127.0.0.1:{port}/json/list')
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            pages = []
        page = next((item for item in pages if item.get('type') == 'page'
                     and (item.get('title') == 'WorkBuddy'
                          or '/renderer/index.html' in (item.get('url') or ''))), None)
        if page and page.get('webSocketDebuggerUrl', '').startswith('ws://127.0.0.1:'):
            return {'id': page.get('id'), 'title': page.get('title'),
                    'webSocketDebuggerUrl': page['webSocketDebuggerUrl']}
        time.sleep(.2)
    raise RuntimeError('WorkBuddy CDP page was not found on the owned debug port')


class WorkBuddyAgent:
    """Start the installed WorkBuddy desktop app and admit one owned prompt."""

    def __init__(self, profile, process_boundary=None, confinement=None):
        self.profile = profile
        self.confinement = confinement
        self.main_pid = None
        self.process_boundary = process_boundary
        self.process = None
        self.view = None
        self.request_id = None
        self.prompt = None
        self.directory = None

    def prepare(self, workspace, browser, evidence_directory):
        self.directory = Path(evidence_directory)
        self.view = browser
        stopped = stop_owned_debug_instance(self.profile['debugPort'])
        save_startup = self.directory / 'workbuddy-startup.json'
        command = launch_command(self.profile, workspace, self.confinement)
        self.process = subprocess.Popen(
            command, cwd=workspace, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if self.confinement else subprocess.DEVNULL,
            stderr=subprocess.PIPE if self.confinement else subprocess.DEVNULL,
            text=True, encoding='utf8', **hidden_process_options())
        if self.process_boundary:
            try:
                self.process_boundary.assign(self.process, evidence_directory)
                stopped['jobAssigned'] = True
            except OSError as error:
                stopped['jobAssigned'] = False
                stopped['jobAssignError'] = str(error)
        self.main_pid = wait_finshield_main(self.process, self.directory) if self.confinement else self.process.pid
        stopped.update(launcherPid=self.process.pid, mainPid=self.main_pid, finSafe=bool(self.confinement))
        save_startup.write_text(json.dumps(stopped, indent=2) + '\n', encoding='utf8')
        probe = wait_for_probe()
        if self.process.poll() is not None:
            raise RuntimeError('WorkBuddy exited before the owned page was ready')
        page = wait_for_page(self.profile['debugPort'])
        browser.connect(page['webSocketDebuggerUrl'], self.main_pid)
        browser.prepare()
        session = browser.prepare_session(workspace, self.profile['modelId'],
                                          require_native_sandbox=not self.confinement)
        if self.confinement:
            identities = execution_identities(self.main_pid)
            (self.directory / 'workbuddy-process-identities.json').write_text(
                json.dumps(identities, indent=2) + '\n', encoding='utf8')
            if not protected_daemon_pids(identities):
                raise RuntimeError('No owned WorkBuddy AppContainer daemon under a FinSafe supervisor; no prompt submitted')
        visible = browser.snapshot()
        account = visible.get('visibleAccountText') or ''
        if presentation_has_account(account) or visible.get('accountVisible'):
            raise RuntimeError('Account chrome is still visible; no prompt submitted')
        return {
            'sessionId': session['sessionId'],
            'agent': 'WorkBuddy',
            'agentVersion': probe.get('version') or 'unknown',
            'model': {'model': session['modelId'].removeprefix('custom-local:'), 'reasoningEffort': 'not-exposed'},
            'nativeModelId': session['modelId'],
            'permissions': {'currentValue': session['permissionMode']},
            'nativeSandboxEnabled': session['useSandboxCLI'],
            'captureWindowTitle': visible.get('title') or 'WorkBuddy',
            'addedProtection': bool(self.confinement),
            'sandboxMode': 'enabled' if session['useSandboxCLI'] else 'disabled',
            'approvalPolicy': 'ask',
            'uiLanguage': visible.get('uiLanguage') or 'und',
        }

    def finish_startup(self, browser, recorder, directory):
        browser.hide_account()
        visible = browser.snapshot()
        account = visible.get('visibleAccountText') or ''
        if presentation_has_account(account) or visible.get('accountVisible'):
            raise RuntimeError('Account chrome is still visible after recording start; no prompt submitted')
        return {}

    def submit(self, prompt, request_id):
        self.prompt = prompt
        self.request_id = request_id
        self.view.hook_submit(prompt, request_id)

    def observe(self):
        if self.process and self.process.poll() is not None:
            raise RuntimeError('Owned WorkBuddy process exited before trial completion')
        output = self.view.hook_output()
        if self.directory:
            from arena.runner.trial import save
            save(self.directory / 'workbuddy-hook-output.json', output)
        return events_from_hook(output, self.prompt or '')

    def cancel(self):
        if self.view:
            self.view.hook_cancel()

    def close(self):
        if self.confinement and self.main_pid and self.process and self.process.poll() is None:
            if self.main_pid in _descendant_pids(self.process.pid):
                subprocess.run(['taskkill', '/PID', str(self.main_pid), '/T', '/F'],
                               capture_output=True, timeout=15, **hidden_process_options())
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'],
                               capture_output=True, timeout=10, **hidden_process_options())
                self.process.wait(timeout=5)
