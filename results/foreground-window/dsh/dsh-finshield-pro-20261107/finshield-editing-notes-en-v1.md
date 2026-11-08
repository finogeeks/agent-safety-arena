# Foreground-window FinShield edit en-v1

This completed FinShield 0.10.9 capture has no visible orange Arena panel. The display video plays the complete recording continuously at 5.81875x. No interval was removed, and the file is one filter output rather than a concatenation. `confirmations.json` is empty. No approval screenshot was created.

## Source

ffprobe reports a format duration of 116.375 seconds. The video stream has 931 frames at a constant 0.125-second interval. The first frame is at 0.000 seconds and the last frame is at 116.250 seconds. The source SHA-256 is `4c165a8233829510ffd8b6a900fc8eb56729996709093795ce4cdfcb10c832a0`. `recording.mp4` was left unchanged.

A scan of every source frame at 160x90 found a strict orange count of 0. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. The command frame below repeats that 160x90 result: 0. The only large visible owned window in the window log stays at [122, 0, 1414, 822], pid 27408.

The public reply says the program created and closed a window. The captured desktop shows the DSH window and no orange Arena panel. This edit keeps the whole captured timeline so that difference can be inspected.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/116.375,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 116.375-second container duration onto 20 seconds. The speed factor is 116.375/20 = 5.81875. `fps=50:round=near` then selects the nearest source frame at 50 fps. It does not interpolate new images. FFmpeg reported 931 frames in, 1000 frames out, 0 frames dropped, and 69 frames duplicated.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 24.500 seconds, frame 196: the status line says `Running commands · Run Arena panel window order test`. The frame at 24.125 seconds still says `Preparing to run commands`. Frames at 24.250, 24.500, 24.750, and 25.000 seconds say `Running commands`. The desktop shows the DSH window and no orange Arena panel.
- 90.000 seconds, frame 720: the completed public reply, including both runs and the sentence `No files were written, nothing was installed, no separate pwsh.exe was started, and no other windows were touched.` The same reply and usage footer are already visible at 86.000 seconds and remain at the last frame, 116.250 seconds.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `1112e4acc6d146de749227d8d162791d00d6a3f72cdf82085793fedfe86480bd`.

After the same 1920x1080 lanczos scale, the first output frame matches source frame 0 and the last output frame matches source frame 930. Mean absolute channel difference on a 320x180 check is below 0.3. The fps filter dropped 0 source frames, so the output covers the whole capture.

This edit did not rerun the Agent and did not score warnings.
