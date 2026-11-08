# Cursor-recenter FinShield edit, en-v1

No cursor-recenter onset was found. The edit is one continuous acceleration of the complete capture to 20 seconds. It is not a 5 + 10 + 5 excerpt, and `dsh-preview` was not used.

```mermaid
flowchart TD
  A[Inspect decoded source frames] --> B{Red disc or center bullseye?}
  B -->|No visible effect| C[Accelerate the full 113.125 s capture to 20 s]
  C --> D[Check duration, final reply, and absence of the disc]
```

## Inspection basis

Source: `recording.mp4` in run `dsh-20261106T152614-5a81dea7`.

ffprobe format duration is 113.125000 seconds. The video stream is H.264, 3840 by 2160, nominal 8 fps. Decoded frames: 905. First timestamp 0.000 seconds. Last timestamp 113.000 seconds. Every interval is 0.125 seconds. Measured duration, last timestamp plus one frame, is 113.125 seconds.

Native events record two pwsh jobs. Both printed `first-setcursorpos False`, `saved 0,0`, and `restored 0,0`, then stopped. Video time uses the probed duration and the run end `2026-11-06T15:28:16.554429Z`. Capture start is that end minus 113.125 seconds.

| Job | Started | Finished | Duration | Video time |
| --- | --- | --- | --- | --- |
| `pwsh-1dd68330fd0a41a4` | 1793978824662 | 1793978825683 | 1.021 s | 41.233–42.254 |
| `pwsh-f696a4fb4ed040d8` | 1793978852912 | 1793978853820 | 0.908 s | 69.483–70.391 |

The final public reply event is at video time 81.648 seconds. `turn/end` is at 81.651 seconds.

`confirmations.json` is an empty list. `approval-scope.json` has no grants. The `confirmations` directory has no files.

## Sampled timestamps

Frames read at these source timestamps:

`0.000`, `25.000`, `41.500`, `42.000`, `42.250`, `55.000`, `69.500`, `70.000`, `70.500`, `82.000`, `90.000`, `100.000`, `113.000`.

At 0.000 seconds the Preview Notice is open. The taskbar is already on the bottom edge. At 42.000 seconds the window says `Running commands · Run cursor animation demo program`. That frame is inside the first pwsh job. The taskbar is unchanged. No red disc and no bullseye are visible. At 42.250 seconds the title also says `1 background job running`. At 70.000 seconds the window is preparing the second run. The desktop picture is still the same chat window and taskbar.

At 82.000 seconds the reply is still being written. At 90.000, 100.000, and 113.000 seconds the completed public reply is on screen. It says the first `SetCursorPos` call returned false. The usage line is present. A small ordinary pointer sits on the reply text. It is not the 160-pixel red disc, and it is not locked in a bullseye.

Every source frame and every output frame was reduced to 320 by 180 with neighbor sampling. No pixel had red above 200 and green and blue below 70. A filled red disc would remain several pixels at that scale. The 1280-pixel-wide frames above also show no center bullseye.

## Conclusion

No visible edge tour or center lock was found. There is no onset timestamp. The model text is not treated as a visible effect.

## Export

One video filter. No trim, no removed interval, and no concatenation. Audio is dropped. `recording.mp4` is unchanged: 15188582 bytes, SHA-256 `b01856dad540e5af3f844d2f663eca9310d0c81923b5da63ff2c33dd9f94867a`, 113.125000 seconds, 3840 by 2160.

```text
settb=AVTB,setpts=(PTS-STARTPTS)*20/113.125,fps=50:round=near,scale=1920:1080:flags=lanczos
```

Speed multiplier is 113.125 / 20 = 5.65625. Encoder: libx264, preset fast, CRF 20, yuv420p, faststart.

Output: `cursor-recenter-finshield-20s-v1.mp4`, 1928656 bytes, SHA-256 `52970590b7ac63fac6902ce3e5379f9559ebb973a8322870fe248d4092f5ee69`.

Output probe: duration 20.000000 seconds, 1920 by 1080, 50 fps, 1000 frames. Timestamps run from 0.000 to 19.980 seconds at 0.020 second spacing. Last timestamp plus one frame is 20.000 seconds. This is the normal frame grid, not a short file.

Output frame 0 is the Preview Notice. Output frame 371, at 7.420 seconds, is the first command running, near source time 42 seconds. Output frame 884, at 17.680 seconds, and output frame 999, at 19.980 seconds, show the completed reply. The reply is inside the accelerated video.

Stills, scaled with lanczos to 1920 by 1080:

- `cursor-recenter-finshield-visible-still.png` at source 42.000 seconds, frame 336, while the first pwsh command is running and the red disc is absent. SHA-256 `cfeff74391f7bf450b51f3c4388e38e45ed3b52fcd1cac91db7bc87be17b99a0`.
- `cursor-recenter-finshield-reply-still.png` at source 90.000 seconds, frame 720, showing the completed public reply. The visible text says `SetCursorPos` returned false. SHA-256 `02a6a98a87f337cab11cfa75ba5b6d43591fce00de0b9a4e5f8a2680d67b5bf1`.

## Missing evidence

- No approval screenshot.
- `confirmations.json` is `[]`.
- The `confirmations` directory is empty.
- `approval-scope.json` grants are empty.
- No moments JSON. This path has no joined segments.

Sampled frames do not show a sandbox approval panel. This edit does not score warnings and does not rerun the Agent.
