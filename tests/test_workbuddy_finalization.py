import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch
from arena.adapters.agents.workbuddy import WorkBuddyAgent
from arena.runner import batch


class WorkBuddyFinalization(unittest.TestCase):
    def test_slow_shutdown_defers_only_to_a_verified_assigned_job(self):
        with tempfile.TemporaryDirectory() as folder:
            agent=WorkBuddyAgent({},process_boundary=object())
            agent.job_assigned=True
            agent.directory=Path(folder)
            agent.process=Mock(pid=54321)
            agent.process.poll.return_value=None
            agent.process.wait.side_effect=subprocess.TimeoutExpired('owned WorkBuddy',5)
            with patch('arena.adapters.agents.workbuddy.subprocess.run'):
                agent.close()
            note=json.loads((Path(folder)/'workbuddy-shutdown.json').read_text())
            self.assertTrue(note['deferredToOwnedJob'])
            self.assertTrue(note['gracePeriodExpired'])
            agent.job_assigned=False
            with patch('arena.adapters.agents.workbuddy.subprocess.run'):
                with self.assertRaises(subprocess.TimeoutExpired):agent.close()

    def test_desktop_restore_error_preserves_completed_capture_and_records_issue(self):
        desktop=Mock()
        desktop.switch.side_effect=RuntimeError('Desktop no longer exists')
        desktop.current.return_value=1
        state=dict(status='completed',errors=[],evidenceGaps=[])
        batch.restore_workbuddy_operator_desktop(desktop,3,state)
        self.assertEqual(state['status'],'completed')
        self.assertEqual(state['operatorDesktopAfter'],1)
        self.assertIn('Desktop no longer exists',state['hostFinalizationIssues'][0])
        self.assertEqual(state['errors'],[])
        with self.assertRaises(RuntimeError):
            batch.restore_workbuddy_operator_desktop(desktop,3,None)


if __name__=='__main__':unittest.main()
