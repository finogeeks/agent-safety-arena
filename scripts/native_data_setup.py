"""Prepare product-specific native data policies without a model request."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LAUNCH_KEYS = {'codexExecutable', 'codexHome', 'claudeExecutable', 'claudeHome',
               'nodeDir', 'gitDir', 'bash', 'credentialParser', 'credentialStore', 'codexProfile'}
SOURCES = {
    'codex': ['https://learn.chatgpt.com/docs/permissions'],
    'claude': ['https://code.claude.com/docs/en/permissions',
               'https://code.claude.com/docs/en/sandboxing'],
    'workbuddy': ['https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Permission-Modes'],
    'dsh': ['https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/sandbox.md',
            'https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/fs/fs-sandbox/README.md'],
}


def host_setup():
    spec = importlib.util.spec_from_file_location('native_data_host', ROOT/'scripts/prepare-data-safety.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locations(agent, config):
    host = host_setup()
    lab, state = host.validate_paths(config['labRoot'], config['stateRoot'])
    output = host.no_reparse(state/('native-'+agent))
    output.mkdir(parents=True, exist_ok=True)
    return lab, output


def write(path, value):
    host_setup().no_reparse(path)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def base_report(agent, lab):
    return dict(schemaVersion=1, agent=agent, track='configured-native',
        productDefault=False, labRoot=str(lab), checkedDate='2026-11-12',
        generatedAtUtc=datetime.now(timezone.utc).isoformat(), sources=SOURCES[agent],
        runtimeVerified=False, applied=False, files={},
        verificationRequired=['Record installed version and observed effective rules without a model prompt',
            'Verify allowed controls and protected paths, including ancestor deletion',
            'Freeze approval policy and launcher conditions before collection'])


def prepare(agent, config, profile=None):
    if agent not in SOURCES:
        raise ValueError('Unsupported native Agent')
    lab, output = locations(agent, config)
    report = base_report(agent, lab)
    ro, na = lab/'ro-ancestor/ro-parent/read-only', lab/'na-ancestor/na-parent/no-access'
    if agent == 'codex':
        if not profile or not profile.get('launchConfig'):
            raise ValueError('Codex requires a local recording profile with launchConfig')
        launch = json.loads(Path(profile['launchConfig']).read_text('utf-8-sig'))
        if set(launch) != LAUNCH_KEYS or any(not isinstance(v, str) or not v for v in launch.values()):
            raise ValueError('Unexpected launcher fields; only known path references are permitted')
        name = launch['codexProfile']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Invalid model profile filename')
        original_home = Path(launch['codexHome'])
        model_source = original_home/(name+'.config.toml')
        model = tomllib.loads(model_source.read_text('utf8'))
        sys.path.insert(0, str(ROOT/'src'))
        from arena.adapters.agents.codex import model_arguments
        model_arguments(model)  # Enforce the existing model-only, env-credential contract.
        home = host_setup().no_reparse(output/'codex-home')
        home.mkdir(exist_ok=True)
        policy = 'default_permissions = "arena-data"\napproval_policy = "on-request"\n\n'
        original_base = original_home/'config.toml'
        backend = tomllib.loads(original_base.read_text('utf8')).get('windows', {}) if original_base.exists() else {}
        if backend.get('sandbox') in {'elevated','unelevated'}:
            policy += '[windows]\nsandbox = '+json.dumps(backend['sandbox'])+'\n\n'
        policy += '[permissions.arena-data]\nextends = ":workspace"\n\n[permissions.arena-data.filesystem]\n'
        for path, access in ((lab,'write'),(ro,'read'),(na,'deny')):
            policy += json.dumps(path.as_posix())+' = '+json.dumps(access)+'\n'
        host_setup().no_reparse(home/'config.toml').write_text(policy, encoding='utf8')
        provider = model['model_provider']
        connection = 'model = '+json.dumps(model['model'])+'\nmodel_provider = '+json.dumps(provider)+'\n'
        connection += '\n[model_providers.'+provider+']\n'
        for key, value in model['model_providers'][provider].items():
            connection += key+' = '+json.dumps(value)+'\n'
        # No auth.json, credentials, trust overrides, or legacy sandbox settings are copied.
        host_setup().no_reparse(home/(name+'.config.toml')).write_text(connection, encoding='utf8')
        launch['codexHome'] = str(home)
        write(output/'launch.json', launch)
        recording = dict(profile, launchConfig=str(output/'launch.json'), dataSetup=str(config['_path'])
                         if '_path' in config else profile.get('dataSetup',''),
                         dataNativePreparation=str(output/'preparation.json'))
        write(output/'recording-profile.json', recording)
        report.update(status='configuration-generated', codexHome=str(home),
            recordingProfile=str(output/'recording-profile.json'),
            limits=['Beta permissions require a compatible installed version and effective-profile verification',
                    'Any loaded legacy sandbox setting or --sandbox can shadow this profile',
                    'The current FinShield Codex launcher uses --sandbox danger-full-access; this is not a matched additive track'])
        report['files'] = {str(p):sha(p) for p in (home/'config.toml', home/(name+'.config.toml'),
                          output/'launch.json', output/'recording-profile.json')}
    elif agent == 'claude':
        target = host_setup().no_reparse(lab/'.claude/settings.local.json')
        if (output/'applied.json').exists():
            raise ValueError('Restore the applied Claude settings before preparing again')
        original = target.read_bytes() if target.exists() else None
        settings = json.loads(original.decode('utf-8-sig')) if original is not None else {}
        if not isinstance(settings, dict):
            raise ValueError('Claude project settings must be an object')
        settings = copy.deepcopy(settings)
        permissions = settings.setdefault('permissions', {})
        deny = permissions.setdefault('deny', [])
        if not isinstance(deny, list) or any(not isinstance(v, str) for v in deny):
            raise ValueError('Claude deny permissions must be an array of strings')
        for tool, relative in (('Edit',ro.relative_to(lab)),('Read',na.relative_to(lab)),('Edit',na.relative_to(lab))):
            for suffix in ('', '/**'):
                rule = tool+'(/'+relative.as_posix()+suffix+')'
                if rule not in deny:
                    deny.append(rule)
        backup = output/'original-settings.bin'
        if original is not None:
            host_setup().no_reparse(backup).write_bytes(original)
        write(output/'settings.candidate.json', settings)
        write(output/'original-state.json', dict(existed=original is not None,
            sha256=hashlib.sha256(original).hexdigest() if original is not None else None))
        report.update(status='configuration-generated', candidate=str(output/'settings.candidate.json'),
            target=str(target), limits=['Read/Edit rules cover file tools and selected recognized shell syntax',
                'Arbitrary Python/Node subprocess access is outside these rules',
                'Claude OS shell sandbox is not supported on native Windows',
                'An ancestor deletion can bypass leaf-only tool rules; measure actual effects'])
        if profile:
            write(output/'recording-profile.json', dict(profile, dataNativePreparation=str(output/'preparation.json')))
            report['recordingProfile'] = str(output/'recording-profile.json')
        report['files'] = {str(p):sha(p) for p in (output/'settings.candidate.json',output/'original-state.json')}
    elif agent == 'workbuddy':
        rules = [dict(path=str(lab), read='allow', write='allow', delete='allow'),
                 dict(path=str(ro), read='allow', write='deny', delete='deny'),
                 dict(path=str(na), read='deny', write='deny', delete='deny')]
        report.update(status='pending-installed-ui-verification', rules=rules,
            limits=['The Desktop guide documents File Security UI, not a persisted JSON schema',
                'Verify that the installed version exposes the UI and narrower rules take precedence',
                'Keep Default Permissions, Full Access off, and sandbox on',
                'Do not substitute CodeBuddy CLI settings for WorkBuddy Desktop settings'])
        checklist = 'WorkBuddy native File Security preparation\n\n'
        checklist += 'Keep Default Permissions. Keep Full Access off and sandbox on.\n'
        for rule in rules:
            checklist += '\n'+json.dumps(rule)+'\n'
        checklist += '\nCapture installed version, original settings, each path rule, rule precedence, and effective sandbox state.\n'
        checklist += 'If the installed UI lacks these rules, record unsupported-installed-version.\n'
        host_setup().no_reparse(output/'ui-checklist.txt').write_text(checklist, encoding='utf8')
        report['checklist'] = str(output/'ui-checklist.txt')
    else:
        report.update(status='unsupported-per-directory-zones',
            nativeDefault=dict(sandbox='workspace-write', approval='ask'),
            limits=['The documented modes do not define read/deny carveouts inside a writable workspace',
                'Native file-tool reads retain host access; a global read-only mode is not a No Access zone',
                'Windows process enforcement is partial and ignores extra directory grants',
                'Retain the product-default baseline; per-directory zone support is unsupported'])
    write(output/'preparation.json', report)
    return report


def prepare_claude_session(config, profile):
    if not profile or not profile.get('launchConfig'):
        raise ValueError('Claude session preparation requires a recording profile')
    lab, output = locations('claude-session', config)
    launch = json.loads(Path(profile['launchConfig']).read_text('utf-8-sig'))
    home = Path(launch['claudeHome'])
    existing = json.loads((home/'settings.json').read_text('utf-8-sig')) if (home/'settings.json').exists() else {}
    deny = list((existing.get('permissions') or {}).get('deny') or [])
    if 'Bash' not in deny:
        deny.append('Bash')
    def absolute(path):
        value = path.resolve().as_posix()
        if re.match(r'^[A-Za-z]:/', value):
            value = value[0].lower()+'/'+value[3:]
        return '//'+value.lstrip('/')
    ro, na = lab/'ro-ancestor/ro-parent/read-only', lab/'na-ancestor/na-parent/no-access'
    for tool,path in [('Edit',ro),('Read',na),('Edit',na)]:
        for suffix in ('','/**'):
            rule = tool+'('+absolute(path)+suffix+')'
            if rule not in deny:
                deny.append(rule)
    target = output/'session-permissions.json'
    write(target,dict(permissions=dict(deny=deny)))
    report=base_report('claude',lab)
    recording=dict(profile,dataSetup=config.get('_path',profile.get('dataSetup','')),
                   dataNativePreparation=str(output/'preparation.json'))
    write(output/'recording-profile.json',recording)
    report.update(status='session-settings-ready',method='cli-settings',sessionSettings=str(target),
        recordingProfile=str(output/'recording-profile.json'),
        limits=['Read/Edit file-tool rules do not confine arbitrary Python/Node subprocess access',
                'Native Windows Claude has no OS shell sandbox; record actual effects',
                'No project settings were applied; approval mode is inherited unchanged'])
    report['files']={str(f):sha(f) for f in [target,output/'recording-profile.json']}
    write(output/'preparation.json',report)
    return report


def apply_claude(config):
    lab, output = locations('claude', config)
    report = json.loads((output/'preparation.json').read_text('utf8'))
    original = json.loads((output/'original-state.json').read_text('utf8'))
    target = host_setup().no_reparse(lab/'.claude/settings.local.json')
    if (target.exists() != original['existed'] or
            (target.exists() and sha(target) != original['sha256'])):
        raise ValueError('Claude settings changed since preparation')
    candidate = Path(report['candidate'])
    if sha(candidate) != report['files'][str(candidate)]:
        raise ValueError('Claude candidate changed since preparation')
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(candidate.read_bytes())
    write(output/'applied.json', dict(sha256=sha(target)))
    report.update(applied=True, status='file-tool-settings-applied')
    report['files'][str(target)] = sha(target)
    write(output/'preparation.json', report)
    return report


def restore_claude(config):
    lab, output = locations('claude', config)
    target = host_setup().no_reparse(lab/'.claude/settings.local.json')
    applied = json.loads((output/'applied.json').read_text('utf8'))
    if not target.exists() or sha(target) != applied['sha256']:
        raise ValueError('Claude settings changed after apply; refusing to overwrite')
    original = json.loads((output/'original-state.json').read_text('utf8'))
    if original['existed']:
        backup = output/'original-settings.bin'
        if sha(backup) != original['sha256']:
            raise ValueError('Claude backup changed')
        target.write_bytes(backup.read_bytes())
    else:
        target.unlink()
    (output/'applied.json').unlink()
    report = json.loads((output/'preparation.json').read_text('utf8'))
    report.update(applied=False, status='restored')
    report['files'].pop(str(target), None)
    write(output/'preparation.json', report)
    return report


def main(agent):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('action', choices=('prepare','apply','restore','session'), default='prepare', nargs='?')
    args = parser.parse_args()
    config = json.loads(args.config.read_text('utf-8-sig'))
    config['_path'] = str(args.config.resolve())
    profile = json.loads(args.profile.read_text('utf-8-sig')) if args.profile else None
    if args.action != 'prepare' and agent != 'claude':
        parser.error('Only Claude uses apply/restore; Codex uses an isolated home; WorkBuddy requires UI verification; DSH zones are unsupported')
    result = (prepare_claude_session(config,profile) if args.action=='session' else
              prepare(agent, config, profile) if args.action=='prepare' else
              apply_claude(config) if args.action=='apply' else restore_claude(config))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    raise SystemExit('Use a product-specific prepare-<agent>-native.py entry point')
