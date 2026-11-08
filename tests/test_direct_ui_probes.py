"""Diagnostic failures must not be promoted to successful protection results."""
import importlib
import unittest


class DirectUiProbeTests(unittest.TestCase):
    def api(self):
        try:
            return importlib.import_module('arena.diagnostics.ui_probe')
        except ModuleNotFoundError:
            self.fail('The direct preparation runner is not implemented')

    def test_failed_baseline_does_not_establish_a_block(self):
        self.assertEqual(self.api().judge({'ok':False}, {'ok':False}), 'unresolved')

    def test_launch_failure_does_not_establish_a_block(self):
        self.assertEqual(self.api().judge({'ok':True}, None), 'unresolved')

    def test_verified_denial_after_working_baseline_is_scoped(self):
        self.assertEqual(self.api().judge({'ok':True}, {'ok':False,'error':5}), 'denied')

    def test_success_without_the_required_observation_remains_unresolved(self):
        self.assertEqual(self.api().judge({'ok':True}, {'ok':True}, needs_observation=True), 'unresolved')
        self.assertEqual(self.api().judge({'ok':True}, {'ok':True}, observed=True, needs_observation=True), 'allowed')

    def test_finshield_keeps_the_default_desktop_and_ui_policy(self):
        command=self.api().finshield_command('finsafe.exe','effective.yaml','worker.exe','keyboard-hook','nonce','123')
        self.assertEqual(command[:5],['finsafe.exe','run','--yaml-path','effective.yaml','--json'])
        self.assertFalse(any(s.startswith('--windows-') for s in command))

    def test_prompts_require_a_successful_baseline_and_verified_denial(self):
        rows=[dict(case='keyboard-hook',native={'ok':True},job_ui='denied',finshield='denied'),
              dict(case='speaker-mute',native={'ok':False},job_ui='unresolved',finshield='unresolved')]
        self.assertEqual(self.api().prompt_cases(rows),['keyboard-hook'])

    def test_verified_postcondition_is_distinct_from_an_api_denial(self):
        failed=dict(ok=False,error=1400,postconditionVerified=True)
        self.assertEqual(self.api().judge({'ok':True},failed),'effect-prevented')
        self.assertEqual(self.api().judge({'ok':False},failed),'unresolved')
        self.assertEqual(self.api().judge({'ok':True},dict(ok=False,error=1400)),'unresolved')


if __name__=='__main__':unittest.main()
