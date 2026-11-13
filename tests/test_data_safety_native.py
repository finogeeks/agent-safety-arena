"""Native recipes describe real product controls without claiming enforcement."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


class NativeDataPreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab, self.state = self.root/'lab', self.root/'host'
        self.lab.mkdir()
        self.config = dict(labRoot=str(self.lab), stateRoot=str(self.state))

    def module(self):
        source = ROOT/'scripts/native_data_setup.py'
        self.assertTrue(source.exists(), 'Per-product native preparation must be implemented')
        spec = importlib.util.spec_from_file_location('native_data_setup', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_codex_isolated_profile_drops_legacy_policy_and_copies_no_credentials(self):
        native = self.module()
        home = self.root/'codex'
        home.mkdir()
        (home/'config.toml').write_text('sandbox_mode="danger-full-access"\napproval_policy="never"\n[windows]\nsandbox="elevated"\n')
        (home/'model.config.toml').write_text('model="test"\nmodel_provider="deepseek"\n[model_providers.deepseek]\nname="DeepSeek"\nbase_url="https://api.deepseek.com"\nwire_api="responses"\nenv_key="DEEPSEEK_API_KEY"\nrequires_openai_auth=false\n')
        (home/'auth.json').write_text('DO NOT COPY THIS')
        launch = self.root/'launch.json'
        settings = {key:str(self.root/key) for key in native.LAUNCH_KEYS}
        settings.update(codexHome=str(home), codexProfile='model')
        launch.write_text(json.dumps(settings))
        result = native.prepare('codex', self.config, dict(launchConfig=str(launch),agent='codex-cli'))
        target = Path(result['codexHome'])
        parsed = tomllib.loads((target/'config.toml').read_text())
        self.assertNotIn('sandbox_mode', parsed)
        self.assertEqual(parsed['approval_policy'], 'on-request')
        permissions = parsed['permissions']['arena-data']['filesystem']
        self.assertEqual(permissions[str(self.lab).replace('\\','/')], 'write')
        self.assertEqual(permissions[str(self.lab/'na-ancestor/na-parent/no-access').replace('\\','/')], 'deny')
        self.assertFalse((target/'auth.json').exists())
        self.assertEqual(result['track'], 'configured-native')
        self.assertFalse(result['runtimeVerified'])
        settings['apiKey'] = 'must-not-be-copied'
        launch.write_text(json.dumps(settings))
        with self.assertRaisesRegex(ValueError, 'launcher'):
            native.prepare('codex', self.config, dict(launchConfig=str(launch)))

    def test_claude_merges_settings_and_restores_original_exact_bytes(self):
        native = self.module()
        target = self.lab/'.claude/settings.local.json'
        target.parent.mkdir()
        original = b'{"permissions":{"allow":["Read(./ordinary/**)"]},"someSetting":true}\n'
        target.write_bytes(original)
        result = native.prepare('claude', self.config)
        candidate = json.loads(Path(result['candidate']).read_text())
        self.assertTrue(candidate['someSetting'])
        self.assertEqual(candidate['permissions']['allow'], ['Read(./ordinary/**)'])
        deny = candidate['permissions']['deny']
        for name in ('Read', 'Edit'):
            self.assertIn(name+'(/na-ancestor/na-parent/no-access)', deny)
            self.assertIn(name+'(/na-ancestor/na-parent/no-access/**)', deny)
        self.assertIn('Edit(/ro-ancestor/ro-parent/read-only/**)', deny)
        self.assertFalse(any(value.startswith('Write(') for value in deny))
        self.assertEqual(target.read_bytes(), original, 'Preparation alone must not apply settings')
        native.apply_claude(self.config)
        self.assertEqual(json.loads(target.read_text()), candidate)
        target.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed'):
            native.restore_claude(self.config)
        target.write_bytes(Path(result['candidate']).read_bytes())
        native.restore_claude(self.config)
        self.assertEqual(target.read_bytes(), original)

    def test_workbuddy_and_dsh_do_not_claim_unsupported_settings_are_applied(self):
        native = self.module()
        workbuddy = native.prepare('workbuddy', self.config)
        dsh = native.prepare('dsh', self.config)
        self.assertEqual(workbuddy['status'], 'pending-installed-ui-verification')
        self.assertEqual(len(workbuddy['rules']), 3)
        self.assertEqual(workbuddy['rules'][2]['read'], 'deny')
        self.assertEqual(dsh['status'], 'unsupported-per-directory-zones')
        for result in (workbuddy, dsh):
            self.assertFalse(result['runtimeVerified'])
            self.assertFalse(result['applied'])
            self.assertTrue(result['sources'])
        for agent in ('codex','claude','workbuddy','dsh'):
            self.assertTrue((ROOT/f'scripts/prepare-{agent}-native.py').exists())


if __name__ == '__main__':
    unittest.main()
