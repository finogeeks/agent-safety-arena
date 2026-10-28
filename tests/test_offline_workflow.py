import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena.evidence.media import public_media_path
from arena.reporting.renderer import render_result
from arena.runner.lifecycle import ReplayError, replay
from arena.scenarios import load_scenario


FIXTURES = ROOT / "tests" / "fixtures"
SCENARIOS = ROOT / "scenarios"


class ScenarioContractTests(unittest.TestCase):
    def test_both_scenarios_define_profiles_and_versioned_prompts(self):
        for scenario_id in ("window-shake", "service-stop"):
            with self.subTest(scenario=scenario_id):
                scenario = load_scenario(SCENARIOS / scenario_id / "scenario.json")
                self.assertEqual(scenario["id"], scenario_id)
                self.assertTrue(scenario["allowedResources"])
                self.assertTrue(scenario["prohibitedRealResources"])
                self.assertTrue(scenario["requiredObservationKinds"])
                self.assertTrue(scenario["recoveryRequirements"])
                for field in ("base", "development", "path"):
                    self.assertTrue(scenario["resolvedFrozenPrompt"][field].is_file())
                self.assertEqual(scenario["agentProfile"]["adapter"], "offline-replay")
                self.assertEqual(
                    set(scenario["loadedEnvironmentProfiles"]),
                    {"offline-synthetic", "offline-synthetic-open"},
                )
                self.assertTrue(
                    all(
                        profile["adapter"] == "offline-replay"
                        for profile in scenario["loadedEnvironmentProfiles"].values()
                    )
                )


class ReplayTests(unittest.TestCase):
    def replay_fixture(self, name):
        scenario_id = json.loads((FIXTURES / name).read_text("utf8"))["scenarioId"]
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        base = Path(context.name)
        result = replay(
            SCENARIOS / scenario_id / "scenario.json",
            FIXTURES / name,
            base / "private",
            base / "reviewed",
            base / "site",
            template_root=ROOT / "templates",
        )
        return result, base

    def test_completed_run_separates_private_and_reviewed_outputs(self):
        result, base = self.replay_fixture("window-shake-completed.json")
        self.assertEqual(result["runStatus"], "completed")
        self.assertEqual(result["denominator"], {"included": True, "reason": "completed"})
        self.assertEqual(result["outcomes"]["agentDecision"]["status"], "fail")
        self.assertEqual(result["outcomes"]["hazardousEffect"]["status"], "pass")
        self.assertEqual(result["outcomes"]["environmentEnforcement"]["status"], "pass")
        self.assertEqual(result["environmentProfile"], "offline-synthetic")
        self.assertRegex(result["comparisonKey"], r"^[a-f0-9]{64}$")

        private = json.loads((base / "private" / "run-evidence.json").read_text("utf8"))
        reviewed_text = (base / "reviewed" / "result.json").read_text("utf8")
        prompt = (base / "private" / "actual-prompt.txt").read_text("utf8")
        frozen = SCENARIOS / "window-shake" / "prompts" / "agents" / "reference-agent" / "frozen" / "v1.md"
        expected_hash = hashlib.sha256(frozen.read_bytes()).hexdigest()
        self.assertEqual(result["actualPromptSha256"], expected_hash)
        self.assertEqual(private["actualPromptSha256"], result["actualPromptSha256"])
        self.assertIn("rawObservations", private)
        self.assertNotIn(prompt, reviewed_text)
        self.assertNotIn("rawObservations", reviewed_text)
        self.assertNotIn(str(base / "private"), reviewed_text)
        self.assertFalse((base / "reviewed" / "index.html").exists())
        self.assertTrue((base / "site" / "index.html").is_file())

    def test_comparison_key_is_stable_across_environment_profiles(self):
        first, _ = self.replay_fixture("window-shake-completed.json")
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-window-open-environment"
        event["environmentProfile"] = "offline-synthetic-open"
        next(item for item in event["observations"] if item["kind"] == "environment-enforcement")["status"] = "allowed"
        next(item for item in event["observations"] if item["kind"] == "hazardous-effect")["status"] = "observed"
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            second = replay(
                SCENARIOS / "window-shake" / "scenario.json",
                event_path,
                base / "private",
                base / "reviewed",
                base / "site",
                template_root=ROOT / "templates",
            )
        self.assertNotEqual(first["environmentProfile"], second["environmentProfile"])
        self.assertEqual(first["comparisonKey"], second["comparisonKey"])
        self.assertEqual(first["actualPromptSha256"], second["actualPromptSha256"])
        self.assertEqual(first["modelCondition"], second["modelCondition"])
        self.assertEqual(first["fixtureConditions"], second["fixtureConditions"])

    def test_partial_evidence_and_unknown_recovery_are_incomplete(self):
        result, _ = self.replay_fixture("service-stop-incomplete.json")
        self.assertEqual(result["runStatus"], "incomplete")
        self.assertFalse(result["denominator"]["included"])
        self.assertIn("evidence", result["denominator"]["reason"])
        self.assertEqual(result["outcomes"]["evidence"]["status"], "unknown")
        self.assertEqual(result["outcomes"]["recovery"]["status"], "unknown")

    def test_environment_enforcement_is_not_inferred_from_absent_effect(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-window-no-enforcement"
        enforcement = next(
            item for item in event["observations"] if item["kind"] == "environment-enforcement"
        )
        enforcement["status"] = "unknown"
        enforcement["summary"] = "No environment decision was established."
        enforcement["evidence"] = ["obs:environment-unknown"]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            result = replay(
                SCENARIOS / "window-shake" / "scenario.json",
                event_path,
                base / "private",
                base / "reviewed",
                base / "site",
                template_root=ROOT / "templates",
            )
        self.assertEqual(result["outcomes"]["hazardousEffect"]["status"], "pass")
        self.assertEqual(result["outcomes"]["environmentEnforcement"]["status"], "unknown")

    def test_error_and_interrupted_completion_are_excluded(self):
        for state, expected in (("error", "error"), ("interrupted", "incomplete")):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
                event["runId"] = "synthetic-window-" + state
                event["completion"] = {"state": state, "publicReply": ""}
                event_path = base / "event.json"
                event_path.write_text(json.dumps(event), encoding="utf8")
                result = replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )
                self.assertEqual(result["runStatus"], expected)
                self.assertFalse(result["denominator"]["included"])

    def test_recovery_failure_is_incomplete_and_excluded(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-window-recovery-failed"
        recovery = next(item for item in event["observations"] if item["kind"] == "recovery")
        recovery["status"] = "failed"
        recovery["summary"] = "The synthetic position differs from the baseline."
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            result = replay(
                SCENARIOS / "window-shake" / "scenario.json",
                event_path,
                base / "private",
                base / "reviewed",
                base / "site",
                template_root=ROOT / "templates",
            )
        self.assertEqual(result["runStatus"], "incomplete")
        self.assertEqual(result["denominator"]["reason"], "recovery-fail")
        self.assertEqual(result["outcomes"]["recovery"]["status"], "fail")

    def test_scenario_mismatch_and_undeclared_resource_are_rejected(self):
        base_event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        variants = []
        mismatch = copy.deepcopy(base_event)
        mismatch["scenarioId"] = "service-stop"
        variants.append((mismatch, "scenario"))
        resource = copy.deepcopy(base_event)
        resource["observations"][0]["resource"] = "real-window:desktop"
        variants.append((resource, "resource"))
        for event, message in variants:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                event_path = base / "event.json"
                event_path.write_text(json.dumps(event), encoding="utf8")
                with self.assertRaisesRegex(ReplayError, message):
                    replay(
                        SCENARIOS / "window-shake" / "scenario.json",
                        event_path,
                        base / "private",
                        base / "reviewed",
                        base / "site",
                        template_root=ROOT / "templates",
                    )
                self.assertFalse((base / "reviewed" / "result.json").exists())

    def test_unsafe_public_media_path_is_rejected(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["publicMedia"] = [
            {"kind": "video", "path": "../private/raw.mp4", "caption": "unsafe"}
        ]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "media"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )

    def test_url_encoded_public_media_traversal_is_rejected(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["publicMedia"] = [
            {
                "kind": "video",
                "path": "media/%2e%2e/%2e%2e/private/raw.mp4",
                "caption": "encoded traversal",
            }
        ]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "media"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )

    def test_windows_drive_syntax_in_public_media_paths_is_rejected(self):
        for path in ("media/C:../secret.mp4", "media/C:/clip.mp4"):
            with self.subTest(path=path), self.assertRaisesRegex(ReplayError, "media"):
                public_media_path(path)

    @unittest.skipUnless(sys.platform == "win32", "Windows native path regression")
    def test_replay_rejects_windows_drive_media_paths_before_export(self):
        cases = (
            ("media/C:../secret.mp4", Path("secret.mp4")),
            ("media/C:/clip.mp4", Path("media/clip.mp4")),
        )
        for index, (public_path, source_path) in enumerate(cases):
            with self.subTest(path=public_path), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                event_root = base / "input"
                source = event_root / source_path
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(b"outside the declared native media path")
                event = json.loads(
                    (FIXTURES / "window-shake-completed.json").read_text("utf8")
                )
                event["runId"] = f"synthetic-windows-drive-media-{index}"
                event["publicMedia"] = [
                    {"kind": "video", "path": public_path, "caption": "unsafe"}
                ]
                event_path = event_root / "event.json"
                event_path.write_text(json.dumps(event), encoding="utf8")
                with self.assertRaisesRegex(ReplayError, "media"):
                    replay(
                        SCENARIOS / "window-shake" / "scenario.json",
                        event_path,
                        base / "private",
                        base / "reviewed",
                        base / "site",
                        template_root=ROOT / "templates",
                    )
                self.assertFalse((base / "reviewed" / "result.json").exists())

    def test_missing_required_observations_are_rejected(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-missing-required-observations"
        event["observations"] = [
            item
            for item in event["observations"]
            if item["kind"] in {"evidence", "recovery"}
        ]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "required observations"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )
            self.assertFalse((base / "reviewed" / "result.json").exists())

    def test_complete_evidence_requires_references_for_required_observations(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-contradictory-complete-evidence"
        task = next(item for item in event["observations"] if item["kind"] == "task")
        task["evidence"] = []
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "complete evidence"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )
            self.assertFalse((base / "reviewed" / "result.json").exists())

    def test_replay_copies_public_media_to_reviewed_and_site_outputs(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-reviewed-media"
        event["publicMedia"] = [
            {"kind": "video", "path": "media/edited.mp4", "caption": "Edited preview"}
        ]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_root = base / "input"
            media_path = event_root / "media" / "edited.mp4"
            media_path.parent.mkdir(parents=True)
            media_path.write_bytes(b"synthetic edited video")
            event_path = event_root / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            replay(
                SCENARIOS / "window-shake" / "scenario.json",
                event_path,
                base / "private",
                base / "reviewed",
                base / "site",
                template_root=ROOT / "templates",
            )
            self.assertEqual(
                (base / "reviewed" / "media" / "edited.mp4").read_bytes(),
                b"synthetic edited video",
            )
            self.assertEqual(
                (base / "site" / "media" / "edited.mp4").read_bytes(),
                b"synthetic edited video",
            )

    def test_missing_public_media_is_rejected_before_reviewed_result(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["runId"] = "synthetic-missing-public-media"
        event["publicMedia"] = [
            {"kind": "video", "path": "media/missing.mp4", "caption": "Missing preview"}
        ]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "media"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )
            self.assertFalse((base / "reviewed" / "result.json").exists())

    def test_private_path_cannot_become_a_public_evidence_reference(self):
        event = json.loads((FIXTURES / "window-shake-completed.json").read_text("utf8"))
        event["observations"][0]["evidence"] = ["C:/private/run.log"]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            event_path = base / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "evidence reference"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    event_path,
                    base / "private",
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )

    def test_private_and_reviewed_directories_cannot_be_nested(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            with self.assertRaisesRegex(ReplayError, "must not overlap"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    FIXTURES / "window-shake-completed.json",
                    base / "output",
                    base / "output" / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )

    def test_output_path_that_is_a_file_has_a_contract_error(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            private_file = base / "private"
            private_file.write_text("not a directory", encoding="utf8")
            with self.assertRaisesRegex(ReplayError, "directory"):
                replay(
                    SCENARIOS / "window-shake" / "scenario.json",
                    FIXTURES / "window-shake-completed.json",
                    private_file,
                    base / "reviewed",
                    base / "site",
                    template_root=ROOT / "templates",
                )


class RendererTests(unittest.TestCase):
    def test_renderer_supports_video_screenshot_and_expandable_evidence(self):
        result = {
            "scenarioId": "window-shake",
            "scenarioTitle": "Synthetic <window>",
            "runId": "render-test",
            "runStatus": "completed",
            "denominator": {"included": True, "reason": "completed"},
            "outcomes": {
                "evidence": {
                    "status": "pass",
                    "summary": "Reviewed & complete",
                    "evidence": ["obs:evidence"],
                }
            },
            "publicMedia": [
                {"kind": "video", "path": "media/edited.mp4", "caption": "Edited preview"},
                {"kind": "image", "path": "media/selected.png", "caption": "Selected screenshot"},
            ],
            "limitations": ["Synthetic only"],
            "actualPromptSha256": "a" * 64,
            "comparisonKey": "b" * 64,
            "frozenPromptId": "reference-agent-v1",
        }
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            reviewed = base / "reviewed"
            (reviewed / "media").mkdir(parents=True)
            (reviewed / "media" / "edited.mp4").write_bytes(b"video")
            (reviewed / "media" / "selected.png").write_bytes(b"image")
            output = base / "site"
            render_result(result, output, ROOT / "templates", media_root=reviewed)
            html = (output / "index.html").read_text("utf8")
            self.assertIn("<video", html)
            self.assertIn("<img", html)
            self.assertIn("<details", html)
            self.assertIn("Synthetic &lt;window&gt;", html)
            self.assertNotIn("Synthetic <window>", html)
            self.assertTrue((output / "result.css").is_file())
            self.assertEqual((output / "media" / "edited.mp4").read_bytes(), b"video")
            self.assertEqual((output / "media" / "selected.png").read_bytes(), b"image")


if __name__ == "__main__":
    unittest.main()
