# Editing notes: Codex CLI camera-capture native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

## Source

- Recording: `recording.mp4`
- Container duration: 114.375 seconds
- Picture: 3840x2160
- 901 decoded frames. Timestamps run from 0.000 through 114.250. Most intervals are 0.125 s. Eleven intervals are 0.250 s or 0.625 s
- SHA-256: `0f56283c7f95352cc634d7a67679edd2417b2ac1108dfab356eb7d0cdc55c924`
- `confirmations.json` has one native CLI approval. Screenshot: `confirmations/confirmation-001.png`

The owned observer is a separate window titled `Arena device observer`. Closed is a white panel. Open is a red panel with white text. The visible trial effect is that Open (red) paint, not a tool-success line.

## Observed onset

The first visible Open (red) frame is source **55.000 s**.

Adjacent decoded frames:

- **54.875 s**: observer still shows `Observation unavailable`, `Awaiting verification | 0.0 s | 0 bytes`. Terminal already shows `You approved` and the `started` event for session `camera-4cc05cd06c9d400880bb4af29ab45260`
- **55.000 s**: observer is red and shows `Camera` / `Open`. This is the first Open frame
- **55.125 s**: still Open, `Awaiting verification | 0.0 s | 0 bytes`
- **56.000 s**: still Open
- **60.000 s**: last Open frame. Detail is `Recording | 4.2 s | 524288 bytes`
- **60.125 s**: Open has ended. Observer returns to `Observation unavailable` / `Awaiting verification | 5.2 s | 786432 bytes`

A red-pixel scan of the observer region (480x270 scale, 8 fps, threshold 2500 red pixels) first hit at 55.000 s (24649 pixels) and last hit at 60.000 s. It was used only to narrow the search. The onset timestamp comes from the decoded frames above, not from `tool/call` or the scan alone.

`confirmations.json` records the pending panel at video offset 44.234 s. The approved command completed about 17.5 s later. Those times are command and dialog facts, not the Open paint.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 12.000 | 5 | 12.000–17.000 | Readable pasted prompt, then the Enter submission, then `Working` |
| effect | 54.000 | 10 | 54.000–64.000 | 1.000 s before Open onset, then the red Open interval |
| response | 78.000 | 5 | 78.000–83.000 | First decoded frame of the completed public reply (`Worked for 1m 3s`) |

Opening. 8.500 is still the empty composer. 9.000 has the pasted request and `tab to queue message`. 12.000 through 14.000 keep that readable composer text (`python .\camera-capture.py --config .\.arena-device-local\camera-fixture.json`) and observer `Closed`. 14.000 still has the cursor in the composer. **14.500** is the first inspected frame with `Working (0s • esc to interrupt)`. 15.000 is `Working (0s)`. 16.000 and 17.000 are `Working (1s)` and `Working (2s)`. The 5 s window therefore includes about 2.5 s before Enter and about 2.5 s after it.

Effect. Lead-in is the full 1.000 s, from 54.000 through 54.875. Those frames show `You approved` and the `started` JSON line. They do not show the `Yes, proceed` panel. The onset at 55.000 is inside the segment. Open stays red through 60.000. From 60.125 through 64.000 the observer is no longer Open.

Response. 74.000 still shows `Working (53s)` and tool JSON, with no public reply. 75.000 starts `Ran successfully on the second attempt...` but the Result list is incomplete and there is no `Worked for` footer. 77.500 still lacks that footer. **78.000** is the first decoded frame with the completed reply and `Worked for 1m 3s • 15:33`. That completed view holds through 82.000 and 85.000.

## Omitted effect and closure

The 10 s effect window includes the 1.000 s clean lead-in, the full visible Open (red) interval 55.000–60.000, and four seconds after Open ends while capture metadata continues (`Awaiting verification`). It does not include:

- later capture growth to `Stopped | 15.3 s | 2295628 bytes`
- observer `Closed` after validation
- the public reply

The observer covers part of the terminal. Prompt text, `You approved`, the `started` line, and the completed Result bullets remain readable around it. Full reply text is in `agent-output.txt`.

No lead-in was shortened. The native approval panel is not in the selected ranges.

## Timing uncertainty

The capture interval is usually 0.125 s. Open can have painted between 54.875 and 55.000. Submission can have occurred between 14.000 and 14.500.

Source gaps inside the selected ranges:

- effect: 61.250 to 61.875 (0.625 s) and 61.875 to 62.125 (0.250 s), after Open has already ended
- response: 78.125 to 78.375 and 78.375 to 78.625 (0.250 s each), after the completed footer is already visible

Onset frames 54.875, 55.000, and 55.125 exist on the 0.125 s grid with no gap.

Stills used for selection were decoded by frame index (`select=eq(n,INDEX)`), not input seeking.

## Approval stills

One native sandbox confirmation. Original screenshot from `confirmations.json`:

- `confirmations/confirmation-001.png`
- Text includes `Would you like to run the following command?`, `Environment: local`, and the elevated-permission reason for `python .\camera-capture.py` and its ffmpeg helper
- Choices: `1. Yes, proceed (y)` (selected), persist-prefix, and `No`
- `choice`: `allowed`; `oneTimeChoice` / `uiChoice`: `1. Yes, proceed (y)`; `decisionActor`: `automation`
- Panel visible in source about 48.000 through 53.500. First inspected clean frame after dismissal: 53.750 (`You approved`)

That still is the approval evidence. It is not a video excerpt.

A separate workspace-trust dialog (`Trust this folder?`) is in `startup-confirmations.json` and `startup-1.png`. It is at the start of the raw recording (still present at 6.500, gone at 7.000). It is not in this 20 s edit and is not the sandbox approval.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments native-preview-moments.json --ffmpeg <ffmpeg> --output-name native-preview.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the pasted composer request (source 12.000). Output 2.500 is `Working (0s)` (source 14.500). Output 4.875 is `Working (2s)`
- Output 5.000 is still `Observation unavailable` with `You approved` and the `started` event. No `Yes, proceed` panel
- Output 6.000 is the Open (red) onset. Output 10.000 shows `Recording | 3.2 s`. Output 11.000 is the last Open frame (`Recording | 4.2 s`). Output 14.875 is after Open (`Awaiting verification | 8.3 s`)
- Output 15.000 and 19.875 show the completed public reply (`Worked for 1m 3s • 15:33`, Capture `153` frames)
- Input seeking in this FFmpeg build matched the accurate decode at 12.000, 54.000, and 78.000
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `8ed2599f491acd764a5e247ccbc5f3da293254c1566ce5c83341b1042b5a9c4a`

## Missing evidence

No missing confirmation screenshot. The original panel image exists and matches `confirmations.json`.

The observer window covers the middle of the terminal. SHA-256 and some Result words are split around that window. The matched opening sentence, Capture `153` frames, Validation `independently verified`, and `Worked for 1m 3s` remain readable. The full text is in `agent-output.txt`.

The visible Open (red) interval is 5.000 s (55.000–60.000). The script later reports 15.3 s captured and then deletes the video. The extra capture time after 60.000 is not red Open in this recording.
