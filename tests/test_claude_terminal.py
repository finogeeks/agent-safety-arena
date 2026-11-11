"""Claude native protocol and terminal matching, without a model call."""
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena.adapters.agents.dsh import completion_for
from arena.cli import parser
from arena.runner.batch import load_profile


ROOT = Path(__file__).resolve().parents[1]


def claude_profile(**extra):
    profile = dict(schemaVersion=2, agent='claude-cli', node='node', launchModule='launcher.mjs',
                   launchConfig='setup.json', terminal='wt.exe', ffmpeg='ffmpeg', desktopTool='desktop',
                   desktop=1, windowSize=[1200, 800], theme='light', fontSize=22, timeout=900,
                   confirmationMode='capture-then-allow-once', finalHoldSeconds=30,
                   captureSurface='desktop', screenRegion=[0, 0, 3840, 2160],
                   approvalReview='local-file', windowState='maximized')
    profile.update(extra)
    return profile


class ClaudeTerminalTests(unittest.TestCase):
    def test_profile_accepts_claude_cli_without_ws_module(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(claude_profile()), encoding='utf8')
            loaded = load_profile(path)
            self.assertEqual(loaded['agent'], 'claude-cli')
            self.assertNotIn('wsModule', loaded)
            path.write_text(json.dumps(claude_profile(wsModule='ws', workspaceRoot=str(Path(folder)))),
                            encoding='utf8')
            swapped = load_profile(path)
            self.assertEqual(swapped['agent'], 'claude-cli')
            self.assertEqual(swapped['wsModule'], 'ws')
            path.write_text(json.dumps(claude_profile(approvalPolicy='never')), encoding='utf8')
            with self.assertRaises(ValueError):
                load_profile(path)

    def test_collect_batch_selects_claude_runtime(self):
        from unittest.mock import patch
        from arena.runner.batch import collect_batch
        help_text = parser().format_help()
        self.assertIn('collect-batch', help_text)
        self.assertIn('Claude', help_text)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'runs'

            class Fake:
                def __init__(self, profile):
                    self.profile = profile

                def collect(self, config):
                    directory = output / 'claude-fake'
                    directory.mkdir(parents=True)
                    return dict(status='preflight-completed', runId='claude-fake',
                                directory=str(directory))

            with patch('arena.runner.batch.ClaudeRuntime', Fake):
                batch = collect_batch(
                    [ROOT / 'scenarios/window-flood/case.python-file-v2.json'],
                    claude_profile(), output, preflight=True)
            self.assertEqual(batch['cases'][0]['runId'], 'claude-fake')
            self.assertEqual(batch['operation'], 'preflight')

    def test_native_startup_is_recorded_before_any_prompt_and_uses_shared_preflight(self):
        from arena.runner.trial import run_trial
        from test_dsh_recording import FakeAgent, FakeBrowser, FakeRecorder
        calls = []

        class Agent(FakeAgent):
            def finish_startup(self, browser, recorder, directory):
                self.assertion = 'record-start' in calls and 'submit' not in calls
                calls.append('native-startup')
                return {'approvalPolicy': 'default'}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prompt = root / 'prompt.txt'
            prompt.write_text('Synthetic request')
            agent = Agent(calls)
            result = run_trial(dict(agent_id='claude', prompt=prompt, output_root=root / 'runs',
                                    target='owned', revision='v1', reason='native preflight',
                                    timeout=10, preflight_only=True),
                               agent=agent, browser=FakeBrowser(calls), recorder=FakeRecorder(calls),
                               sleep=lambda _: None)
            self.assertIn('native-startup', calls)
            self.assertTrue(agent.assertion)
            self.assertFalse(result['promptSubmitted'])
            self.assertTrue(result['runId'].startswith('claude-'))

    def test_claude_one_time_yes_uses_the_same_capture_checkpoint_controller(self):
        from arena.runner.trial import Confirmations
        from test_dsh_recording import FakeBrowser, FakeRecorder
        calls = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'confirmations').mkdir()
            now = [1]
            browser = FakeBrowser(calls)
            confirmation = Confirmations(root, browser, lambda: now[0], 0)
            confirmation.native([{'seq': 0, 'type': 'approval/asked', 'data': {
                'id': '42', 'toolName': 'Bash', 'command': 'python camera-capture.py',
                'source': 'Claude CLI native approval'}}])
            confirmation.capture({'dialogs': [{'key': '42', 'native': True, 'text': 'Original warning',
                                              'choices': ['1. Yes', "2. Yes, and don't ask again", '3. No'],
                                              'oneTimeChoice': '1. Yes'}]})
            now[0] = 6
            confirmation.auto_decide(FakeRecorder(calls), lambda _: None, lambda _: True)
            self.assertIn('choose-once', calls)
            self.assertLess(calls.index('record-panel'), calls.index('choose-once'))
            self.assertEqual(confirmation.items[0]['source'], 'Claude CLI native approval')
            self.assertEqual(confirmation.items[0]['command'], 'python camera-capture.py')

    def test_interactive_submit_uses_owned_window_paste_and_enter(self):
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent, ClaudeTerminalView
        submit = inspect.getsource(ClaudeTerminalAgent.submit)
        view = inspect.getsource(ClaudeTerminalView)
        self.assertIn('set_clipboard', submit)
        self.assertIn("press('ctrl', 'shift', 'v')", submit)
        self.assertIn("press('enter')", submit)
        self.assertNotIn("console('paste'", submit)
        self.assertNotIn("key='ctrl-enter'", submit)
        self.assertIn('def focus', view)
        self.assertIn('SetForegroundWindow', view)
        self.assertIn('ShowWindow(self.handle, 3)', view)
        self.assertNotIn('ShowWindow(self.handle, 9)', view)
        self.assertIn('def set_clipboard', view)
        self.assertIn('def press', view)

    def test_one_time_yes_uses_owned_window_enter(self):
        from arena.adapters.agents.claude_terminal import ClaudeTerminalView
        source = inspect.getsource(ClaudeTerminalView.choose_once)
        self.assertIn('focus', source)
        self.assertIn("press('enter')", source)
        self.assertNotIn("!= '1. Yes'", source)
        self.assertNotIn(r'1\.\s*Yes\s*$', source)

    def test_launch_source_uses_claude_without_app_server_or_policy_flags(self):
        source = (ROOT / 'src/arena/adapters/agents/claude_ui.mjs').read_text(encoding='utf8')
        self.assertIn("makeLaunch('claude'", source)
        self.assertNotIn('--remote', source)
        self.assertNotIn('app-server', source)
        self.assertNotIn('dangerously-skip-permissions', source)
        self.assertNotIn('permission-mode', source)
        self.assertNotIn('danger-full-access', source)

    def test_theme_onboarding_is_native_setup_not_a_ready_prompt(self):
        from arena.adapters.agents.claude_terminal import startup_kind
        screen = (
            "Let's get started.\n\nChoose the text style that looks best with your terminal\n"
            "To change this later, run /theme\n\n    Auto (match terminal)\n ❯ ✔ Dark mode\n"
            "    Light mode\n")
        self.assertEqual(startup_kind(screen), 'theme')
        self.assertEqual(startup_kind('Welcome to Claude Code v2.1.314\nPress Enter to continue…\n'), 'continue')
        self.assertEqual(startup_kind('Claude Code\n? for shortcuts\n'), 'ready')
        self.assertEqual(startup_kind('Do you trust the files in this folder?\nC:\\owned\n'
                                     '❯ 1. Yes, proceed\n'), 'trust')
        wrapped = (
            'Accessing workspace:\n\n C:\\owned\\arena-dsh-workspace-c41bbd09-b\n 3adabc7\n\n'
            'Quick safety check: Is this a project you created or one you trust?\n'
            '❯ No, exit\n  Yes, I trust this folder\n')
        self.assertEqual(startup_kind(wrapped), 'trust')
        from arena.adapters.agents.claude_terminal import is_idle
        idle_screen = 'Claude Code v2.1.314\ndeepseek-v4-pro\n❯\n  auto mode on (shift+tab to cycle)\n'
        self.assertTrue(is_idle(idle_screen))
        self.assertFalse(is_idle(idle_screen.replace('❯', 'esc to interrupt\n❯')))

    def test_approval_selects_first_numbered_option_like_codex_capture_then_allow(self):
        from arena.adapters.agents.claude import approval_panel
        from arena.runner.trial import Confirmations
        from test_dsh_recording import FakeBrowser, FakeRecorder
        proceed = (
            'Bash command\n\n  python camera-capture.py\n\nDo you want to proceed?\n'
            '❯ 1. Yes\n  2. Yes, and don\'t ask again for python camera-capture.py\n  3. No\n')
        pending = {'native-1': {'toolName': 'Bash', 'command': 'python camera-capture.py'}}
        panel = approval_panel(proceed, pending)
        self.assertEqual(panel['key'], 'native-1')
        self.assertEqual(panel['oneTimeChoice'], '1. Yes')
        self.assertIsNone(approval_panel(proceed, {**pending, 'native-2': pending['native-1']}))
        self.assertEqual(
            approval_panel(proceed.replace('python camera-capture.py', 'other.py'), pending)['oneTimeChoice'],
            '1. Yes')
        outside = (
            'Allow this read outside the working directories?\n'
            '❯ 1. Yes, and keep allowing any reads outside the working directories\n'
            '  2. No, and block reads outside the working directories from now on\n'
            '  3. No, and ask again next time\n'
            '  4. Yes, but ask again next time\n')
        kept = approval_panel(outside, {'native-2': {'toolName': 'Read', 'command': ''}})
        self.assertEqual(
            kept['oneTimeChoice'],
            '1. Yes, and keep allowing any reads outside the working directories')
        self.assertEqual(kept['choices'][0], kept['oneTimeChoice'])
        idle = 'Claude Code v2.1.314\ndeepseek-v4-pro\n❯\n  auto mode on (shift+tab to cycle)\n'
        self.assertIsNone(approval_panel(idle, pending))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'confirmations').mkdir()
            now = [1]
            calls = []
            confirmation = Confirmations(root, FakeBrowser(calls), lambda: now[0], 0)
            confirmation.native([{'seq': 0, 'type': 'approval/asked', 'data': {
                'id': '42', 'toolName': 'Read', 'command': '',
                'source': 'Claude CLI native approval'}}])
            confirmation.capture({'dialogs': [kept]})
            now[0] = 6
            confirmation.auto_decide(FakeRecorder(calls), lambda _: None, lambda _: True)
            self.assertIn('choose-once', calls)
            self.assertLess(calls.index('record-panel'), calls.index('choose-once'))

    def test_digit_key_selects_unhighlighted_first_numbered_option(self):
        from arena.adapters.agents.claude_terminal import HOST_KEYS, ClaudeTerminalView
        self.assertEqual(HOST_KEYS['1'], 0x31)
        source = inspect.getsource(ClaudeTerminalView.choose_once)
        self.assertIn("press('1')", source)

    def test_completed_reply_numbered_list_is_not_an_approval(self):
        from unittest.mock import MagicMock
        from arena.adapters.agents.claude import numbered_picker
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
        reply = (
            'Two ways to unblock:\n\n'
            '  1. Run it yourself in a normal (non-restricted) terminal, or\n'
            '  2. Type it here with the ! prefix so it runs in this session\'s terminal:\n'
            '? for shortcuts\n')
        self.assertIsNotNone(numbered_picker(reply))
        agent = ClaudeTerminalAgent(claude_profile(), MagicMock())
        agent.transcript_rows = lambda: [
            {'type': 'assistant', 'message': {'stop_reason': 'end_turn', 'content': []}}]
        agent.sync_approval(reply)
        self.assertEqual(agent.stream.pending, {})
        self.assertFalse(any(event['type'] == 'approval/asked' for event in agent.stream.events))
        during = ClaudeTerminalAgent(claude_profile(), MagicMock())
        during.transcript_rows = lambda: [
            {'type': 'assistant', 'message': {'stop_reason': 'tool_use', 'content': []}}]
        during.sync_approval(
            'Do you want to proceed?\n❯ 1. Yes\n  2. No\n')
        self.assertTrue(during.stream.pending)
        self.assertEqual(during.stream.events[-1]['type'], 'approval/asked')

    def test_approval_reads_this_command_requires_approval_panel(self):
        from arena.adapters.agents.claude import approval_panel, command_from_panel
        screen = (
            'Run the requested PowerShell command\n'
            'powershell.exe -NoProfile -Command "echo ARENA_PROMPT_OK"\n'
            'This command requires approval\n\n'
            'Do you want to proceed?\n'
            '❯ 1. Yes\n'
            '  2. Yes, and don’t ask again for: powershell.exe *\n'
            '  3. Yes, and switch to auto mode\n'
            '  4. No\n')
        tool, command = command_from_panel(screen)
        self.assertEqual(tool, 'PowerShell')
        self.assertEqual(command, 'powershell.exe -NoProfile -Command "echo ARENA_PROMPT_OK"')
        pending = {'native-1': {'toolName': tool, 'command': command}}
        panel = approval_panel(screen, pending)
        self.assertEqual(panel['oneTimeChoice'], '1. Yes')
        self.assertIn('switch to auto mode', panel['text'])

    def test_session_jsonl_end_turn_completes_like_codex_turn_completed(self):
        from arena.adapters.agents.claude import session_turn_complete
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
        rows = [
            {'type': 'user', 'message': {'content': 'Run camera-capture.py'}},
            {'type': 'assistant', 'message': {'stop_reason': 'tool_use',
             'content': [{'type': 'tool_use', 'name': 'Bash'}]}},
            {'type': 'assistant', 'message': {'stop_reason': 'end_turn',
             'content': [{'type': 'text', 'text': '152 frames, exit 0'}]}},
        ]
        self.assertFalse(session_turn_complete(rows[:2]))
        self.assertTrue(session_turn_complete(rows))
        source = inspect.getsource(ClaudeTerminalAgent.sync_completion)
        self.assertIn('session_turn_complete', source)
        self.assertNotIn('is_idle', source)
        observe = inspect.getsource(ClaudeTerminalAgent.observe)
        self.assertIn('sync_completion', observe)
        from arena.runner.batch import ClaudeRuntime
        collect = inspect.getsource(ClaudeRuntime.collect)
        self.assertNotIn('while desktop.current()', collect)

    def test_permission_mode_reads_auto_above_trailing_blanks(self):
        from unittest.mock import MagicMock
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
        agent = ClaudeTerminalAgent(claude_profile(), MagicMock())
        text = (
            'Claude Code v2.1.314\n'
            'deepseek-v4-pro[1m]\n'
            '❯\n'
            '  auto mode on (shift+tab to cycle) · high · /effort\n'
            '\n\n\n\n\n\n\n\n')
        self.assertEqual(agent.permission_mode(text), 'auto')
        self.assertEqual(agent.permission_mode('❯\nbypass permissions on\n\n\n'), 'bypass')
        self.assertEqual(agent.permission_mode('Claude Code\n❯\n'), 'default')

    def test_focus_retries_and_clicks_owned_window(self):
        from arena.adapters.agents.claude_terminal import ClaudeTerminalView
        source = inspect.getsource(ClaudeTerminalView.focus)
        self.assertIn('time.monotonic()', source)
        self.assertIn('SetCursorPos', source)
        self.assertIn('mouse_event', source)

    def test_transcript_rows_ignore_other_workspace_jsonl(self):
        from unittest.mock import MagicMock
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            home = root / 'claude-home'
            other = home / 'projects' / 'C--other-workspace'
            other.mkdir(parents=True)
            (other / 'old.jsonl').write_text(json.dumps({
                'type': 'assistant',
                'message': {'stop_reason': 'end_turn',
                            'content': [{'type': 'text', 'text': 'python .\\foreground-window.py'}]},
            }) + '\n', encoding='utf8')
            agent = ClaudeTerminalAgent(claude_profile(), MagicMock())
            agent.claude_home = home
            agent.workspace = root / 'arena-dsh-workspace-current'
            agent.directory = root
            rows = agent.transcript_rows()
            self.assertEqual(rows, [])
            observation = json.loads((root / 'claude-transcript-observation.json').read_text(encoding='utf8'))
            self.assertFalse(observation['complete'])
            self.assertEqual(observation['files'], [])
            own = home / 'projects' / (
                str(agent.workspace).replace('\\', '-').replace('/', '-').replace(':', '-'))
            own.mkdir(parents=True)
            (own / 'session.jsonl').write_text(json.dumps({
                'type': 'assistant',
                'message': {'stop_reason': 'end_turn',
                            'content': [{'type': 'text', 'text': 'camera-capture.py 147 frames'}]},
            }) + '\n', encoding='utf8')
            own_rows = agent.transcript_rows()
            self.assertEqual(own_rows[0]['message']['content'][0]['text'],
                             'camera-capture.py 147 frames')
            own_observation = json.loads((root / 'claude-transcript-observation.json').read_text(encoding='utf8'))
            self.assertTrue(own_observation['complete'])
            self.assertTrue(any('arena-dsh-workspace-current' in path
                                for path in own_observation['files']))
            self.assertFalse(any('other-workspace' in path for path in own_observation['files']))

    def test_completion_events_use_the_shared_turn_contract(self):
        from arena.adapters.agents.claude import ClaudeEventStream
        stream = ClaudeEventStream()
        stream.request_id = 'request-1'
        stream.emit('turn/start', turn='1')
        stream.emit('user/message', source={'rpcId': 'request-1'}, turn='1',
                    message={'content': [{'type': 'text', 'text': 'Hello'}]})
        stream.emit('assistant/message', turn='1',
                    message={'content': [{'type': 'text', 'text': 'Public reply'}]})
        stream.emit('turn/end', turn='1', reason={'kind': 'completed'})
        self.assertEqual(completion_for(stream.events, 'request-1')['text'], 'Public reply')
        self.assertIsNone(completion_for(stream.events, 'other-request'))

    def test_doctor_checks_claude_launch_files_not_ws_module_or_dsh_chrome(self):
        from arena.setup import check_repository
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / 'missing'
            profile = claude_profile(
                node=str(missing / 'node.exe'), launchModule=str(missing / 'launch.mjs'),
                launchConfig=str(missing / 'setup.json'), terminal=str(missing / 'wt.exe'),
                ffmpeg=str(missing / 'ffmpeg.exe'), desktopTool=str(missing / 'desktop.exe'),
                workspaceRoot=str(missing / 'workspaces'))
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(profile), encoding='utf8')
            result = check_repository(ROOT, path)
            names = {row['name']: row['status'] for row in result['checks']}
            self.assertEqual(names['launchModule'], 'fail')
            self.assertEqual(names['launchConfig'], 'fail')
            self.assertEqual(names['workspaceRoot'], 'fail')
            self.assertNotIn('wsModule', names)
            self.assertNotIn('dshEntry', names)
            self.assertNotIn('chrome', names)

    def test_claude_runtime_uses_profile_workspace_root(self):
        from unittest.mock import MagicMock, patch
        from arena.runner.batch import ClaudeRuntime
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launch = root / 'launch.mjs'
            launch.write_text('export {}\n', encoding='utf8')
            setup = root / 'setup.json'
            setup.write_text('{}', encoding='utf8')
            workspace = root / 'workspaces'
            workspace.mkdir()
            profile = claude_profile(node='node', launchModule=str(launch), launchConfig=str(setup),
                                     workspaceRoot=str(workspace))
            captured = {}

            def fake_run(config, **kwargs):
                captured['workspace_root'] = config.get('workspace_root')
                captured['agent_id'] = config.get('agent_id')
                run_dir = root / 'run'
                run_dir.mkdir()
                return dict(status='preflight-completed', runId='claude-fake', directory=str(run_dir),
                            errors=[], evidenceGaps=[])

            desktop = MagicMock()
            desktop.current.return_value = 1
            desktop.number = 1
            job = MagicMock()
            job.close.return_value = dict(recovered=True, observerError=None)
            with patch('shutil.which', return_value='found'), \
                 patch('arena.adapters.environments.windows_desktop.WindowsDesktop', return_value=desktop), \
                 patch('arena.adapters.environments.windows_job.WindowsJob', return_value=job), \
                 patch('arena.adapters.agents.claude_terminal.ClaudeTerminalView'), \
                 patch('arena.adapters.agents.claude_terminal.ClaudeTerminalAgent'), \
                 patch('arena.evidence.recording.DesktopRecorder'), \
                 patch('arena.runner.batch.run_trial', side_effect=fake_run):
                ClaudeRuntime(profile).collect(dict(prompt='x'))
            self.assertEqual(captured['workspace_root'], str(workspace.resolve()))
            self.assertEqual(captured['agent_id'], 'claude')

    def test_collect_batch_source_routes_claude_cli(self):
        from arena.runner.batch import collect_batch
        source = inspect.getsource(collect_batch)
        self.assertIn("claude-cli", source)
        self.assertIn('ClaudeRuntime', source)

    def test_powershell_shell_settings_enable_tool_deny_bash_and_keep_protection(self):
        from arena.adapters.agents.claude import apply_powershell_shell, powershell_shell_settings
        merged = powershell_shell_settings({'theme': 'auto', 'env': {'OTHER': '1'}})
        self.assertEqual(merged['theme'], 'auto')
        self.assertEqual(merged['env']['OTHER'], '1')
        self.assertEqual(merged['env']['CLAUDE_CODE_USE_POWERSHELL_TOOL'], '1')
        self.assertEqual(merged['defaultShell'], 'powershell')
        self.assertIn('Bash', merged['permissions']['deny'])
        blob = json.dumps(merged)
        self.assertNotIn('dangerously-skip-permissions', blob)
        self.assertNotIn('permission-mode', blob)
        self.assertNotIn('sandbox', blob.lower())
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / 'settings.json').write_text(json.dumps({'theme': 'auto'}), encoding='utf8')
            applied = apply_powershell_shell(home)
            saved = json.loads((home / 'settings.json').read_text(encoding='utf8'))
            self.assertEqual(saved, applied)
            self.assertEqual(saved['theme'], 'auto')
            self.assertEqual(saved['env']['CLAUDE_CODE_USE_POWERSHELL_TOOL'], '1')
            self.assertIn('Bash', saved['permissions']['deny'])
        from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
        self.assertIn('apply_powershell_shell', inspect.getsource(ClaudeTerminalAgent.prepare))
        self.assertIn('shellPolicy', inspect.getsource(ClaudeTerminalAgent.prepare))

    def test_launch_env_enables_powershell_and_drops_git_bash_path(self):
        from arena.adapters.agents.claude import apply_powershell_launch_env
        env = apply_powershell_launch_env({
            'CLAUDE_CODE_GIT_BASH_PATH': r'C:\Program Files\Git\bin\bash.exe',
            'PATH': r'C:\Program Files\Git\cmd;C:\Windows',
        })
        self.assertEqual(env['CLAUDE_CODE_USE_POWERSHELL_TOOL'], '1')
        self.assertNotIn('CLAUDE_CODE_GIT_BASH_PATH', env)
        self.assertIn('Git', env['PATH'])

    def test_ui_wrapper_applies_powershell_env(self):
        source = (ROOT / 'src/arena/adapters/agents/claude_ui.mjs').read_text(encoding='utf8')
        self.assertIn('CLAUDE_CODE_USE_POWERSHELL_TOOL', source)
        self.assertIn("CLAUDE_CODE_GIT_BASH_PATH", source)
        self.assertIn('delete launch.env.CLAUDE_CODE_GIT_BASH_PATH', source)
        self.assertNotIn('dangerously-skip-permissions', source)

    def test_execution_tool_names_distinguish_powershell_from_bash(self):
        from arena.adapters.agents.claude import (
            bash_startup_failure, execution_tool_names)
        rows = [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Read'},
                {'type': 'tool_use', 'name': 'PowerShell'}]}},
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Bash'}]}},
        ]
        self.assertEqual(execution_tool_names(rows), ['Read', 'PowerShell', 'Bash'])
        self.assertTrue(bash_startup_failure(
            'NtCreateDirectoryObject(\\BaseNamedObjects\\msys-2.0): 0xC0000022 STATUS_ACCESS_DENIED'))
        self.assertFalse(bash_startup_failure('summary status complete, camera Open'))

    def test_snapshot_survives_console_read_failure(self):
        from arena.adapters.agents.claude_terminal import ClaudeTerminalView

        class Stream:
            pending = {}
            events = []

        class Agent:
            stream = Stream()

            def observe(self):
                return []

        view = ClaudeTerminalView.__new__(ClaudeTerminalView)
        view.agent = Agent()
        view.title = 'Arena Claude CLI test'
        view.choices = []
        view.text = lambda: (_ for _ in ()).throw(
            RuntimeError('The native console observer failed: [WinError 87] 参数错误。'))
        shot = view.snapshot()
        self.assertEqual(shot['dialogs'], [])
        self.assertEqual(shot['terminalText'], '')
        self.assertEqual(shot['title'], 'Arena Claude CLI test')

    def test_console_coord_is_packed_as_win32_dword(self):
        from arena.adapters.agents.windows_console import pack_coord
        self.assertEqual(pack_coord(0, 0), 0)
        self.assertEqual(pack_coord(0, 12), 12 << 16)
        self.assertEqual(pack_coord(80, 24), (24 << 16) | 80)
        source = (ROOT / 'src/arena/adapters/agents/windows_console.py').read_text(encoding='utf8')
        self.assertIn('pack_coord(0,info.window.top)', source)
        self.assertIn('w.DWORD', source.split('ReadConsoleOutputCharacterW.argtypes')[1].split(']', 1)[0])


if __name__ == '__main__':
    unittest.main()
