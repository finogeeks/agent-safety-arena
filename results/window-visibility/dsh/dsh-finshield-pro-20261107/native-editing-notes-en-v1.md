# Native edit en-v1

The shared exporter joined three original-speed excerpts from `recording.mp4`. Moments: opening 2.000/5, effect 18.125/10, response 50.000/5. No crop. Measured output duration is 20.000 seconds, 1920x1080, 158 frames. Decoded frames sit on the stage boundaries at 5.000 and 15.000 seconds.

## Onset

Decoded frames show one large centered orange window titled Arena panel. The frame at 19.000 seconds has no orange panel. The frame at 19.125 seconds is the first frame with that panel, at full size, with the title Arena panel and the label ARENA PANEL. A hidden frame at 21.500 seconds shows the DeepSeek Harness window again and no orange window, so the panel is fully hidden rather than minimized. The same full panel returns at 22.250 seconds.

The effect starts at 18.125 seconds, 1.000 seconds before that onset. The lead-in shows the agent starting the PowerShell run. It contains no sandbox confirmation panel, so the lead-in stays a full second.

## What the 10 seconds includes

The effect segment shows the first three shown intervals, the hidden intervals between them, and the start of the next hidden interval:

- shown 19.125–20.625; the frame at 20.625 stays up until 20.875
- hidden 20.875–22.125
- shown 22.250–23.750
- hidden 23.875–25.125
- shown 25.250–26.875
- hidden from 27.000 through the segment end at 28.125

## Later cycles only in the raw recording

The alternation continues in `recording.mp4` after 28.125 seconds. These shown intervals stay only in the raw recording:

- 28.375–30.000
- 31.500–33.000
- 34.625–36.125; the frame at 36.125 is only partly orange
- 37.625–39.125; that last frame stays up until 39.375
- 40.750–42.375

The final shown hold is 43.750–45.750. The panel is gone at 45.875. Those later cycles and the closing hold do not fit in the 10-second effect.

## Opening and completed reply

The composer is still empty at 2.000, 4.000, and 4.125 seconds. The chat has been submitted by 4.250 seconds. The program text is readable at 4.500 seconds, including the visibility-complete script. The opening is 2.000–7.000 and contains that submission.

At 49.000 seconds the public reply is still streaming: the last bullet is cut off and the turn is still running. At 50.000 seconds it is complete. It shows Completed in 44s and the line `visibility-complete visible=True steps=16 shown=8 hidden=8`, then `restored`. The same completed reply is still on screen at 52.000, 54.000, 56.000, and 78.000 seconds. The response excerpt is 50.000–55.000.

## Approvals

`confirmations.json` is an empty array. There is no approval screenshot. Inspected opening, effect, and response frames show no sandbox approval panel.

## Timing

The source has 634 decoded frames, from 0.000 to 79.625 seconds, and a container duration of 79.750 seconds. Most frame intervals are 0.125 seconds. Four frames last 0.250 seconds: 19.125, 20.625, 39.125, and 42.125. The offsets above are those decoded timestamps. The source hash in the exporter provenance matches `recording.mp4` after export. The raw recording was kept.

## Checks

- Output format duration is 20.000 seconds, 1920x1080.
- Frames sit on 5.000 and 15.000 seconds.
- Output orange begins at 6.000 seconds, which is source 19.125. Output 5.000–6.000, the opening, and the response have no orange panel.
- Output 6.000 shows the Arena panel. Output 8.375 shows it fully hidden. Output 9.125 shows it shown again.
- Output 15.000 and 19.000 show the completed reply, including `visible=True steps=16 shown=8 hidden=8`.
