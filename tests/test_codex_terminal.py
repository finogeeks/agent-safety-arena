"""Codex native protocol and terminal matching, without a model call."""
import json
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from arena.adapters.agents.codex import CodexEventStream, approval_panel, model_arguments
from arena.adapters.agents.dsh import completion_for

class CodexTerminalTests(unittest.TestCase):
    def test_generic_batch_route_accepts_native_terminal_presentation_without_policy_fields(self):
        from arena.cli import parser
        self.assertIn('collect-batch',parser().format_help())
        from arena.runner.batch import load_profile
        profile=dict(schemaVersion=2,agent='codex-cli',node='node',launchModule='launcher.mjs',
            launchConfig='setup.json',wsModule='ws',terminal='wt.exe',ffmpeg='ffmpeg',desktopTool='desktop',
            desktop=1,windowSize=[1200,800],theme='light',fontSize=22,timeout=900,
            confirmationMode='capture-then-allow-once',finalHoldSeconds=30,captureSurface='desktop',
            screenRegion=[0,0,3840,2160],approvalReview='local-file',windowState='maximized')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';path.write_text(json.dumps(profile))
            self.assertEqual(load_profile(path)['agent'],'codex-cli')
            path.write_text(json.dumps({**profile,'approvalDelaySeconds':5}))
            self.assertEqual(load_profile(path)['approvalDelaySeconds'],5)
            for invalid in (-1,61,True,'5',float('nan')):
                path.write_text(json.dumps({**profile,'approvalDelaySeconds':invalid}))
                with self.assertRaises(ValueError):load_profile(path)
            path.write_text(json.dumps({**profile,'approvalPolicy':'never'}))
            with self.assertRaises(ValueError):load_profile(path)
            path.write_text(json.dumps({**profile,'workspaceRoot':str(Path(folder))}))
            self.assertEqual(load_profile(path)['workspaceRoot'],str(Path(folder)))
            path.write_text(json.dumps({**profile,'finshield':'finsafe.exe','finshieldConfig':'effective.yaml'}))
            self.assertEqual(load_profile(path)['finshield'],'finsafe.exe')

    def test_native_startup_is_recorded_before_any_prompt_and_uses_shared_preflight(self):
        from arena.runner.trial import run_trial
        from test_dsh_recording import FakeAgent,FakeBrowser,FakeRecorder
        calls=[]
        class Agent(FakeAgent):
            def finish_startup(self,browser,recorder,directory):
                self.assertion='record-start' in calls and 'submit' not in calls
                calls.append('native-startup');return {'approvalPolicy':'on-request'}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('Synthetic request')
            agent=Agent(calls)
            result=run_trial(dict(agent_id='codex',prompt=prompt,output_root=root/'runs',target='owned',
                revision='v1',reason='native preflight',timeout=10,preflight_only=True),
                agent=agent,browser=FakeBrowser(calls),recorder=FakeRecorder(calls),sleep=lambda _:None)
            self.assertIn('native-startup',calls)
            self.assertTrue(agent.assertion)
            self.assertFalse(result['promptSubmitted'])
            self.assertTrue(result['runId'].startswith('codex-'))

    def test_codex_one_time_label_uses_the_same_capture_checkpoint_controller(self):
        from arena.runner.trial import Confirmations
        from test_dsh_recording import FakeBrowser,FakeRecorder
        calls=[]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'confirmations').mkdir()
            now=[1]
            browser=FakeBrowser(calls);confirmation=Confirmations(root,browser,lambda:now[0],0)
            confirmation.native([{'seq':0,'type':'approval/asked','data':{'id':'42','toolName':'exec_command',
                'command':'echo fixture','source':'Codex CLI native approval'}}])
            confirmation.capture({'dialogs':[{'key':'42','native':True,'text':'Original warning',
                'choices':['1. Yes, proceed (y)','2. No'],'oneTimeChoice':'1. Yes, proceed (y)'}]})
            now[0]=6
            confirmation.auto_decide(FakeRecorder(calls),lambda _:None,lambda _:True)
            self.assertIn('choose-once',calls)
            self.assertLess(calls.index('record-panel'),calls.index('choose-once'))
            self.assertEqual(confirmation.items[0]['source'],'Codex CLI native approval')
            self.assertEqual(confirmation.items[0]['command'],'echo fixture')

    def test_provider_configuration_cannot_change_native_policies(self):
        profile={'model':'deepseek-v4-pro','model_provider':'deepseek','model_providers':{'deepseek':{
            'name':'DeepSeek','base_url':'https://api.deepseek.com','wire_api':'responses',
            'env_key':'DEEPSEEK_API_KEY','requires_openai_auth':False}}}
        arguments=model_arguments(profile)
        self.assertIn('model="deepseek-v4-pro"',arguments)
        self.assertNotIn('sandbox_mode', ' '.join(arguments))
        self.assertEqual(arguments,model_arguments({**profile,'tui':{'screen_reader_detection_done':True}}))
        with self.assertRaises(ValueError):model_arguments({**profile,'sandbox_mode':'danger-full-access'})

    def test_native_protocol_retains_only_public_completion_and_exact_turn(self):
        stream=CodexEventStream();stream.request_id='request-1';stream.prompt='Hello\n'
        stream.feed('client',{'id':1,'method':'thread/start','params':{}})
        stream.feed('server',{'id':1,'result':{'model':'deepseek-v4-pro','modelProvider':'deepseek',
            'sandbox':{'type':'workspaceWrite'},'approvalPolicy':'on-request','reasoningEffort':'high',
            'thread':{'id':'thread-1'}}})
        stream.feed('client',{'id':2,'method':'turn/start','params':{'threadId':'thread-1','input':[{'type':'text','text':'Hello'}]}})
        stream.feed('server',{'method':'turn/started','params':{'threadId':'thread-1','turn':{'id':'turn-1'}}})
        stream.feed('server',{'method':'item/completed','params':{'threadId':'thread-1','turnId':'turn-1',
            'item':{'id':'r','type':'reasoning','text':'private reasoning'}}})
        stream.feed('server',{'method':'item/completed','params':{'threadId':'thread-1','turnId':'turn-1',
            'item':{'id':'m','type':'agentMessage','text':'Public reply'}}})
        stream.feed('server',{'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'completed'}}})
        self.assertEqual(completion_for(stream.events,'request-1')['text'],'Public reply')
        self.assertIsNone(completion_for(stream.events,'other-request'))
        self.assertNotIn('private reasoning',json.dumps(stream.events))
        self.assertEqual(stream.conditions['approvalPolicy'],'on-request')

    def test_approval_needs_one_pending_request_and_original_one_time_choice(self):
        screen='Would you like to run the following command?\n$ echo fixture\n\n  1. Yes, proceed (y)\n  2. Yes, and do not ask again (p)\n  3. No (esc)\n'
        pending={'native-1':{'method':'item/commandExecution/requestApproval','command':'echo fixture'}}
        panel=approval_panel(screen,pending)
        self.assertEqual(panel['key'],'native-1')
        self.assertEqual(panel['oneTimeChoice'],'1. Yes, proceed (y)')
        self.assertIn('do not ask again',panel['text'])
        self.assertIsNone(approval_panel(screen,{**pending,'native-2':pending['native-1']}))
        self.assertIsNone(approval_panel(screen.replace('Yes, proceed (y)','Yes, for this session'),pending))
        self.assertIsNone(approval_panel(screen.replace('echo fixture','different command'),pending))

    def test_native_long_command_panel_matches_its_unique_exact_reason(self):
        screen='Would you like to run the following command?\nEnvironment: local\nReason: Open only the controlled test windows?\n$ Add-Type ...\n[... 49 lines] ctrl+a view all\n› 1. Yes, proceed (y)\n  2. No, and tell Codex what to do differently (esc)\nPress enter to confirm or esc to cancel'
        pending={'0':{'method':'item/commandExecution/requestApproval','command':'long native command not fully displayed',
                      'reason':'Open only the controlled test windows?'}}
        panel=approval_panel(screen,pending)
        self.assertIsNotNone(panel)
        self.assertTrue(panel['commandTruncated'])
        self.assertEqual(panel['oneTimeChoice'],'1. Yes, proceed (y)')
        self.assertIsNone(approval_panel(screen.replace('controlled test windows','unrelated files'),pending))

    def test_native_title_generation_cannot_change_the_owned_trial_thread(self):
        stream=CodexEventStream();stream.request_id='request-1';stream.prompt='Hello'
        for identifier,thread in [(1,'main'),(2,'title')]:
            stream.feed('client',{'id':identifier,'method':'thread/start','params':{}})
            stream.feed('server',{'id':identifier,'result':{'thread':{'id':thread},'model':thread,
                'sandbox':{'type':'readOnly'},'approvalPolicy':'on-request'}})
        self.assertEqual(stream.thread_id,'main')
        self.assertEqual(stream.conditions['model'],'main')
        stream.feed('client',{'id':3,'method':'turn/start','params':{'threadId':'main','input':[{'type':'text','text':'Hello'}]}})
        stream.feed('client',{'id':4,'method':'turn/start','params':{'threadId':'title','input':[{'type':'text','text':'Generate title'}]}})
        stream.feed('server',{'method':'turn/started','params':{'threadId':'main','turn':{'id':'turn-main'}}})
        self.assertEqual(stream.admitted_prompt,'Hello')
        before=len(stream.events)
        stream.feed('server',{'method':'turn/completed','params':{'threadId':'title','turn':{'id':'title','status':'completed'}}})
        self.assertEqual(len(stream.events),before)

    def test_native_approval_identity_and_response_are_not_synthesized(self):
        stream=CodexEventStream()
        stream.feed('server',{'id':42,'method':'item/commandExecution/requestApproval','params':{
            'threadId':'t','turnId':'u','itemId':'i','command':'echo fixture','cwd':'owned'}})
        self.assertIn('42',stream.pending)
        self.assertEqual(stream.events[-1]['data']['command'],'echo fixture')
        stream.feed('client',{'id':42,'result':{'decision':'accept'}})
        self.assertFalse(stream.pending)
        self.assertEqual(stream.events[-1]['type'],'approval/decided')
        self.assertEqual(stream.events[-1]['data']['nativeDecision'],'accept')

    def test_doctor_checks_codex_launch_files_not_dsh_chrome(self):
        from arena.setup import check_repository
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            missing=Path(folder)/'missing'
            profile=dict(schemaVersion=2,agent='codex-cli',node=str(missing/'node.exe'),
                launchModule=str(missing/'launch.mjs'),launchConfig=str(missing/'setup.json'),
                wsModule=str(missing/'ws'),terminal=str(missing/'wt.exe'),ffmpeg=str(missing/'ffmpeg.exe'),
                desktopTool=str(missing/'desktop.exe'),desktop=1,windowSize=[1200,800],theme='light',
                fontSize=22,timeout=900,confirmationMode='capture-then-allow-once',finalHoldSeconds=30,
                captureSurface='desktop',screenRegion=[0,0,3840,2160],approvalReview='local-file',
                windowState='maximized',workspaceRoot=str(missing/'workspaces'))
            path=Path(folder)/'profile.json';path.write_text(json.dumps(profile),encoding='utf8')
            result=check_repository(root,path)
            names={row['name']:row['status'] for row in result['checks']}
            self.assertEqual(names['launchModule'],'fail')
            self.assertEqual(names['launchConfig'],'fail')
            self.assertEqual(names['wsModule'],'fail')
            self.assertEqual(names['workspaceRoot'],'fail')
            self.assertNotIn('dshEntry',names)
            self.assertNotIn('chrome',names)

    def test_codex_runtime_uses_profile_workspace_root(self):
        from unittest.mock import MagicMock,patch
        from arena.runner.batch import CodexRuntime
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            launch=root/'launch.mjs';launch.write_text('export {}\n',encoding='utf8')
            setup=root/'setup.json';setup.write_text('{}',encoding='utf8')
            workspace=root/'workspaces';workspace.mkdir()
            profile=dict(schemaVersion=2,agent='codex-cli',node='node',launchModule=str(launch),
                launchConfig=str(setup),wsModule='ws',terminal='wt.exe',ffmpeg='ffmpeg',desktopTool='desktop',
                desktop=1,windowSize=[1200,800],theme='light',fontSize=22,timeout=900,
                confirmationMode='capture-then-allow-once',finalHoldSeconds=30,captureSurface='desktop',
                screenRegion=[0,0,3840,2160],approvalReview='local-file',windowState='maximized',
                workspaceRoot=str(workspace))
            captured={}
            def fake_run(config,**kwargs):
                captured['workspace_root']=config.get('workspace_root')
                run_dir=root/'run';run_dir.mkdir()
                return dict(status='preflight-completed',runId='codex-fake',directory=str(run_dir),
                            errors=[],evidenceGaps=[])
            desktop=MagicMock();desktop.current.return_value=1;desktop.number=1
            job=MagicMock();job.close.return_value=dict(recovered=True,observerError=None)
            with patch('shutil.which',return_value='found'),\
                 patch('arena.adapters.environments.windows_desktop.WindowsDesktop',return_value=desktop),\
                 patch('arena.adapters.environments.windows_job.WindowsJob',return_value=job),\
                 patch('arena.adapters.agents.codex_terminal.NativeTerminalView'),\
                 patch('arena.adapters.agents.codex_terminal.CodexTerminalAgent'),\
                 patch('arena.evidence.recording.DesktopRecorder'),\
                 patch('arena.runner.batch.run_trial',side_effect=fake_run):
                CodexRuntime(profile).collect(dict(prompt='x'))
            self.assertEqual(captured['workspace_root'],str(workspace.resolve()))

if __name__=='__main__':unittest.main()
