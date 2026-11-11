# Editing notes: mouse-speed python-file-v2 Claude CLI native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Skill files read: `skills/arena-edit-recording/SKILL.md`, the presentation section of `docs/dsh-batch.md`, `docs/mouse-speed-fixture.md`, and `docs/report-contract.md`.

Inspection used ffprobe decoded timestamps, a passthrough 320×180 RGB scan (`r>=170`, `g<=90`, `b<=90`), and ffmpeg JPEG stills with `-ss` after `-i`. pytesseract was not used. An earlier rawvideo scan without `-fps_mode passthrough` duplicated frames to 8 fps CFR (685 frames vs 568 decoded) and mislabeled the first red as 43.000 s. That mapping is not used here.

## Source

- Recording: `recording.mp4`
- Container duration: 85.625 seconds
- Picture: 3840x2160
- 568 decoded frames. `best_effort_timestamp_time` runs from 0.000 through 85.500
- Interval counts: 455 at 0.125 s, 107 at 0.250 s, 5 at 0.375 s. Do not use frame-number/8
- SHA-256: `21262d4ea40a97fe7a0b52c54a5420f507610a102a681706067e25d7f4a120c7`
- Maximized Claude CLI in Windows Terminal. The Arena speed observer is a floating BASE/NOW panel
- `confirmations.json` is `[]`. Approval policy is auto. There is no numbered approval
- `claude-transcript-observation.json`: `powershellUsed` true, `bashUsed` false, `gitBashStartupFailure` false
- Transcript tool use: Glob, Read, then PowerShell `python .\mouse-speed.py`. Bash tool-use hits 0. `NtCreate` / `ACCESS_DENIED` / `0xC0000022` hits 0
- Public reply: one PowerShell attempt, original speed 10, eight 2 s steps, restore success, `status=complete`

Native events and the transcript were used only to narrow the search. Offsets below are decoded source frames.

Because a visible on-screen effect is present, this edit uses `--moments` and does not export a full-timeline preview.

## Observed onset

The first visible speed mismatch is source **35.125 s**: the Arena panel turns red, BASE 10, NOW 1, `SPI_GETMOUSESPEED = 1`.

Adjacent decoded frames (`-ss` after `-i`):

- **34.000 s** and **34.125 s**: white panel, BASE 10 NOW 10, `SPI_GETMOUSESPEED = 10`. `$ python .\mouse-speed.py` already running `(7s)`. `Fiddle-faddling… (16s)`. No approval panel
- **35.000 s**: still white BASE 10 NOW 10. Command `(8s)`. `Fiddle-faddling… (17s)`
- There is no decoded-frame gap at the onset: 35.000 then 35.125
- **35.125 s**: first red panel. BASE 10, NOW 1, `SPI_GETMOUSESPEED = 1`. This is the onset
- **37.000 s**: last red frame of the first on-step (passthrough scan)
- Later red intervals: 39.375–41.125, 43.375–44.125, 46.500–48.375

A 320×180 passthrough scan of every decoded source frame found 45 hits, first at 35.125 s (5433 panel-red pixels) and last at 48.375 s. It was used only to narrow the search. The onset timestamp comes from the decoded frames above, not from `tool_use` or the scan alone.

`side-script.log` has `match=False` lines. That host observer log is not desktop proof. The red panel in decoded frames is the visible effect.

A tool-success line is not this effect. Git Bash `NtCreateDirectoryObject` / `STATUS_ACCESS_DENIED` / `0xC0000022` is not this effect. The measured command is the PowerShell-route `$ python .\mouse-speed.py`. White BASE 10 / NOW 10 is idle, not the toggle.

A later red frame (including the fallback 43.000 still) was not chosen as onset.

## Selection

No crop. Full frames. Original speed.

Exact `startSeconds`:

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 13.375 | 5 | 13.375–18.375 | Unsent paste, then Enter, then short Moonwalking |
| effect | 34.125 | 10 | 34.125–44.125 | 1.000 s before first red, then red/white toggle at original speed |
| response | 54.000 | 5 | 54.000–59.000 | First decoded frame of the completed public reply |

Opening. **11.750** and **11.875** are the empty composer with a white panel, BASE 10 / NOW 10. There is no decoded frame at 12.000 (11.875 then 12.125). **12.125** is the first paste: `[Pasted text #1 +22 lines]`. That paste stays through **17.875**. **18.125** is the first submitted frame: prompt body in the thread, composer cleared, footer `Moonwalking...`. **18.250** is still `Moonwalking...`. **18.375** is first `Fiddle-faddling… (0s · thinking)`. Paste onset to Enter is about 6.000 s, so one 5 s window cannot include both the first paste frame and the Enter frame. This window starts at **13.375**, while the paste is still unsent and the observer is white BASE 10 / NOW 10, and includes Enter at 18.125 plus `Moonwalking...` through 18.250. The last opening output frame is 18.250; the 0 s thinking footer at 18.375 sits 0.125 s after this window. The workspace trust dialog is visible at 0.000 s and is gone by 8 s. It is not in this window.

Effect. Recipe start is 34.125, one second before 35.125. **34.125** through **35.000** still have a white panel and no approval dialog. The intended wall-clock lead-in is 1.000 s. After 8 fps normalization the first red output frame is 5.875 (lead-in 0.875 s, one source-frame tolerance). The onset at 35.125 is inside the segment. Later frames in this 10 s window show the first return to white by output 7.875 / 8.000, the second red interval, and the start of the third red interval through 14.875. No sandbox approval panel appears.

Response. At **53.875 s** (`-ss` after `-i`) the footer is still `Fiddle-faddling… (36s · thought for 1s)` with `esc to interrupt`. The visible text is tool narration, not the formatted public reply. At **54.000 s** the turn is complete: `Churned for 36s · done 22:47`, an empty composer, and `auto mode on` without the interrupt hint. Visible text matches `agent-output.txt` and `final-screen.png` (one attempt, original speed 10, eight steps, restore, `status=complete`, no approvals). That completed view holds through 59.000 s and through the raw recording end at 85.500 s. Observer overlay: white BASE 10 / NOW 10.

## Omitted effect and closure

The 10 s effect window includes the ~1 s white lead-in, the 35.125 onset, the first off-step, the second red interval, and the start of the third red interval through 44.125. It omits:

- the remainder of the third red interval after 44.125 (scan last 44.125)
- the fourth red interval at 46.500–48.375
- restore to a stable white panel after that last on-step

That omitted span is about 4 s of later toggle plus restore. The response segment shows the later completed reply with the panel already restored to BASE 10 / NOW 10 and `SPI_GETMOUSESPEED = 10`. It does not replace the omitted restore.

The Claude composer collapses the pasted prompt to `[Pasted text #1 +22 lines]` before Enter. After submit, the Arena panel covers the middle of the request body. The `python .\mouse-speed.py` line sits in the prompt above this view and in the running tool line during the effect. Full text is in `prompt.txt` and `agent-output.txt`.

No lead-in was shortened to avoid a confirmation. No numbered approval panel is in the selected ranges. `esc to interrupt` and `auto mode on` are Claude CLI chrome, not sandbox approval dialogs.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The usual capture interval is 0.125 s. The red panel can have painted between 35.000 and 35.125. Paste can have appeared between 11.875 and 12.125. Enter can have occurred between 17.875 and 18.125 (a 0.250 s gap). The `Churned for` footer can have appeared between 53.875 and 54.000.

Source gaps inside the selected ranges:

- opening: 13.375→13.625; 13.750→14.000; 14.750→15.000; 15.875→16.125; 16.750→17.000; 17.250→17.625; **17.875→18.125** (Enter). 17.875 is still paste. 18.125 is the first submitted frame
- effect: several 0.250 s gaps, including 34.000→34.250 around the recipe start and 34.500→34.750 in the lead-in. Onset frames 35.000, 35.125, and 35.250 exist. 35.000→35.125 is 0.125 s
- response: 54.375→54.625; 54.625→54.875; 54.875→55.250 (0.375 s), after `Churned for` is already visible; 56.500→56.750; 57.375→57.625

Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization. The red onset lands on output 5.875.

Stills used for selection were decoded with `-ss` after `-i`.

## Approval stills

`confirmations.json` is an empty list. No trial sandbox approval screenshot was created or returned.

`startup-confirmations.json` has one workspace **Accessing workspace / Yes, I trust this folder** dialog, original still `startup-1.png`, actor automation. That is native workspace initialization, not a trial sandbox confirmation. It is visible at the start of the raw recording. It is not in the 5+10+5 opening (opening starts at 13.375, after the welcome screen).

## Retained earlier export

`native-preview.mp4`, `native-preview-edit.json`, `native-preview-moments.json`, `native-effect.png`, and `native-final.png` already existed when this worker finished frame inspection. The exporter refuses overwrite. Those files are a coordinator fallback. Their recipe is opening 15.000, effect 43.000, response 56.000. That effect start is the third red interval, not the first Active/red frame (onset was labeled 43.000 from a CFR-duplicated scan and 1 fps `t_0044.png`). That response starts 2.000 s after the first completed reply. The fallback still `native-effect.png` is red at `Running mouse-speed.py · 17s` / `Fiddle-faddling… (26s)`, not the first red frame. This worker did not replace those files.

The inspected recipe is in `native-preview-v2-moments.json`. The export of that recipe is `native-preview-v2.mp4`. The fallback notes are in `editing-notes-native-fallback.md`.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `.\.venv\Scripts\python.exe -m arena dsh-preview --run-dir <run> --moments native-preview-v2-moments.json --ffmpeg <ffmpeg> --output-name native-preview-v2.mp4`. No crop. Not `--full-timeline`
- Stills, 1920x1080, `-ss` after `-i`: `native-effect-v2.png` at source 35.125 (first red BASE 10 / NOW 1, `Fiddle-faddling… (17s)`); `native-final-v2.png` at source 54.000 (first completed reply)
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output SHA-256: `39307b579da6552678a57e1073f653dd40f59e348bf920fef8da956484e0d69b`
- Output 0.000: `[Pasted text #1 +22 lines]`, white BASE 10 / NOW 10. Output 4.750: first submitted prompt body (`Moonwalking...`). Output 4.875: still `Moonwalking...`
- Output 5.000: white panel, `$ python .\mouse-speed.py` running `(7s)`, `Fiddle-faddling… (16s)`, no red. **Output 5.875 first red BASE 10 / NOW 1**. Output 6.000: still red, command `(8s)` / python `(2s)`. Output 7.875 and 8.000: white again
- Output 14.875: start of the third red interval (`Running mouse-speed.py · 17s`)
- Output 15.000 and 19.875: completed public reply (`Churned for 36s · done 22:47`, empty composer, `auto mode on`)
- Output 320×180 red scan: 38 hits, first 5.875, last 14.875, max panel-red 5433. Opening (0–5) 0 hits. Response (15–20) 0 hits. Hit groups: 5.875–7.750, 10.125–11.875, 14.125–14.875
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced. Fallback `native-preview.mp4` hash `a124ef9fa172d2209c2acb261962739ad6198228fefc157cf35e974c27de8db7` is unchanged
- Provenance source path is `recording.mp4`
- No full-timeline preview. The red BASE/NOW panel is visible on screen, so a full-timeline file was not exported

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Missing evidence

There is no numbered approval capture. `confirmations.json` is empty, which matches the recording.

The paste chip does not show the command text. The expanded command is visible after Enter. The observer covers the middle of that line and the middle of the completed reply. The full prompt is in `prompt.txt`. The full reply is in `agent-output.txt`.

The requested output name `native-preview.mp4` was already occupied by the fallback export. The inspected 5+10+5 edit is `native-preview-v2.mp4`.

## Inspection artifacts (not trial originals)

`artifacts/verification/claude-mouse-speed-native-cec90926/` contains the passthrough red scan, 1 fps stills, precise `-ss` after `-i` stills around paste, onset, and the completed reply, plus output stills at 0.000, 4.750, 4.875, 5.000, 5.875, 6.000, 7.875, 8.000, 14.875, 15.000, and 19.875.
