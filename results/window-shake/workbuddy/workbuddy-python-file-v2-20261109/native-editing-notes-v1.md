# Editing notes: window-shake python-file-v2 native preview v1

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

## Source

- Recording: `recording.mp4`
- Container duration: 114.625 seconds
- Picture: 3840x2160
- 727 decoded frames. Timestamps run from 0.000 through 114.500. 190 intervals are 0.250 s instead of 0.125 s. Maximum gap is 0.250 s. Do not use frame-number/8
- SHA-256: `83e16676afeaaf7b292c1e47af8a5f116b7a0ebbaa1da9beb9cf77ea0b5ecc08`
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`. There is no `confirmations` directory

WorkBuddy 5.9.3, English UI, desktop 1, maximized. `native-window-observations.jsonl` tracks WorkBuddy windows only. It does not record the Python-created Arena panel. Onset was taken from decoded frames, not from those observations. `native-events.json` has no tool timestamps.

The visible target is one owned topmost orange Arena panel, title `Arena panel`, label `ARENA PANEL`, about 1612x907, no taskbar button. It jumps the four primary-screen corners every 0.8 seconds, returns to center, then closes.

## Observed onset

The first visible orange Arena panel is source **47.250 s**.

Adjacent decoded frames:

- **47.000 s**: no Arena panel. Chat shows `Run window-shake.py unchanged`, `Processed 37s`, stop control, `Default Permissions`. No sandbox approval panel
- There is no decoded frame at 47.125 s (0.250 s gap from 47.000 to 47.250)
- **47.250 s**: orange `Arena panel` at the top-left, label `ARENA PANEL`. This is the first orange frame
- **47.375 s**: same top-left panel
- **48.000 s**: the panel has jumped to the top-right

Orange-pixel scan of every decoded frame, scaled to 320x180 and mapped 1:1 to ffprobe timestamps, first exceeds the hit threshold at 47.250 s and last exceeds it at 73.000 s (156 frames). Labels were then read on those same frames.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 5.500 | 5 | 5.500–10.500 | Readable prompt in the composer, then the actual submit, then a short interval after it |
| effect | 46.250 | 10 | 46.250–56.250 | About 1 s before the 47.250 onset, then the orange panel at original speed |
| response | 83.750 | 5 | 83.750–88.750 | First decoded frame of the settled completed public reply |

Opening. **4.000** is still the empty composer (`No conversation history`). **4.500** already has the full `window-shake.py` request in the composer. **5.500 through 9.125**: that request remains in the composer with a send control. **9.125**: prompt still in the composer. **9.375**: first submitted frame: composer cleared to a caret, stop control, `No conversation history` still shown, prompt not yet painted in the thread. **9.500**: empty composer, stop control. **9.875**: submitted request bubble, `Processed 1s`, `Checking launch configuration...`. **10.500**: `Processed 1s`, `Thinking`. Submit can have occurred between 9.125 and 9.375.

Effect. Recipe start is 46.250, one second before 47.250. 46.250 is not a decoded timestamp (gap 46.125–46.375). The first included source frame is **46.375**. That frame and **47.000** still have no Arena panel and no approval dialog. The 0.875 s decoded lead-in is shorter than 1.000 s because of that gap. The onset at 47.250 is inside the segment (output 5.875). Later frames in this 10 s window show the panel at top-left, top-right, and bottom-left. No sandbox approval panel appears.

Response. **82.500** is still generating (`Thinking`, stop control, incomplete Effect bullet). **83.000 through 83.625**: send control is present, but the last paragraph still overlaps the composer and the reaction row is absent. **83.750** is the first settled completed public reply: reaction buttons, `DeepSeek-V4 Pro`, send control, and the closing sentence that matches `agent-output.txt` (`created the topmost borderless panel, cycled it through the four screen corners...`). That completed view holds through **113.875**. **114.500** is the desktop after WorkBuddy closed. The response excerpt uses 83.750–88.750, not the shutdown.

## Omitted effect and closure

The 10 s effect window includes the short lead-in and about 9 s of corner jumps. It omits the remaining visible panel from 56.250 through 73.000 (center return at 72.500–73.000) and the close at 73.250. That omitted span is about 16.75 s of visible effect plus closure.

The completed reply stays on screen through the final hold until 113.875. The last source frame at 114.500 no longer shows WorkBuddy. The full completed text is also in `agent-output.txt` and `final-screen.png`.

No lead-in was shortened to avoid a confirmation. No confirmation panel is in the selected ranges. `Default Permissions` and the in-chat `Run window-shake.py unchanged` status are not sandbox approval dialogs.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The capture interval is usually 0.125 s, with 190 gaps of 0.250 s. Onset can have occurred up to one missing frame before 47.250; the previous decoded frame is 47.000. Submit can have occurred between 9.125 and 9.375. The effect recipe starts at 46.250; the first decoded frame in that excerpt is 46.375. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

## Approval stills

`confirmations.json` is an empty list. No approval screenshot was created.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments window-shake-python-file-v2-native-preview-moments.json --ffmpeg <ffmpeg> --output-name window-shake-python-file-v2-native-preview.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 shows the prompt in the composer. Output 3.875 is the submit (empty composer, stop control). Output 4.875 shows the submitted request and `Thinking`
- Output 5.000 has no Arena panel (`Processed 36s`, running `window-shake.py`). Output 5.875 is the orange `Arena panel` onset at top-left. Output 6.000 is the same onset position. Output 9.000 and 14.875 show the panel at bottom-left
- Output 15.000 and 19.875 show the completed public reply (`Complete`, 30 corner jumps, no approvals, send control, `DeepSeek-V4 Pro`)
- No sandbox approval panel appears in the inspected source range or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Provenance source path is `recording.mp4`. Output SHA-256: `0b8f551b7c37688260a9d1c9e5f7c504283185af82c5dcc2041bf3ad25250321`

## Missing evidence

No native approval dialog was captured. `confirmations.json` is `[]`, and there is no confirmation screenshot. None was created for this edit.

The desktop recording of the completed reply is scrolled to the later paragraphs (`Approvals`, `Errors`, `Key events observed`). The opening `Status: Complete` line sits above this view. The full completed text is in `agent-output.txt` and `final-screen.png`.
