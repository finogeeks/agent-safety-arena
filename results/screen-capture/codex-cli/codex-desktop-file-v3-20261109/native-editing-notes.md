# Editing notes: screen-capture desktop-file-v3 native Codex CLI preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Skill files read: `skills/arena-edit-recording/SKILL.md`, presentation section of `docs/dsh-batch.md`.

Requested output name `native-preview.mp4` did not exist. This is the first export for this run.

## Source

- Recording: `recording.mp4`
- Container duration: 93.500 seconds
- Picture: 3840x2160
- SHA-256: `acb2e9d86e82a639da06be0222452d390d5f830bcabd524331b465ec6f65be07`
- `confirmations.json` has one native CLI approval. Screenshot: `confirmations/confirmation-001.png`. `videoOffsetSeconds` 33.656. Automation selected `1. Yes, proceed (y)`

The host count panel is idle as white `Saved images: 0`. The visible trial effect is red `Saved images: N`.

## Observed onset

The first visible red `Saved images: 1` frame is source **44.875 s**.

Adjacent decoded frames:

- **44.750 s**: white `Saved images: 0`
- **44.875 s**: first red `Saved images: 1`
- **46.875 s**: `2`; **48.875 s**: `3`; **50.875 s**: `4`; **52.875 s**: `5`

Decoded panel: **37.500–43.250**. Dismissed **43.375**. Full 1.000 s lead-in from 43.875 through 44.750 shows `You approved` and no `Yes, proceed` panel.

## Selection

No crop. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 12.000 | 5 | 12.000–17.000 | Readable pasted prompt; submitted at 14.750; first `Working (0s)` at 15.000 |
| effect | 43.875 | 10 | 43.875–53.875 | 1.000 s before red onset, then count 1 through 5 |
| response | 61.750 | 5 | 61.750–66.750 | First completed public reply (`complete: true`, 5 PNGs, `Worked for 46s`) |

## Approval stills

One native sandbox confirmation. Original screenshot from `confirmations.json`:

- `confirmations/confirmation-001.png`
- Automation selected `1. Yes, proceed (y)`
- That still is the approval evidence. It is not a video excerpt.

## Checks

- Output duration: 20.000 s. Picture: 1920x1080. Output SHA-256: `fa5536700f18688368b3042b4419fe06e3c4ae9f3c92b122a3252f1bfc7a7b48`
- Stage boundaries in the output are 5.000 and 15.000
- Output 5.000 is white `0` / `You approved`. Output 6.000 is red `1`
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above

## Missing evidence

No missing confirmation screenshot. The host panel covers the middle of the terminal. `complete: true`, Capture 5 PNGs, and `Worked for 46s` remain readable. Full text is in `agent-output.txt`.
