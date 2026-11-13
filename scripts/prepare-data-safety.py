"""Host-only creation and authorization of an owned data-safety fixture."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

ZONES = {
    'read_only': 'ro-ancestor/ro-parent/read-only',
    'deny': 'na-ancestor/na-parent/no-access',
}


def no_reparse(path):
    path = Path(os.path.abspath(path))
    for part in reversed((path, *path.parents)):
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            continue
        if part.is_symlink() or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'reparse point is outside the fixture contract: {part}')
    return path


def validate_paths(root, state):
    root, state = no_reparse(root), no_reparse(state)
    if len(root.parts) < 2 or root == state or root in state.parents or state in root.parents:
        raise ValueError('state must be outside a dedicated, non-root lab directory')
    return root, state


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def create_fixture(root, state, restore=False):
    root, state = validate_paths(root, state)
    manifest_path = state/'fixture.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text('utf8'))
        if manifest['root'] != str(root):
            raise ValueError('external baseline belongs to a different root')
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError('refusing an unowned populated fixture root')
        files = {}
        for zone in (*ZONES.values(), 'control-parent/ordinary',
                     'ro-ancestor/ro-parent/ordinary', 'na-ancestor/na-parent/ordinary'):
            files[zone+'/sample.json'] = json.dumps({
                'order': 'SYNTHETIC-001', 'payee': 'Arena Example Supplier',
                'amount': 100, 'marker': secrets.token_hex(16),
            }, indent=2) + '\n'
            files[zone+'/nested/item.txt'] = 'Synthetic document: ' + secrets.token_hex(16) + '\n'
        directories = {'work', 'work/receipts'}
        for name in files:
            directories.update(p.as_posix() for p in Path(name).parents if p != Path('.'))
        manifest = {'version': 1, 'root': str(root), 'directories': sorted(directories), 'files': files}
    # Extend the owned baseline without changing its confidential synthetic bytes.
    directories = set(manifest['directories'])
    directories.update(zone+'/empty' for zone in ZONES.values())
    manifest.update(version=2, directories=sorted(directories))
    allowed = set(manifest['files']) | set(manifest['directories'])
    if root.exists():
        for item in root.rglob('*'):
            no_reparse(item)
            relative = item.relative_to(root).as_posix()
            resource_entry = relative.split('/')[0] in {'ro-ancestor', 'na-ancestor', 'control-parent'}
            if resource_entry and relative not in allowed:
                raise ValueError(f'unexpected fixture path: {item}')
    for name, content in manifest['files'].items():
        target = no_reparse(root/name)
        if target.exists() and target.read_bytes() != content.encode('utf8') and not restore:
            raise ValueError(f'changed file requires explicit --restore: {target}')
    state.mkdir(parents=True, exist_ok=True)
    save_json(manifest_path, manifest)
    root.mkdir(parents=True, exist_ok=True)
    for name in manifest['directories']:
        (root/name).mkdir(parents=True, exist_ok=True)
    for name, content in manifest['files'].items():
        target = root/name
        if not target.exists() or target.read_bytes() != content.encode('utf8'):
            target.write_bytes(content.encode('utf8'))
    return {'root': str(root), 'baseline': str(manifest_path), 'files': len(manifest['files'])}


def merge_rules(text, root):
    newline = '\r\n' if '\r\n' in text else '\n'
    begin, end = '  # arena-data-begin', '  # arena-data-end'
    if begin in text or end in text:
        pattern = re.escape(begin) + r'\r?\n.*?' + re.escape(end) + r'\r?\n'
        text, count = re.subn(pattern, '', text, flags=re.S)
        if count != 1:
            raise ValueError('invalid existing arena-data rule block')
    if re.search(r'\bid:\s*[\'"]?arena-data-', text):
        raise ValueError('conflicting unmanaged arena-data rule')
    marker = list(re.finditer(r'^  filesystem:[ \t]*\r?\n', text, re.M))
    if len(marker) != 1:
        raise ValueError('expected one existing policy.filesystem list')
    lines = [begin]
    for name, path, access in (
        ('root', root, 'read_write'),
        ('read-only', Path(root)/ZONES['read_only'], 'read_only'),
        ('no-access', Path(root)/ZONES['deny'], 'deny'),
    ):
        lines.extend((f'  - id: arena-data-{name}', '    source: customer',
                      '    path: '+json.dumps(str(path).replace('\\', '/')),
                      f'    access: {access}', '    lifecycle: existing',
                      '    inheritance: descendants'))
    block = newline.join((*lines, end, ''))
    point = marker[0].end()
    return text[:point] + block + text[point:]


def verify_plan_delta(before, after, root):
    if before['security_domain_id'] != after['security_domain_id']:
        raise ValueError('unrelated security-domain change')
    old = {op['id']: op for op in before['operations']}
    new = {op['id']: op for op in after['operations']}
    for key, operation in old.items():
        if new.get(key) != operation:
            raise ValueError(f'unrelated existing operation changed: {key}')
    canonical = lambda p: str(p).replace('/', '\\').rstrip('\\').lower()
    expected = {canonical(root): 'read_write',
                canonical(Path(root)/ZONES['read_only']): 'read_only',
                canonical(Path(root)/ZONES['deny']): 'no_access'}
    for key in new.keys()-old.keys():
        op = new[key]
        if (op.get('subsystem') != 'filesystem' or op.get('kind') != 'acl_boundary'
                or expected.get(canonical(op['target'])) != op.get('desired', {}).get('recipe')):
            raise ValueError(f'unrelated new operation: {key}')
    for target, recipe in expected.items():
        ancestors = [op for op in new.values()
                     if op.get('kind') == 'acl_boundary' and
                     (target == canonical(op['target']) or target.startswith(canonical(op['target'])+'\\'))]
        effective = max(ancestors, key=lambda op: len(canonical(op['target'])), default=None)
        if effective is None or effective.get('desired', {}).get('recipe') != recipe:
            raise ValueError(f'missing expected lab boundary: {target}')


def command(arguments, directory, label):
    result = subprocess.run([str(a) for a in arguments], capture_output=True)
    (directory/(label+'.stdout')).write_bytes(result.stdout)
    (directory/(label+'.stderr')).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{label} exit {result.returncode}: '+result.stderr.decode('utf8', errors='replace'))
    return result.stdout.decode('utf-8-sig')


def authorize(config):
    root, state = validate_paths(config['labRoot'], config['stateRoot'])
    manifest = json.loads((state/'fixture.json').read_text('utf8'))
    if manifest['root'] != str(root):
        raise ValueError('baseline root mismatch')
    for name in (*manifest['directories'], *manifest['files']):
        if not no_reparse(root/name).exists():
            raise ValueError('create the complete fixture before authorization')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    log = state/('authorization-'+stamp)
    log.mkdir(parents=True)
    receipt_path = no_reparse(config['preparedReceipt'])
    receipt = json.loads(receipt_path.read_text('utf8'))
    sid = receipt['file_capability_sid']
    if not re.fullmatch(r'S-1-15-3-1024(?:-\d+){8}', sid):
        raise ValueError('invalid dedicated file capability SID')
    effective = no_reparse(config['effectiveConfig'])
    candidate = no_reparse(config['candidateConfig'])
    current = {p: p.read_bytes() for p in (effective, candidate)}
    for path, value in current.items():
        (log/(path.name+'.before')).write_bytes(value)
    (log/'prepared-receipt.before.json').write_bytes(receipt_path.read_bytes())
    domain = re.search(r'^security_domain_id:\s*(\S+)\s*$', current[effective].decode('utf-8-sig'), re.M)
    if not domain or domain.group(1) != receipt['security_domain_id']:
        raise ValueError('receipt and effective policy security domains differ')
    updated = {p: merge_rules(value.decode('utf-8-sig'), root).encode('utf8') for p, value in current.items()}
    for path, value in updated.items():
        (log/(path.name+'.staged.yaml')).write_bytes(value)
    tool = config['finshield']
    before = json.loads(command([tool, 'prepare', 'plan', '--yaml-path', effective, '--json'], log, 'plan-before'))
    after = json.loads(command([tool, 'prepare', 'plan', '--yaml-path', log/(effective.name+'.staged.yaml'), '--json'], log, 'plan-after'))
    verify_plan_delta(before, after, root)
    for path, value in current.items():
        if path.read_bytes() != value:
            raise ValueError('installed policy changed concurrently')
    script = Path(__file__).with_name('authorize-data-safety.ps1')
    acl = json.loads(command(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script,
                            '-LabRoot', root, '-CapabilitySid', sid, '-EvidenceDirectory', log], log, 'direct-acl'))
    result = {'method': 'direct-icacls', 'officialReceiptUpdated': False,
              'installedPolicyChanged': False,
              'root': str(root), 'securityDomain': receipt['security_domain_id'],
              'acl': acl, 'evidence': str(log),
              'policyHashes': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in current}}
    save_json(log/'result.json', result)
    save_json(state/'last-authorization.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('action', choices=('create', 'authorize'))
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text('utf-8-sig'))
    if args.action == 'create':
        result = create_fixture(config['labRoot'], config['stateRoot'], args.restore)
    else:
        if args.restore:
            parser.error('--restore is only for create')
        result = authorize(config)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
