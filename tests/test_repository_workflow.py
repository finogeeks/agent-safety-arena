"""A clone can check local inputs and publish saved reports without a trial."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arena.cli import main


class RepositoryWorkflowTests(unittest.TestCase):
    def call(self, arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = main(arguments)
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def record(self, results, scenario='owned-windows', agent='dsh', identity='sample'):
        record = json.loads((ROOT / 'templates/reviewed-record.example.json').read_text('utf8'))
        record.update(scenarioId=scenario, agentId=agent)
        for group in record['groups'].values():
            if group:
                group['conditions']['agentId'] = agent
        record['publicMedia'] = []
        path = results / scenario / agent / identity / 'record.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf8')
        return path, record

    def test_offline_doctor_does_not_execute_products(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No product process')):
            code, output = self.call(['doctor', '--root', str(ROOT)])
        self.assertEqual(code, 0, output)
        result = json.loads(output)
        self.assertTrue(result['ok'])
        self.assertFalse(result['trialReady'])
        self.assertEqual(result['trialExecutions'], 0)

    def test_doctor_lists_missing_finshield_inputs_without_touching_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / 'profile.json'
            data = json.loads((ROOT / 'profiles/recording/windows-native-pro.json').read_text('utf8'))
            for key in ('node', 'dshEntry', 'chrome', 'ffmpeg', 'desktopTool',
                        'finshield', 'finshieldConfig', 'dshDesktop', 'workspaceRoot'):
                data[key] = str(Path(folder) / ('missing-' + key))
            data['screenRegion'] = [0, 0, 0, 1080]
            profile.write_text(json.dumps(data), encoding='utf8')
            before = profile.read_bytes()
            with patch('subprocess.Popen', side_effect=AssertionError('No product process')):
                code, output = self.call(['doctor', '--root', str(ROOT), '--profile', str(profile),
                                          '--environment', 'finshield'])
            self.assertEqual(code, 2, output)
            result = json.loads(output)
            failed = {row['name'] for row in result['checks'] if row['status'] == 'fail'}
            self.assertTrue({'finshield', 'finshieldConfig', 'dshDesktop', 'workspaceRoot',
                             'screenRegion', 'node', 'dshEntry'}.issubset(failed))
            self.assertEqual(before, profile.read_bytes())

    def test_builds_all_comparisons_without_raw_runs_or_processes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            first, _ = self.record(results)
            self.record(results, agent='codex', identity='second')
            replay = results / 'old-case/reference-agent/replay/result.json'
            replay.parent.mkdir(parents=True); replay.write_text('{}')
            (first.parent / 'private-notes.txt').write_text('not public')
            with patch('subprocess.Popen', side_effect=AssertionError('No model or product')):
                code, output = self.call(['build-site', '--results', str(results), '--output', str(site)])
            self.assertEqual(code, 0, output)
            self.assertTrue((site / 'owned-windows/dsh/sample/en.html').is_file())
            self.assertTrue((site / 'owned-windows/codex/second/zh-CN.html').is_file())
            self.assertFalse(list(site.rglob('private-notes.txt')))
            index = (site / 'index.html').read_text('utf8')
            self.assertIn('owned-windows/dsh/sample/zh-CN.html', index)
            self.assertNotIn('href="/', index)
            manifest = json.loads((site / 'site-manifest.json').read_text('utf8'))
            self.assertEqual(manifest['trialExecutions'], 0)
            self.assertEqual(manifest['excludedReplayResults'], ['old-case/reference-agent/replay/result.json'])
            source = first.relative_to(results).as_posix()
            self.assertEqual(manifest['sources'][source], hashlib.sha256(first.read_bytes()).hexdigest())
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((site / name).read_bytes()).hexdigest(), digest)

    def test_checks_explicit_case_locks_and_accepts_non_executable_dsh_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = json.loads((ROOT / 'profiles/recording/windows-native-pro.json').read_text('utf8'))
            for key in ('node', 'chrome', 'ffmpeg', 'desktopTool', 'finshield', 'dshDesktop'):
                path = root / ('finsafe.exe' if key == 'finshield' else key + '.exe')
                path.write_bytes(b'controlled installed fixture')
                data[key] = str(path)
            script = root / 'bin.js'; script.write_text('// controlled fixture')
            config = root / 'effective.yaml'; config.write_text('controlled: fixture')
            data.update(dshEntry=str(script), finshieldConfig=str(config), workspaceRoot=str(root),
                        screenRegion=[0, 0, 1920, 1080])
            profile = root / 'profile.json'; profile.write_text(json.dumps(data))
            for version, content, expected in [('fixture-a', b'controlled installed fixture', 0),
                                               ('fixture-b', b'a different build', 2)]:
                lock = root / (version + '.json')
                lock.write_text(json.dumps(dict(schemaVersion=1, product='FinShield', version=version,
                    runtimeFiles={'finsafe.exe': hashlib.sha256(content).hexdigest()})))
                with patch.dict('os.environ', {'PATHEXT': '.EXE;.COM'}), patch(
                        'arena.setup.sys.platform', 'win32'), patch(
                        'subprocess.Popen', side_effect=AssertionError('No product process')):
                    code, output = self.call(['doctor', '--root', str(ROOT), '--profile', str(profile),
                        '--environment', 'finshield', '--lock', str(lock)])
                self.assertEqual(code, expected, output)
                checks = {item['name']: item['status'] for item in json.loads(output)['checks']}
                self.assertEqual(checks['dshEntry'], 'pass')
                self.assertEqual(checks['finshield-runtime:finsafe.exe'], 'pass' if expected == 0 else 'fail')
            alternate = root / 'other-launcher.exe'; alternate.write_bytes(b'different launcher')
            data['finshield'] = str(alternate); profile.write_text(json.dumps(data))
            with patch('arena.setup.sys.platform', 'win32'):
                code, output = self.call(['doctor', '--root', str(ROOT), '--profile', str(profile),
                    '--environment', 'finshield', '--lock', str(root / 'fixture-a.json')])
            self.assertEqual(code, 2, 'Check the configured launcher, not a different finsafe.exe next to it: ' + output)

    def test_rejects_invalid_records_and_missing_media_before_creating_site(self):
        for problem in ('identity', 'unreviewed', 'missing-media'):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); results = root / 'results'; site = root / 'site'
                path, record = self.record(results)
                if problem == 'identity':
                    record['agentId'] = 'other-agent'
                elif problem == 'unreviewed':
                    record['reviewStatus'] = 'unreviewed'
                else:
                    record['publicMedia'] = [dict(kind='image', path='media/missing.png', group='native',
                                                   caption={'en': 'Missing', 'zh-CN': '缺失'})]
                path.write_text(json.dumps(record), encoding='utf8')
                code, output = self.call(['build-site', '--results', str(results), '--output', str(site)])
                self.assertEqual(code, 2, output)
                self.assertFalse(site.exists())

    def test_rejects_existing_output_and_source_overlap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            site = root / 'site'; site.mkdir(); marker = site / 'keep.txt'; marker.write_text('keep')
            for output in (site, results / 'site', root):
                code, message = self.call(['build-site', '--results', str(results), '--output', str(output)])
                self.assertEqual(code, 2, message)
            self.assertEqual(marker.read_text(), 'keep')
            self.assertFalse((results / 'site').exists())

    def test_failed_export_keeps_partial_output_private_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            path, _ = self.record(results); before = path.read_bytes()
            with patch('arena.reporting.bilingual.export_reports', side_effect=OSError('controlled write failure')):
                code, output = self.call(['build-site', '--results', str(results), '--output', str(site)])
            self.assertEqual(code, 2, output)
            self.assertFalse(site.exists())
            self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
