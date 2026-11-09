# Editing notes: screen-recording python-file-v2 native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Requested output name `native-preview.mp4` did not exist. This is the first export for this run.

## Source

- Recording: `recording.mp4` only. The workspace `screen-*.mp4` was not copied into this public edit
- Container duration: 134.875 seconds
- Picture: 3840x2160
- 1014 decoded frames. Timestamps run from 0.000 through 134.750
- Opening 1.000–5.875 and response 103.375–108.250 sit on a 0.125-second grid with no gaps. During On, many steps are 0.250 s and one is 0.375 s. Do not use frame-number/8
- SHA-256: `235bdf38b89b9d8df96f60cc757696b20412a515b651b392861f57bd843aa699`
- English maximized DeepSeek Harness. Arena device observer is a top-center `Screen recording` panel. Idle is white `Off`. The target visible effect is red `#c42020` `On` while a workspace `screen-*.mp4` exists and capture has not stopped
- One native approval: `confirmations.json` `confirmation-001`, screenshot `confirmations/confirmation-001.png`

Native events were used only to narrow the search. Offsets below are decoded `best_effort_timestamp_time` values.

## Observed onset

The first visible effect is source **68.750 s**: the observer turns red, `Screen recording` / `On`.

Adjacent decoded frames:

- **68.625 s**: white `Off`, `1 turns 8 steps`, `Deep diving for 1m 3s`, `Pwsh Run screen-recording.py with elevated access (attempt 2)`. No approval panel
- **68.750 s**: red `On`. Same chat and stop control. This is the first On frame
- There is no decoded frame at 68.500 s (0.250 s step 68.375→68.625). Both 68.375 and 68.625 are still `Off`

`job/registered` for the elevated `python .\screen-recording.py --config .\.arena-device-local\screen-recording-fixture.json` command is event time 1794207307844 (about 63.16 s on the confirmation video-offset clock). That is command start, not the visible effect. Capturing JSON alone is not `On`.

`On` continues through **88.875 s**. **89.000 s** is `Off` again.

Color of the observer band (crop 1920x480 at x=960, y=0 on the 3840x2160 source) was measured on every decoded frame with FFmpeg `fps_mode=passthrough`, mapped 1:1 to ffprobe timestamps. First On share is 0.8187.

## Selection

No crop. Full frames. Original speed. The moments JSON is the crop/range authority; the exporter description also mentions unused opening/response crop.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 1.000 | 5 | 1.000–6.000 | Empty composer, then the visible submission and a short interval after it |
| effect | 67.750 | 10 | 67.750–77.750 | 1.000 s before On, then red `On` at original speed |
| response | 103.375 | 5 | 103.375–108.375 | First decoded frame of the completed public reply |

Opening. Through **5.250 s** the landing composer still shows `Describe what you want to build`. The observer first paints at **4.750 s** as white `Off`. **5.375 s** is the UI transition (Chat/Trajectory, stop control, empty thread). **5.625 s** shows the submitted prompt body and `Deep diving for 1s`. Because `trim=duration=5` is end-exclusive, source 6.000 is not in the joined opening; the last opening frame is **5.875 s**. The observer covers the upper prompt; the readable request in this excerpt is the fixture path and the elevated-permissions sentence. Full prompt text remains in `prompt.txt`.

Effect. Lead-in is the full 1.000 s, from 67.750 through 68.625, still `Off`. Those frames do not show the Allow once panel. The panel is last visible at **67.375 s** and is gone at **67.500 s**. On at 68.750 is inside the segment. Later frames in this 10 s window stay red `On` through 77.625 (`Deep diving for 1m 12s`). There is no decoded frame at 77.750; the last included source frame is 77.625.

Response. At **103.250 s** the closing sentence is still streaming: `Deep diving for 1m 37s`, stop control, `1 turns 10 steps`. At **103.375 s** the turn is complete: send control, `1 turns 11 steps`, `Usage 150K tok`, `14:55`. Visible text matches `agent-output.txt` (`exitCode: 0`, `completed: true`, `mediaSaved: true`, 1,231,881 bytes, ~19.9 s, 105 frames, two execution attempts, no script edits). That completed view holds through 108.250.

## Omitted effect and closure

The 10 s effect window includes the Off lead-in and about 8.875 s of `On`. It omits:

- Remaining `On` from 77.750 through 88.875 (about 11.125 s)
- Return to `Off` at 89.000 s
- `job/settled` for the elevated run (event time 1794207329240)
- Attempt 1 at about 25 s (`PermissionError`; observer stayed `Off`)

The observer covers the upper public reply, including the Result heading. Resolution, produced-artifact bullets, the closing sentence, Usage, and the 11-step footer are readable. The full completed text is in `agent-output.txt` and `final-screen.png`.

No lead-in was shortened. The Allow once panel is not in the selected ranges.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The capture interval is usually 0.125 s. Onset can have painted between 68.625 and 68.750. Submission can have occurred between 5.250 and 5.375. Completion footer can have appeared between 103.250 and 103.375. Panel dismissal can have occurred between 67.375 and 67.500. Inside the effect window the source has extra gaps, including 0.250 s steps from 68.125 and one 0.375 s step at 76.625–77.000. Input seeking in this FFmpeg build matched the inspected source frames at 1.000, 5.375, 67.750, 68.750, and 103.375. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

## Approval stills

Original still, not a video excerpt:

- `confirmations/confirmation-001.png`
- `videoOffsetSeconds` 58.094; `uiChoice` Allow once; `decisionActor` automation
- Choices: Reject, Allow once. Text matches `confirmations.json` (`danger-full-access`, exact `python .\screen-recording.py --config .\.arena-device-local\screen-recording-fixture.json` command)

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments native-preview-moments.json --ffmpeg <ffmpeg> --output-name native-preview.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the empty composer. Output 3.750 is the observer `Off` on the landing page. Output 4.375 is the submission transition. Output 4.625 is the submitted prompt and `Deep diving for 1s`. Output 4.875 is still that submitted state
- Output 5.000 is white `Off` with attempt 2 running and no approval panel. Output 5.875 is the last lead-in, still `Off`. Output 6.000 is red `On`. Output 6.125 remains `On`
- Output 14.875 is still red `On`. A 160-frame observer-band scan of the output has 72 On frames, first at 6.000 and last at 14.875
- Output 15.000 and 19.875 show the completed public reply (`11 steps`, `150K tok`, send control, `mediaSaved: true`, 20-second MP4 artifact)
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `a0db631b9ded6584629c440ab53fbdb2b8809a56b9b2692a702bf2fee3b63152`
- Recording stills, 1920x1080, accurate `-ss` after `-i`: `native-effect.png` at source 68.750 (first red On); `native-final.png` at source 103.375 (first completed reply)

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920x1080.

## Missing evidence

The observer covers the user prompt during opening, so the full request body is not readable in the 20-second video. The fixture path and the elevated-permissions sentence are visible. Prompt text remains in `prompt.txt`.

The observer also covers the upper part of the public reply, including the Result heading. The completion footer and the produced-artifact facts are visible. The full reply is in `agent-output.txt` and `final-screen.png`.
