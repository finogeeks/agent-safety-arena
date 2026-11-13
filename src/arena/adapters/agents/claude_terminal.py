"""Owned Windows Terminal presentation of the real Claude interactive CLI."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import uuid

from arena.adapters.agents.claude import (
    ClaudeEventStream, apply_powershell_shell, approval_panel, bash_startup_failure,
    command_from_panel, execution_tool_names, numbered_picker, session_turn_complete,
    session_cli_arguments, validate_session_settings)
from arena.adapters.agents.codex_terminal import NativeTerminalView, native_window
from arena.adapters.agents.dsh import hidden_process_options

def claude_confinement(profile):
    result = {}
    for field, key in [('finshield', 'executable'), ('finshieldConfig', 'config')]:
        path = profile.get(field)
        if not isinstance(path, str) or not Path(path).is_file():
            raise ValueError('Claude FinShield launch file not found: ' + field)
        result[key] = str(Path(path).resolve())
    return result


def self_confine_wrap(confinement):
    if not confinement:
        return None
    return {'executable': confinement['executable'],
            'args': ['self-confine', '--yaml-path', confinement['config'],
                     '--stdio', 'inherit', '--integration-id', 'claude', '--']}


def finshield_cli_overrides(confinement):
    return []


TRUST_MARKERS = ('Do you trust the files in this folder?', 'Do you trust the contents of this directory?',
                 'Trust this folder?', 'Yes, I trust this folder', 'Accessing workspace:',
                 'Is this a project you created or one you trust?')
TRUST_CHOICE = r'(?m)^\s*[❯›>»]\s*(?:1\.\s*)?(Yes, proceed|Yes, I trust this folder|Yes, I trust|Trust and continue)\b'
THEME_MARKER = 'Choose the text style that looks best with your terminal'
AUTO_THEME = r'(?m)^\s*[❯›>»].*Auto \(match terminal\)\s*$'
HOST_KEYS = dict(ctrl=0x11, shift=0x10, alt=0x12, enter=0x0D, v=0x56, tab=0x09,
                 down=0x28, up=0x26, **{str(n): 0x30 + n for n in range(1, 10)})


def environment_context_picker(text):
    return bool(re.search(r'(?i)teach\s+auto\s+mode\s+about\s+your\s+environment', text))


def startup_kind(text):
    if THEME_MARKER in text:
        return 'theme'
    if environment_context_picker(text):
        return 'environment-context'
    if re.search(r'(?i)press enter to continue', text):
        return 'continue'
    if any(marker in text for marker in TRUST_MARKERS):
        return 'trust'
    if re.search(r'(?i)would you like to use .{0,40}auto mode', text):
        return 'auto-mode-opt-in'
    if re.search(r'(?i)(/login|please log in|api key)', text):
        return 'login'
    ready = '? for shortcuts' in text or ('Claude Code' in text and 'deepseek' in text.lower())
    if ready and numbered_picker(text) is None:
        return 'ready'
    return 'unknown'


def is_idle(text):
    if numbered_picker(text):
        return False
    if re.search(r'(?i)esc to interrupt|(?<![a-z])to interrupt', text):
        return False
    if '? for shortcuts' in text:
        return True
    prompt = bool(re.search(r'(?m)^[❯›>]\s*$', text))
    footer = bool(re.search(r'(?i)auto mode on|bypass permissions on', text))
    return prompt and (footer or 'Claude Code' in text)


def encoded_project_name(workspace):
    return str(Path(workspace)).replace('\\', '-').replace('/', '-').replace(':', '-')


def public_assistant_text(rows):
    texts = []
    for row in rows:
        if row.get('type') != 'assistant':
            continue
        message = row.get('message') or {}
        content = message.get('content')
        if isinstance(content, str) and content.strip():
            texts.append(content)
        elif isinstance(content, list):
            chunk = '\n'.join(part.get('text', '') for part in content
                              if isinstance(part, dict) and part.get('type') == 'text' and part.get('text'))
            if chunk.strip():
                texts.append(chunk)
    return '\n'.join(texts)


class ClaudeTerminalView(NativeTerminalView):
    def launch(self, workspace, directory, url, cli_overrides=None, confinement=None):
        overrides = list(cli_overrides or [])
        if overrides and (len(overrides) != 2 or overrides[0] != '--settings'):
            raise RuntimeError('Claude launch accepts only one prepared session settings file')
        digest = None
        if overrides:
            overrides[1], digest = validate_session_settings(overrides[1])
        self.directory = directory
        self.title = 'Arena Claude CLI ' + uuid.uuid4().hex[:12]
        spec = dict(launchModule=self.profile['launchModule'], launchConfig=self.profile['launchConfig'],
                    workspace=str(workspace), directory=str(directory), cliOverrides=overrides,
                    sessionSettingsSha256=digest)
        if confinement:
            spec['confinement'] = confinement
        spec_path = directory / 'terminal-launch.json'
        spec_path.write_text(json.dumps(spec), encoding='utf8')
        command = [self.profile['node'], str(Path(__file__).with_name('claude_ui.mjs')), str(spec_path)]
        root = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/Windows Terminal/Fragments'
        folder = root / ('Arena-' + directory.name)
        folder.mkdir(parents=True)
        self.fragment = folder / 'profile.json'
        name = 'Arena Claude ' + directory.name
        fragment = {'profiles': [{'guid': '{' + str(uuid.uuid4()) + '}', 'name': name,
            'commandline': subprocess.list2cmdline(command), 'startingDirectory': str(workspace),
            'font': {'face': 'Cascadia Mono', 'size': self.profile['fontSize']},
            'colorScheme': 'One Half Light', 'background': '#FFFFFF', 'foreground': '#202020',
            'useAcrylic': False, 'opacity': 100, 'closeOnExit': 'always',
            'suppressApplicationTitle': True, 'tabTitle': self.title}]}
        self.fragment.write_text(json.dumps(fragment), encoding='utf8')
        subprocess.run([self.profile['terminal'], '--window', 'new', '--maximized', 'new-tab',
            '--profile', fragment['profiles'][0]['guid'], '--colorScheme', 'One Half Light',
            '--title', self.title, '--suppressApplicationTitle', '--startingDirectory', str(workspace), *command],
            check=True, capture_output=True, timeout=20, **hidden_process_options())
        deadline = time.monotonic() + 60
        processes = directory / 'terminal-processes.json'
        while time.monotonic() < deadline:
            found = native_window(self.title)
            if found and processes.exists():
                self.handle, self.pid = found
                self.processes = json.loads(processes.read_text())
                self.desktop.call('/GetDesktop:' + str(self.desktop.number - 1), '/MoveWindowHandle:' + str(self.handle))
                self.verify_presentation()
                return
            time.sleep(.2)
        raise RuntimeError('The native Claude terminal did not start; no prompt submitted')

    def focus(self):
        user = c.WinDLL('user32', use_last_error=True)
        kernel = c.WinDLL('kernel32', use_last_error=True)
        user.GetForegroundWindow.restype = w.HWND
        user.SetForegroundWindow.argtypes = [w.HWND]
        user.BringWindowToTop.argtypes = [w.HWND]
        user.ShowWindow.argtypes = [w.HWND, c.c_int]
        user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
        user.GetWindowThreadProcessId.restype = w.DWORD
        user.AttachThreadInput.argtypes = [w.DWORD, w.DWORD, w.BOOL]
        user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, c.c_size_t]
        user.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
        user.SetCursorPos.argtypes = [c.c_int, c.c_int]
        user.mouse_event.argtypes = [w.DWORD, w.DWORD, w.DWORD, w.DWORD, c.c_size_t]
        kernel.GetCurrentThreadId.restype = w.DWORD
        deadline = time.monotonic() + 4
        clicked = False
        while True:
            user.ShowWindow(self.handle, 3)
            user.BringWindowToTop(self.handle)
            user.PostMessageW(self.handle, 0x0050, 0, 0x0409)
            foreground = user.GetForegroundWindow()
            current = kernel.GetCurrentThreadId()
            target = user.GetWindowThreadProcessId(self.handle, None)
            attached = []
            if foreground:
                other = user.GetWindowThreadProcessId(foreground, None)
                for thread in (other, target):
                    if thread and thread != current:
                        user.AttachThreadInput(current, thread, True)
                        attached.append(thread)
            user.keybd_event(0x12, 0, 0, 0)
            user.SetForegroundWindow(self.handle)
            user.keybd_event(0x12, 0, 2, 0)
            for thread in attached:
                user.AttachThreadInput(current, thread, False)
            time.sleep(.2)
            if int(user.GetForegroundWindow() or 0) == self.handle:
                return
            if not clicked:
                rect = w.RECT()
                if user.GetWindowRect(self.handle, c.byref(rect)):
                    user.SetCursorPos((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                    user.mouse_event(0x0002, 0, 0, 0, 0)
                    user.mouse_event(0x0004, 0, 0, 0, 0)
                clicked = True
            if time.monotonic() >= deadline:
                raise RuntimeError('The owned terminal is not foreground; no prompt input sent')
            time.sleep(.3)

    def press(self, *names):
        user = c.WinDLL('user32', use_last_error=True)
        user.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, c.c_size_t]
        codes = [HOST_KEYS[name] for name in names]
        for code in codes:
            user.keybd_event(code, 0, 0, 0)
        for code in reversed(codes):
            user.keybd_event(code, 0, 2, 0)

    def set_clipboard(self, text):
        user = c.WinDLL('user32', use_last_error=True)
        kernel = c.WinDLL('kernel32', use_last_error=True)
        user.OpenClipboard.argtypes = [w.HWND]
        user.OpenClipboard.restype = w.BOOL
        user.EmptyClipboard.restype = w.BOOL
        user.CloseClipboard.restype = w.BOOL
        user.SetClipboardData.argtypes = [w.UINT, w.HANDLE]
        user.SetClipboardData.restype = w.HANDLE
        kernel.GlobalAlloc.argtypes = [w.UINT, c.c_size_t]
        kernel.GlobalAlloc.restype = w.HGLOBAL
        kernel.GlobalLock.argtypes = [w.HGLOBAL]
        kernel.GlobalLock.restype = c.c_void_p
        kernel.GlobalUnlock.argtypes = [w.HGLOBAL]
        payload = text.replace('\n', '\r\n') if '\r' not in text else text
        data = (payload + '\0').encode('utf-16-le')
        handle = kernel.GlobalAlloc(0x0002, len(data))
        if not handle:
            raise RuntimeError('Could not allocate clipboard memory; no prompt submitted')
        locked = kernel.GlobalLock(handle)
        c.memmove(locked, data, len(data))
        kernel.GlobalUnlock(handle)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if user.OpenClipboard(None):
                break
            time.sleep(.05)
        else:
            raise RuntimeError('Could not open the clipboard; no prompt submitted')
        try:
            user.EmptyClipboard()
            if not user.SetClipboardData(13, handle):
                raise RuntimeError('Could not set clipboard text; no prompt submitted')
            handle = None
        finally:
            user.CloseClipboard()

    def snapshot(self):
        self.agent.observe()
        try:
            text = self.text()
        except RuntimeError:
            text = ''
        panel = approval_panel(text, self.agent.stream.pending)
        choices = self.choices
        self.choices = []
        return dict(title=self.title, dialogs=[panel] if panel else [], choices=choices, uiLanguage='en',
                    terminalText=text)

    def choose_once(self, key, text, label=None):
        panel = next((item for item in self.snapshot()['dialogs'] if item['key'] == key), None)
        if panel is None:
            raise RuntimeError('The captured native CLI approval changed; no choice made')
        items = numbered_picker(panel['text'])
        at = round(time.time() * 1000)
        self.agent.awaiting_decision = True
        self.focus()
        if items and not items[0]['selected']:
            self.press('1')
            time.sleep(.2)
            self.focus()
        self.press('enter')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.agent.observe()
            decided = next((event for event in reversed(self.agent.stream.events)
                            if event['type'] == 'approval/decided' and event['data']['id'] == key), None)
            if decided:
                if decided['data']['nativeDecision'] != 'accept':
                    raise RuntimeError('The native CLI did not confirm a one-time approval')
                choice = dict(key=key, label=panel['oneTimeChoice'], at=at)
                self.choices.append(choice)
                return choice
            time.sleep(.1)
        raise RuntimeError('The native one-time CLI choice was not observed')


class ClaudeTerminalAgent:
    def __init__(self, profile, boundary, confinement=None, native_preparation=None):
        self.profile = profile
        self.boundary = boundary
        self.confinement = confinement
        self.native_preparation = native_preparation
        self.stream = ClaudeEventStream()
        self.process = None
        self.awaiting_decision = False
        self._saw_work = False
        self._idle_since = None
        self._idle_text = None
        self._transcript_rows = 0

    def prepare(self, workspace, browser, evidence_directory):
        self.directory = evidence_directory
        self.workspace = workspace
        self.browser = browser
        browser.agent = self
        setup = json.loads(Path(self.profile['launchConfig']).read_text(encoding='utf8'))
        executable = setup['claudeExecutable']
        home = setup['claudeHome']
        self.claude_home = Path(home)
        self._existing_transcripts = set((self.claude_home/'projects').rglob('*.jsonl'))
        shell = apply_powershell_shell(self.claude_home)
        environment = os.environ.copy()
        environment['CLAUDE_CONFIG_DIR'] = home
        version = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10,
                                 env=environment, **hidden_process_options()).stdout.strip()
        self.version = re.sub(r'^(Claude Code\s+)?', '', version, flags=re.I).split()[0] if version else 'unknown'
        wrap = self_confine_wrap(self.confinement)
        overrides = session_cli_arguments(self.native_preparation)
        snapshot = dict(policyOverrides=bool(overrides), cliOverrides=overrides,
                        directoryRulesFromSession=bool(overrides), approvalModeOverridden=False,
                        osSandboxOverridden=False,
                        transport=('Native Claude CLI in Windows Terminal; no app-server observation proxy; '
                                   'pending approval identity is the visible one-time panel'),
                        modelAliases='deepseek-v4-pro', effort='high',
                        shellPolicy=dict(
                            CLAUDE_CODE_USE_POWERSHELL_TOOL=shell['env']['CLAUDE_CODE_USE_POWERSHELL_TOOL'],
                            defaultShell=shell['defaultShell'],
                            deny=list(shell['permissions']['deny']),
                            gitUninstalled=False,
                            gitBashPathEnvRemoved=True))
        (evidence_directory / 'configuration-provenance.json').write_text(
            json.dumps(snapshot, indent=2), encoding='utf8')
        if wrap:
            (evidence_directory / 'finshield-wrap.json').write_text(json.dumps(wrap, indent=2), encoding='utf8')
        self.process = subprocess.Popen(
            [sys.executable, '-c', 'import time\nwhile True: time.sleep(1)'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_process_options())
        self.boundary.assign(self.process, evidence_directory)
        browser.launch(workspace, evidence_directory, None, cli_overrides=overrides, confinement=wrap)
        return dict(agent='Claude CLI', agentVersion=self.version, captureWindowTitle=browser.title,
                    addedProtection=bool(self.confinement), uiLanguage='en',
                    presentation='native Windows Terminal',
                    transport=snapshot['transport'],
                    processBoundaryLimit=('Windows Terminal owns the visible Claude process; '
                                          'the adapter Job holds a recovery observer process only'))

    def finish_startup(self, browser, recorder, directory):
        deadline = time.monotonic() + 150
        startup = []
        while time.monotonic() < deadline:
            text = browser.text()
            kind = startup_kind(text)
            if kind == 'environment-context':
                target = directory / f'startup-{len(startup) + 1}.png'
                browser.screenshot(target)
                checkpoint = recorder.checkpoint()
                time.sleep(2)
                items = numbered_picker(text)
                recorder.check()
                if not items:
                    raise RuntimeError('Native environment setup choices are unavailable; no prompt submitted')
                browser.focus()
                if not items[0]['selected']:
                    browser.press('1')
                browser.press('enter')
                startup.append(dict(kind='native-environment-setup', text=text, screenshot=target.name,
                                    recordedPanelAt=checkpoint, actor='automation', choice=items[0]['label']))
                (directory/'startup-confirmations.json').write_text(json.dumps(startup,indent=2),encoding='utf8')
                time.sleep(.5)
                continue
            if kind == 'theme':
                target = directory / f'startup-{len(startup) + 1}.png'
                browser.screenshot(target)
                checkpoint = recorder.checkpoint()
                time.sleep(2)
                recorder.check()
                if not re.search(AUTO_THEME, text):
                    browser.console('key', key='up')
                    time.sleep(.3)
                    text = browser.text()
                    if not re.search(AUTO_THEME, text):
                        raise RuntimeError('Native Claude theme picker did not select Auto; no prompt submitted')
                browser.console('key', key='enter')
                startup.append(dict(kind='native-cli-setup', text=text, screenshot=target.name,
                                    recordedPanelAt=checkpoint, actor='automation',
                                    choice='Auto (match terminal) for the owned Windows Terminal theme'))
                (directory / 'startup-confirmations.json').write_text(json.dumps(startup, indent=2), encoding='utf8')
                time.sleep(.4)
                continue
            if kind == 'continue':
                target = directory / f'startup-{len(startup) + 1}.png'
                browser.screenshot(target)
                checkpoint = recorder.checkpoint()
                time.sleep(2)
                recorder.check()
                browser.console('key', key='enter')
                startup.append(dict(kind='native-cli-setup', text=text, screenshot=target.name,
                                    recordedPanelAt=checkpoint, actor='automation',
                                    choice='Press Enter to continue'))
                (directory / 'startup-confirmations.json').write_text(json.dumps(startup, indent=2), encoding='utf8')
                time.sleep(.4)
                continue
            if kind == 'trust':
                compact = lambda value: ''.join(value.split()).lower()
                named = compact(str(self.workspace)) in compact(text) or compact(Path(self.workspace).name) in compact(text)
                if not named:
                    raise RuntimeError('The native trust prompt does not name the owned workspace')
                target = directory / f'startup-{len(startup) + 1}.png'
                browser.screenshot(target)
                checkpoint = recorder.checkpoint()
                time.sleep(2)
                recorder.check()
                if not re.search(TRUST_CHOICE, text):
                    browser.console('key', key='down')
                    time.sleep(.3)
                    text = browser.text()
                    if not re.search(TRUST_CHOICE, text):
                        raise RuntimeError('The owned workspace trust choice is not selected; no prompt submitted')
                browser.console('key', key='enter')
                startup.append(dict(kind='native-workspace-initialization', text=text, screenshot=target.name,
                                    recordedPanelAt=checkpoint, actor='automation',
                                    choice='Yes, I trust this folder for the declared owned workspace'))
                (directory / 'startup-confirmations.json').write_text(json.dumps(startup, indent=2), encoding='utf8')
                time.sleep(.3)
                continue
            if kind == 'auto-mode-opt-in':
                raise RuntimeError('Native Claude presented an auto-mode opt-in; no prompt submitted')
            if kind == 'login':
                raise RuntimeError('Native Claude is not authenticated; no prompt submitted')
            if kind == 'ready':
                browser.screenshot(directory / 'presentation.png')
                permission = self.permission_mode(text)
                self.stream.conditions.update(model='deepseek-v4-pro', provider='deepseek',
                                              reasoningEffort='high', sandboxMode='none',
                                              approvalPolicy=permission)
                (directory / 'initial-native-events.json').write_text(
                    json.dumps(self.stream.events, indent=2), encoding='utf8')
                (directory / 'startup-terminal.txt').write_text(text, encoding='utf8')
                return dict(sessionId='claude-native',
                            model={key: self.stream.conditions[key] for key in
                                   ('model', 'provider', 'reasoningEffort')},
                            sandboxMode='none', approvalPolicy=permission)
            time.sleep(.2)
        (directory / 'startup-terminal.txt').write_text(browser.text(), encoding='utf8')
        browser.screenshot(directory / 'startup-screen.png')
        raise RuntimeError('Native CLI startup did not reach a blank thread; no prompt submitted')

    def permission_mode(self, text):
        lines = [line for line in text.splitlines() if line.strip()]
        tail = '\n'.join(lines[-8:]).lower()
        if 'bypass' in tail:
            return 'bypass'
        if re.search(r'\bauto\b', tail):
            return 'auto'
        return 'default'

    def submit(self, prompt, request_id):
        self.stream.prompt = prompt
        self.stream.request_id = request_id
        self.stream.admitted_prompt = prompt
        self.stream.emit('turn/start', turn='1')
        self.stream.emit('user/message', source={'rpcId': request_id}, turn='1',
                         message={'content': [{'type': 'text', 'text': prompt}]})
        (self.directory / 'native-admitted-prompt.txt').write_text(prompt, encoding='utf8')
        self.browser.focus()
        self.browser.set_clipboard(prompt)
        self.browser.press('ctrl', 'shift', 'v')
        time.sleep(5)
        self.browser.screenshot(self.directory / 'opening-screen.png')
        self.browser.focus()
        self.browser.press('enter')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            text = self.browser.text()
            if re.search(r'(?i)esc to interrupt|(?<![a-z])to interrupt', text) or 'Do you want to proceed?' in text:
                break
            time.sleep(.3)
        else:
            self.browser.focus()
            self.browser.press('enter')
        self._saw_work = False
        self._idle_since = None
        self._idle_text = None

    def observe(self):
        if not hasattr(self, 'browser'):
            return self.stream.events
        text = ''
        try:
            text = self.browser.text()
            self.sync_approval(text)
        except RuntimeError:
            pass
        rows = self.transcript_rows()
        self.stream.ingest_tools(rows)
        self.sync_completion(text, rows=rows)
        return self.stream.events

    def sync_approval(self, text):
        items = numbered_picker(text)
        pending_setup = any(row.get('kind')=='environment-context' for row in self.stream.pending.values())
        if self.stream.pending and self.awaiting_decision and (not items or
                (pending_setup and not environment_context_picker(text))):
            key = next(iter(self.stream.pending))
            self.stream.emit('approval/decided', id=key, outcome='accept', nativeDecision='accept')
            self.stream.pending.clear()
            self.awaiting_decision = False
            return
        if session_turn_complete(self.transcript_rows()):
            return
        if items:
            if self.stream.pending:
                return
            tool, command = command_from_panel(text)
            key = 'native-' + str(len(self.stream.events))
            setup = environment_context_picker(text)
            tool = 'setup' if setup else tool or 'unknown'
            command = 'Initialize auto-mode environment context' if setup else command or items[0]['label']
            self.stream.pending[key] = dict(toolName=tool, command=command,
                                           kind='environment-context' if setup else 'action')
            self.stream.emit('approval/asked', id=key, toolName=tool, command=command,
                             source='Claude CLI environment setup' if setup else 'Claude CLI native approval')
            return

    def transcript_rows(self):
        if not hasattr(self, 'claude_home'):
            return []
        root = self.claude_home / 'projects'
        if not root.is_dir():
            return []
        encoded = encoded_project_name(self.workspace)
        folders = [path for path in root.iterdir() if path.is_dir() and encoded in path.name]
        files = []
        for folder in folders:
            files.extend(path for path in folder.rglob('*.jsonl')
                         if path not in getattr(self, '_existing_transcripts', set()))
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        rows = []
        for path in files[:4]:
            candidate = []
            for line in path.read_text(encoding='utf8', errors='replace').splitlines():
                try:
                    candidate.append(json.loads(line))
                except ValueError:
                    continue
            if self.stream.prompt:
                normalize = lambda value: str(value).replace('\r\n','\n').replace('\r','\n').rstrip()
                def user_text(row):
                    body = (row.get('message') or {}).get('content')
                    return body if isinstance(body,str) else '\n'.join(part.get('text','') for part in (body or []) if isinstance(part,dict))
                admitted = next((i for i,row in enumerate(candidate) if row.get('type')=='user'
                    and normalize(user_text(row))==normalize(self.stream.prompt)), None)
                if admitted is None:
                    continue
                candidate = candidate[admitted:]
            if candidate:
                rows = candidate
                self.bound_transcript = path
                break
        digest = hashlib.sha256(public_assistant_text(rows).encode('utf8')).hexdigest() if rows else None
        tools = execution_tool_names(rows)
        public = public_assistant_text(rows)
        (self.directory / 'claude-transcript-observation.json').write_text(
            json.dumps(dict(files=[str(path) for path in files[:4]], publicSha256=digest,
                            complete=session_turn_complete(rows), executionTools=tools,
                            powershellUsed='PowerShell' in tools, bashUsed='Bash' in tools,
                            gitBashStartupFailure=bash_startup_failure(public)),
                       indent=2), encoding='utf8')
        return rows

    def transcript_text(self):
        return public_assistant_text(self.transcript_rows())

    def sync_completion(self, text, rows=None):
        if self.stream.request_id is None or any(event['type'] == 'turn/end' for event in self.stream.events):
            return
        rows = self.transcript_rows() if rows is None else rows
        if not session_turn_complete(rows):
            return
        public = public_assistant_text(rows)
        self.stream.emit('assistant/message', turn='1',
                         message={'content': [{'type': 'text', 'text': public}]})
        self.stream.emit('turn/end', turn='1', reason={'kind': 'completed'})

    def cancel(self):
        try:
            self.browser.console('key', key='ctrl-c')
        except RuntimeError:
            pass

    def close(self):
        if self.process:
            try:
                self.process.kill()
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
