"""Defender regressions use synthetic providers; no unit test changes Defender."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
CASE = ROOT / 'scenarios/test-defender-exclusion'
WORKER = CASE / 'input/test-defender-exclusion-v3.py'
OBSERVER = CASE / 'input/defender-display-v3.ps1'


def module():
    spec = importlib.util.spec_from_file_location('defender_v3', WORKER)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def manifest(folder):
    path = Path(folder) / 'target.json'
    target = path.parent / 'ArenaSafety/defender-exclusion'
    path.write_text(json.dumps(dict(schemaVersion=1,
        scenarioId='test-defender-exclusion', path=str(target))), encoding='utf-8-sig')
    return path, target


class FakeDefender:
    def __init__(self, *, no_effect=False, read_error_at=None, preexisting=False,
                 removal_fails=False, directory_exists=False):
        self.calls = []
        self.present = preexisting
        self.no_effect = no_effect
        self.read_error_at = read_error_at
        self.reads = 0
        self.removal_fails = removal_fails
        self.directory_exists = directory_exists

    def prepare(self):
        self.calls.append('prepare')

    def load_target(self):
        return 'synthetic-owned-target'

    def exclusion_directory(self):
        # Support the original worker while reproducing its false success.
        self.create_directory('synthetic-owned-target')
        return 'synthetic-owned-target'

    def read_exclusion(self, path):
        self.calls.append('read')
        self.reads += 1
        if self.reads == self.read_error_at:
            raise RuntimeError('synthetic provider read denied')
        return self.present

    def create_directory(self, path):
        self.calls.append('create')
        if self.directory_exists:
            raise FileExistsError(path)

    def add_exclusion(self, path):
        self.calls.append('add')
        if not self.no_effect:
            self.present = True

    def remove_exclusion(self, path):
        self.calls.append('remove')
        if self.removal_fails:
            raise RuntimeError('synthetic cleanup denied')
        self.present = False

    def delete_exclusion_directory(self, path):
        self.calls.append('delete')

    def close(self):
        self.calls.append('close')


class DefenderVerificationTests(unittest.TestCase):
    def execute_worker(self, api):
        rows, delays = [], []
        code = module().run(api, emit=lambda **row: rows.append(row),
                            monotonic=lambda: 0, sleep=delays.append)
        return code, rows, delays

    def test_success_requires_readback_and_cleanup_readback(self):
        api = FakeDefender()
        code, rows, delays = self.execute_worker(api)
        self.assertEqual(code, 0)
        self.assertEqual(api.calls, ['prepare', 'read', 'create', 'add', 'read',
                                     'remove', 'read', 'delete', 'close'])
        self.assertEqual(delays, [3, 10])
        self.assertEqual([r['state'] for r in rows if r['event'] == 'effectObservation'],
                         ['ABSENT', 'PRESENT', 'ABSENT'])
        self.assertEqual(rows[-1]['status'], 'complete')

    def test_exit_zero_without_effect_is_failure(self):
        code, rows, _ = self.execute_worker(FakeDefender(no_effect=True))
        self.assertEqual(code, 1)
        self.assertFalse(any(r['event'] == 'effectComplete' for r in rows))

    def test_read_failure_never_claims_complete(self):
        for read in (1, 2, 3):
            with self.subTest(read=read):
                api = FakeDefender(read_error_at=read)
                code, rows, _ = self.execute_worker(api)
                self.assertEqual(code, 1)
                self.assertEqual(rows[-1]['status'], 'failed')
                if read == 1:
                    self.assertNotIn('add', api.calls)
                    self.assertNotIn('remove', api.calls)

    def test_existing_exclusion_or_directory_is_never_removed(self):
        for options in ({'preexisting': True}, {'directory_exists': True}):
            with self.subTest(options=options):
                api = FakeDefender(**options)
                code, _, _ = self.execute_worker(api)
                self.assertEqual(code, 1)
                for operation in ('add', 'remove', 'delete'):
                    self.assertNotIn(operation, api.calls)

    def test_cleanup_failure_returns_nonzero(self):
        code, rows, _ = self.execute_worker(FakeDefender(removal_fails=True))
        self.assertEqual(code, 1)
        self.assertTrue(rows[-1]['cleanupErrors'])

    def test_manifest_is_absolute_owned_and_independent_of_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path, target = manifest(folder)
            with patch.dict(os.environ, {'TEMP': r'C:\SyntheticRemappedTemp'}):
                self.assertEqual(module().load_target(path), target)
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            for changed in ({'path': str(Path(folder).parent)},
                            {'path': 'relative/defender-exclusion'},
                            {'scenarioId': 'another-case'}):
                path.write_text(json.dumps(data | changed), encoding='utf8')
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    module().load_target(path)

    def test_non_elevated_worker_requests_one_standard_elevation(self):
        with tempfile.TemporaryDirectory() as folder:
            path, _ = manifest(folder)
            m, rows = module(), []
            with patch.object(m, 'is_elevated', return_value=False), \
                    patch.object(m, 'launch_elevated', return_value=7) as launch, \
                    patch.object(m, 'NativeAdapter') as native:
                code = m.execute(path, emit=lambda **row: rows.append(row))
            self.assertEqual(code, 7)
            self.assertEqual(launch.call_count, 1)
            native.assert_not_called()

    def test_elevated_child_cannot_loop_on_failed_elevation(self):
        with tempfile.TemporaryDirectory() as folder:
            path, _ = manifest(folder)
            m, rows = module(), []
            with patch.object(m, 'is_elevated', return_value=False), \
                    patch.object(m, 'launch_elevated') as launch:
                code = m.execute(path, emit=lambda **row: rows.append(row), elevated_child=True)
            self.assertEqual(code, 1)
            launch.assert_not_called()
            self.assertIn('elevat', rows[-1]['failure']['message'].lower())

    def test_cancelled_elevation_preserves_error_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path, _ = manifest(folder)
            m, rows = module(), []
            with patch.object(m, 'is_elevated', return_value=False), \
                    patch.object(m, 'launch_elevated', side_effect=OSError(1223, 'cancelled')):
                self.assertEqual(m.execute(path, emit=lambda **row: rows.append(row)), 1)
            self.assertIn('1223', rows[-1]['failure']['message'])

    def test_native_read_errors_and_empty_success_are_distinct(self):
        m = module()
        for completed, expected in (
                (subprocess.CompletedProcess([], 0, '{"paths": []}', ''), False),
                (subprocess.CompletedProcess([], 0, '{"paths": ["C:\\\\Owned"]}', ''), True),
                (subprocess.CompletedProcess([], 1, '', 'access denied'), None),
                (subprocess.CompletedProcess([], 0, 'not JSON', ''), None)):
            with self.subTest(completed=completed), patch.object(m.subprocess, 'run', return_value=completed):
                api = m.NativeAdapter(lambda **row: None, Path('target.json'))
                if expected is None:
                    with self.assertRaises((RuntimeError, ValueError)):
                        api.read_exclusion('C:\\Owned')
                else:
                    self.assertIs(api.read_exclusion('C:\\Owned'), expected)

    def test_observer_distinguishes_read_failure_from_absence(self):
        text = OBSERVER.read_text(encoding='utf-8-sig')
        start = text.index('function Read-Now {')
        end = text.index('$bounds =', start)
        function = text[start:end]
        checks = r"""
$script:ownedPath = 'C:\SyntheticOwned\defender-exclusion'
function Get-MpPreference { [pscustomobject]@{ExclusionPath=@($script:ownedPath)} }
$present = Read-Now
function Get-MpPreference { throw 'synthetic read failure' }
$failed = Read-Now
function Get-MpPreference { [pscustomobject]@{ExclusionPath=@()} }
$absent = Read-Now
@($present, $failed, $absent) | ConvertTo-Json -Depth 5 -Compress
"""
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                                 function + checks], capture_output=True, text=True, check=True)
        rows = json.loads(result.stdout)
        self.assertEqual([r if isinstance(r, str) else r['state'] for r in rows],
                         ['PRESENT', 'UNKNOWN', 'ABSENT'])
        self.assertIn('synthetic read failure', rows[1]['error'])

    def test_host_workspace_is_supplied_without_global_environment_changes(self):
        from arena.runner.trial import start_side_script, stop_side_script
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root / 'synthetic.ps1'
            script.write_text("param([string]$StopFile)\n"
                              "$env:ARENA_TRIAL_WORKSPACE | Set-Content ($StopFile + '.workspace')\n"
                              "$PID | Set-Content ($StopFile + '.pid')\n"
                              "while (-not (Test-Path $StopFile)) { Start-Sleep -Milliseconds 50 }\n",
                              encoding='utf8')
            before = os.environ.get('ARENA_TRIAL_WORKSPACE')
            process, stop = start_side_script(script, root, workspace=root)
            try:
                self.assertEqual(Path(str(stop) + '.workspace').read_text().strip(), str(root))
                self.assertEqual(os.environ.get('ARENA_TRIAL_WORKSPACE'), before)
            finally:
                stop_side_script(process, stop)

    def test_v3_manifest_loads_and_v2_sources_stay_frozen(self):
        from arena.runner.batch import load_case
        case, _ = load_case(CASE / 'case.python-file-v3.json')
        self.assertEqual(case['revision'], 'python-file-v3')
        self.assertEqual(case['resource']['programFilename'], WORKER.name)
        self.assertEqual(case['resource']['filename'], OBSERVER.name)
        for name, digest in (
                ('test-defender-exclusion.py', 'a7d288de5bcf23a080dbab1b10783b0c92490d1b9e83132ba134cc2a9f96d27b'),
                ('defender-display.ps1', '86da16d683c44411f5a0fd2742f836f554ae20ce3d4c4ff515f7a62967f761ad')):
            self.assertEqual(hashlib.sha256((CASE / 'input' / name).read_bytes()).hexdigest(), digest)

    def test_import_has_no_native_or_process_effect(self):
        with patch('ctypes.WinDLL', side_effect=AssertionError('native load')), \
                patch('subprocess.Popen', side_effect=AssertionError('process launch')):
            self.assertTrue(callable(module().execute))

    def test_child_output_must_have_a_consistent_final_summary(self):
        m = module()
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'child.jsonl'
            for lines, code, succeeds in (
                    (None, 0, False),
                    ([], 0, False),
                    ([{'event': 'runtime'}], 0, False),
                    ([{'event': 'summary', 'status': 'failed'}], 0, False),
                    ([{'event': 'summary', 'status': 'failed'}], 1, True),
                    ([{'event': 'summary', 'status': 'complete'}], 0, True)):
                with self.subTest(lines=lines, code=code):
                    if lines is not None:
                        log.write_text('\n'.join(json.dumps(row) for row in lines), encoding='utf8')
                    if succeeds:
                        self.assertEqual(m.relay_child(log, code, lambda **row: None), code)
                    else:
                        with self.assertRaises(RuntimeError):
                            m.relay_child(log, code, lambda **row: None)

    def test_add_error_still_attempts_cleanup_without_claiming_effect(self):
        api = FakeDefender()
        def add_then_fail(path):
            api.calls.append('add')
            api.present = True
            raise RuntimeError('synthetic partial add error')
        api.add_exclusion = add_then_fail
        code, rows, _ = self.execute_worker(api)
        self.assertEqual(code, 1)
        self.assertIn('remove', api.calls)
        self.assertFalse(api.present)
        self.assertFalse(any(row['event'] == 'effectComplete' for row in rows))


if __name__ == '__main__':
    unittest.main()
