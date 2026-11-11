"""Claude FinShield uses installed self-confine, not AppSeam app launch."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.adapters.agents.claude_terminal import (
    claude_confinement, finshield_cli_overrides, self_confine_wrap)
from arena.cli import parser
from arena.runner.batch import load_profile
from arena.setup import check_repository


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


class ClaudeFinShieldTests(unittest.TestCase):
    def test_collect_batch_selects_finshield_without_a_suite(self):
        parsed = parser().parse_args([
            'collect-batch', '--case', 'case.json', '--profile', 'profile.json',
            '--environment', 'finshield'])
        self.assertEqual(parsed.environment, 'finshield')

    def test_only_finshield_wraps_the_owned_cli(self):
        confinement = {'executable': 'C:/FinSafe/finsafe.exe', 'config': 'C:/FinSafe/effective.yaml'}
        wrapped = self_confine_wrap(confinement)
        self.assertEqual(wrapped, {
            'executable': 'C:/FinSafe/finsafe.exe',
            'args': ['self-confine', '--yaml-path', 'C:/FinSafe/effective.yaml',
                     '--stdio', 'inherit', '--integration-id', 'claude', '--']})
        self.assertNotIn('app', wrapped['args'])
        self.assertNotIn('launch', wrapped['args'])
        self.assertNotIn('--windows-desktop', wrapped['args'])
        self.assertIsNone(self_confine_wrap(None))

    def test_finshield_does_not_add_sandbox_or_skip_permission_flags(self):
        overrides = finshield_cli_overrides(
            {'executable': 'C:/FinSafe/finsafe.exe', 'config': 'C:/FinSafe/effective.yaml'})
        self.assertEqual(overrides, [])
        self.assertEqual(finshield_cli_overrides(None), [])

    def test_finshield_shares_powershell_shell_without_a_settings_cli_flag(self):
        from arena.adapters.agents.claude import powershell_shell_settings
        source = (ROOT / 'src/arena/adapters/agents/claude_ui.mjs').read_text(encoding='utf8')
        self.assertNotIn('--settings', source)
        native = powershell_shell_settings({})
        wrapped = powershell_shell_settings({})
        self.assertEqual(native, wrapped)
        self.assertEqual(native['defaultShell'], 'powershell')
        self.assertIn('Bash', native['permissions']['deny'])

    def test_missing_launch_files_fail_before_start(self):
        with self.assertRaises(ValueError):
            claude_confinement({'finshield': 'C:/absent/finsafe.exe',
                                'finshieldConfig': 'C:/absent/effective.yaml'})

    def test_claude_doctor_does_not_require_the_dsh_desktop_launcher(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            executable = folder / 'finsafe.exe'
            executable.write_bytes(b'synthetic executable')
            config = folder / 'effective.yaml'
            config.write_text('synthetic: true', encoding='utf8')
            workspace = folder / 'workspaces'
            workspace.mkdir()
            profile = folder / 'profile.json'
            profile.write_text(json.dumps(claude_profile(
                node=str(folder / 'missing-node'),
                launchModule=str(folder / 'missing-launch.mjs'),
                launchConfig=str(folder / 'missing-setup.json'),
                terminal=str(folder / 'missing-wt.exe'),
                ffmpeg=str(folder / 'missing-ffmpeg.exe'),
                desktopTool=str(folder / 'missing-desktop.exe'),
                workspaceRoot=str(workspace),
                finshield=str(executable),
                finshieldConfig=str(config))), encoding='utf8')
            checks = check_repository(ROOT, profile, 'finshield')['checks']
            names = {row['name']: row['status'] for row in checks}
            self.assertNotIn('dshDesktop', names)
            self.assertNotIn('claudeFinshield', names)
            self.assertEqual(names['finshield'], 'pass')
            self.assertEqual(names['finshieldConfig'], 'pass')
            self.assertEqual(names['workspaceRoot'], 'pass')

    def test_ui_wrapper_applies_the_self_confine_prefix(self):
        source = (ROOT / 'src/arena/adapters/agents/claude_ui.mjs').read_text(encoding='utf8')
        self.assertIn('spec.confinement', source)
        self.assertIn('confinement.args', source)
        self.assertIn('confinement.executable', source)
        self.assertNotIn('dangerously-skip-permissions', source)

    def test_runtime_wraps_only_the_finshield_environment(self):
        from unittest.mock import MagicMock, patch
        from arena.runner.batch import ClaudeRuntime
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launch = root / 'launch.mjs'
            launch.write_text('export {}\n', encoding='utf8')
            setup = root / 'setup.json'
            setup.write_text('{}', encoding='utf8')
            executable = root / 'finsafe.exe'
            executable.write_bytes(b'fixture')
            config = root / 'effective.yaml'
            config.write_text('fixture: true', encoding='utf8')
            workspace = root / 'workspaces'
            workspace.mkdir()
            profile = claude_profile(
                node='node', launchModule=str(launch), launchConfig=str(setup),
                workspaceRoot=str(workspace), finshield=str(executable),
                finshieldConfig=str(config))
            captured = {}

            def fake_run(config, **kwargs):
                captured['environment_adapter'] = config.get('environment_adapter')
                run_dir = root / 'run'
                run_dir.mkdir(exist_ok=True)
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
                 patch('arena.adapters.agents.claude_terminal.ClaudeTerminalAgent') as agent_cls, \
                 patch('arena.evidence.recording.DesktopRecorder'), \
                 patch('arena.runner.batch.run_trial', side_effect=fake_run):
                ClaudeRuntime(profile).collect(dict(prompt='x', environment_adapter='finshield'))
                self.assertEqual(Path(agent_cls.call_args.kwargs['confinement']['executable']).name, 'finsafe.exe')
                agent_cls.reset_mock()
                ClaudeRuntime(profile).collect(dict(prompt='x'))
                self.assertIsNone(agent_cls.call_args.kwargs.get('confinement'))


if __name__ == '__main__':
    unittest.main()
