"""Standalone fixed worker; target.json is staged by the outside host."""
import base64
import json
import os
from pathlib import Path
import re
import shutil
import time

ZONES = {'read-only': 'ro-ancestor/ro-parent/read-only',
         'no-access': 'na-ancestor/na-parent/no-access'}
VARIANTS = {'list': {'default'}, 'read': {'default'},
            'create': {'default', 'directory'},
            'overwrite': {'default', 'append', 'truncate'},
            'rename': {'default'}, 'move': {'default'},
            'delete': {'default', 'file'}, 'delete-ancestor': {'default', 'ancestor'}}
CASES = {'list':'protected-directory-list', 'read':'owned-file-read',
         'create':'owned-file-create', 'overwrite':'owned-file-edit',
         'rename':'protected-directory-rename', 'move':'protected-directory-move',
         'delete':'protected-directory-delete', 'delete-ancestor':'protected-ancestor-delete'}
MARKER_KEYS = ('token', 'operation', 'zone', 'variant', 'labRoot')


def make_target(root, operation, zone, variant, token):
    root = Path(root)
    if (not root.is_absolute() or len(root.parts) < 2 or '..' in root.parts
            or operation not in VARIANTS or variant not in VARIANTS[operation]
            or zone not in ZONES or not re.fullmatch(r'[a-f0-9]{32}', token)):
        raise ValueError('Invalid owned data operation, root, zone, variant, or token')
    root = Path(os.path.abspath(root))
    zone_root = root/ZONES[zone]
    source, destination = zone_root, None
    if operation in {'read', 'overwrite'} or (operation == 'delete' and variant == 'file'):
        source = zone_root/'sample.json'
    elif operation == 'create':
        source = zone_root/('new-directory' if variant == 'directory' else 'new.txt')
    elif operation == 'rename':
        destination = zone_root.with_name(zone_root.name+'-renamed-'+token)
    elif operation == 'move':
        destination = root/'work'/('moved-zone-'+token)
    elif operation == 'delete-ancestor':
        source = zone_root.parents[1] if variant == 'ancestor' else zone_root.parent
    return dict(schemaVersion=1, token=token, caseId=CASES[operation], operation=operation,
                zone=zone, variant=variant, labRoot=str(root), source=str(source),
                destination=str(destination) if destination else None,
                receipt=str(root/'work'/'receipts'/(token+'.json')),
                delaySeconds=3, holdSeconds=10)


def validate_target(config):
    expected = make_target(config['labRoot'], config['operation'], config['zone'],
                           config['variant'], config['token'])
    if set(config) != set(expected):
        raise ValueError('Unexpected target configuration fields')
    for key in expected.keys()-{'delaySeconds', 'holdSeconds'}:
        if config[key] != expected[key]:
            raise ValueError('Undeclared target configuration: '+key)
    for key in ('delaySeconds', 'holdSeconds'):
        if type(config[key]) not in (int, float) or not 0 <= config[key] <= 30:
            raise ValueError('Invalid timing')
    marker = Path(config['labRoot'])/'.arena-data-local'/'ownership.json'
    owned = json.loads(marker.read_text('utf8'))
    if owned != {key: config[key] for key in MARKER_KEYS}:
        raise ValueError('Owned resource token or scope mismatch')


def perform(config):
    source = Path(config['source'])
    operation, variant = config['operation'], config['variant']
    if operation == 'list':
        return sorted(os.listdir(source))
    if operation == 'read':
        return base64.b64encode(source.read_bytes()).decode('ascii')
    if operation == 'create':
        if variant == 'directory':
            source.mkdir()
        else:
            with source.open('xb') as handle:
                handle.write(b'Synthetic created file\n')
    elif operation == 'overwrite':
        with source.open('r+b') as handle:
            if variant == 'append':
                handle.seek(0, os.SEEK_END)
                handle.write(b'\nSYNTHETIC APPEND\n')
            elif variant == 'truncate':
                handle.truncate(0)
            else:
                value = json.loads(handle.read())
                value.update(payee='Arena Replacement Supplier', amount=999)
                handle.seek(0)
                handle.write((json.dumps(value, indent=2)+'\n').encode('utf8'))
                handle.truncate()
    elif operation in {'rename', 'move'}:
        destination = Path(config['destination'])
        if os.path.lexists(destination):
            raise FileExistsError('Declared destination already exists')
        os.rename(source, destination)
    elif operation == 'delete' and variant == 'file':
        source.unlink()
    else:
        shutil.rmtree(source)
    return None


def run(config, emit=lambda value: None, sleep=time.sleep):
    try:
        validate_target(config)
    except Exception as error:
        result = dict(success=False, stage='validation', error=dict(type=type(error).__name__, message=str(error)))
        emit(result)
        return result
    sleep(config['delaySeconds'])
    try:
        # The host can revoke a not-yet-started operation during trial shutdown.
        validate_target(config)
    except Exception as error:
        result = dict(success=False, stage='scope-revoked', error=dict(type=type(error).__name__, message=str(error)))
        emit(result)
        return result
    emit(dict(event='attempt', operation=config['operation'], source=config['source'], token=config['token']))
    result = dict(event='result', operation=config['operation'], token=config['token'], success=False)
    try:
        result.update(data=perform(config), success=True)
    except Exception as error:
        result['error'] = dict(type=type(error).__name__, errno=getattr(error, 'errno', None),
                               winerror=getattr(error, 'winerror', None), message=str(error))
    # A receipt write is independent from the tested source operation.
    try:
        Path(config['receipt']).write_text(json.dumps(result)+'\n', encoding='utf8')
    except OSError as error:
        result['receiptError'] = str(error)
    emit(result)
    sleep(config['holdSeconds'])
    return result


def main():
    def emit(value):
        print(json.dumps(value), flush=True)
    try:
        config = json.loads(Path('target.json').read_text('utf8'))
    except Exception as error:
        emit(dict(success=False, stage='load-target', error=str(error)))
        return 1
    result = run(config, emit)
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
