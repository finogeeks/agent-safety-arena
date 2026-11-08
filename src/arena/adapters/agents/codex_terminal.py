"""Owned Windows Terminal presentation of the real Codex interactive CLI."""
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
import tomllib
import uuid

from arena.adapters.agents.codex import CodexEventStream, approval_panel, model_arguments
from arena.adapters.agents.dsh import hidden_process_options


def native_window(title):
    user=c.WinDLL('user32',use_last_error=True)
    callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
    user.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
    matches=[]
    @callback
    def visit(hwnd,unused):
        text=c.create_unicode_buffer(2048);user.GetWindowTextW(hwnd,text,len(text))
        if text.value.startswith(title):
            pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,c.byref(pid))
            matches.append((int(hwnd),pid.value))
        return True
    user.EnumWindows(visit,0)
    if len(matches)>1:raise RuntimeError('More than one owned terminal window was found')
    return matches[0] if matches else None


class NativeTerminalView:
    def __init__(self, profile, desktop):
        self.profile=profile;self.desktop=desktop;self.agent=None;self.handle=None
        self.fragment=None;self.choices=[];self.pid=None

    def launch(self, workspace, directory, url):
        self.directory=directory;self.title='Arena Codex CLI '+uuid.uuid4().hex[:12]
        spec=dict(launchModule=self.profile['launchModule'],launchConfig=self.profile['launchConfig'],
                  url=url,workspace=str(workspace),directory=str(directory))
        spec_path=directory/'terminal-launch.json';spec_path.write_text(json.dumps(spec),encoding='utf8')
        command=[self.profile['node'],str(Path(__file__).with_name('codex_ui.mjs')),str(spec_path)]
        root=Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows Terminal/Fragments'
        folder=root/('Arena-'+directory.name);folder.mkdir(parents=True)
        self.fragment=folder/'profile.json'
        name='Arena Codex '+directory.name
        fragment={'profiles':[{'guid':'{'+str(uuid.uuid4())+'}','name':name,
            'commandline':subprocess.list2cmdline(command),'startingDirectory':str(workspace),
            'font':{'face':'Cascadia Mono','size':self.profile['fontSize']},
            'colorScheme':'One Half Light','background':'#FFFFFF','foreground':'#202020',
            'useAcrylic':False,'opacity':100,'closeOnExit':'always',
            'suppressApplicationTitle':True,'tabTitle':self.title}]}
        self.fragment.write_text(json.dumps(fragment),encoding='utf8')
        subprocess.run([self.profile['terminal'],'--window','new','--maximized','new-tab',
            '--profile',fragment['profiles'][0]['guid'],'--colorScheme','One Half Light',
            '--title',self.title,'--suppressApplicationTitle','--startingDirectory',str(workspace),*command],
            check=True,capture_output=True,timeout=20,**hidden_process_options())
        deadline=time.monotonic()+60;processes=directory/'terminal-processes.json'
        while time.monotonic()<deadline:
            found=native_window(self.title)
            if found and processes.exists():
                self.handle,self.pid=found
                self.processes=json.loads(processes.read_text())
                self.desktop.call('/GetDesktop:'+str(self.desktop.number-1),'/MoveWindowHandle:'+str(self.handle))
                self.verify_presentation()
                return
            time.sleep(.2)
        raise RuntimeError('The native Codex terminal did not start; no prompt submitted')

    def console(self, action, **fields):
        request={'pid':self.processes['cliPid'],'action':action,**fields}
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('windows_console.py'))],
            input=json.dumps(request),text=True,encoding='utf8',capture_output=True,timeout=10,**hidden_process_options())
        try:response=json.loads(result.stdout)
        except ValueError:raise RuntimeError('The native console observer failed: '+result.stderr[:300]) from None
        if not response['ok']:raise RuntimeError('The native console observer failed: '+response['error'])
        return response['value']

    def text(self):return self.console('read')['text']

    def enlarge_text(self):
        """Use only this owned host's normal per-window zoom, never CLI settings."""
        user=c.WinDLL('user32',use_last_error=True)
        user.GetForegroundWindow.restype=w.HWND
        user.SetForegroundWindow.argtypes=[w.HWND]
        user.keybd_event.argtypes=[w.BYTE,w.BYTE,w.DWORD,c.c_size_t]
        user.SetForegroundWindow(self.handle)
        time.sleep(.15)
        if int(user.GetForegroundWindow() or 0)!=self.handle:
            raise RuntimeError('The owned terminal is not foreground; no zoom input sent')
        before=self.console('read')
        for _ in range(8):
            self.desktop.check_active()
            if int(user.GetForegroundWindow() or 0)!=self.handle:
                raise RuntimeError('The foreground changed during native terminal zoom')
            for key in (17,16,187):user.keybd_event(key,0,0,0)
            for key in (187,16,17):user.keybd_event(key,0,2,0)
            time.sleep(.05)
        time.sleep(.2)
        after=self.console('read')
        (self.directory/'terminal-presentation.json').write_text(json.dumps({
            'nativeWindowHandle':self.handle,'hostZoomSteps':8,'columnsBefore':before['columns'],
            'columnsAfter':after['columns'],'requestedFontSize':self.profile['fontSize'],
            'cliSettingsChanged':False},indent=2),encoding='utf8')
        if after['columns']>=before['columns']:raise RuntimeError('Native terminal text did not enlarge; no prompt submitted')

    def verify_presentation(self):
        result=self.desktop.call('/GetDesktopFromWindowHandle:'+str(self.handle))
        if result.returncode!=self.desktop.number-1 or self.desktop.current()!=self.desktop.operator_desktop:
            raise RuntimeError('The owned terminal is not on the declared recording desktop')
        return dict(recordingVirtualDesktop=self.desktop.number,operatorVirtualDesktop=self.desktop.operator_desktop)

    def snapshot(self):
        self.agent.observe()
        text=self.text()
        panel=approval_panel(text,self.agent.stream.pending)
        choices=self.choices;self.choices=[]
        return dict(title=self.title,dialogs=[panel] if panel else [],choices=choices,uiLanguage='en',terminalText=text)

    def screenshot(self, path, key=None):
        if key and not any(d['key']==key for d in self.snapshot()['dialogs']):return False
        x,y,width,height=self.profile['screenRegion']
        result=subprocess.run([self.profile['ffmpeg'],'-hide_banner','-loglevel','error','-n',
            '-f','gdigrab','-offset_x',str(x),'-offset_y',str(y),'-video_size',f'{width}x{height}',
            '-i','desktop','-frames:v','1','-threads','1',str(path)],capture_output=True,timeout=15,**hidden_process_options())
        if result.returncode:raise RuntimeError('The terminal screenshot failed: '+result.stderr.decode(errors='replace')[:300])
        if key and not any(d['key']==key for d in self.snapshot()['dialogs']):return False
        return {'at':round(time.time()*1000)}

    def choose_once(self, key, text, label=None):
        panel=next((d for d in self.snapshot()['dialogs'] if d['key']==key and d['text']==text),None)
        if panel is None:raise RuntimeError('The captured native CLI approval changed; no choice made')
        at=round(time.time()*1000)
        selected=re.search(r'(?m)^\s*[›>]\s*1\. Yes, proceed \(y\)\s*$',panel['text'])
        self.console('key',key='enter' if selected else 'y')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            self.agent.observe()
            decided=next((e for e in reversed(self.agent.stream.events) if e['type']=='approval/decided' and e['data']['id']==key),None)
            if decided:
                if decided['data']['nativeDecision']!='accept':raise RuntimeError('The native CLI did not confirm a one-time approval')
                choice=dict(key=key,label=panel['oneTimeChoice'],at=at);self.choices.append(choice)
                return choice
            time.sleep(.1)
        raise RuntimeError('The native one-time CLI choice was not observed')

    def close(self):
        found=native_window(self.title) if hasattr(self,'title') else None
        if found:
            user=c.WinDLL('user32',use_last_error=True)
            user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
            user.PostMessageW(found[0],0x0010,0,0)
        if self.fragment:
            expected=Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows Terminal/Fragments'
            target=self.fragment.resolve()
            if target.parent.parent!=expected.resolve() or not target.parent.name.startswith('Arena-'):
                raise RuntimeError('Owned terminal fragment is outside the cleanup boundary')
            target.unlink(missing_ok=True);target.parent.rmdir()


class CodexTerminalAgent:
    def __init__(self, profile, boundary):
        self.profile=profile;self.boundary=boundary;self.stream=CodexEventStream()
        self.process=None;self.lines=0

    def command(self, **request):
        self.process.stdin.write(json.dumps(request)+'\n');self.process.stdin.flush()
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('The owned Codex observation bridge exited')
        response=json.loads(line)
        if not response['ok']:raise RuntimeError(response['error'])
        return response['value']

    def prepare(self, workspace, browser, evidence_directory):
        self.directory=evidence_directory;self.workspace=workspace;self.browser=browser;browser.agent=self
        setup=json.loads(Path(self.profile['launchConfig']).read_text('utf8'))
        base=Path(setup['codexHome'])/'config.toml'
        profile=Path(setup['codexHome'])/(setup['codexProfile']+'.config.toml')
        settings=tomllib.loads(profile.read_text('utf8'))
        arguments=model_arguments(settings)
        self.base_path=base;self.base_before=tomllib.loads(base.read_text('utf8'))
        snapshot={'baseSha256':hashlib.sha256(base.read_bytes()).hexdigest(),
                  'modelProfileSha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
                  'modelProfileKeys':list(settings),'baseWindows':self.base_before.get('windows'),
                  'policyOverrides':False,'transport':'Native CLI remote terminal through an owned loopback observation proxy'}
        (evidence_directory/'configuration-provenance.json').write_text(json.dumps(snapshot,indent=2),encoding='utf8')
        version=subprocess.run([setup['codexExecutable'],'--version'],capture_output=True,text=True,timeout=10,**hidden_process_options()).stdout.strip()
        self.version=version.removeprefix('codex-cli ')
        self.process=subprocess.Popen([self.profile['node'],str(Path(__file__).with_name('codex_wire.cjs'))],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(evidence_directory/'bridge-error.log').open('w'),
            text=True,encoding='utf8',**hidden_process_options())
        self.boundary.assign(self.process,evidence_directory)
        ready=self.command(action='start',directory=str(evidence_directory),workspace=str(workspace),
            launchModule=self.profile['launchModule'],launchConfig=self.profile['launchConfig'],
            wsModule=self.profile['wsModule'],modelArguments=arguments)
        browser.launch(workspace,evidence_directory,ready['url'])
        return dict(agent='Codex CLI',agentVersion=self.version,captureWindowTitle=browser.title,
                    addedProtection=True,uiLanguage='en',presentation='native Windows Terminal',
                    transport=snapshot['transport'],processBoundaryLimit='Windows Terminal owns its UI processes; native sandbox service workers can be outside the adapter Job Object')

    def finish_startup(self, browser, recorder, directory):
        deadline=time.monotonic()+90;startup=[]
        while time.monotonic()<deadline:
            self.observe();text=browser.text()
            trust=('Do you trust the contents of this directory?' in text or 'Trust this folder?' in text)
            if trust:
                compact=lambda s:''.join(s.split()).lower()
                if compact(str(self.workspace)) not in compact(text):raise RuntimeError('The native trust prompt does not name the owned workspace')
                if not re.search(r'(?m)^\s*›\s*1\. Trust and continue\s*$',text):
                    raise RuntimeError('The owned workspace trust choice is not the native selected default')
                target=directory/f'startup-{len(startup)+1}.png';browser.screenshot(target)
                checkpoint=recorder.checkpoint();time.sleep(2);recorder.check()
                browser.console('key',key='enter')
                startup.append(dict(kind='native-workspace-initialization',text=text,screenshot=target.name,
                                    recordedPanelAt=checkpoint,actor='automation',choice='Native default trust choice for the declared owned workspace'))
                (directory/'startup-confirmations.json').write_text(json.dumps(startup,indent=2),encoding='utf8')
                time.sleep(.3);continue
            if self.stream.thread_id and self.stream.conditions.get('model'):
                browser.screenshot(directory/'presentation.png')
                (directory/'initial-native-events.json').write_text(json.dumps(self.stream.events,indent=2),encoding='utf8')
                return dict(sessionId=self.stream.thread_id,model={k:self.stream.conditions[k] for k in ('model','provider','reasoningEffort')},
                            sandboxMode=self.stream.conditions['sandboxMode'],approvalPolicy=self.stream.conditions['approvalPolicy'])
            time.sleep(.2)
        (directory/'startup-terminal.txt').write_text(browser.text(),encoding='utf8')
        browser.screenshot(directory/'startup-screen.png')
        raise RuntimeError('Native CLI startup did not reach a blank thread; no prompt submitted')

    def submit(self, prompt, request_id):
        self.stream.prompt=prompt;self.stream.request_id=request_id
        self.browser.console('paste',text=prompt)
        time.sleep(5)
        self.browser.screenshot(self.directory/'opening-screen.png')
        self.browser.console('key',key='enter')

    def observe(self):
        path=self.directory/'codex-native-wire.jsonl'
        if path.exists():
            lines=path.read_text('utf8').splitlines()
            for index in range(self.lines,len(lines)):
                try:row=json.loads(lines[index])
                except ValueError:break
                self.stream.feed(row['direction'],row['message']);self.lines=index+1
            if self.stream.admitted_prompt is not None:
                (self.directory/'native-admitted-prompt.txt').write_text(self.stream.admitted_prompt,encoding='utf8')
        return self.stream.events

    def cancel(self):
        self.browser.console('key',key='ctrl-c')

    def close(self):
        if self.process:
            try:self.command(action='close')
            except (OSError,RuntimeError):pass
            try:self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
            self.process.stdin.close();self.process.stdout.close()
        if hasattr(self,'base_path'):
            after=tomllib.loads(self.base_path.read_text('utf8'))
            (self.directory/'configuration-after.json').write_text(json.dumps({
                'baseSha256':hashlib.sha256(self.base_path.read_bytes()).hexdigest(),
                'nativeWindowsSettingsUnchanged':after.get('windows')==self.base_before.get('windows'),
                'sandboxModeUnchanged':after.get('sandbox_mode')==self.base_before.get('sandbox_mode'),
                'approvalPolicyUnchanged':after.get('approval_policy')==self.base_before.get('approval_policy')},indent=2),encoding='utf8')
