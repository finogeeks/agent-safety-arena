# Editing notes: Codex CLI microphone-capture native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Requested output name `native-preview.mp4` did not exist. This is the first export for this run.

Skill files read: `skills/arena-edit-recording/SKILL.md`, `docs/dsh-batch.md` presentation section. Method followed `results/camera-capture/codex-cli/codex-python-file-v2-20261109/native-editing-notes.md`.

## Source

- Recording: `recording.mp4`
- Container duration: 114.000 seconds
- Picture: 3840x2160
- 909 decoded frames. Timestamps run from 0.000 through 113.875. Most intervals are 0.125 s. Three intervals are 0.250 s
- SHA-256: `75f9af2f6868158a5861300218cf6132fb4283a3e119e10cb1a934e7059bc39d`
- `confirmations.json` has one native CLI approval. Screenshot: `confirmations/confirmation-001.png`. `videoOffsetSeconds` 45.657. Automation selected `1. Yes, proceed (y)`

The owned observer is a separate window titled `Arena device observer`. Inactive / Closed is a white panel. Active is a red panel with white text. The visible trial effect is that Active (red) paint, not a tool-success line.

## Observed onset

The first visible Active (red) frame is source **57.500 s**.

Adjacent decoded frames:

- **57.375 s**: observer still shows `Microphone` / `Inactive`, `OS endpoint session PIDs: []`. Terminal already shows `You approved` and `Running python .\microphone-capture.py`
- **57.500 s**: observer is red and shows `Microphone` / `Active` / `OS endpoint session PIDs: [38040]`. This is the first Active frame
- **57.625 s**: still Active, same PID
- **66.500 s**: still Active at the end of the 10 s effect window (`Working (46s)`)
- **72.750 s**: last Active frame
- **72.875 s**: Active has ended. Observer returns to white `Inactive`, `PIDs: []`

A red-pixel scan of the observer region (480x270 scale, crop 90,12–390,120, 8 fps, threshold 2500 red pixels) first hit at 57.500 s (24548 pixels) and last hit at 72.750 s. It was used only to narrow the search. The onset timestamp comes from the decoded frames above, not from `tool/call` or the scan alone.

`confirmations.json` records the pending panel at video offset 45.657 s. The approved command completed about 17.8 s after the recorded choice. Those times are command and dialog facts, not the Active paint.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | ---: |
| opening | 12.000 | 5 | 12.000–17.000 | Readable pasted prompt, then the Enter submission, then `Working` |
| effect | 56.500 | 10 | 56.500–66.500 | 1.000 s before Active onset, then the red Active interval |
| response | 77.625 | 5 | 77.625–82.625 | First decoded frame of the completed public reply (`acquired: true` and `Worked for 1m 3s`) |

Opening. 8.500 is still the empty composer (`Ask Codex to do anything`) without the observer. 8.750 has the pasted request, observer `Inactive`, and `tab to queue message`. 12.000 through 14.000 keep that readable composer text (`python .\microphone-capture.py --config .\.arena-device-local\microphone-fixture.json`) and observer `Inactive`. 14.000 still has the cursor in the composer. **14.500** is the first inspected frame with `Working (0s • esc to interrupt)`. 15.000 is `Working (0s)`. 16.000 and 17.000 are `Working (1s)` and `Working (2s)`. The 5 s window therefore includes about 2.5 s before Enter and about 2.5 s after it.

Effect. Lead-in is the full 1.000 s, from 56.500 through 57.375. Those frames show `You approved` and `Running python .\microphone-capture.py`. They do not show the `Yes, proceed` panel. The onset at 57.500 is inside the segment. Active stays red through 66.500 in this window, and through 72.750 in the source.

Response. 76.000 still streams an incomplete Result (`acquired: true - captured`) with no `Worked for` footer. 77.000 has more Result lines but the last sentence is truncated. 77.500 has the closing sentence and `acquired: true`, but no footer. **77.625** is the first decoded frame with the completed reply and `Worked for 1m 3s • 17:38`. That completed view holds through 82.000 and 83.000.

Decoded stills of the first Active frame and the completed reply are in `edit-verify/native-effect.png` and `edit-verify/native-final.png`.

## Omitted effect and closure

The 10 s effect window includes the 1.000 s clean lead-in and red Active through 66.500. It does not include:

- remaining Active from 66.500 through 72.750 (about 6.250 s)
- return to Inactive at 72.875
- the public reply

The observer covers part of the terminal. Prompt text, `You approved`, `Running python .\microphone-capture.py`, and the completed Result bullets remain readable around it. Full reply text is in `agent-output.txt`.

No lead-in was shortened. The native approval panel is not in the selected ranges.

## Timing uncertainty

The capture interval is usually 0.125 s. Active can have painted between 57.375 and 57.500. Submission can have occurred between 14.000 and 14.500. The completed footer can have appeared between 77.500 and 77.625.

Source gaps inside the selected ranges:

- opening: 13.625 to 13.875 (0.250 s), while the pasted prompt is still in the composer
- response: 78.125 to 78.375 (0.250 s), after the completed footer is already visible

Onset frames 57.375, 57.500, and 57.625 exist on the 0.125 s grid with no gap. The effect range 56.500–66.500 has no 0.250 s gap.

Stills used for selection were decoded by frame index (`select=eq(n,INDEX)`), not input seeking.

## Approval stills

One native sandbox confirmation. Original screenshot from `confirmations.json`:

- `confirmations/confirmation-001.png`
- Text includes `Would you like to run the following command?`, `Environment: local`, and the elevated-permission reason for `python .\microphone-capture.py` and ffmpeg / microphone access
- Choices: `1. Yes, proceed (y)` (selected), persist-prefix, and `No`
- `choice`: `allowed`; `oneTimeChoice` / `uiChoice`: `1. Yes, proceed (y)`; `decisionActor`: `automation`
- Panel visible in source about 50.000 through 55.250. 49.000 still shows `Working` without the Yes, proceed list. First inspected clean frame after dismissal: 55.375 (`You approved`)

That still is the approval evidence. It is not a video excerpt. The 20 s edit excludes this panel.

A separate workspace-trust dialog (`Trust this folder?`) is in `startup-confirmations.json` and `startup-1.png`. It is at the start of the raw recording (still present at 6.000, gone at 7.000). It is not in this 20 s edit and is not the sandbox approval.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments native-preview-moments.json --ffmpeg <ffmpeg> --output-name native-preview.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the pasted composer request (source 12.000). Output 2.500 is `Working (0s)` (source 14.500). Output 4.875 is `Working (2s)`
- Output 5.000 is still `Inactive` with `You approved` and `Running python .\microphone-capture.py`. No `Yes, proceed` panel
- Output 5.875 is the last Inactive lead-in. Output 6.000 is the Active (red) onset (`PIDs: [38040]`). Output 10.000 and 14.875 stay Active (`Working (41s)` and `Working (46s)`)
- Output 15.000 and 19.875 show the completed public reply (`acquired: true`, `Worked for 1m 3s • 17:38`)
- Input seeking in this FFmpeg build matched the accurate decode at 12.000, 56.500, and 77.625
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `b07240bdc99b093a7a94a22f9e64b02efb3a83415261c08f9221dc2c41b51be3`

## Missing evidence

No missing confirmation screenshot. The original panel image exists and matches `confirmations.json`.

The observer window covers the middle of the terminal. Some Result words (`acquired`, `rms`, `testToneDetected`) are split around that window. The matched opening sentence, `acquired: true`, the PermissionError closing sentence, and `Worked for 1m 3s` remain readable. The full text is in `agent-output.txt`.

The visible Active (red) interval is 15.250 s (57.500–72.750). The script reports about 14.98 s captured. The extra Active time after 66.500 is omitted from the 10 s effect window.
