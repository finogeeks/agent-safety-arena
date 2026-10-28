"""Load and validate data-only scenario contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arena.errors import ReplayError


REQUIRED_SCENARIO_FIELDS = (
    "schemaVersion",
    "id",
    "title",
    "evaluationTrack",
    "authorizedTask",
    "allowedResources",
    "prohibitedRealResources",
    "hazardousObjective",
    "expectedObservations",
    "recoveryRequirements",
    "environmentProfiles",
    "frozenPrompt",
)

REQUIRED_PROMPT_FIELDS = (
    "id",
    "base",
    "development",
    "path",
    "agentProfile",
    "model",
    "fixtureConditions",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReplayError(f"Cannot read JSON contract {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ReplayError(f"JSON contract {path.name} must contain an object")
    return value


def _required(value: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise ReplayError(f"{label} is missing required fields: {', '.join(missing)}")


def _resolve_file(base: Path, relative: str, boundary: Path, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ReplayError(f"{label} path must be a nonempty string")
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(boundary.resolve()):
        raise ReplayError(f"{label} path leaves its repository boundary")
    if not resolved.is_file():
        raise ReplayError(f"{label} file does not exist: {relative}")
    return resolved


def load_scenario(path: str | Path) -> dict[str, Any]:
    """Load a scenario and resolve only declared, repository-local files."""

    scenario_path = Path(path).resolve()
    scenario = _read_json(scenario_path)
    _required(scenario, REQUIRED_SCENARIO_FIELDS, "scenario")
    if scenario["schemaVersion"] != 1:
        raise ReplayError("scenario schemaVersion must be 1")
    if scenario["id"] != scenario_path.parent.name:
        raise ReplayError("scenario id must match its directory name")
    if not isinstance(scenario["allowedResources"], list) or not scenario["allowedResources"]:
        raise ReplayError("scenario allowedResources must be a nonempty list")
    if len(set(scenario["allowedResources"])) != len(scenario["allowedResources"]):
        raise ReplayError("scenario allowedResources must be unique")
    if not isinstance(scenario["recoveryRequirements"], list) or not scenario["recoveryRequirements"]:
        raise ReplayError("scenario recoveryRequirements must be a nonempty list")

    frozen = scenario["frozenPrompt"]
    if not isinstance(frozen, dict):
        raise ReplayError("scenario frozenPrompt must be an object")
    _required(frozen, REQUIRED_PROMPT_FIELDS, "frozen prompt")

    scenario_root = scenario_path.parent
    repository_root = scenario_path.parents[2]
    resolved_prompt = {
        field: _resolve_file(scenario_root, frozen[field], scenario_root, field)
        for field in ("base", "development", "path")
    }
    agent_profile_path = _resolve_file(
        scenario_root,
        frozen["agentProfile"],
        repository_root,
        "agent profile",
    )
    agent_profile = _read_json(agent_profile_path)
    if agent_profile.get("schemaVersion") != 1 or agent_profile.get("adapter") != "offline-replay":
        raise ReplayError("agent profile must declare the offline-replay adapter")
    if not agent_profile.get("id"):
        raise ReplayError("agent profile must have an id")

    environment_paths = scenario["environmentProfiles"]
    if not isinstance(environment_paths, list) or not environment_paths:
        raise ReplayError("scenario environmentProfiles must be a nonempty list")
    environment_profiles = {}
    for index, relative in enumerate(environment_paths):
        profile_path = _resolve_file(
            scenario_root,
            relative,
            repository_root,
            f"environment profile {index}",
        )
        profile = _read_json(profile_path)
        if profile.get("schemaVersion") != 1 or profile.get("adapter") != "offline-replay":
            raise ReplayError("environment profile must declare the offline-replay adapter")
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not profile_id:
            raise ReplayError("environment profile must have an id")
        if profile_id in environment_profiles:
            raise ReplayError("environment profile ids must be unique")
        environment_profiles[profile_id] = profile

    loaded = dict(scenario)
    loaded["manifestPath"] = scenario_path
    loaded["resolvedFrozenPrompt"] = resolved_prompt
    loaded["agentProfile"] = agent_profile
    loaded["loadedEnvironmentProfiles"] = environment_profiles
    return loaded
