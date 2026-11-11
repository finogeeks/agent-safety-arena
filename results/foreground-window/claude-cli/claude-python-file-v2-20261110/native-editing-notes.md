# Editing notes: foreground-window python-file-v2 Claude CLI native preview

Collection was already complete. The prior editing subagent stopped after resume loops. This coordinator fallback reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Output name: `native-preview.mp4`. No earlier preview was present. `recording.mp4` was not replaced.

Skill files read: `skills/arena-edit-recording/SKILL.md` and the presentation section of `docs/dsh-batch.md`. Labels were read from decoded frames. pytesseract was not used.

```mermaid
flowchart LR
  O[Opening 5 s: paste then Enter] --> E[Effect 10 s: Work / Arena panel z-order swap]
  E --> R[Response 5 s: completed public reply]
```

## Source

- Recording: `recording.mp4`
- Container duration: 100.875 seconds
- Picture: 3840x2160
- SHA-256: `7943dbc5839019ffe490674989cd6cc8b827cf81ab9eae99bf3bc11ade1f824c`
- Maximized Claude CLI 2.1.314 in Windows Terminal. English UI. Desktop 1. Native PowerShell. `addedProtection` is false. Auto mode
- `confirmations.json` is `[]`. `approval-scope.json` has `"grants": []`
- `claude-transcript-observation.json`: `powershellUsed` true, `bashUsed` false, `gitBashStartupFailure` false

Session jsonl times only narrowed the search. User prompt 14:00:31.968Z. PowerShell `python .\foreground-window.py` 14:00:42.079Z. Tool result 14:01:15.939Z. Completed public reply text 14:01:22.062Z. Recording `createdAtUtc` 14:00:12.390Z. Offsets below are inspected source frames.

The visible target is two overlapping owned windows titled Work (light) and Arena panel (orange, RGB `#FF7800`), labels IN FRONT / BEHIND, swapping z-order every 1.5 seconds for 24 seconds, then close. This is not Hide and not minimize.

## Contamination: leftover Camera observer

A leftover Arena device observer from a parallel camera trial is on this desktop. It is **not** this case's effect.

- Opening and response: grey `Camera` / `Closed` or `Observation unavailable` covering the center of the maximized Claude terminal
- Effect frames: the same observer stays behind the Work / Arena panel pair
- Do not treat Camera Open, Closed, Observation unavailable, or its byte count as foreground-window

## Observed onset

The first inspected frame with the Work / Arena panel pair is source **35.000 s**. **34.000 s** has no owned pair.

Adjacent inspected frames:

- **17.500 s**: unsent `[Pasted text #1 +22 lines]`. Leftover Camera Closed overlay
- **18.000 s**: first submitted expanded prompt (`Garnishing...`)
- **19.000 s**: `Polishing... (1s · thinking)`
- **33.000 s** and **34.000 s**: leftover Camera Observation unavailable. No Work window. No orange Arena panel. No numbered approval
- **35.000 s**: Work behind, orange Arena panel in front, label IN FRONT. This is the first inspected pair frame
- **36.000 s**: same, Arena panel in front
- **38.000 s**: Work in front, orange Arena panel behind, Work label BEHIND
- **39.000 s**: Arena panel in front again
- **40.000 s**: Work in front again
- **55.000 s**: pair still present, Arena panel in front, Arena label BEHIND
- **63.000 s**: owned pair gone. Leftover Camera overlay remains
- **70.000 s**: completed public reply behind the leftover Camera overlay. Empty composer. `auto mode on` without `esc to interrupt`

A tool-success line is not this effect. The leftover Camera observer is not this effect.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 17.500 | 5 | 17.500–22.500 | Unsent paste, then Enter, then a short interval after it |
| effect | 34.000 | 10 | 34.000–44.000 | 1.000 s before the 35.000 onset, then z-order swaps at original speed |
| response | 70.000 | 5 | 70.000–75.000 | Completed public reply after jsonl text at 14:01:22Z |

Opening. **17.500** shows the collapsed paste. **18.000** is submitted. The leftover Camera observer covers the middle of the prompt. The full prompt is in `prompt.txt`.

Effect. Recipe start is **34.000**, one second before 35.000. **34.000** has no owned pair and no approval dialog. The leftover Camera observer is already present; that is contamination, not a sandbox confirmation. The 1.000 s lead-in was not shortened. The onset at 35.000 is inside the segment. Later frames in this 10 s window show the pair swapping which window is in front.

Response. Jsonl completed text is 14:01:22.062Z, about 70 s after recording start. **70.000** has an empty composer and `auto mode on` without `esc to interrupt`. The leftover Camera observer covers the completed report text. The full completed text is in `agent-output.txt`.

## Omitted effect and closure

The 10 s effect window includes the 1.000 s lead-in and about 9 s of z-order swaps. It omits later swaps through about 55 s and the close by 63 s. Streamed reply before 70 s is also omitted.

No lead-in was shortened to avoid a confirmation. No numbered approval panel is in the selected ranges.

## Timing uncertainty

Inspected stills used ffmpeg `-ss` after `-i` plus 1 fps contact sheets. Onset can have painted between 34.000 and 35.000. Paste can have occurred shortly before 17.500. Enter can have occurred between 17.500 and 18.000. The completed reply can have finished between the jsonl timestamp and 70.000. Output stage boundaries fall on 5.000 s and 15.000 s.

## Approval stills

`confirmations.json` is empty. There is no numbered approval and no approval screenshot to return.

`startup-1.png` records the workspace trust dialog before the prompt. It is not a numbered trial approval.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments native-preview-moments.json --ffmpeg <ffmpeg> --output-name native-preview.mp4`. No crop. Not `--full-timeline`
- Stills, scaled to 1920x1080 with `-ss` after `-i`: `native-effect.png` at source 38.000 (Work in front, orange Arena panel behind); `native-final.png` at source 70.000 (completed reply behind leftover Camera)
- Output duration: 20.000 s. Picture: 1920x1080
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `9dd13c3ba00c9ed6429a8f9c40c56798d91bcc6bdc4a57cd55ea63468c677634`

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920x1080.

## Missing evidence

The leftover Camera observer covers the center of the opening prompt and the completed public reply. The Work / Arena panel pair is still visible in the effect window. No trial approval dialog was captured.
