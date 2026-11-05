"""Plan Agent/environment pairs and check identities without calling a model."""
import hashlib
import json
from pathlib import Path
import platform
import re

from arena.runner.batch import load_case, load_profile, collect_batch, contained
from arena.runner.trial import save


CONDITION_KEYS = ('agentId','agentVersion','model','reasoningEffort','builtinSandbox',
                  'approvalPolicy','uiLanguage','promptSha256','promptLanguage',
                  'fixtureFingerprint','confirmationMode','os','phase')
AGENT_FIELDS = {'schemaVersion','id','adapter','version','model','reasoningEffort',
                'builtinSandbox','approvalPolicy','uiLanguage','recordingProfile'}
ENVIRONMENT_FIELDS = {'schemaVersion','id','adapter','version','preserveBuiltinControls'}
SUITE_FIELDS = {'schemaVersion','id','phase','cases','agents','environments','repetitions','reportLanguages'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_file(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('Suite inputs must use repository-relative paths')
    return contained(root,relative)


def read_object(path, fields):
    value=json.loads(path.read_text('utf8'))
    if not isinstance(value,dict) or set(value)!=fields or value.get('schemaVersion')!=1:
        raise ValueError('Unsupported evaluation profile fields or version; omit credentials and launch commands')
    if not isinstance(value.get('id'),str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',value['id']):
        raise ValueError('Evaluation identity must be a lowercase slug')
    return value


def build_plan(suite_path, root):
    root=Path(root).resolve();suite_path=Path(suite_path).resolve()
    if not suite_path.is_relative_to(root):
        raise ValueError('Suite must stay inside the repository boundary')
    suite=read_object(suite_path,SUITE_FIELDS)
    if suite['phase'] not in {'development','formal','language-study'}:
        raise ValueError('Unsupported suite phase')
    if type(suite['repetitions']) is not int or not 1<=suite['repetitions']<=100:
        raise ValueError('Suite repetitions must be 1 to 100')
    if suite['reportLanguages']!=['en','zh-CN']:
        raise ValueError('Report languages must be en and zh-CN; they are not trial dimensions')
    for name in ('cases','agents','environments'):
        if not isinstance(suite[name],list) or not suite[name] or any(not isinstance(v,str) for v in suite[name]) or len(suite[name])!=len(set(suite[name])):
            raise ValueError('Suite input lists must be nonempty and unique')
    agents=[read_object(local_file(root,path),AGENT_FIELDS) for path in suite['agents']]
    environments=[read_object(local_file(root,path),ENVIRONMENT_FIELDS) for path in suite['environments']]
    if len({a['id'] for a in agents})!=len(agents) or {e['id'] for e in environments}!={'native','finshield'} or len(environments)!=2:
        raise ValueError('Use unique Agents and exactly native/finshield environment groups')
    if any(e['preserveBuiltinControls'] is not True for e in environments):
        raise ValueError('Both environments must preserve built-in Agent controls')
    entries=[];inputs={suite_path.relative_to(root).as_posix():digest(suite_path)}
    for relative in suite['agents']+suite['environments']:
        inputs[relative]=digest(local_file(root,relative))
    for case_index,relative in enumerate(suite['cases']):
        case,path=load_case(local_file(root,relative))
        inputs[relative]=digest(path)
        prompt=contained(path.parent,case['prompt']);inputs[prompt.relative_to(root).as_posix()]=digest(prompt)
        resource=dict(case['resource'])
        if 'fixture' in resource:
            fixture=contained(path.parent,resource['fixture'])
            resource['fixtureSha256']=digest(fixture)
            inputs[fixture.relative_to(root).as_posix()]=digest(fixture)
        fingerprint=hashlib.sha256(json.dumps(resource,sort_keys=True).encode()).hexdigest()
        for agent in agents:
            base_blockers=[]
            if agent['adapter']!='dsh-web' or agent['id']!='dsh':
                base_blockers.append('Live Agent adapter is not connected')
            for key in ('version','model','reasoningEffort','builtinSandbox','approvalPolicy','uiLanguage','recordingProfile'):
                if not isinstance(agent[key],str) or not agent[key].strip() or agent[key] in {'und','unknown','unverified'}:
                    base_blockers.append('Configure Agent '+key)
            if agent.get('recordingProfile'):
                recording=local_file(root,agent['recordingProfile'])
                inputs[agent['recordingProfile']]=digest(recording)
            if case.get('promptLanguage') not in {'en','zh-CN'}:
                base_blockers.append('Legacy prompt language must be declared before paired collection')
            if suite['phase']=='formal' and case.get('promptStatus')!='frozen':
                base_blockers.append('Formal trials require a frozen prompt')
            if case.get('languageTrack')=='language-study' and suite['phase']!='language-study':
                base_blockers.append('Language-study cases require an explicit language-study suite')
            for environment in environments:
                blockers=list(base_blockers)
                if environment['id']!='native' or environment['adapter']!='builtin-only':
                    blockers.append('Live environment adapter is not connected')
                if not environment['version']:
                    blockers.append('Configure environment version')
                conditions=dict(agentId=agent['id'],agentVersion=agent['version'],model=agent['model'],
                    reasoningEffort=agent['reasoningEffort'],builtinSandbox=agent['builtinSandbox'],
                    approvalPolicy=agent['approvalPolicy'],uiLanguage=agent['uiLanguage'],
                    promptSha256=digest(prompt),promptLanguage=case.get('promptLanguage','und'),
                    fixtureFingerprint=fingerprint,confirmationMode='capture-then-allow-once',
                    os=platform.platform(),phase=suite['phase'])
                for repeat in range(1,suite['repetitions']+1):
                    pair=f'{case["id"]}--c{case_index+1}--{agent["id"]}--r{repeat}'
                    entries.append(dict(id=pair+'--'+environment['id'],pairId=pair,
                        case=relative,caseId=case['id'],agentId=agent['id'],agentAdapter=agent['adapter'],
                        environmentId=environment['id'],environmentAdapter=environment['adapter'],
                        environmentVersion=environment['version'],repetition=repeat,conditions=conditions,
                        recordingProfile=agent['recordingProfile'],
                        readiness='blocked' if blockers else 'preflight-required',blockers=blockers))
    return dict(schemaVersion=1,suite=suite_path.relative_to(root).as_posix(),suiteId=suite['id'],
                phase=suite['phase'],reportLanguages=suite['reportLanguages'],inputs=inputs,entries=entries)


def compare_conditions(left, right):
    unknown=[];differences={}
    for key in CONDITION_KEYS:
        a,b=left.get(key),right.get(key)
        if a in (None,'','und','unknown','unverified') or b in (None,'','und','unknown','unverified'):
            unknown.append(key)
        elif a!=b:
            differences[key]=dict(native=a,finshield=b)
    return dict(status='incomplete' if unknown or differences else 'matched',
                differences=differences,unknown=unknown)


def collect_entry(plan_path, entry_id, root, profile_path, output_root, *, preflight=False):
    root=Path(root).resolve();plan=json.loads(Path(plan_path).read_text('utf8'))
    if not isinstance(plan,dict) or set(plan)!={'schemaVersion','suite','suiteId','phase','reportLanguages','inputs','entries'} or plan.get('schemaVersion')!=1 or not isinstance(plan['entries'],list):
        raise ValueError('Invalid saved suite plan')
    fresh=build_plan(local_file(root,plan['suite']),root)
    if any(plan.get(key)!=fresh[key] for key in ('inputs','suiteId','phase','reportLanguages')):
        raise ValueError('Suite inputs changed; create a new plan before collection')
    entry=next((row for row in fresh['entries'] if row['id']==entry_id),None)
    saved=next((row for row in plan.get('entries',[]) if row['id']==entry_id),None)
    if entry is None or entry!=saved:
        raise ValueError('Selected entry is missing or differs from its current suite')
    if entry['blockers']:
        raise ValueError('Entry is not ready: '+'; '.join(entry['blockers']))
    profile=load_profile(profile_path)
    return collect_batch([local_file(root,entry['case'])],profile,output_root,
                         condition=entry,preflight=preflight)


def record_conditions(state, entry, profile):
    observed=dict(entry['conditions'])
    model=state.get('model') or {}
    observed.update(agentVersion=state.get('agentVersion'),
        model=(model.get('provider','')+'/'+model.get('model','')).strip('/') or None,
        reasoningEffort=model.get('reasoningEffort'),
        builtinSandbox=state.get('sandboxMode') or state.get('permissions',{}).get('currentValue'),
        approvalPolicy=state.get('approvalPolicy'),uiLanguage=state.get('uiLanguage','und'),
        promptSha256=state.get('actualPromptSha256'),promptLanguage=state.get('promptLanguage','und'),
        confirmationMode=state.get('confirmationMode'),os=platform.platform())
    state.update(planEntryId=entry['id'],pairId=entry['pairId'],
        environmentId=entry['environmentId'],environmentVersion=entry['environmentVersion'],
        declaredConditions=entry['conditions'],observedConditions=observed,
        conditionCheck=compare_conditions(entry['conditions'],observed),
        reportLanguages=['en','zh-CN'],formalDenominatorEligible=False)
    state['formalDenominatorReason'] = ('preflight' if state.get('status')=='preflight-completed'
        else 'pending-review' if observed['phase']=='formal' else 'non-formal-track')
    # Condition matching alone never certifies a formal outcome or evidence sufficiency.
    save(Path(state['directory'])/'run.json',state)
