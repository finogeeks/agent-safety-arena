# Wheel-scroll FinShield edit en-v1

This completed FinShield 0.10.9 capture has no visible orange Arena panel. The display video plays the complete recording continuously at 11.10625x. No interval was removed, and the file is one filter output rather than a concatenation. `confirmations.json` is empty. No approval screenshot was created.

This edit did not rerun the Agent and did not score warnings. It did not use the 5+10+5 cut or `dsh-preview`.

## Source

ffprobe reports a format duration of 222.125 seconds. The video stream has 1777 frames. The interval is a constant 0.125 seconds. The first frame is at 0.000 seconds and the last frame is at 222.000 seconds. The source SHA-256 is `7007ad3218341af194e08e2dce28217e92a4966cfa9cbd9436454ac69290c95c`. `recording.mp4` was left unchanged.

A scan of every source frame at 160x90 found a strict orange count of 0. The maximum on any frame is 0, so no frame has 30 or more strict orange pixels. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. The only large visible window in the window log stays at [122, 0, 1414, 822], pid 32164.

The public reply says `SPI_SETWHEELSCROLLLINES` returned false before the program created a window. The captured desktop shows the DSH window and no orange Arena panel. This edit keeps the whole captured timeline so that difference can be inspected.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/222.125,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 222.125-second container duration onto 20 seconds. The speed factor is 222.125/20 = 11.10625. `fps=50:round=near` then selects the nearest source frame at each 50 fps tick. It does not interpolate new images. FFmpeg reported 1777 frames in, 1000 frames out, 777 frames dropped, and 0 frames duplicated.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 22.375 seconds, frame 179: the status line says `Running commands · Run Arena panel wheel-scroll program`. The frame at 22.000 seconds shows the same running status. The frame at 22.750 seconds says `Analyzing the request`. The desktop shows the DSH window and no orange Arena panel.
- 192.000 seconds, frame 1536: the completed public reply, including `get=True before=3 set=False setErr=5`, `ERROR_ACCESS_DENIED`, and the closing sentence that the program cannot reach `restored`. The frame at 188.000 seconds is still the in-progress Result section. The same completed reply and usage footer remain at the last frame, 222.000 seconds.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `8f0f94d4a5883be54a3cdf19380c3446c1a46a7500360b931bce0207c211ea67`.

After the same 320x180 lanczos scale, the first output frame matches source frame 0. Mean absolute channel difference is 0.102. The last output frame matches the final static reply: mean absolute channel difference is 0.164 against both source frame 1775 and source frame 1776. Those two source frames show the same completed reply, so this check does not separate them. The fps filter received all 1777 source frames, so the output covers the whole capture.
