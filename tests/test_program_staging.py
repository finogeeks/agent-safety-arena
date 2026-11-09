"""Programs are staged as data; preparation must not execute their contents."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.runner.batch import load_case, prepare_case
from arena.runner.suite import build_plan
import test_evaluation_suite as fixtures


class ProgramStagingTests(unittest.TestCase):
    fixture = fixtures.SuiteTests.fixture

    def add_program(self, root):
        source = root/'case/case.json'
        case = json.loads(source.read_text('utf8'))
        program = root/'case/program.py'
        program.write_text("raise AssertionError('preparation must not execute this')\n",encoding='utf8')
        case['resource'].update(program='program.py', programFilename='program.py')
        source.write_text(json.dumps(case),encoding='utf8')
        return source, program

    def test_program_is_snapshotted_and_staged_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root);source,program=self.add_program(root)
            case,path=load_case(source)
            config,resource,setup=prepare_case(case,path,root)
            self.assertTrue(config['process_resource'])
            self.assertEqual(config['input_file'].name,'program.py')
            self.assertNotEqual(config['input_file'],program)
            self.assertEqual(config['input_file'].read_bytes(),program.read_bytes())
            self.assertEqual(resource['programSha256'],hashlib.sha256(program.read_bytes()).hexdigest())
            self.assertNotIn('side_script',config)

    def test_program_hash_changes_plan_and_resource_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);suite=self.fixture(root);source,program=self.add_program(root)
            before=build_plan(suite,root)
            program.write_text('# another fixed program\n',encoding='utf8')
            after=build_plan(suite,root)
            self.assertNotEqual(before['inputs']['case/program.py'],after['inputs']['case/program.py'])
            self.assertNotEqual(before['entries'][0]['conditions']['fixtureFingerprint'],after['entries'][0]['conditions']['fixtureFingerprint'])

    def test_observer_remains_separate_and_paths_are_constrained(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root);source,program=self.add_program(root)
            case=json.loads(source.read_text('utf8'))
            observer=source.parent/'observer.ps1';observer.write_text('# observer',encoding='utf8')
            case['resource'].update(script='observer.ps1',filename='observer.ps1')
            source.write_text(json.dumps(case),encoding='utf8')
            loaded,path=load_case(source)
            config,_,_=prepare_case(loaded,path,root)
            self.assertEqual(config['side_script'],observer)
            self.assertEqual(config['input_file'].name,'program.py')
            for relative,filename in [('../outside.py','outside.py'),('program.py','wrong.py'),('observer.ps1','observer.ps1')]:
                case['resource'].update(program=relative,programFilename=filename)
                source.write_text(json.dumps(case),encoding='utf8')
                with self.subTest(relative=relative),self.assertRaises(ValueError):load_case(source)


if __name__=='__main__':unittest.main()
