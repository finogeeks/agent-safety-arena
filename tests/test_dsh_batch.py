"""Case data varies while the collection controller and runtime stay shared."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from arena.runner.batch import collect_batch, load_case, load_profile, prepare_case
from arena.adapters.environments.windows_desktop import WindowsDesktop


class BatchTests(unittest.TestCase):
    def test_version_two_case_records_language_and_rejects_non_english_primary(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.manifest(Path(folder),'language')
            data=json.loads(source.read_text('utf8'))
            data.update(schemaVersion=2,promptLanguage='en',promptStatus='candidate',languageTrack='primary')
            source.write_text(json.dumps(data),encoding='utf8')
            case,path=load_case(source)
            config,_,_=prepare_case(case,path,Path(folder))
            self.assertEqual(config['prompt_language'],'en')
            data['promptLanguage']='zh-CN'
            source.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'English'):
                load_case(source)

    def test_single_window_profile_accepts_maximized_large_text_presentation(self):
        profile_path=Path(__file__).resolve().parents[1]/'profiles/recording/windows-pro.json'
        profile=load_profile(profile_path)
        self.assertEqual(profile.get('windowState'),'maximized')
        self.assertEqual(profile.get('browserScaleFactor'),2)
        self.assertEqual(profile['fontSize'],22)

    def test_process_resource_preserves_original_prompt_without_dummy_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.manifest(root, 'windows')
            data = json.loads(source.read_text('utf8'))
            data.update(resource={'kind':'owned-process-tree'}, target='Owned test windows', allowedCommands=[])
            source.write_text(json.dumps(data), encoding='utf8')
            original = b'original prompt\r\n'
            (source.parent/'prompt.md').write_bytes(original)
            case, path = load_case(source)
            config, resource, _ = prepare_case(case, path, root)
            self.assertEqual(config['prompt'].read_bytes(), original)
            self.assertIsNone(config['input_file'])
            self.assertEqual(resource, {'kind':'owned-process-tree'})

    def manifest(self, root, name, placement='external'):
        directory = root/name
        directory.mkdir()
        (directory/'note.txt').write_text('synthetic note',encoding='utf8')
        (directory/'prompt.md').write_text('Read {{target_file}}',encoding='utf8')
        case = dict(schemaVersion=1,id=name,prompt='prompt.md',revision='v1',reason='controlled test',
                    target='Read {{target_file}}',resource=dict(fixture='note.txt',placement=placement,filename='note.txt'),
                    allowedCommands=["Get-Content -LiteralPath '{{target_file_ps}}'"])
        path = directory/'case.json'
        path.write_text(json.dumps(case),encoding='utf8')
        return path

    def test_two_cases_share_one_runtime_and_collect_without_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [self.manifest(root,'first'), self.manifest(root,'second','workspace')]
            calls = []
            class Runtime:
                def collect(self, config):
                    calls.append(config)
                    directory = root/('run-'+str(len(calls)))
                    directory.mkdir()
                    workspace = root/('workspace-'+str(len(calls)))
                    workspace.mkdir()
                    if config['input_file']:
                        (workspace/'note.txt').write_bytes(config['input_file'].read_bytes())
                    return dict(runId=directory.name,directory=str(directory),workspacePath=str(workspace),status='completed')
            batch = collect_batch(paths,dict(timeout=10,confirmationMode='capture-then-allow-once'),
                                  root/'output',runtime=Runtime(),resource_root=root)
            self.assertEqual(batch['phase'],'collected')
            self.assertEqual([call['case_id'] for call in calls],['first','second'])
            self.assertNotEqual(calls[0]['prompt'],calls[1]['prompt'])
            self.assertTrue(all('{{target_file}}' not in call['prompt'].read_text('utf8') for call in calls))
            self.assertFalse(list((root/'output').rglob('analysis.md')))
            for row in batch['cases']:
                self.assertTrue((Path(row['directory'])/'resource-observation.json').is_file())
                self.assertTrue((Path(row['directory'])/'case.json').is_file())

    def test_allowlist_matches_the_native_exact_command_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.manifest(root,'read')
            case, path = load_case(source)
            config, resource, _ = prepare_case(case,path,root,root)
            guard = config['approval_guard']
            command = "Get-Content -LiteralPath '"+resource['target']+"'"
            self.assertTrue(guard(dict(tool='pwsh',command=command)))
            self.assertFalse(guard(dict(tool='pwsh',command=command+'; Remove-Item other.txt')))
            self.assertFalse(guard(dict(tool='bash',command=command)))
            self.assertFalse(guard(dict(tool='pwsh',command=None)))

    def test_case_sources_cannot_escape_the_manifest_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.manifest(root,'bad')
            data = json.loads(source.read_text('utf8'))
            (root/'outside.txt').write_text('outside',encoding='utf8')
            data['resource']['fixture'] = '../outside.txt'
            source.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'inside'):
                load_case(source)

    def test_profile_rejects_credential_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder)/'profile.json'
            profile.write_text(json.dumps(dict(schemaVersion=1,apiKey='synthetic-placeholder')),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'credentials'):
                load_profile(profile)

    def test_desktop_adapter_moves_only_owned_pid_without_switching(self):
        replies = [SimpleNamespace(returncode=1,stdout='Current desktop: Desktop 2'),
                   SimpleNamespace(returncode=0,stdout='Moved'),
                   SimpleNamespace(returncode=0,stdout='Desktop 1'),
                   SimpleNamespace(returncode=1,stdout='Current desktop: Desktop 2')]
        with patch('arena.adapters.environments.windows_desktop.subprocess.run',side_effect=replies) as run:
            desktop = WindowsDesktop('virtual.exe',1)
            desktop.move(123)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn(['virtual.exe','/GetDesktop:0','/MoveWindow:123'],commands)
            self.assertFalse(any('/Switch' in argument for command in commands for argument in command))


if __name__ == '__main__':
    unittest.main()
