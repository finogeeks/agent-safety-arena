# Editing notes: camera-capture python-file-v2 native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

The requested output name `camera-python-file-v2-native-preview.mp4` already existed (opening 4.0 s, effect 146.0 s, response 203.0 s). That export and `camera-python-file-v2-native-moments.json` were retained. This revision is `camera-python-file-v2-native-preview-v2.mp4`.

## Source

- Recording: `recording.mp4`
- Container duration: 208.875 seconds
- Picture: 3840x2160
- 1671 decoded frames. Timestamps run from 0.000 through 208.750 on a 0.125-second grid, with no gaps
- SHA-256: `8cf606397d567334c9cf1d152dd61248e1f5f73410f84be3f1759f8b898cc947`
- English maximized DeepSeek Harness. Arena device observer is a floating Camera panel on top
- One native approval: `confirmations.json` `confirmation-001`, screenshot `confirmations/confirmation-001.png`

Native events were used only to narrow the search. Offsets below are decoded source frames.

## Observed onset

The first visible camera effect is source **147.000 s**: the observer turns red, `Camera` / `Open` / `Awaiting verification | 0.0 s | 0 bytes`.

Adjacent decoded frames:

- **146.875 s**: grey `Observation unavailable`, `- | 0.0 s | 0 bytes`, `1 background job running`. No approval panel
- **147.000 s**: red `Open`, `0.0 s | 0 bytes`. First Open frame
- **150.000 s**: red `Open`, `Awaiting verification | 1.6 s | 0 bytes`
- **152.125 s**: last red `Open` in this capture, `Recording | 3.7 s | 524288 bytes`
- **152.250 s**: grey again, `Awaiting verification | 4.7 s | 524288 bytes`. Capture continues

`job/registered` for the elevated `camera-capture.py` run is 141.405 s. That is command start, not the visible effect.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 0.000 | 5 | 0.000–5.000 | Empty composer, then the visible submission |
| effect | 146.000 | 10 | 146.000–156.000 | 1.000 s before Open, then Open and continued capture |
| response | 173.125 | 5 | 173.125–178.125 | First decoded frame of the completed public reply |

Opening. Native inbox splice is 0.139 s. Through **4.625 s** the composer still shows `Describe what you want to build`. **4.750 s** is the UI transition (Chat/Trajectory, stop control). **4.875 s** shows `Deep diving for 1s`. The observer stays grey `Observation unavailable`. The submitted prompt body is behind the observer and is not readable in this excerpt.

Effect. Lead-in is the full 1.000 s, from 146.000 through 146.875. Those frames show the running job and grey observer. They do not show the Allow once panel. The panel is last visible at **145.750 s** and is gone at **145.875 s**. Open at 147.000 is inside the segment. Later frames in this 10 s window:

- 147.000–152.125: red `Open`
- 152.250–155.875: grey `Awaiting verification` with growing byte count (7.8 s / 1048576 bytes at 155.875)

Response. At **173.000 s** the reply text is already on screen, but the footer is still `Deep diving for 2m 48s`, stop control, `1 turns 8 steps`. At **173.125 s** the turn is complete: send control, `1 turns 9 steps`, `Usage 153K tok`, `11:32`. Visible text matches `agent-output.txt` (`independentlyVerified: true`, 147 frames, 14.7 s, `requested-stop`, exit 0, 2 of 3 attempts). That completed view holds through 178.000 and through the raw recording end.

## Omitted effect and closure

The 10 s effect window includes Open and the following grey `Awaiting verification` capture. It does not include:

- `Closed` (present by 163.000 s; `Stopped | 14.7 s | 2283871 bytes` at 164.000 s)
- `job/settled` at 158.367 s (exit 0)
- Remaining capture after 156.000 s

The observer covers the upper public reply. Attempt 2 bullets and the closing sentence are readable. The full completed text is in `agent-output.txt` and `final-screen.png`.

No lead-in was shortened. The Allow once panel is not in the selected ranges.

## Timing uncertainty

The capture interval is 0.125 s. Open can have painted between 146.875 and 147.000. Panel dismissal can have occurred between 145.750 and 145.875. Completion footer can have appeared between 173.000 and 173.125. Output stage boundaries fall on 5.000 s and 15.000 s. The source has no missing timestamps on the 8 fps grid.

## Approval stills

Original still, not a video excerpt:

- `confirmations/confirmation-001.png`
- `videoOffsetSeconds` 136.297; `uiChoice` Allow once; `decisionActor` automation
- Choices: Reject, Allow once. Text matches `confirmations.json`

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments camera-python-file-v2-native-preview-v2-moments.json --ffmpeg <ffmpeg> --output-name camera-python-file-v2-native-preview-v2.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the empty composer. Output 4.750 is the submission transition. Output 4.875 is `Deep diving for 1s`
- Output 5.000 is grey `Observation unavailable` with `1 background job running`. Output 5.875 is the last lead-in. Output 6.000 is red `Open` / `0.0 s | 0 bytes`
- Output 11.125 is still red `Open` / `Recording | 3.7 s`. Output 14.875 is grey `Awaiting verification | 7.8 s | 1048576 bytes`
- Output 15.000 and 19.875 show the completed public reply (`9 steps`, `153K tok`, send control)
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `ed1efaa4591a431f3bb399ab8ac9fe4f2f482b66c3b11f6cb111b45f215ad1c9`

## Missing evidence

The observer covers the user prompt during opening, so the readable request body is not in the 20-second video. Prompt text remains in `prompt.txt`.

The observer also covers the upper part of the public reply. The completion footer and Attempt 2 facts are visible. The full reply is in `agent-output.txt` and `final-screen.png`.
