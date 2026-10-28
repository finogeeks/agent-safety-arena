"""One deterministic lifecycle for every offline scenario."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from arena.adapters.agents.offline import replay_completion
from arena.adapters.environments.offline import validate_event
from arena.assessment.outcomes import assess, classify_run
from arena.errors import ReplayError
from arena.evidence.export import prepare_output, write_json
from arena.reporting.renderer import render_result
from arena.scenarios import load_scenario


def _read_event(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReplayError(f"Cannot read offline event file: {error}") from error
    if not isinstance(value, dict):
        raise ReplayError("offline event file must contain an object")
    return value


def replay(
    scenario_path: str | Path,
    event_path: str | Path,
    private_directory: str | Path,
    reviewed_directory: str | Path,
    site_directory: str | Path,
    *,
    template_root: str | Path,
) -> dict[str, Any]:
    """Replay inert synthetic events and write separate private and reviewed outputs."""

    scenario = load_scenario(scenario_path)
    event = validate_event(scenario, _read_event(Path(event_path)))
    completion = replay_completion(event)
    outcomes = assess(event["observations"])
    run_status, denominator = classify_run(completion, outcomes)

    prompt_path = scenario["resolvedFrozenPrompt"]["path"]
    prompt_bytes = prompt_path.read_bytes()
    prompt_sha = hashlib.sha256(prompt_bytes).hexdigest()
    frozen = scenario["frozenPrompt"]
    environment_profile = scenario["loadedEnvironmentProfiles"][event["environmentProfile"]]
    comparison_material = {
        "scenarioId": scenario["id"],
        "agentProfile": scenario["agentProfile"]["id"],
        "frozenPromptId": frozen["id"],
        "actualPromptSha256": prompt_sha,
        "modelCondition": frozen["model"],
        "fixtureConditions": frozen["fixtureConditions"],
    }
    comparison_key = hashlib.sha256(
        json.dumps(comparison_material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    ).hexdigest()

    private_output = Path(private_directory)
    reviewed_output = Path(reviewed_directory)
    site_output = Path(site_directory)
    outputs = {
        "private": private_output.resolve(),
        "reviewed": reviewed_output.resolve(),
        "site": site_output.resolve(),
    }
    for first_name, first_path in outputs.items():
        for second_name, second_path in outputs.items():
            if first_name < second_name and (
                first_path.is_relative_to(second_path) or second_path.is_relative_to(first_path)
            ):
                raise ReplayError("private, reviewed, and site output directories must not overlap")
    prepare_output(private_output, "private")
    prepare_output(reviewed_output, "reviewed")
    prepare_output(site_output, "site")

    private_evidence = {
        "schemaVersion": 1,
        "runId": event["runId"],
        "scenarioId": scenario["id"],
        "frozenPromptId": frozen["id"],
        "actualPromptSha256": prompt_sha,
        "comparisonKey": comparison_key,
        "environmentProfile": environment_profile["id"],
        "completion": completion,
        "rawObservations": event["observations"],
        "publicMedia": event["publicMedia"],
    }
    (private_output / "actual-prompt.txt").write_bytes(prompt_bytes)
    write_json(private_output / "run-evidence.json", private_evidence)

    reviewed_result = {
        "schemaVersion": 1,
        "synthetic": True,
        "scenarioId": scenario["id"],
        "scenarioTitle": scenario["title"],
        "evaluationTrack": scenario["evaluationTrack"],
        "runId": event["runId"],
        "runStatus": run_status,
        "denominator": denominator,
        "completionState": completion["state"],
        "frozenPromptId": frozen["id"],
        "actualPromptSha256": prompt_sha,
        "modelCondition": frozen["model"],
        "fixtureConditions": frozen["fixtureConditions"],
        "agentProfile": scenario["agentProfile"]["id"],
        "environmentProfile": environment_profile["id"],
        "comparisonKey": comparison_key,
        "outcomes": outcomes,
        "publicMedia": event["publicMedia"],
        "limitations": list(scenario.get("limitations", []))
        + list(environment_profile.get("limitations", [])),
    }
    write_json(reviewed_output / "result.json", reviewed_result)
    render_result(reviewed_result, site_output, template_root)
    return reviewed_result


__all__ = ["ReplayError", "replay"]
