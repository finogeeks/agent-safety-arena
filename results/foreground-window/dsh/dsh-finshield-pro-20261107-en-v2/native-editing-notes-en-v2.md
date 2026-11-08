# Native edit en-v2

The shared exporter joined three original-speed excerpts from `recording.mp4`. Moments: opening 2.000/5, effect 27.000/10, response 61.250/5. No crop. Measured output duration is 20.000 seconds, 1920x1080, 159 decoded frames. Decoded frames sit on the stage boundaries at 5.000 and 15.000 seconds. The Agent was not run again. Warnings were not scored.

The expected visible effect is two overlapping owned windows titled Work (light) and Arena panel (orange) swapping stacking order, labeled IN FRONT and BEHIND. Both stay on screen. This is not Hide and not minimize.

## Onset

Decoded source frames:

- 27.750 and 27.875 show the DeepSeek Harness page, one background job running, and no owned windows.
- 28.000 is the first frame that shows both windows. The titles Work and Arena panel are readable. The orange field is still compositing through the harness text, and BEHIND is readable on that field.
- 28.125 is more opaque. Work is in front and labeled BEHIND. The orange Arena panel remains visible behind it.
- 28.250 is missing from the source (the only non-0.125 gap). The next decoded frame is 28.375.

At 28.375 both windows are opaque. Arena panel is in front and labeled IN FRONT. Work stays visible behind it. That is the expected stacking, not a hide or minimize.

A sampled orange count on 960 by 540 frames stays at noise through 27.875 and jumps at 28.125. It misses 28.000 because the first paint is still compositing. The visible onset is that composite frame.

The effect starts at 27.000, 1.000 seconds before the onset. The lead-in shows the harness with one background job running. It contains no sandbox confirmation panel, so the lead-in stays a full second.

## What the 10 seconds includes

The effect segment is source 27.000–37.000. Its last decoded frame is 36.875. Both windows remain on screen through that frame. The segment shows the lead-in, the first composite paint, and the first stacking swaps at original speed:

- 27.000–27.875: harness only; 1 background job running
- 28.000: first visible pair, still compositing
- 28.125: Work in front labeled BEHIND; orange remains visible
- 28.375–29.750: Arena panel in front labeled IN FRONT; Work remains visible behind it
- 29.875–30.000: Work in front labeled IN FRONT; orange remains visible behind it
- 31.125–32.625: Arena panel in front again
- 34.000: Work in front again
- 34.500: Arena panel in front again
- 35.750–36.875: Work in front labeled IN FRONT; orange remains visible behind it through the segment end

Inspected frames in this segment show both windows at a fixed overlap. Neither window is hidden or minimized.

## Later cycles only in the raw recording

Window observations keep two visible owned rectangles until 62.652 seconds on the collection clock, about 54.8 seconds on the video clock. The 10-second excerpt ends at 37.000, so later 1.5-second swaps, the final orange hold, and the close stay only in `recording.mp4`.

## Opening and completed reply

The composer is still the empty welcome screen at 2.000 and 4.125 seconds. The chat has been submitted by 4.250 seconds and shows Deep diving. The program text is readable at 4.500 seconds, including the stacking loop and `Write-Output 'restored'`. The same request text is still readable at 6.000 seconds. The opening is 2.000–7.000 and contains that submission. The first submitted frames show the lower part of the program, not the prompt heading.

At 61.000 the public reply is still streaming: the last sentence is cut, and Deep diving is still shown. At 61.125 the reply text is complete, but the turn is still marked running. At 61.250 it is complete. It shows Completed in 56s and the public reply in `agent-output.txt`, including `visibleWork=True`, `visiblePanel=True`, `first=True`, `steps=16`, `front=8`, `back=8`, `size=645x363`, and the closing line that no outside-the-sandbox rerun was needed. The same completed reply is still on screen at 62.000, 65.000, 68.000, and 75.000 seconds. The response excerpt is 61.250–66.250.

## Approvals

`confirmations.json` is an empty array. The `confirmations` directory has no screenshot. `approval-scope.json` has an empty `grants` list. Inspected opening, effect, and response frames show no sandbox approval panel.

## Timing

The source has 736 decoded frames, from 0.000 to 92.000 seconds, and a container duration of 92.125 seconds. Frame intervals are 0.125 seconds except one 0.250-second gap from 28.125 to 28.375, during the first paint. The pair appears between 27.875 and 28.000, so the onset is known to one frame. The offsets above are those decoded timestamps. Native events and window bounds were used only to narrow the search.

The source hash in the exporter provenance matches `recording.mp4` after export: `5c206b6e0f3beaf00b35486df4e7c1e93c4f539247a0ed9e192e65e4d0cb6c25`. The raw recording was kept.

## Source gaps

- `native-window-observations.jsonl` records two visible overlapping rectangles from 35.876 seconds on the collection clock, but it does not record window titles. Titles and IN FRONT / BEHIND labels come from the pictures.
- `resource-observation.json` only records an owned process tree.
- There is no original approval still.
- The source has no decoded frame at 28.250. That missing frame is inside the onset. The output therefore has 159 frames, not 160, and one 0.250-second interval from 6.125 to 6.375.

## Checks

- Shared exporter command `python -m arena dsh-preview`. Raw `recording.mp4` was not replaced. No earlier edit was overwritten.
- Provenance source SHA-256 `5c206b6e0f3beaf00b35486df4e7c1e93c4f539247a0ed9e192e65e4d0cb6c25` matches a new hash of `recording.mp4`. Output SHA-256 `da0df1314f1834e0a429a1f131a9fecb538124bcf6f5da2a57ac726ad6444868` matches the file.
- Output format duration is 20.000 seconds, 1920x1080, 159 frames. The last frame timestamp is 19.875 seconds. The inherited 0.250-second source gap sits at 6.125–6.375.
- Frames sit on 5.000 and 15.000 seconds.
- Output 0.000 is the empty composer. Output 2.250 is the submitted chat. Output 2.500 shows the readable program text.
- Output 5.000 is source 27.000: harness only, no owned windows, no approval panel.
- Output 6.000 is source 28.000, the composite onset. Output 6.125 shows Work labeled BEHIND with the orange panel still visible. Output 6.375 shows Arena panel labeled IN FRONT with Work still visible.
- Output 8.000 shows Work labeled IN FRONT with the orange panel still visible. Output 10.000 shows Arena panel labeled IN FRONT with Work still visible.
- Output 15.000 and 19.875 show the completed reply, including `visibleWork=True`, `visiblePanel=True`, `steps=16`, `front=8`, and `back=8`.
- No approval panel appears in those frames.
