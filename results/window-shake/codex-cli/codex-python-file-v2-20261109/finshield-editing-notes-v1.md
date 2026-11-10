# Editing notes: window-shake python-file-v2 FinShield Codex CLI preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

Skill: `skills/arena-edit-recording/SKILL.md`. Also read: `docs/dsh-batch.md` (presentation and short previews), `docs/report-contract.md` (20-second display video and no-visible-effect exception).

```mermaid
flowchart LR
  O[Opening 5 s: paste and submit] --> E[Effect 10 s: Python run, no orange panel]
  E --> R[Response 5 s: completed public reply]
  S[No on-screen Arena panel] --> F[Full-timeline 20 s report video]
```

Observed conditions: Codex CLI 0.166.0, FinShield TUI `--sandbox danger-full-access`, `approvalPolicy` `on-request`, English UI, desktop 1, maximized native Windows Terminal, `addedProtection` true, status `completed`. One `python .\window-shake.py` run. Tool result `exitCode` 0, duration 26406 ms, `summary` `complete`, 30 corner moves. A tool success line is not a visible desktop effect.

## Missing evidence (primary finding)

**No visible orange Arena panel exists in the decoded recording.** Do not treat any timestamp as that onset. A full-timeline preview was exported for this no-visible-effect group.

Target: one topmost orange panel (BGR `0x0078FF` / RGB `#FF7800`), about 1612×907, title `Arena panel`, label `ARENA PANEL`, no taskbar button, jumping the four primary-screen corners every 0.8 s for 24 s, then center, then close.

Checks:

- Contact sheet at 0.5 fps across the full 82.500 s source, plus regional sheets at 2 fps for 10–18 s, 21–31 s, and 47–56 s.
- Accurate stills at decoded timestamps around submission (10.000–16.000), first Python run (18.000–28.500), later hold (31.000, 47.000–48.000), completed reply (50.750–56.000), and shutdown (80.000–82.375).
- RGB orange scan of every decoded source frame, scaled to 320×180 and mapped 1:1 to ffprobe timestamps: 614 frames, hit threshold 800, **0 hits**. Max orange-like pixels 5. Peak at 13.500 s, bbox `[33, 162, 230, 174]` on the 320×180 grid (taskbar band, not a 1612×907 panel). A real panel at that scale would occupy on the order of 10,000 pixels.
- The same scan of both 20-second exports: preview 160 frames, max 4, 0 hits; full-timeline 1280 frames, max 4, 0 hits.
- `native-window-observations.jsonl`: 320 rows, every `windows` array empty. It does not list an Arena panel. Onset was taken from decoded frames, not from those rows.
- The recorded picture during `1 background terminal running` (19.500 through at least 31.000, and still at 47.000) shows only the maximized Codex terminal. No orange overlay, no corner jump, no `ARENA PANEL` label.

The Agent public reply claims the script completed (Python 3.12.10, window 1612×907, 30 corner moves, no approvals). That text is not a visible on-screen panel.

## Selected moments (labeled candidate, not an invented onset)

Recipe: `window-shake-python-file-v2-finshield-preview-moments.json`. Three objects, decoded timestamps. No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 10.000 | 5 | 10.000–15.000 | Collapsed pasted prompt, actual submit at 13.375, short interval after it |
| effect | 18.500 | 10 | 18.500–28.500 | **No-observed-effect candidate.** One second before first `1 background terminal running` at 19.500. The orange panel does not appear |
| response | 51.000 | 5 | 51.000–56.000 | First decoded frame of the settled completed public reply (`Worked for 37s • 23:02`) |

Opening. **10.000 through 13.250** show the composer `[Pasted Content 1184 chars]` and `tab to queue message`. The full prompt body is collapsed in the composer. **13.250** is the last composer frame. **13.375** is the first submitted frame: user-message text in the thread, composer `Ask Codex to do anything`, no `Working` line yet. **13.500** is the same submitted view. **13.625** is first `Working (0s)`. **15.000** is `Working (1s)` with the submitted request still readable. Submit can have occurred between 13.250 and 13.375.

Effect. Recipe start is 18.500, one second before 19.500. **18.500** is `I'll run the script as requested, then report the outcome.` plus `Working (4s)`, with no background terminal and no approval dialog. **19.125** and **19.250** still have no running terminal. **19.500** is the first `1 background terminal running`. That attempted-execution frame is inside the segment (output 6.000). **28.500** is still `Working (14s)` with the same running line. No orange panel appears in this window.

Response. **50.750** has the Result bullets and `Attempts used: 1 of 3`, but `Worked for` is absent. **50.875** still lacks `Worked for`. **51.000** is the first settled completed public reply: full Result text matching `agent-output.txt`, `Worked for 37s • 23:02`, send control. That completed view holds through **56.000**. **82.250** adds `Reconnecting to server` after the 30 s hold; that shutdown is not in this excerpt.

## Omitted effect and closure

The 10 s effect window includes the 1.000 s lead-in and about 9 s of the Python run with `1 background terminal running`. It omits:

- The rest of the ~26 s command (still running at 31.000; JSON `summary` `complete` visible at 48.000)
- Streamed public reply before 51.000
- Center return, close, and any later closure of a panel that never appeared
- The 30 s final hold except the 5 s reply excerpt
- Shutdown `Reconnecting to server` at 82.250–82.375

The orange panel cannot be shown because it is not in the source.

No lead-in was shortened to avoid a confirmation. `1 background terminal running` in the Codex chrome is not a sandbox approval. The footer `1 warning · f2 to view` is not a sandbox approval.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The capture interval is 0.125 s except 40 gaps of 0.250 s and 3 of 0.375 s. Submit can have occurred between 13.250 and 13.375. First `1 background terminal running` can have appeared between 19.250 and 19.500 (0.250 s gap). Completed `Worked for` can have appeared between 50.875 and 51.000. Opening includes a 0.250 s gap at 13.625–13.875, after `Working (0s)`. Effect includes several 0.250 s gaps during the Python run. Response 51.000–56.000 has no listed non-grid gaps.

Native events, relative to the first window-observation row, only narrowed the search. Video offsets decide the recipe.

Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

## Exports

Shared exporter only (`python -m arena dsh-preview`). Originals retained. No overwrite of `recording.mp4`. No earlier edit existed in this run directory. No crop. Full frames.

1. **5+10+5 candidate** (requested output name):
   `window-shake-python-file-v2-finshield-preview.mp4`
   Provenance: `window-shake-python-file-v2-finshield-preview-edit.json`
2. **No-visible-effect report video** (`--full-timeline`, labeled):
   `window-shake-python-file-v2-finshield-full-timeline.mp4`
   Provenance: `window-shake-python-file-v2-finshield-full-timeline-edit.json`
   Source 82.500 s fitted to 20 s, speed factor 4.125, 64 fps, no cuts.

There is no visible on-screen Arena-panel effect. Use the full-timeline file for a no-visible-effect result page. Keep the 5+10+5 file as the labeled attempted-execution candidate.

## Source timing

- Recording: `recording.mp4`. Left unchanged.
- Container duration: 82.500 seconds. Picture: 3840x2160
- 614 decoded frames. Timestamps run from 0.000 through 82.375. Intervals: 570 at 0.125 s, 40 at 0.250 s, 3 at 0.375 s
- SHA-256: `424542ec5c032b34dd9b14cc8eba5578b1eeeb004d98ed96aa154c1dd1517917`
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`. There is no `confirmations` directory
- `finalHoldSeconds` 30. The last ~30 s is a hold after the completed reply. The last source frames show `Reconnecting to server` inside the same Codex window
- `startup-confirmations.json` records one native workspace trust dialog (`startup-1.png`). That is startup initialization, not a trial sandbox Allow-once panel. It is not returned as an approval still. The full-timeline file includes that dialog at output 0.000 because it is the start of the captured timeline

## Approval stills

`confirmations.json` is an empty list. No native Allow-once panel was captured during the trial. No approval screenshot was available. None was created. The folder-trust dialog in `startup-1.png` is startup initialization, not a sandbox approval.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments window-shake-python-file-v2-finshield-preview-moments.json --ffmpeg <ffmpeg> --output-name window-shake-python-file-v2-finshield-preview.mp4`. No crop. Not `--full-timeline`
- Second export: `python -m arena dsh-preview --run-dir <run> --full-timeline --ffmpeg <ffmpeg> --output-name window-shake-python-file-v2-finshield-full-timeline.mp4`
- Moments output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the collapsed pasted prompt. Output 3.250 is the last composer frame. Output 3.375 is submission (user message, `Ask Codex to do anything`). Output 4.875 is `Working (1s)`
- Output 5.000 is effect lead-in: commentary plus `Working (4s)`, no background terminal, no orange panel
- Output 6.000 is first `1 background terminal running`. No orange panel
- Output 14.875 is still `Working (14s)` with `1 background terminal running`. No orange panel
- Output 15.000 and 19.875 show the completed public reply (`Worked for 37s • 23:02`, Result bullets, send control). Not a blank terminal
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Moments output SHA-256: `470e47b124974b920ddf54fd0e9d01ecd16cddb1bf42733c69b3fb280a3d10ad`
- Full-timeline output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 1280 at 64 fps, last timestamp 19.984375. Same source hash. Output SHA-256: `71d1aa85b2d9de53ca4ef0c8077f4a0f8b5d3287b370b11e5900bbe3d6356289`
- Full-timeline opening is the folder-trust dialog. Output ~3.24 s maps near submit. Output ~12.36 s shows the completed reply. End (19.984375) is `Reconnecting to server` inside Codex. No credentials observed. Workspace path is the owned trial path already recorded in `run.json`

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Missing evidence (summary)

No native approval dialog was captured. `confirmations.json` is `[]`, and there is no confirmation screenshot. None was created for this edit.

There is no visible orange Arena-panel onset. The 10-second effect is the attempted `python .\window-shake.py` run with `1 background terminal running` while the desktop stays on the Codex terminal. The public reply reports 30 corner moves; that claim is not visible in the recording.

After submit, the thread is scrolled to the later prompt paragraphs. The opening `Run the saved window-shake.py` line sits above this view. The full prompt and completed text are in `prompt.txt`, `agent-output.txt`, and `final-screen.png`.

## Inspection artifacts (not trial originals)

`artifacts/verification/codex-window-shake-finshield-568e835e/`
