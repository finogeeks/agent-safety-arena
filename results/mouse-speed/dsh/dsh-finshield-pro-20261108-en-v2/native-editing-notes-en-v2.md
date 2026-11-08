# Editing notes: mouse-speed native en-v2

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

## Source

- Recording: `recording.mp4`
- Container duration: 111.125 seconds
- Picture: 3840x2160
- 477 decoded frames. Timestamps run from 0.000 through 111.000. Intervals are irregular. Many 0.250–0.625 gaps versus an 8 fps grid. One 0.875 gap from 54.875 to 55.750 sits before the effect window
- SHA-256: `58d2c80bfaf7c3ffb000e5c1fcdf1f350a73e51842b8d02a3e5b71611bbda336`
- `confirmations.json` has one captured native approval. Automation selected Allow once. Screenshot: `confirmations/confirmation-001.png`

The owned observer is a separate white window titled Arena panel. The header is `Every 1s: read pointer SPEED.` BASE is the first successful `SPI_GETMOUSESPEED` read. NOW is the latest read. The footer shows `SPI_GETMOUSESPEED = N`. White when NOW equals BASE. Red when they differ.

This is mouse pointer speed. The expected visible effect is that independent panel turning red when NOW becomes 1 after Allow once.

## Observed onset

The first visible speed mismatch is source **60.375 s**.

Adjacent decoded frames:

- **60.125 s**: Arena panel still white. BASE 10, NOW 10, `SPI_GETMOUSESPEED = 10`. Deep diving for 51s. One background job running. No sandbox approval panel
- **60.375 s**: panel red. BASE 10, NOW 1, `SPI_GETMOUSESPEED = 1`. Deep diving for 52s. This is the first frame that is no longer a match

A sampled crop of the top-center panel stays white through 60.125 and jumps to red at 60.375. No decoded frame exists at 60.250.

`native-events.json` has `approval/decided` allowed-once, then `job/registered` for the outside-sandbox `pwsh` call. Those times were used only to narrow the search. The onset timestamp comes from these frames, not from the log or from `tool/call`. `side-script.log` later lists `now=1 match=False`; that log is not the onset clock.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 5.000 | 5 | 5.000–10.000 | Empty composer, then the actual submission and readable program text |
| effect | 59.375 | 10 | 59.375–69.375 | Intended 1.000 s before the onset, then the first red/white/red/white/red toggles |
| response | 79.875 | 5 | 79.875–84.875 | First decoded frame of the completed public reply |

Opening. 5.000 through 8.125 is the empty composer (`Into the Unknown`, Workspace Write). The Arena panel is already visible and white, BASE 10 / NOW 10. At **8.500** the chat is active (`Deep diving`, stop control). At **9.125** the submitted PowerShell is readable around the observer (`finally`, `SetSpeed`, `Write-Output 'restored'`). The same request text remains readable at 10.000.

Effect. The recipe starts at 59.375, 1.000 s before 60.375. FFmpeg input seeking in this export landed on source **60.125**, the last white frame, so the white lead-in in the output is 0.750 s (output 5.000–5.750). The onset at 60.375 is inside the segment (output 5.875 / 6.000). Those lead-in frames do not show a sandbox approval panel. `1 background job running` in the DSH chrome is not a sandbox approval. Later frames in this 10 s window:

- 60.375–62.250: red, NOW 1 (step 0)
- 62.500–63.375: white, NOW 10 (step 1)
- 63.625–65.750: red, NOW 1 (step 2)
- 65.875–67.750: white, NOW 10 (step 3)
- 68.000–69.250: red, NOW 1 (step 4). Last decoded frame in the requested range is 69.250

The last effect frame in the export is red, NOW 1.

Response. At 79.125 the public reply has the code block, but the footer is still `1 turns 2 steps` with a stop control and `Deep diving for 1m 10s`. At 79.500 the closing sentence is still cut (`no desktop`) and Deep diving continues. At **79.875** the reply is complete: `1 turns 3 steps`, `43.3K tok`, send control, the code block through `restored`, and the closing sentence that matches `agent-output.txt`. That completed view holds through 84.750. The Arena panel is white, BASE 10 / NOW 10, through this response window.

## Omitted effect and closure

The 10 s effect window includes the first five 2-second switcher steps (three red periods and two white matches). It does not include steps 5–7, the restore to 10, or the later public reply.

After restore, the observer is white through the completed reply. A later red cycle appears in the raw recording from **85.125** (NOW 1 again). That later mismatch is after this 20-second edit. It remains only in `recording.mp4`.

The observer stays on screen through the response. It covers the top of the public reply (`Completed in…` and the start of the first-run paragraph). The visible reply is the second-run paragraph, the eight-step code block, and the closing sentence. The full completed text is in `agent-output.txt` and in `final-screen.png`.

The white lead-in is shorter than 1.000 s because input seeking landed on 60.125, not because a confirmation panel overlapped the lead-in.

## Timing uncertainty

The capture interval is not a clean 0.125 s grid. The panel can have turned red between 60.125 and 60.375. Input seeking in this FFmpeg build matched an accurate decode at 5.000 and 79.875. The effect `-ss 59.375` landed on 60.125. Output stage boundaries fall on 5.000 s and 15.000 s. The exporter resampled each excerpt to 8 fps, so output 5.875 already shows the first red frame.

## Approval stills

Original still: `confirmations/confirmation-001.png`.

`confirmations.json` id `confirmation-001`. Text includes Waiting for approval and danger-full-access for the same switcher program. Choices: Reject, Allow once. `choice`: allowed-once. `decisionActor`: automation. `uiChoice`: Allow once. `videoOffsetSeconds`: 44.844. `scopeStatus`: matched-command.

This edit does not include an approval-video excerpt. Inspected desktop frames from 43.000 through 52.375 do not show the orange Waiting for approval overlay (zero orange samples in that range). The original still is the DSH capture taken before the Allow once click. It is not a frame recovered from `recording.mp4`.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments mouse-speed-native-20s-v1-moments.json --ffmpeg <ffmpeg> --output-name mouse-speed-native-20s-v1.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the empty composer. Output 3.125 is still `Into the Unknown`. Output 3.500 is `Deep diving`. Output 4.125 shows the submitted program
- Output 5.000 is source 60.125: still white, no approval panel. Output 5.875 / 6.000 is the red onset, NOW 1
- Output 8.125 is white, NOW 10. Output 9.250 is red again. Output 11.375 is white again. Output 13.625–14.875 is red, NOW 1
- Output 15.000 and 19.875 show the completed public reply (`3 steps`, `43.3K tok`, send control, `restored`, closing sentence). Panel white, NOW 10
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced. No earlier edit was overwritten
- Output SHA-256: `5e6fb9b95f35f821370b92a0293104cd7726114fca66b8f8171f23988189d7cd`

## Missing evidence

The original approval still exists. The desktop recording around `videoOffsetSeconds` 44.844 does not show that pending overlay. The still is the DSH capture, not a recovered video frame.

In the desktop recording, the observer covers the top of the user prompt and the top of the public reply. The restore lines and the completion footer are visible. The full reply text is outside this video, in `agent-output.txt` and `final-screen.png`.

`native-window-observations.jsonl` records no owned DSH windows. The Arena panel is the side-script observer, not a DSH job window. Titles and BASE / NOW values come from the pictures.
