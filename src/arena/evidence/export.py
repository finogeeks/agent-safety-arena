"""Write deterministic JSON without crossing private and reviewed boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arena.errors import ReplayError


def prepare_output(path: Path, label: str) -> None:
    try:
        if path.exists() and not path.is_dir():
            raise ReplayError(f"{label} output path must be a directory")
        if path.exists() and any(path.iterdir()):
            raise ReplayError(f"{label} output directory must be new or empty")
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ReplayError(f"Cannot prepare {label} output directory: {error}") from error


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )
