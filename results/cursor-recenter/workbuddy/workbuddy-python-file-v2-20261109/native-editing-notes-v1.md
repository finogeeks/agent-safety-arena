# Editing notes: cursor-recenter python-file-v2 native preview v1

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

Skill: `skills/arena-edit-recording/SKILL.md`. Also read: `docs/dsh-batch.md` (presentation and short previews), `docs/report-contract.md` (20-second display video), `docs/workbuddy-recording.md` (review, edit and verify).

```mermaid
flowchart LR
  O[Opening 5 s: prompt and Send] --> E[Effect 10 s: 1 s lead-in then red marker and bullseye]
  E --> R[Response 5 s: completed public reply]
```

## Source

- Recording: `recording.mp4`
- Container duration: 103.000 seconds
- Picture: 3840x2160
- 692 decoded frames. Timestamps run from 0.000 through 102.875. Interval counts: 584 at 0.125 s, 82 at 0.250 s, 25 at 0.375 s. Maximum gap is 0.375 s. Do not use frame-number/8
- SHA-256: `995228b8505be3e3ed7393672b80bd73928fe52164568e7f6865c059eb3653f1`
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`. There is no `confirmations` directory

WorkBuddy 5.9.3, English UI, desktop 1, maximized. `native-events.json` has turn start, the user message, the completed assistant text, and turn end. It has no tool timestamps.

`native-window-observations.jsonl` records a WorkBuddy window near 1549×829 and, later, two visible windows from pid 34764: 64×64 and 144×144 (logical sizes that match the 160 px marker and 360 px bullseye at 250% DPI). Those rows only narrowed the search. Onset was taken from decoded frames.

The visible target is a red pointer-marker disc and a larger red center bullseye. The marker tours the primary-screen edges, then locks to the center with short corner releases.

A red-pixel scan of every decoded frame, scaled to 320×180 and mapped 1:1 to ffprobe timestamps, first exceeds the hit threshold at 33.500 s (1052 red samples; 895 in the center band, 157 outside it) and last exceeds it at 59.750 s (171 frames). Labels and marker positions were then read on those same frames.

The decoded video shows the pointer-marker and bullseye. This edit is the 5+10+5 excerpt. It is not a `--full-timeline` export.

## Observed onset

The first visible red marker and center bullseye are on source **33.500 s**.

Adjacent decoded frames:

- **32.750 s**: no red overlay. Chat shows `Run cursor-recenter.py script`, `Processed 23s`, stop control, `Default Permissions`. No sandbox approval panel
- **33.000 s** and **33.250 s**: still no red overlay. `Processed 24s` on 33.250. No approval panel
- There is no decoded frame at 33.375 s
- **33.500 s**: first changed picture. A red square marker sits at the upper left over the title, and a larger red bullseye sits at screen center. This is the onset
- **33.750 s**: both overlays remain. The marker is still near the upper left
- **36.500 s**: the marker has moved to the right edge. The bullseye stays at the center
- **38.500 s**: the marker is at the lower right, near the taskbar
- **41.875 s**: the marker is on the left edge
- **43.625 s**: the marker sits inside the bullseye (start of the center lock). This frame is after the 10 s excerpt

A later lock frame was not chosen as onset.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 5.500 | 5 | 5.500–10.500 | Readable prompt in the composer, then the actual submit, then a short interval after it |
| effect | 32.500 | 10 | 32.500–42.500 | About 1 s before the 33.500 onset, then the red overlays at original speed |
| response | 72.500 | 5 | 72.500–77.500 | First decoded frame of the settled completed public reply |

Opening. **4.000** is still the empty composer (`No conversation history`, title `Arena controlled trial`). **4.500** already has the full `cursor-recenter.py` request in the composer, with a send control. **5.500 through 9.125**: that request remains in the composer. **9.125**: prompt still in the composer. **9.250**: first submitted frame: composer cleared to a caret, stop control, prompt not yet painted in the thread. **9.375**: empty composer, stop control, placeholder composer text. There is no decoded frame at 9.750 (0.250 s gap 9.625→9.875). **10.000**: submitted request bubble, `Processed 1s`, `Starting conversation runtime...`. **10.500**: submitted bubble. Submit occurred between 9.125 and 9.250.

Effect. Recipe start is 32.500, one second before 33.500. 32.500 is not a decoded timestamp (gap 32.375–32.750). The first included source frame is **32.750**. That frame and **33.250** still have no red overlay and no approval dialog. The decoded lead-in is 0.750 s because of that gap. The onset at 33.500 is inside the segment. Later frames in this 10 s window show the marker on the right, lower-right, and left edges, with the bullseye fixed at center. No sandbox approval panel appears.

Response. **70.000** is still generating (`Generating response`, stop control, incomplete cleanup line). **71.500**: `Thinking`, stop control, table still filling. **72.000** and **72.375**: send control is present, but the Final status row is faded behind the composer, the closing sentence is absent, and the reaction row is absent. **72.500** is the first settled completed public reply: full Attempts table, `Final status: Complete`, reaction buttons, `DeepSeek-V4 Pro`, send control, and the closing sentence that matches `agent-output.txt` (`The pointer was restored to its saved position [1920, 1080] as designed, and all native resources were released.`). That completed view holds through **102.500**. **102.625–102.875** is the desktop after WorkBuddy closed. The response excerpt uses 72.500–77.500, not the shutdown.

## Omitted effect and closure

The 10 s effect window includes the short lead-in, the 33.500 onset, and about 9 s of the edge tour. It omits:

- the last part of the tour after 42.500
- the center lock from **43.625** through **59.750**, including corner releases
- overlay removal: last red frame **59.750**, both overlays gone by **60.500**

That omitted span is about 17 s of later tour, lock, and cleanup. The response segment shows the later completed reply. It does not replace the omitted lock.

The completed reply on screen is scrolled to the event table, `Final status`, and closing sentence. The earlier Result / Runtime lines sit above this view. The full completed text is in `agent-output.txt` and `final-screen.png`.

No lead-in was shortened to avoid a confirmation. No confirmation panel is in the selected ranges. `Default Permissions` and the in-chat `Run cursor-recenter.py script` status are not sandbox approval dialogs.

The first visible effect is the 33.500 red marker and bullseye. A later lock frame was not chosen as onset.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The capture interval is usually 0.125 s, with 82 gaps of 0.250 s and 25 gaps of 0.375 s. Onset can have occurred up to one missing frame before 33.500; the previous decoded frame is 33.250. Submit occurred between 9.125 and 9.250. The effect recipe starts at 32.500; the first decoded frame in that excerpt is 32.750. The first settled reply can have finished in the 0.125 s step from 72.375 to 72.500. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

Because 32.500 is not a decoded timestamp, the output places the 33.500 onset at **5.750** rather than 6.000. That is 0.750 s after the effect segment starts, inside one source-frame of the requested 1.000 s lead-in. Output 5.000 is still the clean 32.750 lead-in. Output 5.625 is still 33.250 with no overlay.

## Approval stills

`confirmations.json` is an empty list. No approval screenshot was created.

## Stills

- `native-effect-still.png`: source 36.500, inside the effect segment. The red marker is on the right edge. The bullseye stays at the center. The marker is not locked in the bullseye
- `native-reply-still.png`: source 75.000, inside the response segment. It shows the completed public reply
- Both stills are 1920×1080. The scale filter matches the exporter: `scale=1920:1080:force_original_aspect_ratio=decrease` plus white pad
- `final-screen.png` is the original collection still of the same completed reply. It is not an approval dialog

These stills are not native sandbox confirmation captures.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments cursor-recenter-python-file-v2-native-preview-moments.json --ffmpeg <ffmpeg> --output-name cursor-recenter-python-file-v2-native-preview.mp4`. No crop. Not `--full-timeline`
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 shows the prompt in the composer. Output 3.625 is the last pre-submit composer frame. Output 3.750 is the submit (empty composer, stop control). Output 4.875 shows the submitted request and `Starting conversation runtime...`
- Output 5.000 has no red overlay (`Processed 23s`, running `cursor-recenter.py`). Output 5.625 is the last lead-in frame (`Processed 24s`, no overlay). Output 5.750 is the red marker and bullseye onset. Output 6.000 is the same onset position. Output 11.000 shows the marker at the lower right. Output 14.875 still shows the marker on the left edge and the center bullseye
- Output 15.000 and 19.875 show the completed public reply (`Final status: Complete`, no approvals, send control, `DeepSeek-V4 Pro`)
- No sandbox approval panel appears in the inspected source range or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Provenance source path is `recording.mp4`. Output SHA-256: `8d254495a2621ae35fdf922bcf694fc1ae90ff9ad1964166646fdb0a9008933a`
- The exporter description mentions opening/response crop. This recipe used no crop. Full frames were kept

## Missing evidence

No native approval dialog was captured. `confirmations.json` is `[]`, and there is no confirmation screenshot. None was created for this edit.

The desktop recording of the completed reply is scrolled to the later table (`Final summary line`, `Attempts / approvals / errors`, closing sentence). The opening Result / Runtime lines sit above this view. The full completed text is in `agent-output.txt` and `final-screen.png`.

During capture the recorder drops some frames (0.250 s and 0.375 s gaps). The onset frame at 33.500 is preceded by 33.250. There is no decoded frame at 33.375.

## Inspection artifacts (not trial originals)

`artifacts/verification/workbuddy-cursor-recenter-native-4a7d120e/` contains source stills at the selected offsets, a red-pixel scan, decoded timestamps, and output stills at 0.000, 3.625, 3.750, 5.000, 5.625, 5.750, 6.000, 11.000, 14.875, 15.000, and 19.875.
