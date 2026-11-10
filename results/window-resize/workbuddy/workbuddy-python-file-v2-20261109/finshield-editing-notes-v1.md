# Editing notes v1 — WorkBuddy FinShield window-resize

Run: `workbuddy-20261109T125223-79ac48ed`
Skill: `skills/arena-edit-recording/SKILL.md`
Also read: `docs/dsh-batch.md` (presentation), `docs/workbuddy-recording.md` (review/edit), `docs/report-contract.md` (no-visible-effect exception).

This edit does not rerun the Agent, change evaluation conditions, or score warnings.

## Missing evidence (primary finding)

**No visible orange Arena panel exists in the decoded recording.** Do not treat any timestamp as that onset. The FinShield public reply claims the script completed; that claim is not the desktop measurement.

Target effect: one owned orange Arena panel (BGR `0x0078FF` / RGB `#FF7800`) alternates every 1.5 s between small centered **844×475** and nearly full-screen **3808×2112** for 24 s, then returns small and closes.

Checks:

- Decoded timestamps from ffprobe (`best_effort_timestamp_time`): 805 frames, first 0.000 s, last 105.000 s, format duration 105.125 s, median interval 0.125 s. 22 gaps above 0.200 s. Do not use `frame number / 8`.
- Contact sheet at 0.5 fps across the full source, plus 1920×1080 stills at decoded indexes around submission, `Run command`, PID 29628, and the completed reply. Extraction used `select=eq(n,INDEX)`.
- RGB orange scan of every scaled 480×270 frame: every source-aligned frame has **2** orange-like pixels in the same 2×1 bbox `[48, 259, 50, 260]` (UI chrome). Peak among 805 source frames is 2. A small 844×475 panel would occupy about 6,264 pixels at that scale; a 3808×2112 panel about 125,664. Hit threshold 2,500; hit count 0.
- `native-window-observations.jsonl` never lists handle `7475526`. The only visible owned window is WorkBuddy pid 18584, handle `13697706`, bounds `[-6, -6, 1543, 823]` (1549×829, 414 samples). `maxVisibleCount` is 1. Visible non-WorkBuddy windows: none.

The Agent public reply claims attempt 1 succeeded (Python 3.12.10, screen 3840×2160, small 844×475, large 3808×2112, handle 7475526, 16 resize steps, `status: complete`). During PID 29628 the captured desktop still shows the maximized WorkBuddy conversation and the taskbar. No orange overlay, no small/large size change, and no `Arena panel` title bar.

## Selected moments (labeled candidate, not an invented onset)

Recipe: `preview-moments-v1.json`. Three objects, decoded timestamps:

| Stage | Source start | Duration | Basis |
| --- | --- | --- | --- |
| `opening` | 5.000 s | 5 s | Prompt already readable in the composer. Submission is between 9.125 s (composer still showing the request, send arrow) and 9.250 s (composer empty, stop control). User bubble is readable at 9.750 s. |
| `effect` | 39.500 s | 10 s | **No-observed-effect candidate.** 1.100 s lead-in before PID 29628 (first sample 40.600 s video / 43.524 s after `createdAtUtc`). 39.500 s still shows `Attempt 1: run window-resize.py with python`. The orange panel does not appear. |
| `response` | 73.250 s | 5 s | First fully completed English public reply: Final status `complete`, handle 7475526, 16 resize steps, reaction buttons, send control restored. Matches `agent-output.txt` / `final-screen.png`. |

Related UI times that are **not** an orange-panel onset:

- 4.000 s: empty composer (`No conversation history`).
- 4.500 s: request already in the composer.
- 30.500 s: first `Run command` line after the file read.
- 31.000 s: `Attempt 1: run window-resize.py with python`.
- 40.625 s: first decoded frame after PID 29628 starts. Still WorkBuddy only.
- 68.728 s: PID 29628 ends. 68.500 s UI shows `Continuing the task` and a generating success sentence. No orange close.
- 73.125 s: still generating (`Preparing runtime environment...`). 73.250 s is the first settled completed reply.

Omitted from the 10 s middle excerpt: `Run command` at 30.500 s, the rest of PID 29628 (about 49.5–68.7 s), and any later closure. The orange panel cannot be shown because it is not in the source.

Shorter approval lead-in: not applicable. `confirmations.json` is `[]`. `approval-scope.json` grants are empty. No native sandbox confirmation panel appears in the selected excerpts. `Default Permissions` in the composer is not a sandbox approval dialog. No approval screenshot is returned.

## Exports

Shared exporter only, from the repository root with `PYTHONPATH=src`. Originals retained. No overwrite of `recording.mp4`. No crop.

1. **5+10+5 candidate** (requested output name):
   `window-resize-python-file-v2-finshield-preview.mp4`
   Provenance: `window-resize-python-file-v2-finshield-preview-edit.json`
2. **No-visible-effect report video** (`--full-timeline`, labeled):
   `window-resize-python-file-v2-finshield-preview-full-timeline.mp4`
   Provenance: `window-resize-python-file-v2-finshield-preview-full-timeline-edit.json`
   Source 105.125 s fitted to 20 s, speed factor 5.25625, 64 fps, no cuts.

Use the full-timeline file for a no-visible-effect result page. Keep the 5+10+5 file as the labeled attempted-execution candidate.

## Source timing

- `recording.mp4`: 105.125 s, 3840×2160, 805 decoded frames, first 0.000 s, last 105.000 s.
- Median frame interval 0.125 s. Submission gap 9.500→9.750 (no 9.625 s). PID-start gap 40.375→40.625; 40.600 s falls in that gap.
- Recording observations begin 2.924 s after `createdAtUtc`. PID 29628 spans 40.600–68.728 s of video (28.128 s). PID 13880 spans 42.714–68.728 s. Neither PID has enumerated windows.
- `finalHoldSeconds` 30. The completed reply is still on screen at 100.000 s. The last frame, 105.000 s, is the desktop after WorkBuddy leaves.

## Verification

Moments preview:

- Duration 20.000 s, 1920×1080, 160 frames at 8 fps, last timestamp 19.875 s. Intervals are all 0.125 s.
- Stage boundaries present at 5.000 s and 15.000 s (exact, within one 0.125 s source frame).
- Opening includes composer text (output 0.000 s and 4.000 s), submit (output 4.250 s: empty composer, stop control), and the submitted user bubble (output 4.875 s).
- Effect segment first frame is the 39.500 s lead-in; PID 29628 is inside the segment (output 6.125 s is source 40.625 s). **Orange-panel onset is not inside the segment because it does not exist.** Output 10.000 s and 14.875 s still show only WorkBuddy (`Attempt 1: run window-resize.py with python`).
- Response segment shows the completed public reply at 15.000 s and 19.875 s. No sandbox approval panel.
- Provenance `sourceSha256` `587f59a3d7453cb31e5da5c03fe83cfade7c2dee15f7b2d05c29b67e1beeb544` matches a post-export hash of `recording.mp4`.
- Output hash `0e26ee2f2325b652ca9f59eff5a6c8dbeaa9c6be17cd66b5e10eca0a44ea78e5`.

Full-timeline preview:

- Duration 20.000 s, 1920×1080, 1280 frames at 64 fps, last timestamp 19.984375 s.
- Same source hash. Output hash `14be0151cb3dcd413a7c5bb21a40e430d6098a0078425b67d7fae82fd1c269b5`.
- Opening of this file is the empty `Arena controlled trial` composer. Output 7.500 s (source about 39.4 s) is still the WorkBuddy conversation during the PID lead-in, with no orange panel. End is the desktop with `DeepSeek Harness`, `FinShield`, `WorkBuddy`, and standard Chinese shell folders. No credentials observed.

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Approval stills

None. Do not invent one.

## Inspection artifacts (not trial originals)

`artifacts/verification/workbuddy-window-resize-finshield-79ac48ed/`
