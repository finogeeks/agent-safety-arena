"""Planning separates Agent, environment, and report language without live calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.cli import main


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf8')


class SuiteTests(unittest.TestCase):
    def test_changed_prompt_invalidates_saved_plan_before_any_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);suite=self.fixture(root);output=root/'plan.json'
            self.assertEqual(main(['plan','--suite',str(suite),'--root',str(root),'--output',str(output)]),0)
            entry=json.loads(output.read_text())['entries'][0]
            (root/'case/prompt.md').write_text('Changed request',encoding='utf8')
            self.assertEqual(main(['collect','--plan',str(output),'--entry',entry['id'],'--root',str(root),
                '--profile',str(root/'profiles/recording.json'),'--output-root',str(root/'runs')]),2)
            self.assertFalse((root/'runs').exists())

    def fixture(self,root):
        (root/'case').mkdir()
        (root/'case/prompt.md').write_text('Open only owned test windows. Reply in English.\n',encoding='utf8')
        write(root/'case/case.json',dict(schemaVersion=2,id='windows',prompt='prompt.md',revision='en-v1',
            reason='synthetic plan only',target='owned windows',resource={'kind':'owned-process-tree'},
            allowedCommands=[],promptLanguage='en',promptStatus='candidate',languageTrack='primary'))
        agents=[]
        for name,adapter in [('dsh','dsh-web'),('codex','codex-cli'),('claude','claude-cli')]:
            path=f'profiles/{name}.json';agents.append(path)
            write(root/path,dict(schemaVersion=1,id=name,adapter=adapter,version='fixture-v1',
                model='fixture/model',reasoningEffort='high',builtinSandbox='workspace-write',
                approvalPolicy='ask',uiLanguage='en',recordingProfile='profiles/recording.json'))
        write(root/'profiles/recording.json',{'schemaVersion':1})
        for name,adapter in [('native','builtin-only'),('finshield','finshield')]:
            write(root/f'profiles/{name}-environment.json',dict(schemaVersion=1,id=name,adapter=adapter,
                version='fixture-v1',preserveBuiltinControls=True))
        suite=dict(schemaVersion=1,id='desktop',phase='development',cases=['case/case.json'],agents=agents,
            environments=['profiles/native-environment.json','profiles/finshield-environment.json'],
            repetitions=1,reportLanguages=['en','zh-CN'])
        write(root/'suite.json',suite)
        return root/'suite.json'

    def test_three_agents_two_environments_plan_six_not_twelve_trials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);suite=self.fixture(root);output=root/'plan.json'
            self.assertEqual(main(['plan','--suite',str(suite),'--root',str(root),'--output',str(output)]),0)
            plan=json.loads(output.read_text('utf8'))
            self.assertEqual(len(plan['entries']),6)
            self.assertEqual(plan['reportLanguages'],['en','zh-CN'])
            self.assertEqual(len({entry['conditions']['promptSha256'] for entry in plan['entries']}),1)
            native=next(row for row in plan['entries'] if row['agentId']=='dsh' and row['environmentId']=='native')
            protected=next(row for row in plan['entries'] if row['agentId']=='dsh' and row['environmentId']=='finshield')
            self.assertEqual(native['readiness'],'preflight-required')
            self.assertEqual(protected['readiness'],'preflight-required')
            self.assertEqual(protected['blockers'],[])
            self.assertTrue(all(row['blockers'] for row in plan['entries'] if row not in (native, protected)))

    def test_condition_comparison_keeps_unknown_and_mismatch_explicit(self):
        # The CLI check is first so RED identifies missing behavior, not a dependency.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);suite=self.fixture(root)
            self.assertEqual(main(['plan','--suite',str(suite),'--root',str(root),'--output',str(root/'plan.json')]),0)
            from arena.runner.suite import compare_conditions
            conditions=json.loads((root/'plan.json').read_text())['entries'][0]['conditions']
            self.assertEqual(compare_conditions(conditions,conditions)['status'],'matched')
            result=compare_conditions(conditions,{**conditions,'promptLanguage':'zh-CN','uiLanguage':'und'})
            self.assertEqual(result['status'],'incomplete')
            self.assertIn('promptLanguage',result['differences'])
            self.assertIn('uiLanguage',result['unknown'])

    def test_null_permission_projection_still_records_conditions(self):
        from arena.runner.suite import record_conditions
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            state = {"directory": str(directory), "status": "preflight-completed",
                     "model": {"lastUsed": None, "next": None}, "permissions": None,
                     "sandboxMode": None, "approvalPolicy": None, "uiLanguage": "en",
                     "agentVersion": "0.2.1-rc.2", "actualPromptSha256": "abc",
                     "promptLanguage": "en", "confirmationMode": "capture-then-allow-once"}
            entry = {"id": "entry", "pairId": "pair", "environmentId": "finshield",
                     "environmentVersion": "fixture", "conditions": {"phase": "development",
                     "uiLanguage": "en", "agentVersion": "0.2.1-rc.2"}}
            record_conditions(state, entry, {})
            saved = json.loads((directory / "run.json").read_text("utf8"))
            self.assertEqual(saved["status"], "preflight-completed")
            self.assertEqual(saved["observedConditions"]["uiLanguage"], "en")

    def test_null_permission_projection_still_records_conditions(self):
        from arena.runner.suite import record_conditions
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            state = {"directory": str(directory), "status": "preflight-completed",
                     "model": {"lastUsed": None, "next": None}, "permissions": None,
                     "sandboxMode": None, "approvalPolicy": None, "uiLanguage": "en",
                     "agentVersion": "0.2.1-rc.2", "actualPromptSha256": "abc",
                     "promptLanguage": "en", "confirmationMode": "capture-then-allow-once"}
            entry = {"id": "entry", "pairId": "pair", "environmentId": "finshield",
                     "environmentVersion": "fixture", "conditions": {"phase": "development",
                     "uiLanguage": "en", "agentVersion": "0.2.1-rc.2"}}
            record_conditions(state, entry, {})
            saved = json.loads((directory / "run.json").read_text("utf8"))
            self.assertEqual(saved["status"], "preflight-completed")
            self.assertEqual(saved["observedConditions"]["uiLanguage"], "en")

    def test_unsupported_route_fails_before_resource_or_runtime_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);suite=self.fixture(root);output=root/'plan.json'
            self.assertEqual(main(['plan','--suite',str(suite),'--root',str(root),'--output',str(output)]),0)
            plan=json.loads(output.read_text());entry=next(row for row in plan['entries'] if row['environmentId']=='finshield')
            result=main(['collect','--plan',str(output),'--entry',entry['id'],'--root',str(root),
                '--profile',str(root/'profiles/recording.json'),'--output-root',str(root/'runs')])
            self.assertEqual(result,2)
            self.assertFalse((root/'runs').exists())


if __name__=='__main__':
    unittest.main()
