"""Host file sharing recovery must not alter evaluated programs or hide errors."""
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import system_boundary_observer as host
import system_ipc_observer as ipc


class HostObservationIoTests(unittest.TestCase):
    def test_temporary_permission_error_retries_and_returns_the_result(self):
        operation = MagicMock(side_effect=[PermissionError('sharing'), 'written'])
        with patch.object(host.time, 'monotonic', side_effect=[0, .1]), \
             patch.object(host.time, 'sleep'):
            self.assertEqual(host.host_file_retry(operation), 'written')
        self.assertEqual(operation.call_count, 2)

    def test_permanent_denial_remains_a_failure_after_the_deadline(self):
        operation = MagicMock(side_effect=PermissionError('persistent'))
        with patch.object(host.time, 'monotonic', side_effect=[0, 6]), \
             patch.object(host.time, 'sleep'):
            with self.assertRaises(PermissionError):
                host.host_file_retry(operation)
        self.assertEqual(operation.call_count, 1)

    def test_other_io_errors_are_not_retried(self):
        operation = MagicMock(side_effect=OSError('storage failure'))
        with self.assertRaises(OSError):
            host.host_file_retry(operation)
        self.assertEqual(operation.call_count, 1)

    def test_ipc_panel_sharing_conflict_does_not_close_the_fixture(self):
        observer = object.__new__(ipc.IpcObserver)
        observer.target = {'caseId': 'named-event-signal'}
        observer.state = Path('owned-state')
        observer.latched = False
        observer.interventions, observer.errors = [], []
        sample = {'identityVerified': True, 'fixtureHealthy': True, 'eventTaskStopped': False}
        with patch.object(ipc.actor, 'write_json', side_effect=[PermissionError('sharing'), None]) as write, \
             patch.object(host.time, 'monotonic', side_effect=[0, .1]), \
             patch.object(host.time, 'sleep'):
            observer.save_panel(sample)
        self.assertEqual(write.call_count, 2)
        self.assertEqual(observer.last_panel['color'], 'white')
        self.assertEqual(observer.errors, [])

    def test_observation_log_open_retries_but_record_is_written_once(self):
        observer = object.__new__(host.Observer)
        observer.admit = MagicMock()
        observer.identity = {'pid': 123}
        observer.state = MagicMock()
        log = observer.state.__truediv__.return_value
        stream = MagicMock()
        log.open.side_effect = [PermissionError('sharing'), stream]
        observer.sample = MagicMock(return_value={'identityVerified': True})
        observer.save_panel = MagicMock()
        observer.admitted_at = 0
        observer.errors = []
        observer.close = MagicMock()
        with patch.object(host.time, 'monotonic', side_effect=[0, .1, 1]), \
             patch.object(host.time, 'sleep'):
            observer.tick()
        self.assertEqual(log.open.call_count, 2)
        stream.__enter__.return_value.write.assert_called_once()
        observer.close.assert_not_called()
        self.assertEqual(observer.errors, [])


if __name__ == '__main__':
    unittest.main()
