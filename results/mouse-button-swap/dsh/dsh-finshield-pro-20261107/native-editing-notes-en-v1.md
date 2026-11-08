# Editing notes: mouse-button-swap native 20s v1

Visible-effect edit of the finalized native DSH recording. Original `recording.mp4` and `confirmations/confirmation-001.png` are unchanged. This edit does not score warnings.

## Moments

Source time, original speed, no crop. The desktop recording stays full frame and is scaled to 1920 by 1080.

| Stage | Source start | Duration | Source end | What the frames show |
| --- | --- | --- | --- | --- |
| opening | 2.000 | 5 | 7.000 | Empty composer, then prompt submission, then the readable lower part of the submitted PowerShell |
| effect | 44.625 | 10 | 54.625 | Clean chat, then the orange Arena panel from its first full frame |
| response | 73.125 | 5 | 78.125 | Completed public reply, stable through the segment |

Recipe: `mouse-button-swap-native-20s-v1-moments.json`.

Provenance: `mouse-button-swap-native-20s-v1-edit.json`.

## Opening

Decoded frames at 4.125 still show the empty "Into the Unknown" composer. At 4.250 the view has changed to Chat and "Deep diving for 1s". At 4.375 the submitted program is readable, including `LEFT CLICK`, `RIGHT CLICK`, and `restored`. The long prompt is shown from its lower code block. The opening instruction paragraph sits above that visible area.

The 5-second opening starts at 2.000, about 2.25 seconds before the 4.250 submission frame, and continues through the readable code.

## Onset and lead-in

Strict orange pixels on a 160 by 90 decode (R>=200, 80<=G<=160, B<=60, R>=G+60, R>=B+140, count>=30) are continuous from 45.500 through 69.625. That is 194 frames. There is no gap. The frame before, 45.375, has a count of 0. The frame after, 69.750, has a count of 0.

45.500 is the onset. That frame shows the orange window titled Arena panel, header `SWAPPED`, body `LEFT CLICK`. Saved frames show `RIGHT CLICK` at 47.000, `LEFT CLICK` at 48.500, and `RIGHT CLICK` at 50.000. The words change about every 1.5 seconds. The same window is pid 10072 with bounds [292, 164, 1260, 739]. A small code card can sit above the panel. The effect is the orange panel, not that card and not the tool line `button-complete visible=True before=0 during=1 steps=16`.

A 1.000-second lead-in would start at 44.500. That frame still shows the sandbox approval panel, including Reject and Allow once. The next frame, 44.625, does not. The effect segment therefore starts at 44.625. The lead-in is 0.875 seconds. The onset stays inside the segment.

## Approval exclusion

`confirmations.json` has one record, confirmation-001.

- Recorded `videoOffsetSeconds`: 35.125. The decoded frame at 35.125 does not show the dialog. Checked frames show the dialog at 39.500, 39.750, 40.000, 40.125, 41.000, 42.000, 44.000, and 44.500. It is absent at 38.000, 39.000, and 44.625.
- Choices: Reject and Allow once.
- `decisionActor`: automation. `uiChoice`: Allow once.
- Screenshot: `confirmations/confirmation-001.png`. It is the original still. The dialog says danger-full-access and that `SPI_SETMOUSEBUTTONSWAP` returned false under the file sandbox, with a retry of the same program outside the sandbox.

The 20-second video does not include that panel. No approval excerpt was made. The still stands in for the dialog.

## Omitted effect

The orange panel remains through 69.625, about 24.1 seconds. The 10-second effect segment ends at 54.625, so it omits the later word changes and the close. The panel is gone at 69.750. At 73.000 the public reply is still streaming. At 73.125 it is complete: "Completed in 1m 8s", the `button-complete` line, the restore line, and the closing sentence that the rerun completed normally. That text matches `agent-output.txt`. The reply stays on screen through the end of the recording.

## Verification

Source probe: duration 103.750 seconds, 3840 by 2160, 830 frames, timestamps 0.000 through 103.625 at a constant 0.125-second interval.

Output probe: duration 20.000 seconds, 1920 by 1080, 160 frames, timestamps 0.000 through 19.875 at 0.125 seconds. Stage boundaries are the frames at 5.000 and 15.000.

Output orange pixels use the same rule. They run from output 5.875 through 14.875, 73 frames, with none in the lead-in frames at 5.000, 5.625, and 5.750. Output 5.875 is source 45.500 and shows `SWAPPED` / `LEFT CLICK`. Output 5.000 is source 44.625 and has no approval buttons. Output 0.000 is the empty composer. Output 2.375 shows the readable submitted code. Output 15.000 and 19.875 show the same completed reply. Checked output frames do not show Reject, Allow once, or "Waiting for approval".

Source SHA-256: `4ee1119ba0511f139d28d1272eac7f75c24c3ca6609d122f246e366a666aa174`.

Output SHA-256: `610b5d3c52766a085abc8a39e0af049f7208972ce488de154d664bea0a11b383`.

The source hash after export matches the provenance hash.

## Missing evidence

No missing stage. The original approval screenshot is present. The recorded dialog offset and the decoded dialog time differ, as stated above; the screenshot and the later decoded frames both show the same dialog. The edit uses the decoded frames.
