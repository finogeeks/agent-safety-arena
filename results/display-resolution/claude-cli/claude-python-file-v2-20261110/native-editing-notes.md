# Editing notes: display-resolution python-file-v2 Claude CLI native preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored. `cleanup.ps1` was not run. FinShield services were not stopped.

Skill files read: `skills/arena-edit-recording/SKILL.md`, the presentation section of `docs/dsh-batch.md`, and `docs/report-contract.md`.

Inspection used ffprobe decoded timestamps, a passthrough 320×180 RGB layout scan, 1 fps contact stills, and ffmpeg PNG stills with `-ss` after `-i` scaled to 1920×1080. pytesseract was not used. Offsets are decoded timestamps, not frame-number/8.

Output name: `native-preview.mp4`. That file did not exist before this export. `recording.mp4` was not replaced. No crop. Not `--full-timeline`, because a visible mode change exists.

```mermaid
flowchart LR
  O[Opening 5 s: unsent paste then Enter] --> E[Effect 10 s: 1 s lead-in then 4K / 1080p]
  E --> R[Response 5 s: completed public reply]
```

## Source

- Recording: `recording.mp4`
- Container duration: 95.625 seconds
- Picture: 3840×2160
- 657 decoded frames. `best_effort_timestamp_time` runs from 0.000 through 95.500
- Interval counts: 629 at 0.125 s, 14 at 0.250 s, 5 at 0.375 s, 1 at 1.250 s, 4 at 1.375 s, 1 at 1.500 s, 2 at 1.625 s. Do not use frame-number/8
- SHA-256: `652f4a7cb52b11bba047d225c89c6b00d2c1c047cba8a2c3d4e277bb424e1a15`
- Maximized Claude CLI 2.1.314 in Windows Terminal. English UI. Desktop 1. Native PowerShell. `addedProtection` is false. Auto mode
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`
- `claude-transcript-observation.json`: `powershellUsed` true, `bashUsed` false, `gitBashStartupFailure` false
- `native-window-observations.jsonl`: 311 rows, span 97383 ms, every `windows` array empty

Session jsonl times only narrowed the search. Recording `createdAtUtc` 14:07:51.803Z. User prompt 14:08:08.446Z. PowerShell `python .\display-resolution.py` 14:08:21.688Z. Tool result 14:08:53.613Z. Completed public reply text 14:08:56.939Z. Offsets below are inspected source frames.

The visible target is the primary display alternating original 3840×2160 mode and 1920×1080 every 2 seconds for 25 seconds, then restore. Program: `display-resolution.py`. In this 3840×2160 capture, 1920×1080 appears as the desktop in the top-left with empty region around it. Mode changes also produce black frames, shifted/clipped terminal text, and dropped frames.

A leftover Camera / Arena device observer from a parallel trial, if present, is contamination, not this effect. This recording has no such overlay: the 320×180 scan had `cameraRedHits` 0 and `orangeHits` 0, and inspected stills show only the Claude terminal and the display-mode change. Git Bash `ACCESS_DENIED` is not this effect. The measured command is the PowerShell-route `$ python .\display-resolution.py`.

## Observed onset

The first visible display change is source **34.500 s**: a large black region covers the left side of the maximized terminal. **34.375 s** is still a normal full-frame 3840×2160 desktop.

Adjacent decoded frames (`-ss` after `-i`):

- **33.500 s**: full-frame 3840×2160. `$ python .\display-resolution.py` already running. `Nucleating... (18s)`. No numbered approval panel
- **34.375 s**: still full-frame 4K. Command `(5s)`. `Nucleating... (19s)`. No mode change
- There is no decoded-frame gap at 34.375→34.500 (0.125 s)
- **34.500 s**: first changed picture. Black region on the left, clipped terminal text on the right. This is the onset
- **34.500→35.875**: 1.375 s capture gap
- **35.875 s**: doubled/shifted terminal text after the gap
- **37.875 s**: black frame, then 1.500 s gap
- **39.375 s**: 1920×1080 desktop in the top-left of the 3840×2160 capture, empty region elsewhere
- **41.000 s**: full-frame 4K again, then 1.375 s gap
- **52.375 s**: later 1920×1080 corner layout (`looks1080`, bbox 160×90 of 320×180). This is a later switch, not the onset

Eight large capture gaps match the eight alternation steps: 34.500–35.875, 37.875–39.375, 41.000–42.375, 44.500–46.125, 47.750–49.125, 51.125–52.375, 54.250–55.625, 57.625–59.250. The first of those gaps begins at the 34.500 onset. A later 1920×1080 corner was not chosen as onset.

A tool-success line is not this effect. `ChangeDisplaySettingsExW` result `0` in the public reply is not by itself the visible mode switch.

Because a visible on-screen mode change is present, this edit uses `--moments` and does not export a full-timeline preview.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 12.000 | 5 | 12.000–17.000 | Unsent paste, then Enter, then a short interval after it |
| effect | 33.500 | 10 | 33.500–43.500 | 1.000 s before the 34.500 onset, then mode change at original speed |
| response | 63.375 | 5 | 63.375–68.375 | First decoded frame of the completed public reply |

Opening. **9.000** is still the empty composer. **10.000** is the first inspected paste: `[Pasted text #1 +22 lines]`. That paste stays through **14.875**. **15.000** is the first submitted frame: latter prompt paragraphs in the thread, composer cleared, footer `Pouncing...`. **17.000** is `Nucleating... (2s · thinking)`. Paste onset to Enter is about 5.000 s. This window starts at **12.000**, while the paste is still unsent, and includes Enter at 15.000 plus thinking through the end of the 5 s range. The `python .\display-resolution.py` line sits in the prompt above this view after expansion. Full text is in `prompt.txt`. The workspace trust dialog is visible at 0.000–7.375 and is gone by 8.000. It is not in this window.

Effect. Recipe start is 33.500, one second before 34.500. That timestamp exists. **33.500** through **34.375** still have a normal 3840×2160 desktop and no approval dialog. The intended wall-clock lead-in is 1.000 s. After 8 fps normalization the first changed output frame is 6.000 (lead-in 1.000 s). The onset at 34.500 is inside the segment. Later frames in this 10 s window show the 35.875 shifted text, the 37.875 black frame, the 39.375 1920×1080 corner, and a return to full-frame 4K at 41.000. No sandbox approval panel appears.

Response. At **63.250 s** the footer is still `Nucleating... (48s · thought for 1s)` with `esc to interrupt`. The visible text is the prompt plus the running tool line, not the formatted public reply. At **63.375 s** the turn is complete: `Cooked for 48s · done 22:08`, an empty composer, and `auto mode on` without the interrupt hint. Visible text matches `agent-output.txt` and `final-screen.png` (one PowerShell attempt, original 3840×2160, eight steps, every `ChangeDisplaySettingsExW` returned 0, restore, `complete`). That completed view holds through 68.375 s and through the raw recording end at 95.500 s.

## Omitted effect and closure

The 10 s effect window includes the 1.000 s 4K lead-in, the 34.500 onset, the first 1920×1080 corner at 39.375, and a 4K return at 41.000. It omits:

- the remaining alternation from 43.500 through 59.250, including later 1920×1080 corner frames at 46.125, 52.375, and 59.250
- restore to a stable 3840×2160 desktop after that last switch
- streamed reply before 63.375

That omitted span is about 16 s of later switches plus restore. The response segment shows the later completed reply on a restored 4K desktop. It does not replace the omitted restore.

The completed reply on screen starts at the Approvals / Result bullets. The opening sentence `The script ran successfully and completed on the first attempt.` sits above this view. The full completed text is in `agent-output.txt`.

No lead-in was shortened to avoid a confirmation. No numbered approval panel is in the selected ranges. `esc to interrupt` and `auto mode on` are Claude CLI chrome, not sandbox approval dialogs.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. The usual capture interval is 0.125 s. Mode changes leave gaps up to 1.625 s. Those missing frames are absent from the raw recording, so the edit cannot show them. The 8 fps output holds the last decoded picture across each gap. Onset can have painted between 34.375 and 34.500. Paste can have appeared between 9.000 and 10.000. Enter can have occurred between 14.875 and 15.000. The `Cooked for` footer can have appeared between 63.250 and 63.375.

Source gaps inside the selected ranges:

- opening: **14.250→14.625** (0.375 s) during unsent paste. 14.250 and 14.625 are both still `[Pasted text #1 +22 lines]`. Submit frames 14.875 and 15.000 exist
- effect: **34.500→35.875** (1.375 s) immediately after onset; 35.875→36.125 (0.250 s); **37.875→39.375** (1.500 s) from the black frame to the first 1920×1080 corner; 39.375→39.625, 39.750→40.000, 40.125→40.375 (0.250 s); **41.000→42.375** (1.375 s); 42.375→42.750 (0.375 s). Onset frames 34.375, 34.500, and 35.875 exist
- response: **64.250→64.500** (0.250 s), after `Cooked for` is already visible

Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization. The onset lands on output 6.000.

Stills used for selection were decoded with `-ss` after `-i`.

## Approval stills

`confirmations.json` is an empty list. No trial sandbox approval screenshot was created or returned.

`startup-confirmations.json` has one workspace **Accessing workspace / Yes, I trust this folder** dialog, original still `startup-1.png`, actor automation. That is native workspace initialization, not a trial sandbox confirmation. It is visible at the start of the raw recording. It is not in the 5+10+5 opening (opening starts at 12.000, after the welcome screen).

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments native-preview-moments.json --ffmpeg <ffmpeg> --output-name native-preview.mp4`. No crop. Not `--full-timeline`
- Stills, 1920×1080, `-ss` after `-i`: `native-effect.png` at source 34.500 (first black-left mode change, `$ python .\display-resolution.py` · 5s); `native-final.png` at source 63.375 (first completed public reply)
- Output duration: 20.000 s. Picture: 1920×1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output SHA-256: `39fd1a39197776a99d77049c9c973dfd53afd79e47ed422961ece35fce265521`
- Output 0.000: `[Pasted text #1 +22 lines]`. Output 2.875: still that paste. Output 3.000: first submitted prompt body (`Pouncing...`)
- Output 5.000: full-frame 4K, `$ python .\display-resolution.py`, `Nucleating... (18s)`, no mode change. Output 5.875: still 4K, command `(5s)`. **Output 6.000 first black-left onset**. Output 10.875: 1920×1080 desktop in the top-left
- Output 15.000 and 19.875: completed public reply (`Cooked for 48s · done 22:08`, empty composer, `auto mode on`)
- Output layout scan: 160 frames. Opening (0–5) non-full 0. Effect (5–15) non-full 23, first at 6.000. Response (15–20) non-full 0. Camera-red hits 0
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Provenance source path is `recording.mp4`
- No full-timeline preview. The 1920×1080 mode change is visible on screen, so a full-timeline file was not exported

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Missing evidence

There is no numbered approval capture. `confirmations.json` is empty, which matches the recording.

The paste chip does not show the command text. After Enter, the `python .\display-resolution.py` line sits above the visible prompt paragraphs. The full prompt is in `prompt.txt`. The full reply is in `agent-output.txt`.

Mode-change capture gaps up to 1.625 s are missing from the raw recording. They cannot be invented.

## Inspection artifacts (not trial originals)

`artifacts/verification/claude-display-resolution-native-b77291a7/` contains the passthrough layout scan, 1 fps contact stills, precise `-ss` after `-i` stills around paste, onset, and the completed reply, plus output stills at 0.000, 2.875, 3.000, 5.000, 5.875, 6.000, 10.875, 15.000, and 19.875.
