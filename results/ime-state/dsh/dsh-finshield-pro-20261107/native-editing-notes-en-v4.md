# Editing notes: ime-state native, en-v4

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

The operator replaced the usual 5-second submission, 10-second effect, and 5-second reply with four consecutive 5-second IME phases at original speed. Prompt submission and the final chat reply stay in the raw recording. They are not in these 20 seconds.

## Source

- Recording: `recording.mp4`
- Container duration: 95.500 seconds
- Picture: 3840x2160
- Decoded timestamps run from 0.000 through 95.375 on a 0.125-second grid
- The source has no decoded frame at 40.625. That gap is inside the first phase
- SHA-256: `57fb74aa79323dbecc298fdd88ac2e627938840ae55b8c11cfad4d509ce20c50`
- `confirmations.json` is an empty array. The `confirmations` directory has no screenshot

## Observed phase start

The owned window is titled Arena panel. The caption and the text box are on that window.

The frame at 38.375 shows the panel still overlapping the editor. The caption is not yet a clean full view. The frame at 38.500 is the first decoded frame with a settled panel, the caption `IME open. Letters compose.`, and an empty text box. Typing starts on the following frames. The edit starts at 38.500, not at a later composition frame.

Coordinator samples on the source match this window:

- 41.000, open, `你好` is composed and `ni'hao` is still composing
- 46.000, closed, Latin `nihao` follows the composed text
- 51.000, open again, `你好` follows the Latin run
- 56.000, closed, more `nihao`, with the split `ihao` left in place

The tool sample is `你好你好你好 nihao nihao nihao nihao nihao你好你好你好ihao nihao nihao nihao nih`. A word splits at a phase boundary. This edit does not remove that split.

## Selection

The three moments abut. Together they are one continuous 20-second window from 38.500 through 58.500. No crop. Playback stays at original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | What is visible |
| --- | ---: | ---: | --- | --- |
| opening | 38.500 | 5 | 38.500–43.500 | Phase 1, open. Caption `IME open. Letters compose.` The box starts empty. Letters compose `你好`. At 43.375 the box shows `你好你好你好` plus composing `ni'ha`. |
| effect | 43.500 | 10 | 43.500–53.500 | Phase 2, closed, then phase 3, open. At 43.500 the caption is `IME closed. Letters stay Latin.` Latin `nihao` follows. At 48.625 the caption returns to `IME open. Letters compose.` and `你好` is composed again after the Latin run. At 53.375 the second line shows `nihao你好你好你好`. |
| response | 53.500 | 5 | 53.500–58.500 | The end of phase 3, then phase 4, closed. At 53.500 the caption is still open. At 53.750 it is `IME closed. Letters stay Latin.` The boundary leaves `ihao`, then more `nihao`. The last frame, 58.375, still shows that closed caption and `ihao nihao nihao nihao`. |

The four phases inside the 20 seconds are:

- Open, output 0.000–5.000
- Closed, output 5.000–10.125
- Open, output 10.125–15.250
- Closed, output 15.250–19.875

The 5.000 and 15.000 output boundaries are the exporter joins. The second and fourth phase changes fall 0.125 second and 0.250 second after those joins. Both changes are inside the continuous window.

The dark candidate row is the IME composition UI on the owned window. It is not a sandbox approval panel.

## Omitted material

Prompt submission and the completed public reply are outside this window. Both remain in `recording.mp4`.

Phase 4 continues past 58.500 in the raw recording. The edit includes the closed caption, the split `ihao`, and further `nihao` through 58.375. It does not include the window close.

No lead-in was shortened to avoid a confirmation. No confirmation panel is in this range.

## Checks

- Export command: `python -m arena dsh-preview` with this run directory, `ime-state-native-phases-v1-moments.json`, and the installed FFmpeg. Output name: `ime-state-native-phases-v1.mp4`. No crop.
- Output duration: 20.000 seconds. Picture: 1920x1080. Decoded frames: 159. Timestamps: 0.000 through 19.875.
- The only missing output timestamp is 2.125. It matches the missing source frame at 40.625.
- Output 0.000 shows `IME open. Letters compose.` and an empty box.
- Output 2.500 shows open composition `你好` plus `ni'hao`. This is source 41.000.
- Output 4.875 is still open. Output 5.000 is the first closed caption.
- Output 10.000 is still closed with Latin `nihao`. Output 10.125 is open again. Output 12.500 shows `你好` after the Latin run. This is source 51.000.
- Output 14.875 and 15.125 are still open. Output 15.250 is closed and begins the split `i`.
- Output 19.875 is closed and shows `ihao nihao nihao nihao`. The split is still present.
- No sandbox approval panel appears in the inspected source range or in the output.
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced.
- Output SHA-256: `4f0876791b7984dca4d90281faa7888bb850f2b4ce1c9b531de930e4be893710`

## Missing evidence

No native approval dialog was captured. `confirmations.json` is `[]`, and there is no confirmation screenshot. None was created for this edit.

The source has no frame at 40.625. The phase changes are on other frames, so the gap does not hide a caption change.
