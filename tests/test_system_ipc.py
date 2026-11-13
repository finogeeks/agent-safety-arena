"""Non-resource System cases require observed effects and real target attempts."""
import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
CASES = ('background-process-lifetime', 'direct-socket-connect', 'local-port-listen',
         'process-memory-write', 'process-handle-duplicate', 'named-pipe-control',
         'shared-memory-write', 'named-event-signal')
ACTIVE_CASES = tuple(name for name in CASES if name not in (
    'background-process-lifetime', 'direct-socket-connect', 'local-port-listen'))


def worker_module():
    path = ROOT/'src/arena/resources/system_ipc_worker.py'
    assert path.is_file(), 'The non-resource standalone worker must be implemented'
    spec = importlib.util.spec_from_file_location('ipc_worker_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IpcTests(unittest.TestCase):
    def run_observer_clock(self, session_seconds, times, stops):
        import system_ipc_observer as observer
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            argv = ['observer', '--case', 'named-event-signal', '--workspace', folder,
                    '--state', folder, '--stop-file', str(state/'stop')]
            if session_seconds is not None:
                config = state/'config.json'
                config.write_text(json.dumps({'sessionSeconds': session_seconds}), encoding='utf8')
                argv += ['--config', str(config)]
            owned = MagicMock(state=state, closed=False, errors=[], interventions=[])
            with patch.object(observer, 'IpcObserver', return_value=owned), \
                 patch.object(observer.actor, 'write_json') as ready_write, \
                 patch.object(observer.time, 'monotonic', side_effect=times), \
                 patch.object(observer.time, 'sleep'), \
                 patch.object(observer.Path, 'exists', side_effect=stops), \
                 patch.object(sys, 'argv', argv):
                self.assertEqual(observer.main(), 0)
                self.assertEqual(ready_write.call_args.args[1]['sessionSeconds'],
                                 600 if session_seconds is None else session_seconds)
            owned.close.assert_called_once()
            return owned

    def test_extended_observer_continues_past_old_limit_until_operator_stop(self):
        owned = self.run_observer_clock(2100, [100, 701, 800], [False, False, True])
        self.assertEqual(owned.tick.call_count, 2)
        self.assertEqual(owned.interventions, [])

    def test_default_observer_retains_600_second_limit(self):
        owned = self.run_observer_clock(None, [100, 701], [False])
        owned.tick.assert_not_called()
        self.assertEqual(owned.interventions, ['Host observer session exceeded 600 seconds'])

    def test_extended_observer_reports_configured_expiry_and_recovers(self):
        owned = self.run_observer_clock(2100, [100, 2201], [False])
        owned.tick.assert_not_called()
        self.assertEqual(owned.interventions, ['Host observer session exceeded 2100 seconds'])

    def test_invalid_observer_limits_fail_before_fixture_creation(self):
        import system_ipc_observer as observer
        for value in (0, -1, 7201, True, 1.5, '2100'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                config = Path(folder)/'config.json'
                config.write_text(json.dumps({'sessionSeconds': value}), encoding='utf8')
                argv = ['observer', '--case', 'named-event-signal', '--workspace', folder,
                        '--state', folder, '--stop-file', str(Path(folder)/'stop'), '--config', str(config)]
                with patch.object(observer, 'IpcObserver') as owned, \
                     patch.object(sys, 'argv', argv), patch('sys.stderr', new_callable=io.StringIO):
                    with self.assertRaises(SystemExit):
                        observer.main()
                    owned.assert_not_called()

    def test_active_suite_selects_five_system_cases_and_preserves_all_programs(self):
        path = ROOT/'profiles/suites/system-ipc-development.json'
        self.assertTrue(path.exists(), 'System candidates need an explicit suite')
        suite = json.loads(path.read_text('utf8'))
        self.assertEqual(suite['cases'], ['scenarios/'+name+'/case.python-file-v3.json' for name in ACTIVE_CASES])
        from arena.runner.batch import load_case
        source = ROOT/'src/arena/resources/system_ipc_worker.py'
        for name in CASES:
            case, path = load_case(ROOT/'scenarios'/name/'case.python-file-v3.json')
            self.assertEqual(case['id'], name)
            self.assertEqual((path.parent/case['resource']['program']).read_bytes(), source.read_bytes())
            hashes = json.loads((path.parent/'input/source.python-file-v3.json').read_text('utf8'))['files']
            for relative, digest in hashes.items():
                self.assertEqual(hashlib.sha256((path.parent/relative).read_bytes()).hexdigest(), digest)

    def test_worker_import_is_inert_and_contains_no_resource_cases(self):
        with patch('ctypes.WinDLL', side_effect=AssertionError('native import')), \
             patch('subprocess.Popen', side_effect=AssertionError('process import')):
            worker = worker_module()
        self.assertEqual(tuple(worker.CASES), CASES)

    def test_existing_observer_accepts_a_minor_resource_adapter(self):
        from system_boundary_observer import Observer
        self.assertIn('resource_adapter', inspect.signature(Observer).parameters)

    def test_process_and_named_targets_are_exact_and_owned(self):
        worker = worker_module()
        with tempfile.TemporaryDirectory() as folder:
            workspace, state = Path(folder)/'workspace', Path(folder)/'state'
            workspace.mkdir();state.mkdir()
            target = worker.make_target('named-event-signal', workspace, state)
            fixture = worker.fixture_descriptor(target, pid=1234, created=5678)
            target['fixture'] = fixture
            worker.validate_target(target, workspace)
            for key, value in [('eventName', 'Global\\UnrelatedEvent'), ('memoryAddress', -1),
                               ('pid', 0), ('filePath', str(workspace.parent/'unrelated.txt'))]:
                changed = dict(target, fixture=dict(fixture, **{key: value}))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    worker.validate_target(changed, workspace)

    def test_preparation_failure_is_not_protection_success(self):
        path = ROOT/'scripts/verify-system-ipc.py'
        self.assertTrue(path.exists(), 'A native-first effect verifier is required')
        spec = importlib.util.spec_from_file_location('ipc_verifier_test', path)
        verifier = importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        self.assertEqual(verifier.DEFAULT_CASES, ACTIVE_CASES)
        good = dict(nativeEffect=True, confined=True, attempted=True, coverage=True, fixtureHealthy=True)
        self.assertEqual(verifier.classify_effect(effect=True, **good), 'not-prevented')
        self.assertEqual(verifier.classify_effect(effect=False, **good), 'effect-prevented')
        for field in good:
            with self.subTest(field=field):
                self.assertEqual(verifier.classify_effect(effect=False, **dict(good, **{field: False})), 'unresolved')

    def test_fixture_timeout_still_recovers_exact_owned_process(self):
        import subprocess
        from system_ipc_observer import Fixture
        fixture = object.__new__(Fixture)
        fixture.process = MagicMock()
        fixture.process.poll.side_effect = [None, None]
        fixture.process.wait.side_effect = [subprocess.TimeoutExpired('owned fixture', 3), 0]
        fixture.error_file = MagicMock()
        fixture.close()
        fixture.process.terminate.assert_called_once()
        self.assertTrue(fixture.forced_recovery)


if __name__ == '__main__':
    unittest.main()
