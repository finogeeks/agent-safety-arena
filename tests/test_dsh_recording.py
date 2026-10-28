"""Deterministic checks for real-run orchestration, using no live Agent."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arena.adapters.agents.dsh import completion_for, new_blank_sessions, scrub
from arena.assessment.confirmation import validate_review
from arena.runner.trial import Confirmations, run_trial
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
    def test_visible_session_selection_excludes_automatically_created_blank(self):
        rows = [{"sessionId": name, "cwd": str(Path.cwd()), "blank": True, "running": False}
                for name in ("automatic-blank", "selected-in-ui")]
        selected = new_blank_sessions(rows, Path.cwd(), {"automatic-blank"})
        self.assertEqual([item["sessionId"] for item in selected], ["selected-in-ui"])
    def test_recording_source_selects_the_owned_dsh_window(self):
        recorder = BrowserRecorder("ffmpeg.exe", FakeBrowser([]))
        recorder.select_window("Arena owned-test")
        self.assertEqual(recorder.source, "browser-viewport")

    def test_cli_exposes_the_recording_and_review_workflow(self):
        self.assertIn("dsh-run", parser().format_help())
        self.assertIn("dsh-review", parser().format_help())

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

    def close(self):
        self.calls.append("browser-close")


class FakeRecorder:
    def __init__(self, calls, fail_start=False, fail_health=False, fail_stop=False):
        self.calls = calls
        self.fail_start = fail_start
        self.fail_health = fail_health
        self.fail_stop = fail_stop

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
    def execute(self, root, *, recorder_options=None, observations=None, snapshots=None, timeout=10):
        prompt = root / "prompt.txt"
        prompt.write_bytes(b"hello\r\n")
        calls = []
        ticks = iter(range(100))
        result = run_trial(
            {"prompt": prompt, "output_root": root / "runs", "target": "owned test note",
             "workspace_root": root, "revision": "v1", "reason": "initial trial", "timeout": timeout},
            agent=FakeAgent(calls, observations), browser=FakeBrowser(calls, snapshots),
            recorder=FakeRecorder(calls, **(recorder_options or {})),
            clock=lambda: next(ticks), sleep=lambda seconds: None)
        return result, calls

    def test_recording_precedes_submission_and_stops_after_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls = self.execute(Path(folder))
            self.assertEqual(result.get("status"), "completed")
            self.assertLess(calls.index("record-start"), calls.index("submit"))
            self.assertLess(calls.index("submit"), calls.index("record-stop"))
            output = Path(result["directory"])
            self.assertEqual((output / "prompt.txt").read_bytes(), b"hello\r\n")
            self.assertEqual((output / "agent-output.txt").read_text("utf8"), "Public reply")

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
