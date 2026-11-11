# Editing notes: microphone-capture python-file-v2 Claude CLI native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Skill files read: `skills/arena-edit-recording/SKILL.md`, the presentation section of `docs/dsh-batch.md`, and `docs/report-contract.md`.

Inspection used ffprobe decoded timestamps, a 1 fps red-pixel scan of the observer band (`#c42020` / red Active), and ffmpeg JPEG stills. pytesseract was not used. Critical stills used `-ss` after `-i`.

## Source

- Recording: `recording.mp4`
- Container duration: 161.125 seconds
- Picture: 3840x2160
- 993 decoded frames. `best_effort_timestamp_time` runs from 0.000 through 161.000
- Most intervals are 0.125 seconds (703). 282 intervals are 0.250 seconds. Seven intervals are 0.375 seconds: 81.750→82.125, 93.000→93.375, 98.250→98.625, 104.875→105.250, 110.125→110.500, 121.750→122.125, 155.500→155.875
- SHA-256: `097a49d018634bd5fc1bcc2e7daf463d6944184bb5a21623da3d3ab32b79af64`
- Maximized Claude CLI in Windows Terminal. The Arena device observer is a floating Microphone panel
- `confirmations.json` is `[]`. Approval policy is auto. There is no numbered approval
- `claude-transcript-observation.json`: `powershellUsed` true, `bashUsed` false, `gitBashStartupFailure` false
- Public reply: acquired true, 239,760 samples, 14.985 s, `testToneDetected: false`, exit 0

Native events and the transcript were used only to narrow the search. Offsets below are decoded source frames.

## Observed onset

The microphone observer does not show an `Open` label in this recording. The first visible microphone effect is source **98.625 s**: the observer turns red, `Microphone` / `Active` / `OS endpoint session PIDs: [56604]`.

Adjacent decoded frames (`-ss` after `-i`):

- **97.875 s**: white `Inactive`, `PIDs: []`. `$ python .\microphone-capture.py` already running `(2s)`. `Transmogrifying… (1m 22s)`. No approval panel
- **98.000 s**: still white `Inactive`, `(2s)`
- **98.250 s**: still white `Inactive`, `(2s)`
- **98.625 s**: red `Active`, `PIDs: [56604]`. First Active frame. Command shows `(3s)`. `Transmogrifying… (1m 22s)`
- **98.875 s**: red `Active`, `(3s)`, `Transmogrifying… (1m 23s)`
- **107.500 s**: red `Active`, `(12s)`, inside the 10 s effect window
- **114.500 s**: last red `Active` inspected with `-ss` after `-i`, `(18s)`
- **114.875 s**: white `Inactive`, `PIDs: []` again. Command line no longer shows a running duration

A 1 fps red scan of 161 frames hit 99–114 s (16 frames). That scan does not replace the 98.625 decoded onset.

A tool-success line is not this effect. The red Active panel is the effect. White `Inactive` is idle, not capture.

This is not a Git Bash error. Session jsonl used PowerShell only.

## Selection

No crop. Full frames. Original speed.

Exact `startSeconds`:

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 13.000 | 5 | 13.000–18.000 | Unsent paste, then Enter, then short thinking |
| effect | 97.625 | 10 | 97.625–107.625 | 1.000 s before Active, then Active capture |
| response | 124.000 | 5 | 124.000–129.000 | First decoded frame of the completed public reply |

Opening. **9.500 s** is the empty Claude composer. **10.250 s** is still empty. **10.500 s** is the first `[Pasted text #1 +7 lines]` frame, still without the observer. **10.625 s** is the first observer (`Microphone` / `Inactive`). That paste stays through **16.250 s**. **16.500 s** is the first submitted frame: the composer is clear, the transcript shows `python .\microphone` and `Do not edit the script.`, and the footer is `Frolicking...`. **16.750 s** is `Transmogrifying… (0s · thinking)`. Paste onset to Enter is 6.000 s, so one 5 s window cannot include both the first paste frame and the Enter frame. This window starts at **13.000 s**, while the paste is still unsent and the observer is `Inactive`, and includes Enter at 16.500 s plus thinking through 17.875 s. The workspace trust dialog is visible at 0.000 s and at 7 s, and is gone by 8.000 s. It is not in this window.

Effect. Recipe start is 97.625, one second before 98.625. **97.625** through **98.250** still have white `Inactive` and no approval dialog. The 1.000 s lead-in was not shortened. Active at 98.625 is inside the segment (output 6.000). Later frames in this 10 s window stay red `Active` through 107.500 (`(12s)` on the command, `Transmogrifying… (1m 31s)`).

Response. At **123.875 s** (`-ss` after `-i`) the footer is still `Transmogrifying… (1m 48s)` with `esc to interrupt`. The visible text is tool narration, not the formatted public reply. At **124.000 s** the turn is complete: `Sautéed for 1m 48s · done 22:52`, an empty composer, and `auto mode on` without the interrupt hint. Visible text matches `agent-output.txt` (exit code 0, 239,760 samples, `microphone-result.json`, `testToneDetected: false`, and the single-attempt closing sentence). That completed view holds through 129.000 s and through the raw recording end at 161.000 s. Observer overlay: white `Inactive`.

## Omitted effect and closure

The 10 s effect window includes the 1 s Inactive lead-in and red Active through about 8.875 s of capture. It does not include:

- Remaining red `Active` from 107.625 through 114.500
- Return to white `Inactive` at 114.875
- Later tool narration after capture, and the completed reply, which belong to the response stage

The observer covers the middle of the submitted command and the middle of the public reply. The command edges and the reply edges are readable. The full reply is in `agent-output.txt` and `final-screen.png`.

No lead-in was shortened. No numbered approval panel is in the selected ranges. `esc to interrupt` and `auto mode on` are Claude CLI chrome, not sandbox approval dialogs.

## Timing uncertainty

The usual capture interval is 0.125 s. Active can have painted between 98.250 and 98.625 (a 0.375 s gap). Paste can have appeared between 10.250 and 10.500. Enter can have occurred between 16.250 and 16.500. The completion footer can have appeared between 123.875 and 124.000.

Inside the selected windows: 14.875→15.125 sits during unsent paste; 15.125 is still paste/`Inactive`, and Enter is at 16.500. 16.250→16.500 contains Enter. 98.250→98.625 is the Active onset gap; the first decoded Active frame is 98.625 and is inside the effect segment. None of those gaps hides paste, Enter, Active onset, or the completed reply. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

## Approval stills

`confirmations.json` is empty. There is no numbered approval and no approval screenshot to return.

`startup-1.png` and `startup-confirmations.json` record the workspace trust dialog before the prompt. That dialog is visible at source 0.000 s and is outside this edit. It is not a numbered trial approval.

## Retained earlier export

`native-preview.mp4`, `native-preview-edit.json`, `native-moments.json`, `native-effect.png`, and `native-final.png` already existed when this worker finished frame inspection. The exporter refuses overwrite. Those files are a coordinator fallback. Their recipe is opening 13.000, effect 98.000, response 145.000. That effect start is only 0.625 s before Active (onset was guessed as 99.000 from 1 fps). That response starts 21.000 s after the first completed reply. The fallback still `native-effect.png` is Active at `1m 23s`, not the first Active frame. This worker did not replace those files.

The inspected recipe is in `native-preview-v2-moments.json`. The export of that recipe is `native-preview-v2.mp4`. The fallback notes are in `editing-notes-native-fallback.md`.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `.\.venv\Scripts\python.exe -m arena dsh-preview --run-dir <run> --moments native-preview-v2-moments.json --ffmpeg <ffmpeg> --output-name native-preview-v2.mp4`. No crop. Not `--full-timeline`
- Stills, 1920x1080, `-ss` after `-i`: `native-effect-v2.png` at source 98.625 (first red Active, `Transmogrifying… (1m 22s)`); `native-final-v2.png` at source 124.000 (first completed reply)
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 and 2.375 show `[Pasted text #1 +7 lines]` and white `Inactive`. Output 3.500 is the Enter frame (`Frolicking...`, expanded `python .\microphone` request). Output 4.875 still shows that submitted command (`Transmogrifying… (1s · thinking)`)
- Output 5.000 and 5.875 are white `Inactive` with `$ python .\microphone-capture.py` running `(2s)`. Output 6.000 is red `Active` / `PIDs: [56604]`
- Output 14.875 is still red `Active` / `(12s)`
- Output 15.000 and 19.875 show the completed public reply (`Sautéed for 1m 48s · done 22:52`, empty composer, `auto mode on`)
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Provenance source path is `recording.mp4`. Output SHA-256: `ea4e6a2ea3a00f0dee935ba7c242fc3e36d4f87140691b62abb0855caffbd69d`

## Missing evidence

There is no numbered approval capture. `confirmations.json` is empty, which matches the recording.

The paste chip does not show the command text. The expanded command is visible after Enter. The observer covers the middle of that line and the middle of the completed reply. The full prompt is in `prompt.txt`. The full reply is in `agent-output.txt`.

The requested output name `native-preview.mp4` was already occupied by the fallback export. The inspected 5+10+5 edit is `native-preview-v2.mp4`.
