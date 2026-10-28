"""Command-line entry point for deterministic offline replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from arena.errors import ReplayError
from arena.runner.lifecycle import replay


def parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[2]
    command = argparse.ArgumentParser(prog="arena")
    subcommands = command.add_subparsers(dest="command", required=True)
    replay_command = subcommands.add_parser("replay", help="Replay a synthetic offline event file")
    replay_command.add_argument("--scenario", required=True, type=Path)
    replay_command.add_argument("--events", required=True, type=Path)
    replay_command.add_argument("--private-dir", required=True, type=Path)
    replay_command.add_argument("--result-dir", required=True, type=Path)
    replay_command.add_argument("--site-dir", required=True, type=Path)
    replay_command.add_argument("--template-root", type=Path, default=root / "templates")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        result = replay(
            arguments.scenario,
            arguments.events,
            arguments.private_dir,
            arguments.result_dir,
            arguments.site_dir,
            template_root=arguments.template_root,
        )
    except ReplayError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "runId": result["runId"],
                "runStatus": result["runStatus"],
                "result": str(arguments.result_dir / "result.json"),
                "site": str(arguments.site_dir / "index.html"),
            }
        )
    )
    return 0
