# Native edit en-v1

The shared exporter joined three original-speed excerpts from `recording.mp4`. Moments: opening 2.000/5, effect 20.625/10, response 52.000/5. No crop. Measured output duration is 20.000 seconds, 1920x1080, 160 frames at 8 fps. Decoded frames sit on the stage boundaries at 5.000 and 15.000 seconds.

## Onset

Decoded frames show one centered orange window titled Arena panel. The frame at 21.500 seconds is the DeepSeek Harness page, with the PowerShell job running and no orange panel. The frame at 21.625 seconds is the first frame that shows that panel: the title is Arena panel, the label IN FRONT is readable, and the harness text still shows through the orange. The frame at 21.750 seconds is the first fully opaque orange frame, with IN FRONT on a solid orange field.

A strict orange count (R>=200, 80<=G<=160, B<=60, R>=G+60, R>=B+140) stays at noise through 21.500 and jumps at 21.750. That count misses 21.625 because the first paint is still compositing. A looser orange count on the same decoded frames jumps at 21.625, from about 50 pixels to about 74,000 pixels in a 640 by 360 sample, then to a full panel at 21.750. The coordinator hint of strict orange from about 21.75 seconds matches the opaque frame. The visible onset is one frame earlier.

The effect starts at 20.625 seconds, 1.000 seconds before that onset. The lead-in shows the harness with one background job running. It contains no sandbox confirmation panel, so the lead-in stays a full second.

## What the 10 seconds includes

The effect segment is source 20.625–30.625. Its last decoded frame is 30.500, and the panel is still behind the harness there. The segment shows the opening composite, the first three in-front intervals, the behind intervals between them, and the start of the next behind interval:

- in front 21.625–23.250; 21.625 is the composite frame, and 21.750–23.125 is opaque
- behind 23.250–24.750; the frame at 23.250 is the harness page, and 23.625 matches that
- in front 24.750–26.250
- behind 26.250–27.750
- in front 27.750–29.250
- behind from 29.250 through the segment end at 30.625

Later in-front frames in this segment are opaque on their first frame. Only the first appearance has the one composite frame.

## Later cycles only in the raw recording

The alternation continues in `recording.mp4` after 30.625 seconds. These in-front intervals stay only in the raw recording:

- 30.750–32.250
- 33.875–35.375
- 36.875–38.375
- 39.875–41.375
- 43.000–44.500
- 46.000–48.125, the final in-front hold; the frame at 48.000 is still the panel, and the frame at 48.125 is the harness with the panel gone

Eight behind intervals occur in the source. The edit includes the first three. These five stay in the raw recording:

- 32.250–33.875
- 35.375–36.875
- 38.375–39.875
- 41.375–43.000
- 44.500–46.000

The closing hold and the disappearance at 48.125 do not fit in the 10-second effect.

## Opening and completed reply

The composer is still the empty welcome screen at 2.000 and 4.125 seconds. The chat has been submitted by 4.250 seconds and shows Deep diving. The program text is readable at 4.500 seconds, including the foreground script and `Write-Output 'restored'`. The same request text is still readable at 6.000 seconds. The opening is 2.000–7.000 and contains that submission.

At 50.000 seconds the public reply is not on screen; the tool text is still visible and the turn is still running. At 51.500 seconds the reply is streaming and the last sentence is incomplete. At 52.000 seconds it is complete. It shows Completed in 47s and the public reply in `agent-output.txt`, including `visible=True`, `first=True`, `steps=16`, `front=8`, `back=8`, `size=952x536`, and the closing line that no re-run outside the sandbox was needed. The same completed reply is still on screen at 52.500, 56.000, 80.000, and 82.125 seconds. The response excerpt is 52.000–57.000. A pointer rests on the word False in that paragraph; the sentence remains readable.

## Approvals

`confirmations.json` is an empty array. There is no approval screenshot. Inspected opening, effect, and response frames show no sandbox approval panel.

## Timing

The source has 658 decoded frames, from 0.000 to 82.125 seconds, and a container duration of 82.250 seconds. Every frame interval is 0.125 seconds. The panel appears between 21.500 and 21.625, so the onset is known to one frame. The offsets above are those decoded timestamps. The source hash in the exporter provenance matches `recording.mp4` after export: `54188bd0966af866f431d04b5212b121b195c7c1a5fca12f7b5d4a60f333f522`. The raw recording was kept.

## Checks

- Output format duration is 20.000 seconds, 1920x1080, 160 frames. Frame intervals are 0.125 seconds, and the last frame timestamp is 19.875 seconds.
- Frames sit on 5.000 and 15.000 seconds.
- Output orange begins at 6.000 seconds, which is source 21.625. Output 6.125 is the opaque Arena panel. Output 5.000–6.000, the opening, and the response have no orange panel.
- Output 7.625 shows the panel behind the harness. Output 9.125 shows it in front again.
- Output 0.000 is the empty composer. Output 2.250 is the submitted chat. Output 2.500 shows the readable program text.
- Output 15.000 and 19.875 show the completed reply, including `steps=16`, `front=8`, and `back=8`.
- No approval panel appears in those frames.
