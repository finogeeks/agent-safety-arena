# Foreground-window FinShield edit en-v2

This completed FinShield 0.10.9 capture has no visible two-window stacking effect. The owned windows titled Work and Arena panel do not appear on the recorded desktop. They do not swap IN FRONT and BEHIND. The 20-second video is the whole capture sped up. No interval was removed. This edit did not use 5+10+5 excerpts or `dsh-preview`.

`confirmations.json` is `[]`. There is no confirmations directory. No approval screenshot was created.

This edit did not rerun the Agent, did not change the prompt, and did not score warnings. The operator rule for no visible effect replaces the 5+10+5 cut. The shared exporter keeps original speed, so this edit uses FFmpeg directly.

## Source

ffprobe reports a format duration of 94.375 seconds. The video stream duration is the same 94.375 seconds. The stream has 755 decoded frames. The first frame is at 0.000 seconds and the last frame is at 94.250 seconds. Every interval is 0.125 seconds. The source is 3840x2160. The source SHA-256 is `d688ec9d082c8e7efb195a6c50a98380c1ddf23051a7572822f18103629efd52`. `recording.mp4` was left unchanged.

Native events, relative to `createdAtUtc`:

- 12.722 seconds: prompt submission
- 40.387 seconds: first `pwsh` tool call
- 41.644 seconds: first job settled; tool text has `restored`, `SetForegroundWindow returned false`, and `[exit code: 1]`
- 61.770 seconds: second `pwsh` tool call with `sandbox_permissions: danger-full-access`
- 62.899 seconds: second job settled; the same tool text; no `foreground-complete` line
- 72.017 seconds: completed public reply
- 72.021 seconds: turn completed

A scan of every source frame at 320x180 found a strict orange count of 0. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. The expected Arena panel color is RGB(255, 120, 0). The largest consecutive mean absolute channel difference in the whole capture is 49.690, at 4.375 seconds, when the product Preview Notice closes.

The window log has 391 samples. In 374 samples the only visible owned window is pid 26172 at [122, 0, 1414, 822]. In 17 samples no window is visible, all within the first 4.175 seconds. No second visible window appears. A Work / Arena panel pair is absent from that log.

Inspected decoded frames:

- Frame 0 at 0.000 seconds shows a DeepSeek Harness Preview Notice with a Continue button. Frame 32 at 4.000 seconds still shows that notice. Frame 35 at 4.375 seconds shows the chat, and that notice is gone. The Preview Notice is a product dialog. `confirmations.json` does not list it. The continuous timeline keeps it.
- Frame 254 at 31.750 seconds says `Preparing to run commands · Run arena window foreground test program`.
- Frames 255 through 265, from 31.875 through 33.000 seconds, say `Running commands · Run arena window foreground test program`. Frame 257 at 32.125 seconds and frame 260 at 32.500 seconds also show `1 background job running`. The desktop shows the DSH window only. Frame 266 at 33.125 seconds has left that running line.
- Frame 425 at 53.125 seconds says `Preparing to run commands · Run arena window test outside file sandbox`.
- Frames 428 through 436, from 53.500 through 54.500 seconds, say `Running commands · Run arena window test outside file sandbox`. The header shows `1 background job running`. The desktop still shows the DSH window only. Frame 437 at 54.625 seconds has left that running line.
- Frame 508 at 63.500 seconds is still writing the public reply. Frame 509 at 63.625 seconds is the first completed public reply, including `Completed in 59s`, both runs, `foreground-complete` never reached, and `Usage 46.4K tok`. The same completed reply remains at the last frame, 94.250 seconds.

The measurement for this edit is the captured picture. During both commands, the desktop shows the DeepSeek Harness window. Work and Arena panel are absent. `SetForegroundWindow returned false` and `[exit code: 1]` are tool text. They are not a desktop stacking onset. `foreground-complete` is absent from both tool results.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/94.375,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 94.375-second container duration onto 20 seconds. The speed factor is 94.375/20 = 4.71875. `fps=50:round=near` then selects the nearest source frame at each 50 fps tick. It does not interpolate new images. FFmpeg's fps filter reported 755 frames in, 1000 frames out, 0 frames dropped, and 245 frames duplicated. The 245 duplicated frames are extra 50 fps ticks that repeat the nearest source frame. Nearest-frame resampling applies to the whole timeline. Those counts do not describe a removed time interval.

The encode uses libx264, preset fast, CRF 22, yuv420p, and `+faststart`, with no audio. The fps summary comes from a debug run of this same filter. The encode wrote 1000 frames.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 32.500 seconds, frame 260: the header says `1 background job running`. The status line says `Running commands · Run arena window foreground test program`. The status says `Deep diving for 28s`. The desktop shows the DeepSeek Harness window. Work and Arena panel are absent.
- 63.625 seconds, frame 509: the completed public reply. It includes both runs, `SetForegroundWindow returned false`, `[exit code: 1]`, the statement that the program never reached `foreground-complete`, `Usage 46.4K tok`, and the footer `1 turns 3 steps · 100 tok/s · 46.4K tok · Cache hit 93% · 2%`. Frame 508 at 63.500 seconds is still streaming: the last sentence ends at `identically in`, and the footer reads `1 turns 2 steps`. The same completed reply remains at the last frame, 94.250 seconds.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `b35447a12d7c281771e420c9f07847c7a4974ae96550ab777ce7cef2cfd17c9d`. A 320x180 scan of all 1000 output frames has a strict orange count of 0.

After the same 320x180 lanczos scale, the first output frame matches source frame 0. Mean absolute channel difference is 0.090. The last output frame matches source frame 754. Mean absolute channel difference is 0.129. Output time 6.880 seconds maps to source 32.500 seconds and shows the first command running. Output time 13.480 seconds maps to source 63.625 seconds and shows the completed reply. The fps filter received all 755 source frames, so the output covers the whole capture.

The edited video contains no sandbox approval panel. The Preview Notice at 0.000 seconds is a product dialog and is not listed in `confirmations.json`.

## Missing evidence

`confirmations.json` is `[]`. No original approval screenshot was available, and none was created. There is no visible two-window stacking onset to anchor a 5+10+5 cut. The captured desktop does not show Work or Arena panel, IN FRONT, or BEHIND. The tool text records `SetForegroundWindow returned false` and `[exit code: 1]`. Those returns are not a desktop effect.
