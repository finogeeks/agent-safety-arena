"""A shared execution budget stops collection without an extra Agent operation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
from test_dsh_recording import FakeAgent, FakeBrowser, FakeRecorder, event, completed_events
from arena.runner.trial import run_trial, execution_budget
from arena.runner.batch import load_case, prepare_case, collect_batch

ROOT = Path(__file__).resolve().parents[1]


def execution_events(count, *, results=None, duplicate=False):
    rows = [event(0, 'turn/start', turn=1), event(1, 'user/message',
        content=[{'type':'text','text':'hello'}], source={'kind':'user','rpcId':'request'})]
    for number in range(count):
        call = event(len(rows),'tool/call',callId=str(number),tool='exec_command',command='owned operation')
        rows.append(call)
        if duplicate: rows.append(call)
        if results is None or number < results:
            result = event(len(rows),'tool/result',callId=str(number),native={'status':'completed'})
            rows.append(result)
            if duplicate: rows.append(result)
    return rows


class AttemptBudget(unittest.TestCase):
    def test_native_completion_waits_for_captured_picker_without_any_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('hello');calls=[];now=[0]
            frames=completed_events();frames.append(event(4,'approval/asked',id='setup',toolName='setup',command='Environment setup'))
            panel=dict(key='setup',native=True,text='Teach auto mode about your environment?',choices=['1. Yes','2. Not now'],oneTimeChoice='1. Yes')
            state=run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned fixture',revision='v4',
                reason='prompt retries only',timeout=20,approval_delay_seconds=5,approval_guard=lambda _:True),
                agent=FakeAgent(calls,observations=[frames]),browser=FakeBrowser(calls,[dict(dialogs=[panel],choices=[])]),
                recorder=FakeRecorder(calls),clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))
            self.assertEqual(state['status'],'completed')
            self.assertIn('choose-once',calls)
            self.assertNotIn('maxToolExecutions',state)
            self.assertNotIn('cancel',calls)

    def test_captured_pending_picker_is_chosen_before_budget_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('hello')
            calls=[];now=[0]
            dialog=dict(key='setup',native=True,text='Teach auto mode about your environment?',
                choices=['1. Yes','2. Not now'],oneTimeChoice='1. Yes')
            frames=execution_events(3)
            frames.append(event(len(frames),'approval/asked',id='setup',toolName='setup',
                                command='Initialize environment context',source='native environment setup'))
            agent=FakeAgent(calls,observations=[frames])
            state=run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned fixture',
                revision='v3',reason='pending picker',timeout=20,max_tool_executions=3,
                approval_delay_seconds=5,approval_guard=lambda _:True),
                agent=agent,browser=FakeBrowser(calls,[dict(dialogs=[dialog],choices=[])]),
                recorder=FakeRecorder(calls),clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))
            self.assertEqual(state['status'],'attempt-limit-reached')
            self.assertIn('choose-once',calls)
            self.assertLess(calls.index('record-panel'),calls.index('choose-once'))
            self.assertLess(calls.index('choose-once'),calls.index('cancel'))
            self.assertEqual(state['executionBudget']['started'],3)

    def trial(self, *, exceeded=False, natural=False, duplicate=False, late_call=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('hello')
            calls=[];time=[0];counts=[]
            class Agent(FakeAgent):
                cancelled=False
                def observe(inner):
                    if inner.cancelled:
                        if late_call:
                            rows=execution_events(4)
                            rows[1]['data']['source']['rpcId']=inner.request_id
                            return rows
                        return inner.last
                    counts.append(1)
                    if len(counts)>2 and not natural:raise AssertionError('An extra operation observation was requested')
                    rows=execution_events(4 if exceeded else (2 if natural or len(counts)==1 else 3),
                        results=2 if exceeded else None,duplicate=duplicate)
                    if natural:rows += completed_events()[2:]
                    for row in rows:
                        if row['type']=='user/message':row['data']['source']['rpcId']=inner.request_id
                    inner.last=rows;return rows
                def cancel(inner):inner.cancelled=True;super().cancel()
            def sleep(seconds):time[0]+=seconds
            state=run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned fixture',
                revision='bounded',reason='three executions',timeout=10,final_hold_seconds=30,
                max_tool_executions=3),agent=Agent(calls),browser=FakeBrowser(calls),
                recorder=FakeRecorder(calls),clock=lambda:time[0],sleep=sleep)
            path=Path(state['directory'])/'execution-budget.json'
            receipt=json.loads(path.read_text()) if path.exists() else None
            return state,calls,time[0],receipt,len(counts)

    def test_third_result_stops_without_final_hold_or_fourth_observation(self):
        state,calls,elapsed,receipt,observations=self.trial(duplicate=True)
        self.assertEqual(state['status'],'attempt-limit-reached')
        self.assertEqual(receipt['started'],3)
        self.assertEqual(receipt['returned'],3)
        self.assertEqual(observations,2)
        self.assertLess(elapsed,1)
        self.assertIn('cancel',calls)
        self.assertNotIn('completionState',state)

    def test_observed_fourth_call_is_not_reported_as_a_met_budget(self):
        state,_,_,receipt,_=self.trial(exceeded=True)
        self.assertEqual(state['status'],'attempt-limit-exceeded')
        self.assertEqual(receipt['started'],4)
        self.assertTrue(state['evidenceGaps'])

    def test_late_call_seen_during_interruption_is_retained_as_exceeded(self):
        state,_,_,receipt,_=self.trial(late_call=True)
        self.assertEqual(state['status'],'attempt-limit-exceeded')
        self.assertEqual(receipt['started'],4)

    def test_only_this_admitted_request_is_counted(self):
        rows=[event(0,'tool/call',callId='old')]+execution_events(1)
        self.assertEqual(execution_budget(rows,'request',3)['started'],1)
        missing=execution_budget(rows,'not-admitted',3)
        self.assertEqual(missing['started'],0)
        self.assertFalse(missing['admitted'])

    def test_early_native_completion_is_preserved(self):
        state,calls,_,receipt,_=self.trial(natural=True)
        self.assertEqual(state['status'],'completed')
        self.assertEqual(state['completionState'],'completed')
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['started'],2)
        self.assertNotIn('cancel',calls)

    def test_case_budget_is_validated_and_passed_to_shared_trial(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            original=ROOT/'scenarios/owned-file-create/case.ro.direct-v3.json'
            loaded,path=load_case(original)
            config,recorded,_=prepare_case(loaded,path,root)
            self.assertEqual(config['max_tool_executions'],3)
            self.assertEqual(recorded['maxToolExecutions'],3)

    def test_budget_rejects_boolean_zero_and_saved_program_cases(self):
        original=ROOT/'scenarios/owned-file-create/case.ro.direct-v2.json'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'case.json'
            for budget,execution in [(True,'direct'),(0,'direct'),(3,'saved-program')]:
                case=json.loads(original.read_text())
                case['resource'].update(maxToolExecutions=budget,execution=execution)
                path.write_text(json.dumps(case))
                with self.assertRaisesRegex(ValueError,'positive integer'):
                    load_case(path)

    def test_batch_accepts_declared_budget_stop_as_collected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);setup=root/'setup.json'
            setup.write_text(json.dumps(dict(labRoot=str(root/'lab'),stateRoot=str(root/'host'))))
            class Runtime:
                def collect(inner,config):
                    self.assertEqual(config['max_tool_executions'],3)
                    directory=root/'run';directory.mkdir();config['data_process_shutdown']=True
                    return dict(runId='bounded',directory=str(directory),status='attempt-limit-reached',
                                errors=[],evidenceGaps=[])
            result=collect_batch([ROOT/'scenarios/owned-file-create/case.ro.direct-v3.json'],
                dict(dataSetup=str(setup),timeout=10,confirmationMode='manual'),root/'runs',runtime=Runtime())
            self.assertEqual(result['status'],'completed')

    def test_bounded_suite_has_eight_balanced_unchanged_operation_families(self):
        suite=json.loads((ROOT/'profiles/suites/data-safety-bounded-three.json').read_text())
        self.assertEqual(len(suite['cases']),8)
        zones=[]
        for relative in suite['cases']:
            case,path=load_case(ROOT/relative)
            self.assertEqual(case['resource']['maxToolExecutions'],3)
            zones.append(case['resource']['zone'])
            text=(path.parent/case['prompt']).read_text()
            self.assertIn('THREE sequential tool executions',text)
            self.assertIn('Do not run tools in parallel',text)
            self.assertIn('Do not make diagnostic-only calls',text)
        self.assertEqual(zones.count('read-only'),4)
        self.assertEqual(zones.count('no-access'),4)


if __name__=='__main__':unittest.main()
