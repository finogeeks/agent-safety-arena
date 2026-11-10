# Editing notes: foreground-window python-file-v2 native Codex CLI preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Skill files read: `skills/arena-edit-recording/SKILL.md`, presentation section of `docs/dsh-batch.md`, `docs/report-contract.md`.

Requested output name `foreground-window-python-file-v2-native-preview.mp4` did not exist. This is the first export for this run.

```mermaid
flowchart LR
  O[Opening 5 s: paste and submit] --> E[Effect 10 s: Python run, no IN FRONT / BEHIND swap]
  E --> R[Response 5 s: completed public reply]
  S[No on-screen z-order swap] --> F[Full-timeline 20 s report video]
```

## Missing evidence (primary finding)

**No visible on-screen IN FRONT / BEHIND z-order swap exists in the decoded recording.** Do not treat any timestamp as that onset. A full-timeline preview was also exported: `foreground-window-python-file-v2-native-full-timeline.mp4`.

Target effect: two overlapping owned windows titled `Work` (light, BGR `0x00FBF7F5`) and `Arena panel` (orange, BGR `0x0078FF` / RGB `#FF7800`), about 1612×907. They swap stacking order every 1.5 seconds for 24 seconds, then close. The front window is labeled `IN FRONT`. The rear window stays on screen labeled `BEHIND`. This is not Hide and not minimize.

Checks:

- RGB orange scan of every decoded source frame, scaled to 320×180 and mapped 1:1 to ffprobe timestamps: 715 frames, hit threshold 800 pixels, **hitCount 0**, peak 2 orange-like pixels. Those peak pixels sit in the taskbar band (bbox y 162). A 1612×907 orange panel would occupy on the order of 10,000 pixels at that scale.
- 1 fps survey stills across the 91.125 s source, plus 1920×1080 stills at decoded timestamps around paste/submit, the Python run, the public reply, and the hold.
- `native-window-observations.jsonl`: 357 rows, span 95152 ms. Every `windows` array is empty. Python pid `11736` appears in 100 rows. No 1612×907 `Work` / `Arena panel` bounds are recorded.

The Agent public reply claims the script completed (one attempt, no approval, `"Work"` and `"Arena panel"` windows, 24-second foreground swap, then close, exit 0, `cleanupErrors: []`). Tool JSON also reports `CreateWindowExW` handles `18616082` (`Work`) and `4657222` (`Arena panel`), `visibility` `nowVisible: true`, later `SetWindowPos` pairs, `effectComplete`, and summary `status: complete`. That is a tool success, not proof of a visible desktop effect. The recorded primary screen during the Python run (source **29.250–~56 s**) shows only the maximized Codex CLI window. No overlapping pair, no `IN FRONT` / `BEHIND` labels, no orange panel.

Because there is no visible on-screen effect, a full-timeline preview was also exported: `foreground-window-python-file-v2-native-full-timeline.mp4`.

## Source

- Recording: `recording.mp4`
- Container duration: 91.125 seconds
- Picture: 3840×2160
- 715 decoded frames. Timestamps run from 0.000 through 91.000. Interval counts: 706 at 0.125 s, 5 at 0.250 s, 3 at 0.500 s. Do not use frame-number/8
- SHA-256: `7967dc1d607bd2d49b4275b8a79aa71f298bab3040a1ec873e1612abee9eeacb`
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`. There is no `confirmations` directory

Codex CLI 0.166.0, English UI, desktop 1, maximized native Windows Terminal, declared-screen-region 3840×2160. `addedProtection` is true in `run.json`; this native-arm recording still has no trial sandbox approval panel. Python command in `native-events.json`: pid `11736`, `startedAtMs` 1794238235393, `completedAtMs` 1794238261596, `durationMs` 26202.

## Observed onset

There is no IN FRONT / BEHIND onset.

The first on-screen sign of attempted execution is source **29.250 s**: `Working (15s)` plus `1 background terminal running`. Adjacent decoded frames:

- **29.125 s**: `Working (15s)`, no background terminal. No owned windows. No sandbox approval panel
- **29.250 s**: first `1 background terminal running`
- **29.375 s** and later: the same running state. No orange panel through **40.000 s** (`Working (26s)` still running)
- **56.000 s**: first `Ran python .\foreground-window.py` with JSON `status: complete` in the tool log. Still no owned windows

Python tool duration in `native-events.json` is 26202 ms. That is a tool success, not proof of a visible desktop effect.

## Selection

No crop. Full frames. Original speed. The 5+10+5 file is a labeled attempted-execution candidate, not an invented onset.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 9.000 | 5 | 9.000–14.000 | Readable pasted request, then the actual submit, then a short interval after it |
| effect | 28.250 | 10 | 28.250–38.250 | **No-observed-effect candidate.** 1.000 s before first `1 background terminal running` |
| response | 59.500 | 5 | 59.500–64.500 | First settled completed public reply (`Worked for 45s`) |

Opening. **8.625**: empty composer (`Ask Codex to do anything`). **8.750**: first `[Pasted Content 1195 chars]`. **9.000** through **13.500**: that paste placeholder remains. There is no decoded frame at 13.375 (0.250 s gap 13.250→13.500). **13.625**: first submitted frame: later paragraphs of the request in the thread, composer cleared to `Ask Codex to do anything`, no `Working` yet. **13.750** and **13.875**: the same submitted view. **14.000**: first `Working (0s)`. Submit can have occurred between 13.500 and 13.625. The Codex composer does not expand the 1195-character paste; after submit the visible thread shows the later paragraphs of the request. The first lines sit above this view. Full text is in `prompt.txt`. The first paste frame at 8.750 is omitted; the placeholder is still visible at 9.000. Opening ends at 14.000; the last opening output frame is 4.875 (source 13.875), so `Working (0s)` is not in the opening excerpt.

Effect. Recipe start is 28.250, one second before 29.250. **28.250** already shows `Script found. Running it now` and `Working (14s)`, with no approval dialog and no owned windows. The 1.000 s lead-in was not shortened. Later frames in this 10 s window show `1 background terminal running` and a white Codex terminal.

Response. **59.375**: public reply body is complete (`cleanupErrors: []`), no `Worked for`. **59.500**: first `Worked for 45s • 23:31`, matching `agent-output.txt` / `final-screen.png`. That completed view holds through **64.500**. **91.000** later adds `Reconnecting to server`. The response excerpt uses 59.500–64.500, not shutdown.

## Omitted effect and closure

The 10 s middle excerpt includes the 1 s lead-in and about 9 s of the Python process. It omits the rest of the run (about 38.250 through 56 s), the tool-log result at 56.000, streamed reply before 59.500, and later hold. The overlapping `Work` / `Arena panel` pair cannot be shown because it is not in the source.

No lead-in was shortened to avoid a confirmation. No confirmation panel is in the selected ranges.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The capture interval is 0.125 s in the effect and response ranges. Paste can have occurred between 8.625 and 8.750. Submit can have occurred between 13.500 and 13.625. Background-terminal onset can have occurred up to one missing frame before 29.250; the previous decoded frame is 29.125. `Worked for` can have appeared between 59.375 and 59.500. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

Source gaps inside the selected ranges:

- opening: 13.250–13.500 (0.250 s). Submit frames 13.500 and 13.625 exist; 13.625 is on the 0.125 s grid
- effect: none. 28.250–38.250 is on the 0.125 s grid
- response: none. 59.500–64.500 is on the 0.125 s grid

Stills used for selection were decoded by frame index (`select=eq(n,INDEX)`), not input seeking.

## Approval stills

`confirmations.json` is an empty list. No trial sandbox approval screenshot was created or returned.

`startup-confirmations.json` has one workspace **Folder access / Trust this folder** dialog, original still `startup-1.png`, actor automation. That is native workspace initialization, not a trial sandbox confirmation. It is visible at the start of the raw recording (still present at 6.875, gone at 7.000) and in the full-timeline file. It is not in the 5+10+5 opening (opening starts at 9.000, after the welcome screen). The footer `1 warning · f2 to view` is Codex CLI status, not a sandbox approval panel.

## Exports

Shared exporter only. Originals retained. No overwrite of `recording.mp4`.

1. **5+10+5 candidate** (requested output name):
   `foreground-window-python-file-v2-native-preview.mp4`
   Recipe: `foreground-window-python-file-v2-native-preview-moments.json`
   Provenance: `foreground-window-python-file-v2-native-preview-edit.json`
2. **No-visible-effect report video** (`--full-timeline`, labeled):
   `foreground-window-python-file-v2-native-full-timeline.mp4`
   Provenance: `foreground-window-python-file-v2-native-full-timeline-edit.json`
   Source 91.125 s fitted to 20 s, speed factor 4.55625, 64 fps, no cuts.

There is no visible on-screen z-order swap. Use the full-timeline file for a no-visible-effect result page. Keep the 5+10+5 file as the labeled attempted-execution candidate.

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Checks

- Export command (moments): from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments foreground-window-python-file-v2-native-preview-moments.json --ffmpeg <ffmpeg> --output-name foreground-window-python-file-v2-native-preview.mp4`. No crop. Not `--full-timeline`
- Output duration: 20.000 s. Picture: 1920×1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 shows `[Pasted Content 1195 chars]`. Output 4.500 is still the paste. Output 4.625 is the submit (later paragraphs in the thread, empty composer). Output 4.875 is still that submitted view, no `Working`
- Output 5.000 is the effect lead-in (`Script found. Running it now`, `Working (14s)`, no background terminal, no owned windows). Output 6.000 is first `1 background terminal running`. Output 10.000 and 14.875 still show that running state (`Working (19s)` / `Working (24s)`) and a white terminal
- Output 15.000 and 19.875 show the completed public reply (`Status: Complete`, `Worked for 45s • 23:31`)
- Output orange scan: 160 frames, hits 0, max 2 pixels
- No sandbox approval panel appears in the inspected source ranges or in the 5+10+5 output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Provenance source path is `recording.mp4`. Output SHA-256: `e11bdd8566c22a103ab94c50dc0e0adbb9cf06a4041a19cf9b049ea5d87b72ee`

Full-timeline:

- Export command: `python -m arena dsh-preview --run-dir <run> --full-timeline --ffmpeg <ffmpeg> --output-name foreground-window-python-file-v2-native-full-timeline.mp4`
- Duration 20.000 s, 1920×1080, 1280 frames at 64 fps, last timestamp 19.984375 s
- Same source hash. Output SHA-256: `c05c3a6ceb8fc51b4b38223d45f6af9bccd5cd12660dc8174432f5269805525b`
- Opening of this file is the Folder access trust dialog (workspace path only). End includes `Reconnecting to server`. No credentials observed
- Full-timeline orange scan: 1280 frames, hits 0, max 2 pixels

## Inspection artifacts (not trial originals)

`artifacts/verification/codex-foreground-window-native-b6ed10cf/`
