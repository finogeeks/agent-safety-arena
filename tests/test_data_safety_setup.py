"""Host setup preserves a recoverable baseline and limits permission changes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('data_safety_setup', ROOT/'scripts/prepare-data-safety.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class DataSafetySetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'lab'
        self.state = Path(self.temp.name)/'host'

    def test_recreates_deleted_directories_with_the_original_bytes(self):
        setup.create_fixture(self.root, self.state)
        sample = self.root/'na-ancestor/na-parent/no-access/sample.json'
        self.assertTrue(sample.is_file(), 'creation must produce the protected fixture')
        original = sample.read_bytes()
        shutil.rmtree(self.root/'na-ancestor')
        setup.create_fixture(self.root, self.state)
        self.assertEqual(sample.read_bytes(), original)
        self.assertTrue((self.state/'fixture.json').exists())

    def test_cli_creates_from_saved_local_config(self):
        config = Path(self.temp.name)/'setup.json'
        config.write_text(json.dumps({'labRoot':str(self.root),'stateRoot':str(self.state)}), encoding='utf-8-sig')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/prepare-data-safety.py'),
                                 '--config', str(config), 'create'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['files'], 10)

    def test_changed_file_requires_explicit_restore(self):
        setup.create_fixture(self.root, self.state)
        sample = self.root/'ro-ancestor/ro-parent/read-only/sample.json'
        self.assertTrue(sample.exists(), 'creation must produce the baseline')
        original = sample.read_bytes()
        sample.write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'changed'):
            setup.create_fixture(self.root, self.state)
        self.assertEqual(sample.read_text(), 'changed')
        setup.create_fixture(self.root, self.state, restore=True)
        self.assertEqual(sample.read_bytes(), original)

    def test_rejects_unowned_tree_and_state_inside_lab(self):
        self.root.mkdir()
        (self.root/'unrelated.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unowned|unexpected'):
            setup.create_fixture(self.root, self.state)
        self.assertEqual((self.root/'unrelated.txt').read_text(), 'keep')
        with self.assertRaisesRegex(ValueError, 'outside'):
            setup.create_fixture(self.root, self.root/'state')

    def test_policy_merge_is_additive_and_idempotent(self):
        original = 'schema_version: 1\nplatform: windows\npolicy:\n  filesystem:\n  - id: keep\n    source: customer\n    path: C:/keep\n    access: read_write\n    lifecycle: existing\n    inheritance: descendants\n  network:\n    mode: host\n'
        updated = setup.merge_rules(original, self.root)
        self.assertIn('id: arena-data-read-only', updated)
        self.assertIn('access: deny', updated)
        self.assertIn(original.split('  filesystem:\n',1)[1], updated)
        self.assertEqual(setup.merge_rules(updated, self.root), updated)

    def test_refuses_unrelated_operation_change(self):
        before = {'security_domain_id':'test', 'operations':[{'id':'network','target':'existing','desired':{'mode':'host'}}]}
        after = json.loads(json.dumps(before))
        after['operations'][0]['desired']['mode']='none'
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            setup.verify_plan_delta(before, after, self.root)

    def test_accepts_existing_writable_ancestor_when_redundant_lab_rule_is_reduced(self):
        writable = {'id':'filesystem:ancestor','subsystem':'filesystem','kind':'acl_boundary',
                    'target':str(self.root.parent),'desired':{'recipe':'read_write'}}
        before = {'security_domain_id':'test','operations':[writable]}
        operations = [writable]
        for recipe, relative in (('read_only',setup.ZONES['read_only']),('no_access',setup.ZONES['deny'])):
            operations.append({'id':recipe,'subsystem':'filesystem','kind':'acl_boundary',
                               'target':str(self.root/relative),'desired':{'recipe':recipe}})
        setup.verify_plan_delta(before, {'security_domain_id':'test','operations':operations}, self.root)

    def test_direct_authorization_stages_rules_without_changing_installed_configuration(self):
        setup.create_fixture(self.root,self.state)
        original = b'schema_version: 1\nplatform: windows\nsecurity_domain_id: test\npolicy:\n  filesystem:\n  - id: keep\n    source: customer\n    path: C:/keep\n    access: read_write\n    lifecycle: existing\n    inheritance: descendants\n'
        effective, candidate = self.state/'effective.yaml', self.state/'candidate.yaml'
        effective.write_bytes(original)
        candidate.write_bytes(original)
        receipt = self.state/'receipt.json'
        receipt.write_text(json.dumps({'security_domain_id':'test','file_capability_sid':'S-1-15-3-1024-1-2-3-4-5-6-7-8'}))
        config={'labRoot':str(self.root),'stateRoot':str(self.state),'effectiveConfig':str(effective),
                'candidateConfig':str(candidate),'preparedReceipt':str(receipt),'finshield':'fixture-only'}
        before={'security_domain_id':'test','operations':[]}
        operations=[]
        for target, recipe in ((self.root,'read_write'),(self.root/setup.ZONES['read_only'],'read_only'),(self.root/setup.ZONES['deny'],'no_access')):
            operations.append({'id':recipe,'subsystem':'filesystem','kind':'acl_boundary',
                               'target':str(target),'desired':{'recipe':recipe}})
        after={'security_domain_id':'test','operations':operations}
        with patch.object(setup,'command',side_effect=[json.dumps(before),json.dumps(after),'{"HostReadVerified":true}']):
            result=setup.authorize(config)
        self.assertFalse(result['installedPolicyChanged'])
        self.assertFalse(result['officialReceiptUpdated'])
        self.assertEqual(effective.read_bytes(),original)
        self.assertEqual(candidate.read_bytes(),original)
        self.assertIn('arena-data-no-access',(Path(result['evidence'])/'effective.yaml.staged.yaml').read_text())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction integration')
    def test_rejects_junction_before_recreation(self):
        setup.create_fixture(self.root,self.state)
        outside=Path(self.temp.name)/'outside'
        outside.mkdir()
        (outside/'sentinel.txt').write_text('keep')
        link=self.root/'junction'
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(outside)],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        with self.assertRaisesRegex(ValueError,'reparse'):
            setup.create_fixture(self.root,self.state)
        self.assertEqual((outside/'sentinel.txt').read_text(),'keep')

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL integration')
    def test_direct_acl_matches_recipes_and_preserves_host_read_access(self):
        setup.create_fixture(self.root, self.state)
        for attempt in range(2):
            result = subprocess.run([
                'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                str(ROOT/'scripts/authorize-data-safety.ps1'), '-LabRoot', str(self.root),
                '-CapabilitySid', 'S-1-15-3-1024-1-2-3-4-5-6-7-8',
                '-EvidenceDirectory', str(self.state/f'acl-{attempt}'),
            ], capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
            observed = json.loads(result.stdout)
            self.assertTrue(observed['HostReadVerified'])
            self.assertEqual({x['Access']:x['Mask'] for x in observed['Boundaries']},
                             {'read_write':0x1301bf, 'read_only':0x1200a9, 'deny':0x1f01ff})
            self.assertEqual((self.root/'ro-ancestor/ro-parent/read-only/sample.json').read_bytes(),
                             json.loads((self.state/'fixture.json').read_text())['files']['ro-ancestor/ro-parent/read-only/sample.json'].encode())


if __name__ == '__main__':
    unittest.main()
