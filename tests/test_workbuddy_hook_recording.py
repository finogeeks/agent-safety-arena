"""Native hook results, request matching, and safe launch checks."""
import sys
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.adapters.agents import workbuddy
from arena.adapters.agents.dsh import completion_for


class NativeHookRecordingTests(unittest.TestCase):
    def output(self, **extra):
        return dict(sessionId='owned', requestId='req-1', status='running',
                    result=None, error=None, events=[], **extra)

    def test_native_public_reply_and_result_end_the_matching_request(self):
        out = self.output()
        out.update(status='finished', result={'stopReason': 'end_turn'}, events=[
            {'sessionId': 'owned', 'event': {'update': {
                'sessionUpdate': 'agent_thought_chunk', 'content': {'type': 'text', 'text': 'private reasoning'}}}},
            {'sessionId': 'owned', 'event': {'update': {
                'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': 'ARENA_HOOK_OK'}}}},
            {'sessionId': 'other', 'event': {'update': {
                'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': 'unrelated'}}}},
        ])
        events = workbuddy.events_from_hook(out, 'Synthetic input')
        self.assertEqual(completion_for(events, 'req-1')['text'], 'ARENA_HOOK_OK')
        self.assertIsNone(completion_for(events, 'other-request'))
        self.assertEqual(completion_for(events, 'req-1')['state'], 'completed')

    def test_idle_or_error_does_not_become_success(self):
        out = self.output()
        self.assertIsNone(completion_for(workbuddy.events_from_hook(out, 'Synthetic input'), 'req-1'))
        out.update(status='finished', result={'stopReason': 'refusal', '_meta': {'codebuddy.ai/errorMessage': 'Model unavailable'}})
        completion = completion_for(workbuddy.events_from_hook(out, 'Synthetic input'), 'req-1')
        self.assertEqual(completion['state'], 'error')
        self.assertIn('Model unavailable', str(completion['error']))

    def test_frontend_terminal_request_supplies_the_public_reply(self):
        out = self.output()
        out.update(status='finished', result={'nativeRequest': {
            'id': 'native-1', 'state': 'completed', 'userText': 'Synthetic input',
            'assistantText': 'Opened and closed only the test windows.'}})
        completion = completion_for(workbuddy.events_from_hook(out, 'Synthetic input'), 'req-1')
        self.assertEqual(completion['state'], 'completed')
        self.assertEqual(completion['text'], 'Opened and closed only the test windows.')

    def test_existing_app_is_not_killed_or_adopted(self):
        with patch.object(workbuddy, 'running_workbuddy_pids', return_value=[55]), \
             patch.object(workbuddy, 'debug_port_open', return_value={'Browser': 'Chrome/1'}), \
             patch.object(workbuddy.subprocess, 'run') as execute:
            with self.assertRaisesRegex(RuntimeError, 'Another WorkBuddy'):
                workbuddy.stop_owned_debug_instance(9333)
            execute.assert_not_called()

    def test_submit_and_observe_use_hooks(self):
        class View:
            def hook_submit(self, prompt, request_id):
                self.received = (prompt, request_id)
            def hook_output(self):
                return dict(sessionId='owned', requestId='req-1', status='finished',
                            events=[], result={'stopReason': 'end_turn'}, error=None)
        agent = workbuddy.WorkBuddyAgent({})
        agent.view = View()
        agent.submit('Synthetic input\n', 'req-1')
        self.assertEqual(agent.view.received, ('Synthetic input\n', 'req-1'))
        self.assertEqual(completion_for(agent.observe(), 'req-1')['state'], 'completed')

    def test_desktop_switch_pauses_capture_without_cancelling_the_agent(self):
        from unittest.mock import Mock
        desktop = Mock(number=1)
        desktop.current.side_effect = [2, 2, 1]
        recorder, agent = Mock(), Mock()
        agent.process.poll.return_value = None
        with tempfile.TemporaryDirectory() as folder:
            agent.directory = Path(folder)
            guard = workbuddy.WorkBuddyDesktopGuard(desktop, recorder, agent, sleep=lambda _: None)
            guard.check()
            self.assertEqual(recorder.set_paused.call_args_list, [unittest.mock.call(True), unittest.mock.call(False)])
            agent.cancel.assert_not_called()
            agent.close.assert_not_called()
            self.assertTrue((Path(folder)/'recording-interruptions.json').exists())
