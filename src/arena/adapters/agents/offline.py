"""Validate recorded Agent completion without executing it."""

from typing import Any

from arena.errors import ReplayError


COMPLETION_STATES = {"completed", "error", "interrupted"}


def replay_completion(event: dict[str, Any]) -> dict[str, str]:
    completion = event.get("completion")
    if not isinstance(completion, dict):
        raise ReplayError("event completion must be an object")
    state = completion.get("state")
    if state not in COMPLETION_STATES:
        raise ReplayError("event completion state is invalid")
    public_reply = completion.get("publicReply", "")
    if not isinstance(public_reply, str):
        raise ReplayError("event completion publicReply must be a string")
    return {"state": state, "publicReply": public_reply}
