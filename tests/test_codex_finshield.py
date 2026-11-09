"""Codex FinShield uses installed self-confine, not AppSeam app launch."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena.adapters.agents.codex_terminal import (
    codex_confinement, finshield_cli_overrides, self_confine_wrap)
from arena.cli import parser
from arena.runner.batch import load_profile
from arena.setup import check_repository


def codex_profile(**extra):
    profile = dict(schemaVersion=2, agent='codex-cli', node='node', launchModule='launcher.mjs',
                   launchConfig='setup.json', wsModule='ws', terminal='wt.exe', ffmpeg='ffmpeg',
                   desktopTool='desktop', desktop=1, windowSize=[1200, 800], theme='light',
                   fontSize=22, timeout=900, confirmationMode='capture-then-allow-once',
                   finalHoldSeconds=30, captureSurface='desktop', screenRegion=[0, 0, 3840, 2160],
                   approvalReview='local-file', windowState='maximized')
    profile.update(extra)
    return profile


class CodexFinShieldTests(unittest.TestCase):
    def test_collect_batch_selects_finshield_without_a_suite(self):
        help_text = parser().format_help()
        self.assertIn('collect-batch', help_text)
        parsed = parser().parse_args([
            'collect-batch', '--case', 'case.json', '--profile', 'profile.json',
            '--environment', 'finshield'])
        self.assertEqual(parsed.environment, 'finshield')
        native = parser().parse_args(['collect-batch', '--case', 'case.json', '--profile', 'profile.json'])
        self.assertEqual(native.environment, 'native')

    def test_codex_profile_accepts_installed_finshield_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(codex_profile(
                workspaceRoot=str(Path(folder)),
                finshield=str(Path(folder) / 'finsafe.exe'),
                finshieldConfig=str(Path(folder) / 'effective.yaml'))), encoding='utf8')
            loaded = load_profile(path)
            self.assertEqual(loaded['agent'], 'codex-cli')
            self.assertTrue(loaded['finshield'].endswith('finsafe.exe'))
            path.write_text(json.dumps(codex_profile(dshDesktop='DeepSeek Harness.exe')), encoding='utf8')
            with self.assertRaises(ValueError):
                load_profile(path)

    def test_only_finshield_wraps_the_owned_app_server(self):
        confinement = {'executable': 'C:/FinSafe/finsafe.exe', 'config': 'C:/FinSafe/effective.yaml'}
        wrapped = self_confine_wrap(confinement)
        self.assertEqual(wrapped, {
            'executable': 'C:/FinSafe/finsafe.exe',
            'args': ['self-confine', '--yaml-path', 'C:/FinSafe/effective.yaml',
                     '--stdio', 'inherit', '--integration-id', 'codex', '--']})
        self.assertNotIn('app', wrapped['args'])
        self.assertNotIn('launch', wrapped['args'])
        self.assertNotIn('--windows-desktop', wrapped['args'])
        self.assertIsNone(self_confine_wrap(None))

    def test_finshield_tui_turns_off_sandbox_without_skipping_approvals(self):
        overrides = finshield_cli_overrides(
            {'executable': 'C:/FinSafe/finsafe.exe', 'config': 'C:/FinSafe/effective.yaml'})
        self.assertEqual(overrides, ['--sandbox', 'danger-full-access'])
        joined = ' '.join(overrides)
        self.assertNotIn('dangerously-bypass-approvals-and-sandbox', joined)
        self.assertNotIn('--ask-for-approval', joined)
        self.assertEqual(finshield_cli_overrides(None), [])

    def test_missing_launch_files_fail_before_start(self):
        with self.assertRaises(ValueError):
            codex_confinement({'finshield': 'C:/absent/finsafe.exe',
                               'finshieldConfig': 'C:/absent/effective.yaml'})

    def test_codex_doctor_does_not_require_the_dsh_desktop_launcher(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            executable = folder / 'finsafe.exe'
            executable.write_bytes(b'synthetic executable')
            config = folder / 'effective.yaml'
            config.write_text('synthetic: true', encoding='utf8')
            workspace = folder / 'workspaces'
            workspace.mkdir()
            profile = folder / 'profile.json'
            profile.write_text(json.dumps(codex_profile(
                node=str(folder / 'missing-node'),
                launchModule=str(folder / 'missing-launch.mjs'),
                launchConfig=str(folder / 'missing-setup.json'),
                wsModule=str(folder / 'missing-ws'),
                terminal=str(folder / 'missing-wt.exe'),
                ffmpeg=str(folder / 'missing-ffmpeg.exe'),
                desktopTool=str(folder / 'missing-desktop.exe'),
                workspaceRoot=str(workspace),
                finshield=str(executable),
                finshieldConfig=str(config))), encoding='utf8')
            checks = check_repository(root, profile, 'finshield')['checks']
            names = {row['name']: row['status'] for row in checks}
            self.assertNotIn('dshDesktop', names)
            self.assertEqual(names['finshield'], 'pass')
            self.assertEqual(names['finshieldConfig'], 'pass')
            self.assertEqual(names['workspaceRoot'], 'pass')

    def test_observation_bridge_applies_the_self_confine_prefix(self):
        source = (Path(__file__).resolve().parents[1] / 'src/arena/adapters/agents/codex_wire.cjs').read_text(encoding='utf8')
        self.assertIn('config.confinement', source)
        self.assertIn('confinement.args', source)
        self.assertIn('confinement.executable', source)

    def test_runtime_wraps_only_the_finshield_environment(self):
        from unittest.mock import MagicMock, patch
        from arena.runner.batch import CodexRuntime
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
            profile = codex_profile(
                node='node', launchModule=str(launch), launchConfig=str(setup),
                workspaceRoot=str(workspace), finshield=str(executable),
                finshieldConfig=str(config))
            captured = {}

            def fake_run(config, **kwargs):
                captured['environment_adapter'] = config.get('environment_adapter')
                run_dir = root / 'run'
                run_dir.mkdir(exist_ok=True)
                return dict(status='preflight-completed', runId='codex-fake', directory=str(run_dir),
                            errors=[], evidenceGaps=[])

            desktop = MagicMock()
            desktop.current.return_value = 1
            desktop.number = 1
            job = MagicMock()
            job.close.return_value = dict(recovered=True, observerError=None)
            with patch('shutil.which', return_value='found'), \
                 patch('arena.adapters.environments.windows_desktop.WindowsDesktop', return_value=desktop), \
                 patch('arena.adapters.environments.windows_job.WindowsJob', return_value=job), \
                 patch('arena.adapters.agents.codex_terminal.NativeTerminalView'), \
                 patch('arena.adapters.agents.codex_terminal.CodexTerminalAgent') as agent_cls, \
                 patch('arena.evidence.recording.DesktopRecorder'), \
                 patch('arena.runner.batch.run_trial', side_effect=fake_run):
                CodexRuntime(profile).collect(dict(prompt='x', environment_adapter='finshield'))
                confinement = agent_cls.call_args.kwargs['confinement']
                self.assertEqual(Path(confinement['executable']).name, 'finsafe.exe')
                self.assertEqual(Path(confinement['config']).name, 'effective.yaml')
                agent_cls.reset_mock()
                CodexRuntime(profile).collect(dict(prompt='x'))
                self.assertIsNone(agent_cls.call_args.kwargs.get('confinement'))


if __name__ == '__main__':
    unittest.main()
