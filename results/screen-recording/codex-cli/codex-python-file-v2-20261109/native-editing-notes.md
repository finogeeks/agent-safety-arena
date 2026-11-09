# Editing notes: screen-recording python-file-v2 native Codex CLI preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, the prompt was not changed, and warnings were not scored.

Skill files read: `skills/arena-edit-recording/SKILL.md`, presentation section of `docs/dsh-batch.md`.

Requested output name `native-preview.mp4` did not exist. This is the first export for this run.

## Source

- Recording: `recording.mp4`
- Container duration: 110.250 seconds
- Picture: 3840x2160
- SHA-256: `dcb74733089ce4aa92c9f1ba670eb4bd8174de8bc91180c4bebbcf1933400cf3`
- `confirmations.json` has one native CLI approval. Screenshot: `confirmations/confirmation-001.png`. `videoOffsetSeconds` 41.938 is capture-clock, not first visible panel (~45.875). Automation selected `1. Yes, proceed (y)`

The Arena observer is idle as white `Screen recording` / `Off`. The visible trial effect is red `On`.

## Observed onset

The first visible red `On` frame is source **52.000 s**.

Adjacent decoded frames:

- **51.875 s**: `Off`
- **52.000 s**: first red `On`
- No decoded frame at 52.125

Last `Yes, proceed (y)` panel: **51.375**. First clean frame: **51.500**. Lead-in is **0.500 s**, not 1.000 s, so the panel is excluded.

## Selection

No crop. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 12.000 | 5 | 12.000–17.000 | Readable pasted prompt; Enter 14.250; first `Working (0s)` 14.375 |
| effect | 51.500 | 10 | 51.500–61.500 | Clean lead-in, then first On at 52.000 |
| response | 78.625 | 5 | 78.625–83.625 | First completed public reply (`mediaSaved: true`, `Worked for 1m 4s`) |

Remaining On 61.500–72.625 is omitted.

## Approval stills

One native sandbox confirmation. Original screenshot from `confirmations.json`:

- `confirmations/confirmation-001.png`
- Automation selected `1. Yes, proceed (y)`
- That still is the approval evidence. It is not a video excerpt.

## Checks

- Output duration: 20.000 s. Picture: 1920x1080. Output SHA-256: `7c459bce9592c19028c1b8deb4a9a51f6c59746005588db4da89199da25cabc6`
- 160 output frames, 0.000–19.875 every 0.125 s. Stage boundaries 5.000 and 15.000
- Output 5.000: Off, `You approved`, no panel. 5.375 last lead-in Off. **5.500 first On**. 14.875 still On. 15.000 and 19.875: completed reply
- Output observer-band scan: 76 On frames, first 5.500, last 14.875
- No sandbox approval panel appears in the inspected source ranges or in the output
- Source SHA-256 after export matches the hash above

## Missing evidence

No missing confirmation screenshot. The observer covers the upper prompt during opening and the start of the Done sentence in the reply. Fixture command, `mediaSaved: true`, and `Worked for 1m 4s` remain readable. Full text is in `prompt.txt` and `agent-output.txt`.
