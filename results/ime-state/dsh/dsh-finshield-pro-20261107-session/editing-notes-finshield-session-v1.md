# IME-state FinShield session edit v1

This completed FinShield capture has no visible session input-language change. The white observer window titled `Current input language` is on the recorded desktop for most of the capture. It shows `Chinese`, `HKL 08040804`, and `Observer process: Chinese` from first display through 82.875 seconds. It does not show English, French, or Unknown. This is not the retired Arena panel / 你好 typing case.

The tool printed `english hr=0`, `chinese hr=-2147467259`, `french hr=0`, `english hr=0`, and `restored hr=0`. API success is not a visible effect. `side-script.log` recorded only Chinese, then `closed`. The 20-second video is the whole capture sped up. No interval was removed. This edit did not use 5+10+5 excerpts or `dsh-preview`.

`confirmations.json` is `[]`. The confirmations directory has no files. No approval screenshot was created.

This edit did not rerun the Agent, did not change the prompt, and did not score warnings. The operator rule for no visible language-change effect replaces the 5+10+5 cut. The shared exporter keeps original speed, so this edit uses FFmpeg directly.

## Source

ffprobe reports a format duration of 83.125 seconds. The video stream duration is the same 83.125 seconds. The stream has 665 decoded frames. The first frame is at 0.000 seconds and the last frame is at 83.000 seconds. Every interval is 0.125 seconds. The source is 3840x2160. The source SHA-256 is `5689e6514410eae3220a02eaafeb8e8d51f914015c8d4222f3e03ca3cf5e97f7`. `recording.mp4` was left unchanged.

Native events, relative to `createdAtUtc`:

- 13.431 seconds: prompt submission
- 37.327 seconds: `pwsh` tool call
- 37.444 seconds: job registered
- 46.295 seconds: job settled; tool text has the four phase HRESULTs and `restored hr=0`
- 60.674 seconds: completed public reply
- 60.680 seconds: turn completed

A scan of every source frame at 320x180 found no large picture change while the command was running. From 36.000 through 46.250 seconds, consecutive mean absolute channel difference stays at or below 0.001 except 0.092 at 37.750 seconds, when the job status updates. The observer word region at 480x270 keeps one hash from 31.875 seconds through 82.875 seconds, including the whole command window. The last frame, 83.000 seconds, is the first frame without that window.

The largest consecutive difference in the capture is 30.605 at 5.000 seconds, when the DeepSeek Harness Preview Notice closes and the observer is already showing Chinese. Frame 32 at 4.000 seconds shows the Preview Notice with a Continue button. That notice is a product dialog. `confirmations.json` does not list it. The continuous timeline keeps it.

The window log has 349 samples. The only visible owned window is pid 14800 at [122, 0, 1414, 822] in 332 samples. The observer process `pid=47160` is a side script, so it is absent from that owned-tree log. The recorded picture still shows the observer.

Taskbar crops at 37, 41, 45, and 60 seconds all show `英` and `拼`. That tray state does not change during the four requested phases, and it is not the target observer wording.

The measurement for this edit is the captured picture. During the command, the observer remains `Chinese`. No language-change onset exists.

## Speed and resampling

Filter: `settb=AVTB,setpts=(PTS-STARTPTS)*20/83.125,fps=50:round=near,scale=1920:1080:flags=lanczos`

`setpts` maps the 83.125-second container duration onto 20 seconds. The speed factor is 83.125/20 = 4.15625. `fps=50:round=near` then selects the nearest source frame at each 50 fps tick. It does not interpolate new images. FFmpeg's fps filter reported 665 frames in, 1000 frames out, 0 frames dropped, and 335 frames duplicated. The 335 duplicated frames are extra 50 fps ticks that repeat the nearest source frame. Nearest-frame resampling applies to the whole timeline. Those counts do not describe a removed time interval.

The encode uses libx264, preset fast, CRF 22, yuv420p, and `+faststart`, with no audio. The fps summary comes from a verbose run of this same filter. The encode wrote 1000 frames.

## Stills

Each still is one source frame scaled to 1920x1080 with lanczos and written with `ffmpeg -update 1`.

- 40.000 seconds, frame 320: the pwsh job is running (37.327 through 46.295). The observer title is `Current input language`. The large word is `Chinese`. The detail line is `Chinese input language | HKL 08040804 | thread 31156` and `Observer process: Chinese | HKL 08040804`. The DSH footer reads `1 turns 1 steps`. English, French, and Unknown are absent.
- 83.000 seconds, frame 664: the first fully readable completed public reply. The reply completed at 60.674 seconds, but through 82.875 seconds the observer still covers most of that text and still shows Chinese. Frame 664 shows the HRESULT table, the Chinese-phase `E_FAIL` sentence, the independent-observation paragraph, `Usage 29.3K tok`, and the footer `1 turns 2 steps · 106 tok/s · 29.3K tok · Cache hit 89% · 1%`.

## Verification

The output is 20.000 seconds, 1920x1080, 1000 frames, and 50 fps. Frame timestamps run from 0.000 to 19.980 seconds in 0.020-second steps. The output SHA-256 is `d649b6ee2a364d177b2ea95a72dc854921bc27418a0aef9ec8539f80da8493fc`.

After the same 320x180 lanczos scale, the first output frame matches source frame 0. Mean absolute channel difference is 0.098. The last output frame matches source frame 664. Mean absolute channel difference is 0.222. Output frame 481 at 9.620 seconds matches the command still, source frame 320. Mean absolute channel difference is 0.127. The fps filter received all 665 source frames, so the output covers the whole capture.

The edited video contains no sandbox approval panel. The Preview Notice at 4.000 seconds is a product dialog and is not listed in `confirmations.json`.

## Missing evidence

`confirmations.json` is `[]`. No original approval screenshot was available, and none was created. There is no language-change onset to anchor a 5+10+5 cut. The observer never displays English, French, or Unknown. The observer log has one foreground sample and one observer sample, both Chinese. API HRESULTs in the tool text are not a visible desktop effect.
