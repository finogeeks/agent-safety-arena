"""Offline replay and private live DSH recording commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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
    live = subcommands.add_parser("dsh-run", help="Record a real DSH trial with manual native confirmations")
    live.add_argument("--prompt", required=True, type=Path)
    live.add_argument("--target", required=True, help="Declared controlled operation and resource")
    live.add_argument("--revision", required=True)
    live.add_argument("--reason", required=True, help="Reason for this prompt revision")
    live.add_argument("--ffmpeg", required=True, type=Path)
    live.add_argument("--input-file", type=Path, help="Synthetic data copied into the new owned workspace")
    live.add_argument("--output-root", type=Path, default=root / "artifacts" / "runs")
    live.add_argument("--dsh-entry", type=Path,
                      default=Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@deepseek-ai/dsh/lib/bin.js")
    live.add_argument("--chrome", type=Path)
    live.add_argument("--node", default="node")
    live.add_argument("--timeout", type=float, default=1800)
    live.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    review = subcommands.add_parser("dsh-review", help="Validate edited analysis.json and write analysis.md")
    review.add_argument("--run-dir", required=True, type=Path)
    return command


def live_dependencies(arguments):
    if sys.platform != "win32":
        raise ValueError("The first DSH recorder supports Windows only")
    node = shutil.which(str(arguments.node))
    if not node:
        raise ValueError("Node.js 24 or later is required")
    candidates = [arguments.chrome] if arguments.chrome else [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"]
    chrome = next((path for path in candidates if path and path.is_file()), None)
    if not chrome:
        raise ValueError("Chrome was not found; supply --chrome")
    for path, label in ((arguments.ffmpeg, "FFmpeg"), (arguments.dsh_entry, "DSH entry"),
                        (arguments.prompt, "prompt")):
        if not path.is_file():
            raise ValueError(f"{label} is not a file: {path}")
    if arguments.input_file and not arguments.input_file.is_file():
        raise ValueError("--input-file must name a synthetic data file")
    if arguments.region and (arguments.region[2] < 2 or arguments.region[3] < 2):
        raise ValueError("Recording region must be at least 2 by 2 pixels")
    options = {"creationflags": subprocess.CREATE_NO_WINDOW}
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True, **options)
    if int(version.stdout.strip().lstrip("v").split(".")[0]) < 24:
        raise ValueError("Node.js 24 or later is required")
    for flag, capability in (("-devices", "gdigrab"), ("-encoders", "libx264")):
        result = subprocess.run([str(arguments.ffmpeg.resolve()), "-hide_banner", flag],
                                capture_output=True, text=True, timeout=10, check=True, **options)
        if capability not in result.stdout + result.stderr:
            raise ValueError(f"FFmpeg lacks {capability}")
    return node, chrome


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "dsh-review":
            from arena.assessment.confirmation import review_trial
            print(json.dumps({"analysis": str(review_trial(arguments.run_dir))}))
            return 0
        if arguments.command == "dsh-run":
            from arena.adapters.agents.dsh import DshAgent
            from arena.adapters.agents.dsh_browser import DshBrowser
            from arena.evidence.recording import BrowserRecorder, DesktopRecorder
            from arena.runner.trial import run_trial
            node, chrome = live_dependencies(arguments)
            browser = DshBrowser(node, chrome, arguments.region)
            recorder = (DesktopRecorder(arguments.ffmpeg.resolve(), arguments.region) if arguments.region
                        else BrowserRecorder(arguments.ffmpeg.resolve(), browser))
            result = run_trial(vars(arguments), agent=DshAgent(node, arguments.dsh_entry.resolve()),
                               browser=browser, recorder=recorder)
            print(json.dumps({"runId": result["runId"], "status": result["status"],
                              "directory": result["directory"], "errors": result["errors"]}))
            return 0 if result["status"] == "completed" else 2
        result = replay(
            arguments.scenario,
            arguments.events,
            arguments.private_dir,
            arguments.result_dir,
            arguments.site_dir,
            template_root=arguments.template_root,
        )
    except (ReplayError, ValueError, OSError, subprocess.SubprocessError) as error:
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
