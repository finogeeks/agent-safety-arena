"""Session-only directory rules and real transcript execution counting."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from arena.adapters.agents.claude import ClaudeEventStream
from arena.adapters.agents.claude import session_cli_arguments, validate_session_settings
from arena.adapters.agents.claude_terminal import ClaudeTerminalAgent
from arena.runner.trial import execution_budget


class ClaudeDataSession(unittest.TestCase):
    def test_prompt_retry_cases_do_not_enable_recorder_tool_budget(self):
        from arena.runner.batch import load_case,prepare_case
        suite=json.loads((ROOT/'profiles/suites/data-safety-prompt-retries.json').read_text())
        self.assertEqual(len(suite['cases']),8)
        with tempfile.TemporaryDirectory() as folder:
            for relative in suite['cases']:
                case,path=load_case(ROOT/relative)
                self.assertNotIn('maxToolExecutions',case['resource'])
                config,_,_=prepare_case(case,path,Path(folder))
                self.assertNotIn('max_tool_executions',config)
                text=(path.parent/case['prompt']).read_text()
                self.assertIn('retry no more than THREE times',text)

    def test_captured_setup_choice_resolves_even_after_agent_end_turn(self):
        agent=ClaudeTerminalAgent({},MagicMock())
        agent.stream.pending['setup']=dict(toolName='setup',command='context setup')
        agent.awaiting_decision=True
        agent.transcript_rows=lambda:[dict(type='assistant',message=dict(stop_reason='end_turn',content=[]))]
        agent.sync_approval('Claude Code ready')
        self.assertFalse(agent.stream.pending)
        self.assertEqual(agent.stream.events[-1]['type'],'approval/decided')

    def test_only_hash_verified_permission_rules_are_passed_as_session_arguments(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json';path.write_text(json.dumps({'permissions':{'deny':['Bash','Edit(//c/lab/ro/**)']}}))
            report=dict(status='session-settings-ready',sessionSettings=str(path),files={str(path):hashlib.sha256(path.read_bytes()).hexdigest()})
            self.assertEqual(session_cli_arguments(report),['--settings',str(path.resolve())])
            self.assertEqual(session_cli_arguments(),[])
            path.write_text(json.dumps({'permissions':{'defaultMode':'bypassPermissions'}}))
            with self.assertRaises(ValueError):session_cli_arguments(report)
            with self.assertRaises(ValueError):validate_session_settings(path)

    def test_tool_use_and_result_ids_drive_shared_budget_once(self):
        stream=ClaudeEventStream();stream.request_id='request';stream.emit('user/message',source={'rpcId':'request'})
        rows=[]
        for i in range(3):
            rows += [dict(type='assistant',message=dict(content=[dict(type='tool_use',id=str(i),name='PowerShell',input={'command':'owned operation'})])),
                     dict(type='user',message=dict(content=[dict(type='tool_result',tool_use_id=str(i),content='original result')]))]
        stream.ingest_tools(rows);stream.ingest_tools(rows)
        receipt=execution_budget(stream.events,'request',3)
        self.assertEqual((receipt['started'],receipt['returned']),(3,3))
        self.assertIn('original result',json.dumps(stream.events))

    def test_old_same_workspace_transcript_cannot_complete_current_request(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);home=root/'home';workspace=root/'lab';encoded=str(workspace).replace('\\','-').replace('/','-').replace(':','-')
            project=home/'projects'/encoded;project.mkdir(parents=True)
            old=project/'old.jsonl';old.write_text(json.dumps(dict(type='assistant',message=dict(stop_reason='end_turn',content=[])))+'\n')
            agent=ClaudeTerminalAgent({},MagicMock());agent.directory=root;agent.workspace=workspace;agent.claude_home=home
            agent._existing_transcripts={old};agent.stream.prompt='new request'
            self.assertEqual(agent.transcript_rows(),[])
            current=project/'new.jsonl';rows=[dict(type='user',message=dict(content='new request')),dict(type='assistant',message=dict(stop_reason='tool_use',content=[]))]
            current.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
            self.assertEqual(agent.transcript_rows(),rows)

    def test_session_preparation_uses_absolute_rules_without_project_mutation(self):
        spec=importlib.util.spec_from_file_location('session_native',ROOT/'scripts/native_data_setup.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);lab=root/'lab';state=root/'state';home=root/'home';home.mkdir();(home/'settings.json').write_text(json.dumps({'permissions':{'deny':['Bash']},'defaultShell':'powershell'}))
            launch=root/'launch.json';launch.write_text(json.dumps(dict(claudeHome=str(home))))
            report=native.prepare_claude_session(dict(labRoot=str(lab),stateRoot=str(state),_path=str(root/'setup.json')),dict(launchConfig=str(launch)))
            self.assertEqual(report['status'],'session-settings-ready')
            self.assertFalse((lab/'.claude/settings.local.json').exists())
            settings=json.loads(Path(report['sessionSettings']).read_text());self.assertEqual(set(settings),{'permissions'})
            self.assertEqual(len(settings['permissions']['deny']),7)
            self.assertTrue(all(rule=='Bash' or '(//' in rule for rule in settings['permissions']['deny']))


if __name__=='__main__':unittest.main()
