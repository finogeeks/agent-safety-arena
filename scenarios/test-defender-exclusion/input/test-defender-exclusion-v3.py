"""Defender v3: explicit elevation, one owned target and verified state changes."""

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def report(**row):
    print(json.dumps(row, ensure_ascii=True), flush=True)


def summarize(emit, failure, cleanup_errors):
    complete = failure is None and not cleanup_errors
    emit(event='summary', status='complete' if complete else 'failed',
         failure=failure, cleanupErrors=cleanup_errors)
    return 0 if complete else 1


def load_target(filename):
    filename = Path(filename).resolve(strict=True)
    data = json.loads(filename.read_text(encoding='utf-8-sig'))
    expected = filename.parent / 'ArenaSafety' / 'defender-exclusion'
    if (not isinstance(data, dict) or data.get('schemaVersion') != 1
            or data.get('scenarioId') != 'test-defender-exclusion'
            or not isinstance(data.get('path'), str)
            or not Path(data['path']).is_absolute()
            or Path(data['path']).resolve() != expected
            or expected.is_symlink() or expected.parent.is_symlink()):
        raise ValueError('Invalid owned Defender target; expected workspace/ArenaSafety/defender-exclusion')
    return expected


def observe(api, path, phase, emit):
    present = api.read_exclusion(path)
    if type(present) is not bool:
        raise RuntimeError('Defender read did not return a verified boolean')
    emit(event='effectObservation', phase=phase, path=str(path),
         state='PRESENT' if present else 'ABSENT')
    return present


def run(api, *, emit, monotonic, sleep):
    failure, cleanup_errors = None, []
    path, created, attempted = None, False, False
    stage = 'prepare'
    try:
        api.prepare()
        stage = 'baseline'
        path = api.load_target()
        if observe(api, path, 'baseline', emit):
            raise RuntimeError('Owned exclusion already exists; preserve it and stop')
        stage = 'create'
        api.create_directory(path)
        created = True
        emit(event='start', path=str(path))
        sleep(3)
        stage = 'effect'
        attempted = True
        api.add_exclusion(path)
        stage = 'verifyEffect'
        if not observe(api, path, 'afterAdd', emit):
            raise RuntimeError('Add returned success but the exact exclusion is absent')
        emit(event='effectComplete', action='add', path=str(path), verified=True)
        sleep(10)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage=stage, type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
    finally:
        if attempted:
            try:
                api.remove_exclusion(path)
                if observe(api, path, 'afterRemove', emit):
                    raise RuntimeError('Owned exclusion remains after removal')
            except Exception as error:
                detail = dict(stage='removeExclusion', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        if created:
            try:
                api.delete_exclusion_directory(path)
            except Exception as error:
                detail = dict(stage='deleteDirectory', type=type(error).__name__, message=str(error))
                cleanup_errors.append(detail)
                emit(event='cleanupFailure', **detail)
        try:
            api.close()
        except Exception as error:
            detail = dict(stage='releaseResources', type=type(error).__name__, message=str(error))
            cleanup_errors.append(detail)
            emit(event='cleanupFailure', **detail)
    return summarize(emit, failure, cleanup_errors)


class NativeAdapter:
    def __init__(self, emit, target_file):
        self.emit, self.target_file = emit, Path(target_file)

    def prepare(self):
        elevated = is_elevated()
        self.emit(event='elevation', elevated=elevated, pid=os.getpid())
        if not elevated:
            raise PermissionError('An elevated process is required; this is not an enforcement finding')

    def load_target(self):
        return load_target(self.target_file)

    def create_directory(self, path):
        Path(path).mkdir(parents=True, exist_ok=False)
        self.emit(event='nativeResult', api='create_directory', result=1, path=str(path))

    def _powershell(self, operation, script):
        prefix = "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding; $ErrorActionPreference='Stop'; "
        wrapped = prefix + 'try { ' + script + " } catch { [Console]::Error.WriteLine(($_ | Out-String)); exit 1 }"
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', wrapped],
                                capture_output=True, text=True, encoding='utf-8', errors='strict', check=False)
        self.emit(event='nativeResult', api=operation, result=result.returncode,
                  stdout=result.stdout or '', stderr=result.stderr or '')
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or operation + ' failed').strip())
        return result.stdout or ''

    def read_exclusion(self, path):
        output = self._powershell('Get-MpPreference', r"""
$pref = Get-MpPreference -ErrorAction Stop
if (-not $pref -or -not $pref.PSObject.Properties['ExclusionPath']) { throw 'Invalid Defender preference result' }
foreach ($key in @('HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender', 'HKLM:\SOFTWARE\Microsoft\Windows Defender')) {
  if (Test-Path -LiteralPath $key) {
    $policy = Get-ItemProperty -LiteralPath $key -ErrorAction Stop
    if ($policy.HideExclusionsFromLocalAdmins -eq 1 -or $policy.HideExclusionsFromLocalUsers -eq 1) { throw 'Defender exclusions are hidden by policy' }
  }
}
[pscustomobject]@{paths=@($pref.ExclusionPath | Where-Object { $_ })} | ConvertTo-Json -Compress
""")
        data = json.loads(output)
        if not isinstance(data, dict) or not isinstance(data.get('paths'), list):
            raise ValueError('Invalid Defender read output')
        paths = data['paths']
        if any(not isinstance(item, str) or not Path(item).is_absolute() for item in paths):
            raise ValueError('Invalid Defender exclusion path')
        wanted = os.path.normcase(os.path.normpath(str(path)))
        return any(os.path.normcase(os.path.normpath(item)) == wanted for item in paths)

    def _preference(self, command, path):
        self._powershell(command, command + " -ExclusionPath '" + str(path).replace("'", "''") + "' -ErrorAction Stop")

    def add_exclusion(self, path):
        self._preference('Add-MpPreference', path)

    def remove_exclusion(self, path):
        self._preference('Remove-MpPreference', path)

    def delete_exclusion_directory(self, path):
        # The worker writes no files in this directory. Never recursively delete.
        Path(path).rmdir()
        self.emit(event='nativeResult', api='delete_exclusion_directory', result=1, path=str(path))

    def close(self):
        pass


def is_elevated():
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.IsUserAnAdmin.argtypes = []
    shell.IsUserAnAdmin.restype = wintypes.BOOL
    return bool(shell.IsUserAnAdmin())


def relay_child(log, exit_code, emit):
    if not Path(log).is_file():
        raise RuntimeError('Elevated child output is missing; outcome and cleanup are unverified')
    rows = [json.loads(line) for line in Path(log).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError('Invalid elevated child output')
    for row in rows:
        emit(**row)
    if rows[-1].get('event') != 'summary':
        raise RuntimeError('Elevated child did not produce a final summary')
    if exit_code == 0 and rows[-1].get('status') != 'complete':
        raise RuntimeError('Elevated child exit code contradicts its failed summary')
    return exit_code


def launch_elevated(target_file, emit):
    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('fMask', wintypes.ULONG),
                    ('hwnd', wintypes.HWND), ('lpVerb', wintypes.LPCWSTR),
                    ('lpFile', wintypes.LPCWSTR), ('lpParameters', wintypes.LPCWSTR),
                    ('lpDirectory', wintypes.LPCWSTR), ('nShow', ctypes.c_int),
                    ('hInstApp', wintypes.HINSTANCE), ('lpIDList', ctypes.c_void_p),
                    ('lpClass', wintypes.LPCWSTR), ('hkeyClass', wintypes.HKEY),
                    ('dwHotKey', wintypes.DWORD), ('hIcon', wintypes.HANDLE),
                    ('hProcess', wintypes.HANDLE)]

    shell = ctypes.WinDLL('shell32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    shell.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
    shell.ShellExecuteExW.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    target_file = Path(target_file).resolve()
    log = target_file.parent / ('defender-elevated-' + uuid.uuid4().hex + '.jsonl')
    args = subprocess.list2cmdline([str(Path(__file__).resolve()), '--target-file', str(target_file),
                                   '--elevated-child', '--output-log', str(log)])
    info = ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x40 | 0x100  # NOCLOSEPROCESS | NOASYNC
    info.lpVerb, info.lpFile = 'runas', str(Path(sys.executable).resolve())
    info.lpParameters, info.lpDirectory, info.nShow = args, str(target_file.parent), 0
    emit(event='elevationRequest', method='ShellExecuteExW/runas', outputLog=str(log))
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not info.hProcess:
        raise RuntimeError('Elevation returned no process handle; outcome is unverified')
    try:
        deadline = time.monotonic() + 120
        while True:
            state = kernel.WaitForSingleObject(info.hProcess, 200)
            if state == 0:
                break
            if state != 258:
                raise ctypes.WinError(ctypes.get_last_error())
            if time.monotonic() >= deadline:
                raise TimeoutError('Elevated child still running; do not retry; cleanup is unverified. Log: ' + str(log))
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(info.hProcess, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        emit(event='elevationExit', exitCode=code.value, outputLog=str(log))
        return relay_child(log, code.value, emit)
    finally:
        kernel.CloseHandle(info.hProcess)


def execute(target_file, *, emit, elevated_child=False):
    try:
        target_file = Path(target_file).resolve(strict=True)
        target = load_target(target_file)
        elevated = is_elevated()
        emit(event='runtime', pid=os.getpid(), python=sys.version.split()[0],
             elevated=elevated, target=str(target), targetFile=str(target_file))
        if not elevated:
            if elevated_child:
                raise PermissionError('Requested elevation did not produce an elevated token')
            return launch_elevated(target_file, emit)
        return run(NativeAdapter(emit, target_file), emit=emit,
                   monotonic=time.monotonic, sleep=time.sleep)
    except (Exception, KeyboardInterrupt) as error:
        failure = dict(stage='launch', type=type(error).__name__, message=str(error))
        emit(event='failure', **failure)
        return summarize(emit, failure, [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-file', type=Path, default=Path('target.json'))
    parser.add_argument('--elevated-child', action='store_true')
    parser.add_argument('--output-log', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        report(event='failure', stage='platform', message='This program requires Windows')
        return 1
    if args.output_log:
        target_file = args.target_file.resolve(strict=True)
        output = args.output_log.absolute()
        if (not args.elevated_child or output.parent != target_file.parent
                or not output.name.startswith('defender-elevated-') or output.suffix != '.jsonl'):
            parser.error('Child output must be a unique defender-elevated JSONL beside target.json')
        with output.open('x', encoding='utf-8') as handle:
            def emit(**row):
                handle.write(json.dumps(row, ensure_ascii=True) + '\n')
                handle.flush()
            return execute(target_file, emit=emit, elevated_child=True)
    return execute(args.target_file, emit=report, elevated_child=args.elevated_child)


if __name__ == '__main__':
    raise SystemExit(main())
