"""Validate synthetic environment observations and public media references."""

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any

from arena.errors import ReplayError


OBSERVATION_KINDS = {
    "task",
    "agent-decision",
    "approval",
    "hazardous-effect",
    "environment-enforcement",
    "evidence",
    "recovery",
}

MEDIA_EXTENSIONS = {
    "video": {".mp4"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
}


def _validate_media(media: Any) -> list[dict[str, str]]:
    if not isinstance(media, list):
        raise ReplayError("public media must be a list")
    checked = []
    for item in media:
        if not isinstance(item, dict):
            raise ReplayError("public media entry must be an object")
        kind = item.get("kind")
        path_value = item.get("path")
        caption = item.get("caption")
        if kind not in MEDIA_EXTENSIONS or not isinstance(path_value, str) or not isinstance(caption, str):
            raise ReplayError("public media entry has invalid kind, path, or caption")
        path = PurePosixPath(path_value)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "media":
            raise ReplayError("public media path must stay below the media directory")
        if path.suffix.lower() not in MEDIA_EXTENSIONS[kind]:
            raise ReplayError("public media extension does not match its kind")
        checked.append({"kind": kind, "path": path.as_posix(), "caption": caption})
    return checked


def validate_event(scenario: dict[str, Any], event: Any) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("schemaVersion") != 1:
        raise ReplayError("event schemaVersion must be 1")
    run_id = event.get("runId")
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", run_id):
        raise ReplayError("event runId must be a lowercase stable identifier")
    if event.get("scenarioId") != scenario["id"]:
        raise ReplayError("event scenario does not match the selected scenario")
    if event.get("environmentProfile") not in scenario["loadedEnvironmentProfiles"]:
        raise ReplayError("event environment profile is not allowed by the scenario")
    observations = event.get("observations")
    if not isinstance(observations, list):
        raise ReplayError("event observations must be a list")
    allowed = set(scenario["allowedResources"])
    checked_observations = []
    for item in observations:
        if not isinstance(item, dict):
            raise ReplayError("observation must be an object")
        if item.get("kind") not in OBSERVATION_KINDS:
            raise ReplayError("observation kind is invalid")
        if item.get("resource") not in allowed:
            raise ReplayError("observation resource is outside the scenario boundary")
        if not isinstance(item.get("status"), str) or not isinstance(item.get("summary"), str):
            raise ReplayError("observation status and summary must be strings")
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(ref, str) for ref in evidence):
            raise ReplayError("observation evidence must be a list of strings")
        if any(not re.fullmatch(r"obs:[a-z0-9][a-z0-9-]{0,63}", ref) for ref in evidence):
            raise ReplayError("public evidence reference must be a stable observation id")
        checked_observations.append(
            {
                "kind": item["kind"],
                "resource": item["resource"],
                "status": item["status"],
                "summary": item["summary"],
                "evidence": list(evidence),
            }
        )
    checked = dict(event)
    checked["observations"] = checked_observations
    checked["publicMedia"] = _validate_media(event.get("publicMedia", []))
    return checked
