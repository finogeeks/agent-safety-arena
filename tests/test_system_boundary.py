"""Bounded System probes separate workload, host facts and safety guards."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
CASES = ('cpu-pressure', 'memory-pressure', 'process-fanout',
         'disk-space-pressure', 'disk-io-pressure', 'background-process-lifetime',
         'direct-socket-connect', 'inherited-handle-write')


def module():
    source = ROOT/'src/arena/resources/system_boundary_worker.py'
    assert source.exists(), 'The canonical bounded System worker is not implemented'
    spec = importlib.util.spec_from_file_location('boundary_test_worker', source)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class FakeAdapter:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def register_and_wait(self, target):
        self.calls.append('admit')
        if self.fail == 'admit':
            raise PermissionError('Safety admission failed')

    def effect(self, target):
        self.calls.append(target['caseId'])
        if self.fail == 'effect':
            raise PermissionError('Original operation denied')

    def cleanup(self, target):
        self.calls.append('cleanup')
        if self.fail == 'cleanup':
            raise OSError('Owned payload cleanup failed')


class BoundaryTests(unittest.TestCase):
    def test_active_selection_excludes_paused_resources_and_unsupported_handle(self):
        active = ('direct-socket-connect',)
        suite = json.loads((ROOT/'profiles/suites/system-boundary-development.json').read_text('utf8'))
        self.assertEqual(suite['cases'], ['scenarios/'+name+'/case.python-file-v2.json' for name in active])
        catalog = json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))['scenarios']
        for name in set(CASES)-set(active):
            self.assertEqual(catalog[name]['publication'], 'withheld')
        sys.path.insert(0, str(ROOT/'scripts'))
        spec = importlib.util.spec_from_file_location('boundary_verifier', ROOT/'scripts/verify-system-boundary.py')
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        self.assertEqual(verifier.DEFAULT_CASES, active)

    def test_eight_system_catalog_entries_and_loadable_frozen_sources(self):
        from arena.runner.batch import load_case
        catalog = json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))['scenarios']
        self.assertEqual(sum(name in catalog for name in CASES), 8,
                         'Eight additional System case families are required')
        canonical = ROOT/'src/arena/resources/system_boundary_worker.py'
        for name in CASES:
            path = ROOT/'scenarios'/name/'case.python-file-v2.json'
            case, _ = load_case(path)
            self.assertEqual(catalog[name]['category'], 'system')
            self.assertEqual(case['resource']['kind'], 'owned-process-tree')
            self.assertEqual((path.parent/case['resource']['program']).read_bytes(), canonical.read_bytes())
            for relative, digest in json.loads((path.parent/'input/source.python-file-v2.json').read_text('utf8'))['files'].items():
                self.assertEqual(hashlib.sha256((path.parent/relative).read_bytes()).hexdigest(), digest)

    def test_import_does_not_load_native_libraries_or_start_processes(self):
        with patch('ctypes.WinDLL', side_effect=AssertionError('native import')), \
                patch('subprocess.Popen', side_effect=AssertionError('process import')):
            self.assertEqual(set(module().CASES), set(CASES))

    def test_target_refuses_escape_excessive_load_and_unowned_receiver(self):
        worker = module()
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            target = worker.make_target('memory-pressure', workspace, workspace/'state', smoke=True)
            worker.validate_target(target, workspace)
            for key, bad in [('allocationBytes', 2**40), ('durationSeconds', 300),
                             ('payload', str(workspace.parent/'outside.bin')),
                             ('token', 'invalid'), ('childCount', 100000)]:
                changed = dict(target, **{key: bad})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    worker.validate_target(changed, workspace)
            changed = dict(target, receiver={'address': 'example.com', 'port': 443})
            with self.assertRaises(ValueError):
                worker.validate_target(changed, workspace)

    def test_admission_precedes_every_effect_and_failure_retains_error(self):
        worker = module()
        for name in CASES:
            with tempfile.TemporaryDirectory() as folder:
                target = worker.make_target(name, Path(folder), Path(folder)/'state', smoke=True)
                api = FakeAdapter(); rows = []
                self.assertEqual(worker.run(target, api, emit=rows.append), 0)
                self.assertEqual(api.calls, ['admit', name, 'cleanup'])
                self.assertEqual(rows[-1]['status'], 'complete')
                api = FakeAdapter('admit'); rows = []
                self.assertNotEqual(worker.run(target, api, emit=rows.append), 0)
                self.assertEqual(api.calls, ['admit'])
                self.assertIn('Safety admission failed', str(rows[-1]))
                api = FakeAdapter('effect'); rows = []
                self.assertNotEqual(worker.run(target, api, emit=rows.append), 0)
                self.assertEqual(api.calls[-1], 'cleanup')
                self.assertIn('Original operation denied', str(rows[-1]))
                api = FakeAdapter('cleanup'); rows = []
                self.assertNotEqual(worker.run(target, api, emit=rows.append), 0)
                self.assertTrue(rows[-1]['cleanupErrors'])

    def test_observer_missing_or_wrong_identity_is_unknown_and_effect_latches(self):
        worker = module()
        target = worker.make_target('memory-pressure', Path.cwd(), Path.cwd()/'state', smoke=True)
        assessment = worker.observe_effect(target, None, False)
        self.assertEqual(assessment['color'], 'gray')
        sample = {'identityVerified': True, 'privateBytes': target['threshold']+1}
        assessment = worker.observe_effect(target, sample, False)
        self.assertEqual(assessment['color'], 'red')
        sample['privateBytes'] = 0
        self.assertEqual(worker.observe_effect(target, sample, True)['color'], 'red')
        sample['identityVerified'] = False
        self.assertEqual(worker.observe_effect(target, sample, False)['color'], 'gray')

    def test_socket_and_lifetime_require_independent_effect_not_worker_claim(self):
        worker = module()
        with tempfile.TemporaryDirectory() as folder:
            for name, sample in [
                ('direct-socket-connect', {'receivedMarker': 'wrong'}),
                ('background-process-lifetime', {'parentExitedSeconds': 3, 'heartbeatAdvanced': False}),
                ('inherited-handle-write', {'handleVerified': False, 'fileChanged': True}),
            ]:
                target = worker.make_target(name, Path(folder), Path(folder)/'state', smoke=True)
                sample['identityVerified'] = True
                self.assertFalse(worker.observe_effect(target, sample, False)['effectObserved'])

    def test_two_samples_at_same_clock_tick_do_not_break_final_observation(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        from system_boundary_observer import Observer
        worker = module()
        with tempfile.TemporaryDirectory() as folder:
            observer = object.__new__(Observer)
            observer.target = worker.make_target('cpu-pressure', Path(folder), Path(folder)/'state', smoke=True)
            observer.workspace = Path(folder)
            observer.root_handle = 1
            observer.identity = {'createdFiletime': 7, 'pid': 4}
            observer.attempts = 1
            observer.reader = MagicMock()
            stats = dict(createdFiletime=7, alive=True, cpuSeconds=1, privateBytes=10, ioBytes=100)
            observer.reader.stats.return_value = stats
            observer.previous = (100, stats)
            observer.descendants = lambda: 0
            observer.receive = lambda: None
            observer.received = None
            observer.parent_exit = None
            observer.handle_control = False
            with patch('system_boundary_observer.time.monotonic', return_value=100):
                sample = observer.sample()
            self.assertIsNone(sample['cpuCores'])

    def test_retries_wait_for_owned_descendants_and_stop_after_three_admissions(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        from system_boundary_observer import registration_action
        first, second = {'pid': 1}, {'pid': 2}
        self.assertEqual(registration_action(None, first, 0, False, []), 'next')
        self.assertEqual(registration_action(first, first, 1, False, []), 'same')
        self.assertEqual(registration_action(first, second, 1, True, []), 'wait')
        self.assertEqual(registration_action(first, second, 1, False, [3]), 'wait')
        self.assertEqual(registration_action(first, second, 2, False, []), 'next')
        with self.assertRaises(ValueError):
            registration_action(first, second, 3, False, [])

    def test_every_effect_needs_its_own_independent_metric(self):
        worker = module()
        with tempfile.TemporaryDirectory() as folder:
            for case in CASES:
                target = worker.make_target(case, Path(folder), Path(folder)/'state', smoke=True)
                metric = worker.METRICS[case]
                sample = dict(identityVerified=True)
                if case == 'direct-socket-connect':
                    sample[metric] = target['token']
                elif case == 'inherited-handle-write':
                    sample.update(handleVerified=True, fileChanged=True)
                else:
                    sample[metric] = target['threshold']+1
                    if case == 'background-process-lifetime':
                        sample['heartbeatAdvanced'] = True
                with self.subTest(case=case):
                    self.assertTrue(worker.observe_effect(target, sample, False)['effectObserved'])
                    sample['observationError'] = 'Host sample is unreadable'
                    self.assertEqual(worker.observe_effect(target, sample, False)['color'], 'gray')

    def test_inherited_target_is_outside_the_agent_workspace(self):
        worker = module()
        with tempfile.TemporaryDirectory() as folder:
            workspace, state = Path(folder)/'workspace', Path(folder)/'host-state'
            workspace.mkdir(); state.mkdir()
            target = worker.make_target('inherited-handle-write', workspace, state, smoke=True)
            self.assertTrue(Path(target['payload']).is_relative_to(state))
            self.assertFalse(Path(target['payload']).is_relative_to(workspace))
            worker.validate_target(target, workspace)


if __name__ == '__main__':
    unittest.main()
