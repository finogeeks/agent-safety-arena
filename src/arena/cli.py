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
    doctor = subcommands.add_parser('doctor', help='Check repository and local profile files without starting products')
    doctor.add_argument('--root', type=Path, default=root)
    doctor.add_argument('--profile', type=Path)
    doctor.add_argument('--environment', choices=('native', 'finshield'), default='native')
    doctor.add_argument('--lock', type=Path, help='Version-specific FinShield dependency file selected by the case')
    site = subcommands.add_parser('build-site', help='Build an offline catalog from reviewed case/Agent comparisons')
    site.add_argument('--results', type=Path, default=root / 'results')
    site.add_argument('--output', type=Path, required=True)
    replay_command = subcommands.add_parser("replay", help="Replay a synthetic offline event file")
    replay_command.add_argument("--scenario", required=True, type=Path)
    replay_command.add_argument("--events", required=True, type=Path)
    replay_command.add_argument("--private-dir", required=True, type=Path)
    replay_command.add_argument("--result-dir", required=True, type=Path)
    replay_command.add_argument("--site-dir", required=True, type=Path)
    replay_command.add_argument("--template-root", type=Path, default=root / "templates")
    live = subcommands.add_parser("dsh-run", help="Record a real DSH trial and capture native confirmations before choices")
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
    live.add_argument("--confirmation-mode", choices=("capture-then-allow-once", "manual"),
                      default="capture-then-allow-once")
    live.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    review = subcommands.add_parser("dsh-review", help="Validate edited analysis.json and write analysis.md")
    review.add_argument("--run-dir", required=True, type=Path)
    batch = subcommands.add_parser('dsh-batch', help='Collect case manifests with one shared recording controller')
    batch.add_argument('--case', required=True, action='append', type=Path, dest='cases')
    local_profile = root/'profiles/recording/windows-pro.local.json'
    batch.add_argument('--profile', type=Path,
                       default=local_profile if local_profile.is_file() else root/'profiles/recording/windows-pro.json')
    batch.add_argument('--output-root', type=Path, default=root/'artifacts/runs')
    generic=subcommands.add_parser('collect-batch',help='Record case manifests through the shared Agent controller')
    generic.add_argument('--case',required=True,action='append',type=Path,dest='cases')
    generic.add_argument('--profile',required=True,type=Path)
    generic.add_argument('--output-root',type=Path,default=root/'artifacts/runs')
    generic.add_argument('--preflight',action='store_true',help='Record native presentation without submitting a prompt')
    preview = subcommands.add_parser('dsh-preview', help='Join opening, effect, and response video excerpts')
    preview.add_argument('--run-dir',required=True,type=Path)
    preview.add_argument('--moments',required=True,type=Path)
    preview.add_argument('--ffmpeg',type=Path)
    preview.add_argument('--output-name',default='overview.mp4')
    plan = subcommands.add_parser('plan',help='Plan Agent/environment pairs without model calls')
    plan.add_argument('--suite',required=True,type=Path)
    plan.add_argument('--root',type=Path,default=root)
    plan.add_argument('--output',required=True,type=Path)
    for name in ('preflight','collect'):
        entry = subcommands.add_parser(name,help='Prepare or collect one supported planned entry')
        entry.add_argument('--plan',required=True,type=Path)
        entry.add_argument('--entry',required=True)
        entry.add_argument('--root',type=Path,default=root)
        entry.add_argument('--profile',required=True,type=Path)
        entry.add_argument('--output-root',type=Path,default=root/'artifacts/runs')
    report = subcommands.add_parser('report',help='Export bilingual reports sharing reviewed evidence')
    report.add_argument('--record',required=True,type=Path)
    report.add_argument('--output',required=True,type=Path)
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
        if arguments.command == 'doctor':
            from arena.setup import check_repository
            result = check_repository(arguments.root, arguments.profile, arguments.environment, arguments.lock)
            print(json.dumps(result))
            return 0 if result['ok'] else 2
        if arguments.command == 'build-site':
            from arena.reporting.site import build_site
            print(json.dumps(build_site(arguments.results, arguments.output)))
            return 0
        if arguments.command=='plan':
            from arena.runner.suite import build_plan
            from arena.runner.trial import save
            result=build_plan(arguments.suite,arguments.root)
            if arguments.output.exists():
                raise ValueError('Plan output already exists; retain it and choose a new filename')
            arguments.output.parent.mkdir(parents=True,exist_ok=True)
            save(arguments.output,result)
            print(json.dumps(dict(plan=str(arguments.output),entries=len(result['entries']))))
            return 0
        if arguments.command in {'preflight','collect'}:
            from arena.runner.suite import collect_entry
            result=collect_entry(arguments.plan,arguments.entry,arguments.root,arguments.profile,
                                 arguments.output_root,preflight=arguments.command=='preflight')
            print(json.dumps(result))
            return 0 if result['status']=='completed' else 2
        if arguments.command=='report':
            from arena.reporting.bilingual import export_reports
            print(json.dumps(export_reports(arguments.record,arguments.output)))
            return 0
        if arguments.command == 'dsh-preview':
            from arena.evidence.preview import export_preview
            result = export_preview(arguments.run_dir,arguments.moments,arguments.ffmpeg,arguments.output_name)
            print(json.dumps({'preview':str(result)}))
            return 0
        if arguments.command in {'dsh-batch','collect-batch'}:
            from arena.runner.batch import collect_batch, load_profile
            result = collect_batch(arguments.cases, load_profile(arguments.profile), arguments.output_root,
                                   preflight=getattr(arguments,'preflight',False))
            print(json.dumps(result))
            return 0 if result['status'] == 'completed' else 2
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
