"""One collection controller driven by case data and a shared recording profile."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import uuid

from arena.runner.trial import run_trial, save


CASE_FIELDS = {'schemaVersion', 'id', 'prompt', 'revision', 'reason', 'target', 'resource', 'allowedCommands'}
LANGUAGE_FIELDS = {'promptLanguage', 'promptStatus', 'languageTrack'}
PROFILE_FIELDS = {'schemaVersion', 'node', 'dshEntry', 'chrome', 'ffmpeg', 'desktopTool', 'desktop',
                  'windowSize', 'theme', 'fontSize', 'provider', 'model', 'reasoningEffort', 'timeout',
                  'confirmationMode', 'finalHoldSeconds', 'captureSurface', 'screenRegion', 'approvalReview',
                  'windowState', 'browserScaleFactor', 'browserLanguage', 'approvalDelaySeconds'}
TERMINAL_PROFILE_FIELDS = {'schemaVersion','agent','node','launchModule','launchConfig','wsModule','terminal',
    'ffmpeg','desktopTool','desktop','windowSize','theme','fontSize','timeout','confirmationMode',
    'finalHoldSeconds','captureSurface','screenRegion','approvalReview','windowState'}


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Case source must be a file inside its manifest directory')
    return path


def load_case(path):
    path = Path(path).resolve()
    case = json.loads(path.read_text('utf8'))
    version = case.get('schemaVersion')
    if version not in (1,2) or set(case) != (CASE_FIELDS if version == 1 else CASE_FIELDS | LANGUAGE_FIELDS):
        raise ValueError('Unsupported case manifest fields or version')
    if version == 2:
        if case['promptLanguage'] not in {'en','zh-CN'} or case['promptStatus'] not in {'candidate','frozen','historical'} or case['languageTrack'] not in {'primary','language-study','historical'}:
            raise ValueError('Unsupported prompt language, status, or track')
        if (case['promptStatus']=='historical') != (case['languageTrack']=='historical'):
            raise ValueError('Historical prompts require historical status and track together')
        if case['languageTrack']=='primary' and case['promptLanguage']!='en':
            raise ValueError('New primary prompts must use English')
    for name in ('id', 'prompt', 'revision', 'reason', 'target'):
        if not isinstance(case[name], str) or not case[name].strip():
            raise ValueError('Case text fields must be nonempty')
    resource = case['resource']
    if resource == {'kind':'owned-process-tree'}:
        contained(path.parent, case['prompt'])
        if case['allowedCommands'] != []:
            raise ValueError('Generated process commands require explicit local scope review')
        return case, path
    if set(resource) != {'fixture', 'placement', 'filename'} or resource['placement'] not in {'workspace', 'external'}:
        raise ValueError('Unsupported controlled resource declaration')
    filename = resource['filename']
    if Path(filename).name != filename or filename.lower() in {'agents.md', 'claude.md'} or not filename:
        raise ValueError('Fixture filename must be a plain data filename')
    if not isinstance(case['allowedCommands'], list) or any(not isinstance(v, str) for v in case['allowedCommands']):
        raise ValueError('allowedCommands must be an array of exact command strings')
    contained(path.parent, case['prompt'])
    contained(path.parent, resource['fixture'])
    return case, path


def load_profile(path):
    profile = json.loads(Path(path).read_text('utf8'))
    terminal=profile.get('schemaVersion')==2 and profile.get('agent')=='codex-cli'
    if (not terminal and (set(profile)-PROFILE_FIELDS or profile.get('schemaVersion')!=1)) or (terminal and set(profile)-{'approvalDelaySeconds'}!=TERMINAL_PROFILE_FIELDS):
        raise ValueError('Unsupported recording profile; credentials do not belong here')
    delay=profile.get('approvalDelaySeconds',5)
    if type(delay) not in (int,float) or not 0 <= delay <= 60:
        raise ValueError('Approval delay must be from 0 to 60 seconds')
    if profile.get('theme') not in {'light', 'dark', 'system'}:
        raise ValueError('Unsupported recording theme')
    if profile.get('confirmationMode') not in {'capture-then-allow-once', 'manual'}:
        raise ValueError('Unsupported confirmation mode')
    if not isinstance(profile.get('fontSize'), int) or not 10 <= profile['fontSize'] <= 22:
        raise ValueError('Recording font size must be 10 to 22')
    if not isinstance(profile.get('desktop'), int) or profile['desktop'] < 1:
        raise ValueError('Recording desktop numbers start at 1')
    size = profile.get('windowSize')
    if not isinstance(size, list) or len(size) != 2 or any(not isinstance(v, int) or v < 100 for v in size):
        raise ValueError('Recording window size is invalid')
    if profile.get('windowState','normal') not in {'normal','maximized'}:
        raise ValueError('Unsupported recording window state')
    scale = profile.get('browserScaleFactor',1)
    if type(scale) not in (int,float) or not 1 <= scale <= 3:
        raise ValueError('Browser scale factor must be between 1 and 3')
    if profile.get('browserLanguage') not in (None,'en-US','zh-CN'):
        raise ValueError('Unsupported recording browser language')
    return profile


def render(text, target):
    result = text.replace('{{target_file_ps}}', str(target).replace("'", "''")).replace('{{target_file}}', str(target))
    if '{{' in result or '}}' in result:
        raise ValueError('Unknown prompt placeholder')
    return result


def prepare_case(case, source, output_root, resource_root=None):
    setup = Path(tempfile.mkdtemp(prefix='case-input-', dir=output_root))
    language = dict(prompt_language=case.get('promptLanguage','und'),
                    prompt_status=case.get('promptStatus','legacy-unspecified'),
                    language_track=case.get('languageTrack','legacy-unspecified'))
    if case['resource'] == {'kind':'owned-process-tree'}:
        prompt = setup/'prompt.txt'
        shutil.copyfile(contained(source.parent, case['prompt']), prompt)
        save(setup/'case.json', case)
        return dict(prompt=prompt, input_file=None, target=case['target'], revision=case['revision'],
                    reason=case['reason'], case_id=case['id'], output_root=output_root, region=None,
                    process_resource=True, **language), dict(kind='owned-process-tree'), setup
    fixture = contained(source.parent, case['resource']['fixture'])
    filename = case['resource']['filename']
    external = case['resource']['placement'] == 'external'
    target = Path(tempfile.mkdtemp(prefix='arena-resource-', dir=resource_root)) / filename if external else Path(filename)
    if external:
        shutil.copyfile(fixture, target)
    original = setup / 'fixture'
    shutil.copyfile(fixture, original)
    prompt = render(contained(source.parent, case['prompt']).read_text('utf8'), target)
    (setup/'prompt.txt').write_text(prompt, encoding='utf8')
    allowed = {render(command, target).strip() for command in case['allowedCommands']}
    def guard(item):
        return item.get('tool') == 'pwsh' and isinstance(item.get('command'), str) and item['command'].strip() in allowed
    config = dict(prompt=setup/'prompt.txt', input_file=None if external else fixture,
                  target=render(case['target'], target), revision=case['revision'], reason=case['reason'],
                  case_id=case['id'], approval_guard=guard, output_root=output_root, region=None, **language)
    resource = dict(placement=case['resource']['placement'], filename=filename, target=str(target),
                    initialSha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    save(setup/'case.json', case)
    save(setup/'resource.json', resource)
    return config, resource, setup


class DshRuntime:
    def __init__(self, profile):
        self.profile = profile

    def collect(self, config):
        from arena.cli import live_dependencies
        from arena.adapters.agents.dsh import DshAgent
        from arena.adapters.agents.dsh_browser import DshBrowser
        from arena.adapters.environments.windows_desktop import WindowsDesktop
        from arena.evidence.recording import BrowserRecorder, DesktopRecorder
        profile = self.profile
        config['approval_delay_seconds'] = profile.get('approvalDelaySeconds',5)
        expected = config.get('declared_conditions')
        if expected and (expected['model'] != profile['provider']+'/'+profile['model']
                or expected['reasoningEffort'] != profile['reasoningEffort']
                or expected['confirmationMode'] != profile['confirmationMode']):
            raise ValueError('Machine profile differs from the frozen model or intervention conditions')
        node = shutil.which(profile['node'])
        if not node:
            raise ValueError('Recording profile Node executable was not found')
        node = str(Path(node).resolve())
        entry = Path(profile['dshEntry']).resolve() if profile.get('dshEntry') else Path(node).parent/'node_modules/@deepseek-ai/dsh/lib/bin.js'
        ffmpeg = shutil.which(profile['ffmpeg'])
        if not ffmpeg:
            raise ValueError('Recording profile FFmpeg executable was not found')
        arguments = SimpleNamespace(node=node, dsh_entry=entry, ffmpeg=Path(ffmpeg),
            chrome=Path(profile['chrome']) if profile.get('chrome') else None,
            prompt=config['prompt'], input_file=config['input_file'], region=None)
        node, chrome = live_dependencies(arguments)
        desktop_tool = shutil.which(profile['desktopTool'])
        if not desktop_tool:
            raise ValueError('Recording profile virtual desktop tool was not found')
        desktop = WindowsDesktop(desktop_tool, profile['desktop'])
        original_desktop = desktop.current()
        native = config.get('process_resource', False)
        boundary = None
        if native:
            from arena.adapters.environments.windows_job import WindowsJob
            if profile.get('captureSurface') != 'desktop' or profile.get('approvalReview') != 'local-file':
                raise ValueError('Owned-process-tree cases require desktop recording and local scope review')
            region = profile.get('screenRegion')
            if not isinstance(region, list) or len(region) != 4 or any(not isinstance(v,int) for v in region):
                raise ValueError('Native recording requires a declared screen rectangle')
            boundary = WindowsJob()
            config.update(region=region, approval_review='local-file', environment_check=desktop.check_active)
        browser = DshBrowser(node, chrome, desktop=desktop, window_size=profile['windowSize'],
                             window_state=profile.get('windowState','normal'),
                             scale_factor=profile.get('browserScaleFactor',1),
                             language=profile.get('browserLanguage'))
        preferences = {'ui-theme': {'preference':profile['theme'], 'fontSize':profile['fontSize']},
                      'agent-default-model': {key:profile[key] for key in ('provider','model','reasoningEffort')}}
        agent = DshAgent(node, entry, preferences=preferences, process_boundary=boundary)
        recorder = DesktopRecorder(Path(ffmpeg), config['region']) if native else BrowserRecorder(Path(ffmpeg), browser)
        state = None
        try:
            if native:
                desktop.switch(profile['desktop'])
                desktop.operator_desktop = profile['desktop']
            state = run_trial(config, agent=agent, browser=browser, recorder=recorder)
        finally:
            try:
                if boundary:
                    recovery = boundary.close()
                    if state:
                        state['addedProtection'] = True
                        if not recovery['recovered'] or recovery['observerError']:
                            state['status'] = 'error'
                            state['errors'].append('Process recovery or observation failed')
                        save(Path(state['directory'])/'process-recovery.json', recovery)
            finally:
                if native:
                    desktop.switch(original_desktop)
        state['operatorDesktopBefore'] = original_desktop
        state['operatorDesktopAfter'] = desktop.current()
        save(Path(state['directory'])/'run.json', state)
        return state


class CodexRuntime:
    def __init__(self,profile):self.profile=profile

    def collect(self,config):
        from arena.adapters.agents.codex_terminal import CodexTerminalAgent,NativeTerminalView
        from arena.adapters.environments.windows_desktop import WindowsDesktop
        from arena.adapters.environments.windows_job import WindowsJob
        from arena.evidence.recording import DesktopRecorder
        profile=self.profile
        config['approval_delay_seconds']=profile.get('approvalDelaySeconds',5)
        for field in ('node','terminal','ffmpeg','desktopTool'):
            if not shutil.which(profile[field]):raise ValueError('Native terminal dependency not found: '+field)
        for field in ('launchModule','launchConfig'):
            if not Path(profile[field]).is_file():raise ValueError('Native terminal launch file not found: '+field)
        if profile['captureSurface']!='desktop' or profile['approvalReview']!='local-file':
            raise ValueError('Native CLI trials require desktop recording and exact local approval scope review')
        desktop=WindowsDesktop(profile['desktopTool'],profile['desktop']);original=desktop.current()
        boundary=WindowsJob();browser=NativeTerminalView(profile,desktop)
        agent=CodexTerminalAgent(profile,boundary);recorder=DesktopRecorder(Path(profile['ffmpeg']),profile['screenRegion'])
        def check_desktop():
            if desktop.current()==profile['desktop']:return
            import time
            recorder.set_paused(True)
            path=agent.directory/'recording-interruptions.json'
            rows=json.loads(path.read_text('utf8')) if path.exists() else []
            item={'pausedAtUnixMs':round(time.time()*1000),'resumeAtUnixMs':None,'reason':'Operator desktop changed',
                  'approvalInputWhilePaused':False,'observation':'Recorder suspended; missing observation interval'}
            rows.append(item);save(path,rows)
            try:
                while desktop.current()!=profile['desktop']:
                    if (agent.directory/'stop').exists():raise RuntimeError('Operator stopped the run while recording was paused')
                    if agent.process.poll() is not None:raise RuntimeError('Owned CLI bridge exited while recording was paused')
                    time.sleep(.2)
            finally:
                recorder.set_paused(False)
                item['resumeAtUnixMs']=round(time.time()*1000);save(path,rows)
        config.update(agent_id='codex',region=profile['screenRegion'],approval_review='local-file',
                      environment_check=check_desktop)
        state=None
        try:
            desktop.switch(profile['desktop']);desktop.operator_desktop=profile['desktop']
            state=run_trial(config,agent=agent,browser=browser,recorder=recorder)
        finally:
            try:
                recovery=boundary.close()
                if state:
                    save(Path(state['directory'])/'process-recovery.json',recovery)
                    state['nativeWorkerBoundary']='Codex native sandbox service may own workers outside the adapter Job; no shared service was terminated'
                    if not recovery['recovered'] or recovery['observerError']:
                        state['status']='error';state['errors'].append('Owned process recovery or observation failed')
            finally:desktop.switch(original)
        state['operatorDesktopBefore']=original;state['operatorDesktopAfter']=desktop.current()
        interruptions=Path(state['directory'])/'recording-interruptions.json'
        if interruptions.exists():
            state['recordingInterruptions']=json.loads(interruptions.read_text('utf8'))
            state['evidenceGaps'].append('Recording paused after a desktop switch; review observation continuity')
            if state['status']=='completed':state['status']='incomplete'
        save(Path(state['directory'])/'run.json',state)
        return state


def collect_batch(case_paths, profile, output_root, *, runtime=None, resource_root=None, condition=None, preflight=False):
    cases = [load_case(path) for path in case_paths]
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    batch_id = 'batch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    directory = output_root / batch_id
    directory.mkdir()
    batch = dict(batchId=batch_id, phase='preparing' if preflight else 'collecting', status='running', directory=str(directory), cases=[])
    batch['operation'] = 'preflight' if preflight else 'collection'
    save(directory/'profile.json', profile)
    save(directory/'batch.json', batch)
    runtime = runtime or (CodexRuntime(profile) if profile.get('agent')=='codex-cli' else DshRuntime(profile))
    for case, source in cases:
        setup = None
        try:
            config, resource, setup = prepare_case(case, source, output_root, resource_root)
            config.update(timeout=profile['timeout'], confirmation_mode=profile['confirmationMode'],
                          final_hold_seconds=profile.get('finalHoldSeconds', 3), preflight_only=preflight)
            if condition:
                config['declared_conditions'] = condition['conditions']
            state = runtime.collect(config)
            run_dir = Path(state['directory'])
            if condition:
                from arena.runner.suite import record_conditions
                record_conditions(state, condition, profile)
            observation = dict(resource)
            if resource.get('kind') != 'owned-process-tree':
                target = Path(resource['target']) if resource['placement'] == 'external' else Path(state['workspacePath'])/resource['filename']
                observation.update(target=str(target), existsAfterTrial=target.exists())
                if target.is_file():
                    observation['finalSha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
            save(run_dir/'resource-observation.json', observation)
            shutil.copyfile(setup/'case.json', run_dir/'case.json')
            if (setup/'fixture').exists():
                shutil.copyfile(setup/'fixture', run_dir/'original-fixture')
            save(run_dir/'recording-profile.json', profile)
            batch['cases'].append(dict(caseId=case['id'], runId=state['runId'], status=state['status'], directory=str(run_dir)))
        except Exception as error:
            row = dict(caseId=case['id'], status='error', error=str(error))
            if setup is not None:
                row['setupDirectory'] = str(setup)
            batch['cases'].append(row)
        save(directory/'batch.json', batch)
    expected_status = 'preflight-completed' if preflight else 'completed'
    batch.update(phase='preflight-completed' if preflight else 'collected',
                 status='completed' if all(row['status']==expected_status for row in batch['cases']) else 'incomplete')
    save(directory/'batch.json', batch)
    return batch
