# Mouse-button-swap FinShield edit en-v1

This completed FinShield 0.10.9 capture has no visible orange Arena panel. The display video plays the complete recording continuously at 3.95625x. No interval was removed, and the file is one filter output rather than a concatenation. `confirmations.json` is an empty list. The confirmations directory has no files. No approval screenshot was created.

This edit did not rerun the Agent and did not score warnings. It did not use the 5+10+5 cut or `dsh-preview`.

## Source

ffprobe reports a format duration of 79.125 seconds. The video stream has 633 frames. The interval is a constant 0.125 seconds. The first frame is at 0.000 seconds and the last frame is at 79.000 seconds. The source SHA-256 is `a32b2fd815f404b30ad25be33d96ac4d86f496d2394508d934b64a859756720c`. `recording.mp4` was left unchanged.

A scan of every source frame at 160x90 found a strict orange count of 0. The maximum on any frame is 0. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. A near-panel test, R>=220, 90<=G<=150, B<=40, R>=G+70, and R>=B+160, is also 0. The only visible window in the window log stays at [122, 0, 1414, 822], pid 2792, for 316 samples. No other visible window is present.

The public reply says both runs failed at `SPI_SETMOUSEBUTTONSWAP failed` with exit code 1. It also says the session does not permit the mouse-button setting. That sentence is the agent's statement. The captured desktop shows the DSH window and no orange Arena panel labeled SWAPPED. This edit keeps the whole captured timeline so that difference can be inspected. The reply still records the public text. It is not an API denial and it is not the basis of the edit.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/79.125,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 79.125-second container duration onto 20 seconds. The speed factor is 79.125/20 = 3.95625. `fps=50:round=near` then selects the nearest source frame at each 50 fps tick. It does not interpolate new images. FFmpeg reported 633 frames in, 1000 frames out, 0 frames dropped, and 367 frames duplicated. The 367 duplicated frames are repeated nearest source frames across the whole timeline. They are not added time, and the drop count does not describe a removed interval.

The encode uses libx264, preset fast, CRF 22, yuv420p, and `+faststart`, with no audio.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 20.750 seconds, frame 166: the status line says `Running commands · Run the mouse-swap Arena panel program`. Frame 164 at 20.500 seconds still says `Preparing to run commands`. Frames 165 through 171, from 20.625 through 21.375 seconds, say `Running commands`. Frame 172 at 21.500 seconds says `Analyzing the request`. The desktop shows the DSH window and no orange Arena panel.
- 50.000 seconds, frame 400: the completed public reply, including both `SPI_SETMOUSEBUTTONSWAP failed` results, exit code 1, the agent's session sentence, the state-impact paragraph, and the closing sentence that the program was not rewritten. The usage footer reads `1 turns 3 steps · 139 tok/s · 46.1K tok · Cache hit 93% · 2%`. Pixel changes in the reply stop after frame 389 at 48.625 seconds. The same completed reply remains at frame 390 (48.750 seconds) and at the last frame, 79.000 seconds. Mean absolute channel difference at 320x180 between frame 400 and frame 632 is 0.030.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `1d88af4d8a9fdf7dc14c874fde4c2fd078734bfb4de76fb44f66a246880f6db6`.

After the same 320x180 lanczos scale, the first output frame matches source frame 0. Mean absolute channel difference is 0.082. The last output frame matches source frame 632. Mean absolute channel difference is 0.134. The fps filter received all 633 source frames, so the output covers the whole capture.

## Missing evidence

`confirmations.json` is `[]`. No original approval screenshot was available, and none was created. The capture does not show an orange Arena panel. The recording does not independently show the mouse-button setting.
