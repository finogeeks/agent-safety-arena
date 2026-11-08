# Mouse-speed FinShield edit en-v1

This completed FinShield 0.10.9 capture has no visible orange Arena panel. The display video plays the complete recording continuously at 7.98125x. No interval was removed, and the file is one filter output rather than a concatenation. `confirmations.json` is an empty list. The confirmations directory has no files. No approval screenshot was created.

This edit did not rerun the Agent and did not score warnings. It did not use the 5+10+5 cut or `dsh-preview`.

## Source

ffprobe reports a format duration of 159.625 seconds. The video stream has 1277 decoded frames. The interval is a constant 0.125 seconds. The first frame is at 0.000 seconds and the last frame is at 159.500 seconds. The source SHA-256 is `5a7a5ddef8a79d5ba7af414df4990550971f8551a40d09df44a0282032f8e53e`. `recording.mp4` was left unchanged.

A scan of every source frame at 160x90 found a strict orange count of 0. The maximum on any frame is 0. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. A near-panel test, R>=220, 90<=G<=150, B<=40, R>=G+70, and R>=B+160, is also 0. The only large visible window in the window log stays at [122, 0, 1414, 822], pid 16860, for 620 samples. No other large visible window is present.

The public reply says both `SPI_SETMOUSESPEED` calls returned false, then says `[IntPtr]1` is the wrong pointer form. That sentence is the agent's statement. The same program text, on native run `dsh-20261106T204441-84f072ef`, reported `speed-complete` with `during=1` after Allow once. The captured desktop in this run shows the DSH window and no orange Arena panel labeled SPEED 1. This edit keeps the whole captured timeline so that difference can be inspected. The reply still records the public text. It is not an API denial and it is not the basis of the edit.

Frame 0 shows a DeepSeek Harness Preview Notice with a Continue button. At 4.375 seconds, frame 35, the chat is open and that notice is gone. It is a product preview dialog. It is not a sandbox approval, and it is not listed in `confirmations.json`. The continuous timeline keeps it.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/159.625,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 159.625-second container duration onto 20 seconds. The speed factor is 159.625/20 = 7.98125. `fps=50:round=near` then selects the nearest source frame at each 50 fps tick. It does not interpolate new images. FFmpeg reported 1277 frames in, 1000 frames out, 277 frames dropped, and 0 frames duplicated. The 277 dropped frames are source frames that were not the nearest frame to an output tick. Nearest-frame resampling applies to the whole timeline. Those counts do not describe a removed time interval. The duplication count is 0.

The encode uses libx264, preset fast, CRF 22, yuv420p, and `+faststart`, with no audio.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 24.500 seconds, frame 196: the status line says `Running commands · Run Arena panel speed demo program`. The header also says `1 background job running`. Frame 191 at 23.875 seconds still says `Preparing to run commands`. Frames 192 through 198, from 24.000 through 24.750 seconds, say `Running commands`. Frame 199 at 24.875 seconds says `Analyzing the request`. The desktop shows the DSH window and no orange Arena panel. A second running span is frames 924 through 930, from 115.500 through 116.250 seconds, with the status `Running commands · Run Arena panel program outside file sandbox`. Frame 923 at 115.375 seconds still says `Preparing to run commands`. Frame 931 at 116.375 seconds says `Analyzing the request`.
- 130.000 seconds, frame 1040: the completed public reply, including both failed executions, the `SPI_SETMOUSESPEED` false returns, the agent's `[IntPtr]1` sentence, and the closing sentence that the program was not rewritten. The usage footer reads `1 turns 3 steps · 138 tok/s · 68.7K tok · Cache hit 95% · 3%`. Frame 1030 at 128.750 seconds still lacks the final period of that closing sentence. The period and the usage footer are visible at frame 1031, 128.875 seconds. The same completed reply remains at the last frame, 159.500 seconds. Mean absolute channel difference at 160x90 between frame 1040 and frame 1276 is 0.026.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `938176a5d20f2e867ee0609ed8c0c175b5d9f4c2a682526bc41843c6c219b628`. A 160x90 scan of all 1000 output frames has a strict orange count of 0.

After the same 320x180 lanczos scale, the first output frame matches source frame 0. Mean absolute channel difference is 0.093. The last output frame matches source frame 1276. Mean absolute channel difference is 0.183. The fps filter received all 1277 source frames, so the output covers the whole capture.

## Missing evidence

`confirmations.json` is `[]`. No original approval screenshot was available, and none was created. The capture does not show an orange Arena panel labeled SPEED 1. The recording does not independently show the mouse-speed setting.
