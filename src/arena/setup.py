"""Read-only checks for a clone and explicitly selected local dependencies."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

from arena.runner.batch import load_profile


def check_repository(root, profile_path=None, environment='native', lock_path=None):
    root = Path(root).resolve()
    checks = []

    def check(name, passed, detail):
        checks.append(dict(name=name, status='pass' if passed else 'fail', detail=detail))

    check('python', sys.version_info >= (3, 12), sys.version.split()[0])
    for name in ('AGENTS.md', 'pyproject.toml', 'dependencies/runtime.json', 'scenarios',
                 'profiles', 'src/arena', 'templates'):
        path = root / name
        expected_file = name in {'AGENTS.md', 'pyproject.toml', 'dependencies/runtime.json'}
        check(name, path.is_file() if expected_file else path.is_dir(), str(path))

    if profile_path is not None:
        profile = load_profile(profile_path)
        for key in ('node', 'dshEntry', 'chrome', 'ffmpeg', 'desktopTool'):
            value = profile.get(key)
            resolved = None
            if isinstance(value, str) and value:
                resolved = str(Path(value).resolve()) if Path(value).is_file() else shutil.which(value)
            check(key, bool(resolved and Path(resolved).is_file()),
                  resolved or 'Set an existing file or PATH command in the local profile')
        check('platform', sys.platform == 'win32', 'Live DSH recording requires Windows')
        region = profile.get('screenRegion')
        valid_region = (isinstance(region, list) and len(region) == 4
                        and all(type(v) is int for v in region)
                        and region[2] >= 2 and region[3] >= 2)
        check('screenRegion', valid_region, 'Declare the actual physical capture rectangle [x,y,width,height]')
        if environment == 'finshield':
            for key in ('finshield', 'finshieldConfig', 'dshDesktop'):
                value = profile.get(key)
                check(key, isinstance(value, str) and Path(value).is_file(),
                      'Set an existing file in the local profile')
            workspace = profile.get('workspaceRoot')
            check('workspaceRoot', isinstance(workspace, str) and Path(workspace).is_dir(),
                  'Use an existing directory already allowed by the installed policy')
            check('dependencyLock', lock_path is not None, 'Select this case revision\'s FinShield dependency file with --lock')
            if lock_path is not None:
                lock = json.loads(Path(lock_path).read_text('utf8'))
                files = lock.get('runtimeFiles') if isinstance(lock, dict) else None
                if (not isinstance(lock, dict) or lock.get('schemaVersion') != 1
                        or lock.get('product') != 'FinShield'
                        or not isinstance(lock.get('version'), str) or not lock['version']
                        or not isinstance(files, dict) or 'finsafe.exe' not in files):
                    raise ValueError('Invalid version-specific FinShield dependency file')
                executable = profile.get('finshield')
                install_root = Path(executable).resolve().parent if isinstance(executable, str) else None
                for name, expected in files.items():
                    if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name)
                            or name in {'.', '..'} or not isinstance(expected, str)
                            or not re.fullmatch(r'[a-f0-9]{64}', expected)):
                        raise ValueError('Dependency runtime files require plain names and SHA-256 values')
                    path = (Path(executable) if name == 'finsafe.exe' else install_root / name) if install_root else None
                    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None
                    check('finshield-runtime:' + name, actual == expected,
                          f'FinShield {lock["version"]}; expected {expected}; actual {actual or "missing"}')
    elif environment != 'native' or lock_path is not None:
        raise ValueError('A local --profile is required for environment dependency checks')

    return dict(ok=all(row['status'] == 'pass' for row in checks), checks=checks,
                scope='static-files', trialReady=False, trialExecutions=0,
                nextStep='Run the documented installation/version checks and no-prompt preflight before collection.')
