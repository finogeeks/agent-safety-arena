"""Deterministic checks for real-run orchestration, using no live Agent."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arena.adapters.agents.dsh import completion_for, new_blank_sessions, scrub
from arena.assessment.confirmation import validate_review, review_trial
from arena.runner.trial import Confirmations, run_trial, save, local_scope_guard
from arena.cli import parser
from arena.evidence.recording import BrowserRecorder


def event(seq, kind, **data):
    return {"seq": seq, "type": kind, "data": data}


def completed_events(request_id="request-1", reason="completed"):
    return [
        event(0, "turn/start", turn=1),
        event(1, "user/message", content=[{"type": "text", "text": "hello"}],
              source={"kind": "user", "rpcId": request_id}),
        event(2, "assistant/message", turn=1, message={"content": [
            {"type": "reasoning", "text": "private reasoning"},
            {"type": "text", "text": "Public reply"}]}),
        event(3, "turn/end", turn=1, reason={"kind": reason}),
    ]


class CompletionTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows evidence sharing regression')
    def test_evidence_write_survives_a_transient_windows_reader_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'native-events.json'
            target.write_text('[]', encoding='utf8')
            held = target.open('r', encoding='utf8')
            def release():
                time.sleep(.12)
                held.close()
            reader = threading.Thread(target=release)
            reader.start()
            try:
                save(target, [{'type': 'turn/end'}])
                self.assertEqual(json.loads(target.read_text('utf8')), [{'type': 'turn/end'}])
            finally:
                reader.join()
                held.close()

    def test_visible_session_identity_resolves_two_new_blank_sessions(self):
        rows = [{"sessionId": name, "cwd": str(Path.cwd()), "blank": True, "running": False}
                for name in ("automatic-blank", "selected-in-ui")]
        selected = new_blank_sessions(rows, Path.cwd(), set(), "selected-in-ui")
        self.assertEqual([item["sessionId"] for item in selected], ["selected-in-ui"])
        self.assertEqual(new_blank_sessions(rows, Path.cwd(), set(), "unknown-session"), [])

    def test_visible_session_selection_excludes_automatically_created_blank(self):
        rows = [{"sessionId": name, "cwd": str(Path.cwd()), "blank": True, "running": False}
                for name in ("automatic-blank", "selected-in-ui")]
        selected = new_blank_sessions(rows, Path.cwd(), {"automatic-blank"})
        self.assertEqual([item["sessionId"] for item in selected], ["selected-in-ui"])

    def test_visible_blank_session_opened_with_the_workspace_is_owned(self):
        rows = [{"sessionId": "opened-with-workspace", "cwd": str(Path.cwd()),
                 "blank": True, "running": False}]
        selected = new_blank_sessions(rows, Path.cwd(), {"opened-with-workspace"},
                                      "opened-with-workspace")
        self.assertEqual([item["sessionId"] for item in selected], ["opened-with-workspace"])
        self.assertEqual(new_blank_sessions(rows, Path.cwd(), {"opened-with-workspace"},
                                            "different-visible-session"), [])
    def test_recording_source_selects_the_owned_dsh_window(self):
        recorder = BrowserRecorder("ffmpeg.exe", FakeBrowser([]))
        recorder.select_window("Arena owned-test")
        self.assertEqual(recorder.source, "browser-viewport")

    def test_cli_exposes_the_recording_and_review_workflow(self):
        self.assertIn("dsh-run", parser().format_help())
        self.assertIn("dsh-review", parser().format_help())
        self.assertIn("dsh-preview", parser().format_help())

    def test_finshield_launches_dsh_desktop_without_changing_the_native_command(self):
        from arena.adapters.agents.dsh import dsh_web_command
        native=dsh_web_command('node','bin.js')
        self.assertEqual(native,['node','bin.js','web','--host','127.0.0.1','--port','0','--no-open'])
        wrapped=dsh_web_command('node','bin.js',confinement={'executable':'finsafe.exe','config':'effective.yaml','desktop':'DeepSeek Harness.exe'})
        self.assertEqual(wrapped,[
            'finsafe.exe','app','launch','dsh-desktop','--yaml-path','effective.yaml','--integration-id','dsh','--',
            'DeepSeek Harness.exe'])
        self.assertNotIn('self-confine',wrapped)
        self.assertNotIn('bin.js',wrapped)

    def test_finshield_profile_points_at_the_desktop_executable(self):
        from arena.adapters.agents.dsh import finshield_confinement
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, config, desktop = root/'finsafe.exe', root/'effective.yaml', root/'DeepSeek Harness.exe'
            for path in (executable, config, desktop):
                path.write_text('fixture', encoding='utf8')
            confinement = finshield_confinement({'finshield': str(executable), 'finshieldConfig': str(config),
                                                 'dshDesktop': str(desktop)})
            self.assertEqual(Path(confinement['desktop']).name, 'DeepSeek Harness.exe')
            self.assertTrue(Path(confinement['executable']).is_file())

    def test_finshield_workspace_keeps_inherited_directory_access(self):
        if sys.platform != "win32":
            self.skipTest("inherited directory ACL is a Windows behavior")
        import shutil
        import subprocess
        from arena.runner.trial import owned_workspace
        parent = Path(tempfile.gettempdir()) / ("arena-inherit-parent-" + uuid.uuid4().hex[:8])
        parent.mkdir()
        private = Path(tempfile.mkdtemp(prefix="arena-private-workspace-"))
        try:
            workspace = owned_workspace(parent, "dsh-20261105T000000-aabbccdd")
            listed = subprocess.check_output(["icacls", str(workspace)], text=True, errors="replace")
            hidden = subprocess.check_output(["icacls", str(private)], text=True, errors="replace")
            self.assertIn("(I)", listed)
            self.assertNotIn("(I)", hidden)
            self.assertTrue(workspace.is_dir())
            self.assertTrue(str(workspace).startswith(str(parent)))
        finally:
            shutil.rmtree(parent, ignore_errors=True)
            shutil.rmtree(private, ignore_errors=True)

    def test_finshield_workspace_stays_inside_the_allowed_root(self):
        from arena.adapters.agents.dsh import finshield_workspace_root
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(finshield_workspace_root({"workspaceRoot": directory}), str(Path(directory).resolve()))
        with self.assertRaises(ValueError):
            finshield_workspace_root({})

    def test_finshield_sandbox_difference_is_recorded_without_blocking_submission(self):
        from arena.runner.trial import prepared_conflicts
        expected = dict(agentVersion='0.2.1-rc.2', uiLanguage='en',
                        builtinSandbox='workspace-write', approvalPolicy='ask')
        actual = dict(expected, builtinSandbox='danger-full-access')
        self.assertEqual(prepared_conflicts(expected, actual, 'finshield'), [])
        self.assertEqual(prepared_conflicts(expected, actual, 'builtin-only'), ['builtinSandbox'])
        self.assertEqual(prepared_conflicts(expected, dict(actual, uiLanguage='zh-CN'), 'finshield'), ['uiLanguage'])

    def test_desktop_host_buffer_yields_one_loopback_url(self):
        from arena.adapters.agents.dsh import loopback_url_in
        url = "http://127.0.0.1:58023/?token=syntheticTokenValue001"
        self.assertEqual(loopback_url_in(b"dsh web: " + url.encode("ascii") + b"\n"), url)
        self.assertEqual(loopback_url_in(url.encode("utf-16-le")), url)
        self.assertIsNone(loopback_url_in(b'{"main_pid":1,"hook_ready":true}\n'))
        self.assertIsNone(loopback_url_in(b"http://127.0.0.1:1/?token=short\n"))
        self.assertIsNone(loopback_url_in(url.encode("ascii") + b"\n" + b"http://127.0.0.1:9/?token=syntheticTokenValue002\n"))

    def test_diagnostic_redaction_does_not_store_authentication_token(self):
        text = scrub("http://127.0.0.1:1234/?token=synthetic-test-token Bearer synthetic-bearer")
        self.assertNotIn("synthetic-test-token", text)
        self.assertNotIn("synthetic-bearer", text)

    def test_matches_request_and_excludes_reasoning(self):
        result = completion_for(completed_events(), "request-1")
        self.assertEqual(result, {"state": "completed", "text": "Public reply", "turn": 1})

    def test_other_request_and_wrong_turn_cannot_complete_trial(self):
        rows = completed_events()
        self.assertIsNone(completion_for(rows, "different-request"))
        rows[-1]["data"]["turn"] = 2
        self.assertIsNone(completion_for(rows, "request-1"))

    def test_empty_reply_can_finish_and_error_is_not_completion(self):
        rows = completed_events(reason="error")
        rows.pop(2)
        self.assertEqual(completion_for(rows, "request-1")["state"], "error")
        self.assertEqual(completion_for(rows, "request-1")["text"], "")

    def test_provider_failure_preserves_its_reason_for_the_run_summary(self):
        rows = completed_events(reason="error")
        rows[-1]["data"]["reason"]["error"] = {"code": "QUOTA", "message": "Insufficient Balance", "status": 402}
        result = completion_for(rows, "request-1")
        self.assertEqual(result.get("error", {}).get("code"), "QUOTA")


class FakeBrowser:
    def __init__(self, calls, snapshots=None):
        self.calls = calls
        self.snapshots = iter(snapshots or [{"dialogs": [], "choices": []}])
        self.last = {"dialogs": [], "choices": []}

    def snapshot(self):
        self.last = next(self.snapshots, self.last)
        return self.last

    def screenshot(self, path, key=None):
        self.calls.append("screenshot")
        Path(path).write_bytes(b"controlled screenshot")
        self.last_screenshot = Path(path)

    def choose_once(self, key, text):
        saved = self.last_screenshot.parent.parent / 'confirmations.json'
        if not saved.is_file() or json.loads(saved.read_text('utf8'))[0]['captureStatus'] != 'captured':
            raise RuntimeError('Capture was not persisted before choice')
        self.calls.append('choose-once')
        return {'at': 2000, 'label': '允许一次'}

    def close(self):
        self.calls.append("browser-close")


class FakeRecorder:
    def __init__(self, calls, fail_start=False, fail_health=False, fail_stop=False, fail_checkpoint=False):
        self.calls = calls
        self.fail_start = fail_start
        self.fail_health = fail_health
        self.fail_stop = fail_stop
        self.fail_checkpoint = fail_checkpoint

    def select_window(self, title):
        self.calls.append("select-owned-window")

    def start(self, path):
        self.calls.append("record-start")
        if self.fail_start:
            raise RuntimeError("recording unavailable")
        Path(path).write_bytes(b"controlled video")

    def check(self):
        if self.fail_health:
            raise RuntimeError("recorder exited")

    def checkpoint(self):
        self.calls.append('record-panel')
        if self.fail_checkpoint:
            raise RuntimeError('Panel was not recorded')
        return 1.5

    def stop(self):
        self.calls.append("record-stop")
        if self.fail_stop:
            raise RuntimeError("recorder finalization failed")


class FakeAgent:
    def __init__(self, calls, observations=None, fail_submit=False):
        self.calls = calls
        self.observations = iter(observations or [completed_events()])
        self.fail_submit = fail_submit
        self.last = []
        self.request_id = None

    def prepare(self, workspace, browser, evidence_directory):
        self.calls.append("prepare")
        return {"sessionId": "owned-session", "model": {"model": "test-model"},
                "captureWindowTitle": "Arena synthetic test",
                "permissions": {"currentValue": "default"}}

    def submit(self, prompt, request_id):
        self.calls.append("submit")
        self.request_id = request_id
        self.prompt = prompt
        if self.fail_submit:
            raise RuntimeError("submission failed")

    def observe(self):
        following = next(self.observations, self.last)
        if isinstance(following, BaseException):
            raise following
        self.last = copy.deepcopy(following)
        for row in self.last:
            if row["type"] == "user/message":
                row["data"]["source"]["rpcId"] = self.request_id
        return self.last

    def cancel(self):
        self.calls.append("cancel")

    def close(self):
        self.calls.append("agent-close")


class TrialTests(unittest.TestCase):
    def test_attempted_submission_flag_is_persisted_before_transport_call(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('synthetic request',encoding='utf8')
            calls=[];persisted=[]
            class Agent(FakeAgent):
                def prepare(self,workspace,browser,evidence_directory):
                    self.directory=evidence_directory
                    return super().prepare(workspace,browser,evidence_directory)
                def submit(self,prompt,request_id):
                    persisted.append(json.loads((self.directory/'run.json').read_text('utf8'))['promptSubmitted'])
                    return super().submit(prompt,request_id)
            run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned fixture',revision='v1',reason='transport state',timeout=10),
                agent=Agent(calls),browser=FakeBrowser(calls),recorder=FakeRecorder(calls),sleep=lambda seconds:None)
            self.assertEqual(persisted,[True])

    def test_presentation_preflight_never_submits_or_counts_as_completed_trial(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prompt=root/'prompt.txt';prompt.write_text('Do not submit',encoding='utf8')
            calls=[]
            result=run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned fixture',
                revision='v1',reason='no-model-call preflight',timeout=10,preflight_only=True),
                agent=FakeAgent(calls),browser=FakeBrowser(calls),recorder=FakeRecorder(calls),
                sleep=lambda seconds:None)
            self.assertNotIn('submit',calls)
            self.assertEqual(result['status'],'preflight-completed')
            self.assertFalse(result['promptSubmitted'])
            self.assertIn('record-start',calls)
            self.assertIn('record-stop',calls)

    def test_final_hold_retains_background_native_events_after_turn_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            prompt=root/'prompt.txt'
            prompt.write_text('synthetic test',encoding='utf8')
            calls=[]
            complete=completed_events()
            tail=complete+[event(4,'background/completed',jobId='owned-job')]
            ticks=iter(range(100))
            result=run_trial(dict(prompt=prompt,output_root=root/'runs',target='owned process',
                revision='v1',reason='tail capture',timeout=20,final_hold_seconds=5),
                agent=FakeAgent(calls,[complete,tail]),browser=FakeBrowser(calls),recorder=FakeRecorder(calls),
                clock=lambda:next(ticks),sleep=lambda seconds:None)
            events=json.loads((Path(result['directory'])/'native-events.json').read_text('utf8'))
            self.assertEqual(events[-1]['type'],'background/completed')

    def execute(self, root, *, recorder_options=None, observations=None, snapshots=None, timeout=10,
                confirmation_mode='capture-then-allow-once'):
        prompt = root / "prompt.txt"
        prompt.write_bytes(b"hello\r\n")
        calls = []
        ticks = iter(range(100))
        result = run_trial(
            {"prompt": prompt, "output_root": root / "runs", "target": "owned test note",
             "workspace_root": root, "revision": "v1", "reason": "initial trial", "timeout": timeout,
             "confirmation_mode": confirmation_mode,
             "approval_guard": lambda item: item.get('tool') == 'pwsh' and item.get('command') == 'Read synthetic-note'},
            agent=FakeAgent(calls, observations), browser=FakeBrowser(calls, snapshots),
            recorder=FakeRecorder(calls, **(recorder_options or {})),
            clock=lambda: next(ticks), sleep=lambda seconds: None)
        return result, calls

    def approval_fixture(self):
        call = event(2,'tool/call',callId='call-1',name='pwsh',arguments=json.dumps({'command':'Read synthetic-note'}))
        asked = event(3, 'approval/asked', id='native-1', toolName='pwsh',callId='call-1')
        waiting = completed_events()[:2] + [call, asked]
        reply = completed_events()[2]
        reply['seq'] = 5
        finished = waiting + [event(4,'approval/decided',id='native-1',outcome='allowed-once'),reply,
                              event(6,'turn/end',turn=1,reason={'kind':'completed'})]
        panel = {'key':'approval:1','native':True,'text':'Allow this controlled command?',
                 'choices':['拒绝','允许一次']}
        return [waiting, finished], [{'dialogs':[panel]}, {'dialogs':[]}]

    def test_automatic_one_time_choice_follows_saved_capture_and_video_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            observations, snapshots = self.approval_fixture()
            # Keep the request pending while the five-second timer advances.
            observations = observations[:1]*3 + observations[1:]
            snapshots = snapshots[:1]*3 + snapshots[1:]
            result, calls = self.execute(Path(folder), observations=observations, snapshots=snapshots)
            self.assertIn('choose-once', calls)
            self.assertLess(calls.index('screenshot'), calls.index('record-panel'))
            self.assertLess(calls.index('record-panel'), calls.index('choose-once'))
            saved = json.loads((Path(result['directory'])/'confirmations.json').read_text('utf8'))
            self.assertEqual(saved[0]['decisionActor'], 'automation')
            self.assertEqual(saved[0]['choice'], 'allowed-once')

    def test_recorder_checkpoint_failure_never_approves(self):
        with tempfile.TemporaryDirectory() as folder:
            observations, snapshots = self.approval_fixture()
            result, calls = self.execute(Path(folder), observations=observations, snapshots=snapshots,
                                         recorder_options={'fail_checkpoint':True})
            self.assertNotIn('choose-once', calls)
            self.assertEqual(result['status'], 'error')

    def test_manual_confirmation_mode_never_automates_a_choice(self):
        with tempfile.TemporaryDirectory() as folder:
            observations, snapshots = self.approval_fixture()
            _, calls = self.execute(Path(folder), observations=observations, snapshots=snapshots,
                                    confirmation_mode='manual')
            self.assertNotIn('choose-once', calls)

    def test_recording_precedes_submission_and_stops_after_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls = self.execute(Path(folder))
            self.assertEqual(result.get("status"), "completed")
            self.assertLess(calls.index("record-start"), calls.index("submit"))
            self.assertLess(calls.index("submit"), calls.index("record-stop"))
            output = Path(result["directory"])
            self.assertEqual((output / "prompt.txt").read_bytes(), b"hello\r\n")
            self.assertEqual((output / "agent-output.txt").read_text("utf8"), "Public reply")

    def test_collection_leaves_analysis_for_a_separate_review_phase(self):
        with tempfile.TemporaryDirectory() as folder:
            result, _ = self.execute(Path(folder))
            output = Path(result['directory'])
            self.assertFalse((output/'analysis.md').exists())
            form = json.loads((output/'analysis.json').read_text('utf8'))
            self.assertEqual(form['targetOutcome'], 'unknown')

    def test_recorder_start_failure_never_submits(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls = self.execute(Path(folder), recorder_options={"fail_start": True})
            self.assertNotIn("submit", calls)
            self.assertEqual(result.get("status"), "error")
            self.assertIn("agent-close", calls)

    def test_trials_keep_separate_prompts_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            first, _ = self.execute(Path(folder))
            second, _ = self.execute(Path(folder))
            self.assertNotEqual(first.get("directory"), second.get("directory"))
            saved = json.loads((Path(first["directory"]) / "run.json").read_text("utf8"))
            self.assertEqual(saved["revision"], "v1")
            self.assertEqual(saved["reason"], "initial trial")

    def test_target_workspace_is_separate_from_the_repository_evidence_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            result, _ = self.execute(Path(folder))
            workspace = Path(result.get("workspacePath", result["directory"]))
            self.assertFalse(workspace.is_relative_to(Path(result["directory"])))
            self.assertTrue(workspace.is_dir())

    def test_timeout_cancels_before_stopping_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls = self.execute(Path(folder), observations=[[]], timeout=1)
            self.assertEqual(result.get("status"), "timeout")
            self.assertLess(calls.index("cancel"), calls.index("record-stop"))

    def test_operator_interruption_retains_cancelled_trial_and_closes_owned_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls = self.execute(Path(folder), observations=[KeyboardInterrupt()])
            self.assertEqual(result["status"], "cancelled")
            self.assertLess(calls.index("cancel"), calls.index("record-stop"))
            self.assertIn("agent-close", calls)
            self.assertIn("browser-close", calls)
            self.assertTrue((Path(result["directory"]) / "analysis.json").is_file())

    def test_recorder_exit_and_finalization_failure_are_explicit(self):
        for option in ("fail_health", "fail_stop"):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as folder:
                result, _ = self.execute(Path(folder), recorder_options={option: True})
                self.assertEqual(result.get("status"), "error")
                self.assertTrue(result.get("errors"))

    def test_run_summary_retains_provider_error_and_actual_model(self):
        rows = completed_events(reason="error")
        rows[-1]["data"]["reason"]["error"] = {"code": "QUOTA", "message": "Insufficient Balance"}
        rows.insert(2, event(2, "request/header", header={"config": {
            "provider": "synthetic-provider", "model": "actual-model", "reasoningEffort": "high"}}))
        with tempfile.TemporaryDirectory() as folder:
            result, _ = self.execute(Path(folder), observations=[rows])
            self.assertTrue(any("QUOTA" in item for item in result.get("errors", [])))
            self.assertEqual(result.get("model", {}).get("model"), "actual-model")

    def test_repeated_native_approvals_are_not_collapsed_and_missing_capture_is_explicit(self):
        rows = completed_events()
        rows[2:2] = [event(2, "approval/asked", id="a", toolName="pwsh"),
                     event(3, "approval/decided", id="a", outcome="allowed-once"),
                     event(4, "approval/asked", id="b", toolName="pwsh"),
                     event(5, "approval/decided", id="b", outcome="rejected")]
        rows[-2]["seq"] = 6
        rows[-1]["seq"] = 7
        with tempfile.TemporaryDirectory() as folder:
            result, _ = self.execute(Path(folder), observations=[rows])
            captures = json.loads((Path(result["directory"]) / "confirmations.json").read_text("utf8"))
            self.assertEqual([item["requestId"] for item in captures], ["a", "b"])
            self.assertTrue(all(item["captureStatus"] == "missing" for item in captures))
            self.assertEqual(captures[1]["choice"], "rejected")


class ReviewTests(unittest.TestCase):
    def test_report_identifies_an_automated_decision_actor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'analysis.json').write_text(json.dumps(self.review()),encoding='utf8')
            confirmation = {**self.confirmation(),'decisionActor':'automation','choice':'allowed-once'}
            (root/'confirmations.json').write_text(json.dumps([confirmation]),encoding='utf8')
            (root/'run.json').write_text(json.dumps({'runId':'test','status':'completed'}),encoding='utf8')
            self.assertIn('Decision actor: automation',review_trial(root).read_text('utf8'))

    def confirmation(self):
        return {"id": "confirmation-001", "text": "Allow this command?", "captureStatus": "captured"}

    def review(self, classification="none", quote="Allow this command?"):
        return {"targetOutcome": "unknown", "targetEvidence": "Not inspected.", "confirmations": [
            {"id": "confirmation-001", "warning": classification, "quote": quote,
             "consequence": "", "notes": "Only asks permission.", "ordinaryReference": ""}]}

    def test_review_cannot_invent_warning_quotes(self):
        with self.assertRaisesRegex(ValueError, "quote"):
            validate_review(self.review("operation-specific", "Data will be deleted"), [self.confirmation()])

    def test_missing_capture_cannot_be_classified_as_no_warning(self):
        confirmation = self.confirmation()
        confirmation["captureStatus"] = "missing"
        with self.assertRaisesRegex(ValueError, "unassessed"):
            validate_review(self.review(), [confirmation])

    def test_every_confirmation_requires_its_own_review(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            validate_review({**self.review(), "confirmations": []}, [self.confirmation()])

    def test_valid_ordinary_confirmation_does_not_imply_target_effect(self):
        result = validate_review(self.review(), [self.confirmation()])
        self.assertEqual(result["targetOutcome"], "unknown")

    def test_ordinary_comparison_needs_a_named_reference(self):
        review = self.review()
        review["confirmations"][0]["sameAsOrdinary"] = True
        with self.assertRaisesRegex(ValueError, "ordinaryReference"):
            validate_review(review, [self.confirmation()])


class CaptureTests(unittest.TestCase):
    def pending_panel(self, root, calls, clock):
        (root/'confirmations').mkdir()
        confirmations = Confirmations(root, FakeBrowser(calls), clock, 0)
        confirmations.native([event(1,'approval/asked',id='a',toolName='pwsh')])
        confirmations.capture({'dialogs':[{'key':'approval:1','native':True,'text':'Allow?',
                                            'choices':['Allow once']}]})
        return confirmations

    def test_five_second_approval_timer_polls_without_blocking_or_restarting(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[];now=[10.0];root=Path(folder)
            confirmations=self.pending_panel(root,calls,lambda:now[0])
            recorder=FakeRecorder(calls)
            def no_sleep(_):self.fail('Approval scheduling must not block collection')
            confirmations.auto_decide(recorder,no_sleep,lambda _:True)
            self.assertIn('record-panel',calls)
            self.assertNotIn('choose-once',calls)
            now[0]=14.99
            confirmations.auto_decide(recorder,no_sleep,lambda _:True)
            self.assertNotIn('choose-once',calls)
            now[0]=15
            confirmations.auto_decide(recorder,no_sleep,lambda _:True)
            confirmations.auto_decide(recorder,no_sleep,lambda _:True)
            self.assertEqual(calls.count('choose-once'),1)
            self.assertEqual(calls.count('record-panel'),1)
            self.assertEqual(confirmations.items[0]['autoDecisionNotBeforeSeconds'],15)

    def test_late_scope_grant_does_not_add_another_five_second_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[];now=[10.0];root=Path(folder)
            confirmations=self.pending_panel(root,calls,lambda:now[0])
            recorder=FakeRecorder(calls)
            confirmations.auto_decide(recorder,lambda _:None,lambda _:None)
            self.assertNotIn('choose-once',calls)
            now[0]=20
            confirmations.auto_decide(recorder,lambda _:None,lambda _:True)
            self.assertIn('choose-once',calls)
            self.assertEqual(confirmations.items[0]['scopeStatus'],'matched-command')

    def test_local_scope_grant_is_bound_to_request_tool_and_exact_command(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'grants.json'
            item = dict(requestId='request-one', tool='pwsh', command='Read synthetic-note')
            self.assertIsNone(local_scope_guard(path,item))
            grant = dict(requestId=item['requestId'],tool=item['tool'],
                         commandSha256=hashlib.sha256(item['command'].encode()).hexdigest())
            save(path,{'grants':[grant]})
            self.assertTrue(local_scope_guard(path,item))
            for changed in (dict(requestId='other'),dict(tool='bash'),dict(command=item['command']+'; extra')):
                self.assertIsNone(local_scope_guard(path,{**item,**changed}))

    def test_pending_scope_review_waits_without_click_or_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'confirmations').mkdir()
            calls = []
            confirmations = Confirmations(root, FakeBrowser(calls), lambda:1, 0)
            confirmations.native([event(1,'approval/asked',id='a',toolName='pwsh')])
            confirmations.capture({'dialogs':[{'key':'approval:1','native':True,'text':'Allow?',
                                                'choices':['Allow once']}]})
            confirmations.auto_decide(FakeRecorder(calls), lambda seconds:None, lambda item:None)
            self.assertNotIn('choose-once', calls)
            self.assertEqual(confirmations.items[0]['scopeStatus'], 'pending-review')

    def test_native_panel_without_a_scope_guard_never_receives_automatic_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'confirmations').mkdir()
            calls = []
            confirmations = Confirmations(root,FakeBrowser(calls),lambda:1,0)
            confirmations.native([event(1,'approval/asked',id='a',toolName='pwsh')])
            confirmations.capture({'dialogs':[{'key':'approval:1','native':True,'text':'Allow?',
                                                'choices':['Allow once']}]})
            with self.assertRaisesRegex(RuntimeError,'allowlist'):
                confirmations.auto_decide(FakeRecorder(calls),lambda seconds:None)
            self.assertNotIn('choose-once',calls)

    def test_missing_or_unmatched_capture_never_gets_an_automatic_choice(self):
        for native, captured in ((True, False), (False, True)):
            with self.subTest(native=native, captured=captured), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root/'confirmations').mkdir()
                calls = []
                browser = FakeBrowser(calls)
                if not captured:
                    browser.screenshot = lambda path, key=None: False
                confirmations = Confirmations(root, browser, lambda: 1, 0)
                confirmations.native([event(1,'approval/asked',id='a',toolName='pwsh')])
                confirmations.capture({'dialogs':[{'key':'approval:1','native':native,
                    'text':'Allow?', 'choices':['Allow once']} ]})
                confirmations.auto_decide(FakeRecorder(calls), lambda seconds: None)
                self.assertNotIn('choose-once', calls)

    def test_ui_capture_before_history_update_is_one_native_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "confirmations").mkdir()
            captures = Confirmations(root, FakeBrowser([]), lambda: 1, 0)
            captures.capture({"dialogs": [{"key": "approval:1", "native": True, "text": "Allow?"}]})
            captures.native([event(1, "approval/asked", id="native-1", toolName="pwsh")])
            self.assertEqual(len(captures.items), 1)
            self.assertEqual(captures.items[0]["requestId"], "native-1")

    def test_two_visible_native_requests_keep_separate_screenshots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "confirmations").mkdir()
            calls = []
            captures = Confirmations(root, FakeBrowser(calls), lambda: 1, 0)
            captures.native([event(1, "approval/asked", id="a", toolName="pwsh")])
            captures.capture({"dialogs": [{"key": "approval:1", "native": True, "text": "Allow?"}]})
            captures.native([event(2, "approval/decided", id="a", outcome="allowed-once"),
                             event(3, "approval/asked", id="b", toolName="pwsh")])
            captures.capture({"dialogs": [{"key": "approval:2", "native": True, "text": "Allow?"}]})
            self.assertEqual(calls, ["screenshot", "screenshot"])
            self.assertNotEqual(captures.items[0]["screenshot"], captures.items[1]["screenshot"])


if __name__ == "__main__":
    unittest.main()
