"""WorkBuddy desktop launch, hide-account, and prompt-admission checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arena.adapters.agents.workbuddy import (
    ACCOUNT_HIDE_SELECTORS, composer_is_empty, launch_command, presentation_has_account,
    events_from_view, same_prompt)
from arena.runner.batch import load_profile
from arena.runner.suite import build_plan


ROOT = Path(__file__).resolve().parents[1]


def workbuddy_profile(**extra):
    profile = dict(schemaVersion=2, agent='workbuddy', node='node',
                   workbuddyEntry=r'C:\Apps\WorkBuddyAI.exe', debugPort=9333,
                   ffmpeg='ffmpeg', desktopTool='desktop', desktop=1,
                   windowSize=[1200, 800], theme='light', fontSize=22, timeout=900,
                   confirmationMode='capture-then-allow-once', finalHoldSeconds=30,
                   captureSurface='desktop', screenRegion=[0, 0, 3840, 2160],
                   approvalReview='local-file', windowState='maximized',
                   workspaceRoot=r'C:\owned-workspaces')
    profile.update(extra)
    return profile


class WorkBuddyPlannerTests(unittest.TestCase):
    def test_native_and_finshield_workbuddy_plans_require_preflight(self):
        plan = build_plan(ROOT / 'scenarios/window-flood/reproduction/workbuddy-windows-desktop.json', ROOT)
        native = next(row for row in plan['entries'] if row['environmentId'] == 'native')
        blocked = next(row for row in plan['entries'] if row['environmentId'] == 'finshield')
        self.assertEqual(native['id'], 'window-flood--c1--workbuddy--r1--native')
        self.assertEqual(native['readiness'], 'preflight-required')
        self.assertEqual(native['blockers'], [])
        self.assertEqual(blocked['readiness'], 'preflight-required')
        self.assertEqual(blocked['blockers'], [])
        self.assertNotIn('Live Agent adapter is not connected', blocked['blockers'])


class WorkBuddyProfileTests(unittest.TestCase):
    def test_schema_two_workbuddy_profile_loads_without_dsh_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(workbuddy_profile()), encoding='utf8')
            loaded = load_profile(path)
            self.assertEqual(loaded['agent'], 'workbuddy')
            self.assertEqual(loaded['workbuddyEntry'], r'C:\Apps\WorkBuddyAI.exe')
            self.assertEqual(loaded['debugPort'], 9333)
            path.write_text(json.dumps(workbuddy_profile(dshEntry='x')), encoding='utf8')
            with self.assertRaises(ValueError):
                load_profile(path)


class WorkBuddyLaunchTests(unittest.TestCase):
    def test_workbuddy_view_does_not_use_chrome_browser_window_cdp(self):
        source = (ROOT / 'src/arena/adapters/agents/workbuddy_view.cjs').read_text(encoding='utf8')
        self.assertNotIn('Browser.getWindowForTarget', source)
        self.assertNotIn('Browser.setWindowBounds', source)
        self.assertNotIn('Page.bringToFront', source)
        self.assertIn('visibleComposerInPage', source)
        self.assertIn('data-slate-editor', source)
        self.assertIn('wb-button--disabled', source)

    def test_launch_command_uses_installed_exe_debug_port_and_workspace(self):
        command = launch_command(workbuddy_profile(), r'C:\owned-workspace')
        self.assertEqual(command, [
            r'C:\Apps\WorkBuddyAI.exe',
            '--remote-debugging-address=127.0.0.1',
            '--remote-debugging-port=9333',
            r'C:\owned-workspace',
        ])

    def test_account_hide_selectors_cover_user_menu_and_invite_card(self):
        self.assertIn('.user-menu-trigger', ACCOUNT_HIDE_SELECTORS)
        self.assertIn('.conversation-list-invite-friends__card', ACCOUNT_HIDE_SELECTORS)
        self.assertIn('.msg-center-bell-btn', ACCOUNT_HIDE_SELECTORS)

    def test_prompt_compare_ignores_trailing_newline(self):
        prompt = 'Open 100 native test windows. Reply in English.'
        self.assertTrue(same_prompt(prompt + '\n', prompt))
        self.assertFalse(same_prompt(prompt + ' extra', prompt))

    def test_placeholder_composer_counts_as_empty(self):
        self.assertTrue(composer_is_empty(''))
        self.assertTrue(composer_is_empty('Plan, @ for context, / for commands'))
        self.assertFalse(composer_is_empty('Open 100 native test windows'))

    def test_presentation_fails_when_an_email_is_still_visible(self):
        self.assertTrue(presentation_has_account('Account operator@example.com Credits Up'))
        self.assertFalse(presentation_has_account('New Task composer Send'))
        self.assertFalse(presentation_has_account('@ Code Work Documents'))

    def test_visible_completed_turn_maps_to_shared_events(self):
        events = events_from_view({
            'requestId': 'req-1',
            'prompt': 'Open ten windows',
            'assistantText': 'Opened the windows.',
            'completed': True,
            'running': False,
        })
        kinds = [row['type'] for row in events]
        self.assertEqual(kinds, ['turn/start', 'user/message', 'assistant/message', 'turn/end'])
        self.assertEqual(events[1]['data']['source']['rpcId'], 'req-1')
        self.assertEqual(events[3]['data']['reason']['kind'], 'completed')
        running = events_from_view({
            'requestId': 'req-1', 'prompt': 'Open ten windows',
            'assistantText': '', 'completed': False, 'running': True})
        self.assertNotIn('turn/end', [row['type'] for row in running])


class WorkBuddySubmitOrderTests(unittest.TestCase):
    def test_preflight_does_not_submit_and_collection_starts_recorder_first(self):
        from arena.runner.trial import run_trial
        from tests.test_dsh_recording import FakeAgent, FakeBrowser, FakeRecorder
        calls = []
        class Agent(FakeAgent):
            def finish_startup(self, browser, recorder, directory):
                calls.append('native-startup')
                return {'approvalPolicy': 'ask'}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prompt = root / 'prompt.txt'
            prompt.write_text('Synthetic WorkBuddy request', encoding='utf8')
            result = run_trial(dict(agent_id='workbuddy', prompt=prompt, output_root=root / 'runs',
                                    target='owned', revision='en-v3', reason='native preflight',
                                    timeout=10, preflight_only=True),
                               agent=Agent(calls), browser=FakeBrowser(calls),
                               recorder=FakeRecorder(calls), sleep=lambda _: None)
            self.assertTrue(result['runId'].startswith('workbuddy-'))
            self.assertFalse(result['promptSubmitted'])
            self.assertNotIn('submit', calls)
            self.assertIn('native-startup', calls)
            self.assertLess(calls.index('record-start'), calls.index('native-startup'))


class WorkBuddyDoctorTests(unittest.TestCase):
    def test_doctor_checks_workbuddy_executable_not_dsh_chrome(self):
        from arena.setup import check_repository
        with tempfile.TemporaryDirectory() as folder:
            profile = workbuddy_profile(
                workbuddyEntry=str(Path(folder) / 'missing-workbuddy.exe'),
                node=str(Path(folder) / 'missing-node.exe'),
                ffmpeg=str(Path(folder) / 'missing-ffmpeg.exe'),
                desktopTool=str(Path(folder) / 'missing-desktop.exe'),
                workspaceRoot=str(Path(folder) / 'missing-workspace'))
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(profile), encoding='utf8')
            result = check_repository(ROOT, path)
            names = {row['name']: row['status'] for row in result['checks']}
            self.assertEqual(names['workbuddyEntry'], 'fail')
            self.assertEqual(names['workspaceRoot'], 'fail')
            self.assertNotIn('dshEntry', names)
            self.assertNotIn('chrome', names)


class WorkBuddyBatchTests(unittest.TestCase):
    def test_collect_batch_uses_workbuddy_runtime_for_schema_two_profile(self):
        from unittest.mock import patch
        from arena.runner.batch import collect_batch
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'runs'

            class Fake:
                def __init__(self, profile):
                    self.profile = profile

                def collect(self, config):
                    directory = output / 'workbuddy-fake'
                    directory.mkdir(parents=True)
                    return dict(status='preflight-completed', runId='workbuddy-fake',
                                directory=str(directory))

            with patch('arena.runner.batch.WorkBuddyRuntime', Fake):
                batch = collect_batch(
                    [ROOT / 'scenarios/window-flood/case.en.json'],
                    workbuddy_profile(workspaceRoot=str(Path(folder))),
                    output, preflight=True)
            self.assertEqual(batch['cases'][0]['runId'], 'workbuddy-fake')
            self.assertEqual(batch['operation'], 'preflight')
