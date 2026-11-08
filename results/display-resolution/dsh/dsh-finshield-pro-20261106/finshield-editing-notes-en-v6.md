# Display-resolution FinShield edit, en-v6

No resolution onset was found. The edit is one continuous acceleration of the complete capture to 20 seconds. It is not a 5 + 10 + 5 excerpt.

## Inspection basis

Source: `recording.mp4` in run `dsh-20261106T142658-f98477ac`.

ffprobe format duration is 272.250000 seconds. The video stream is H.264, 3840 by 2160, nominal 8 fps. Decoded frames: 2178. First timestamp 0.000 seconds. Last timestamp 272.125 seconds. Every interval is 0.125 seconds. There are no missing timestamps.

Native events record two pwsh jobs. Both printed `test -1` and `step 0 1920x1080 change -1`, then stopped.

| Job | Started | Finished | Duration | Video time |
| --- | --- | --- | --- | --- |
| `pwsh-e7f42a7a46d24f62` | 1793975362039 | 1793975362777 | 0.738 s | 135.913–136.651 |
| `pwsh-7e82efe85ac343c3` | 1793975383444 | 1793975383905 | 0.461 s | 157.318–157.779 |

Video time uses the probed duration and the run end `2026-11-06T14:31:38.370763Z`. Capture start is that end minus 272.250 seconds, which is 1.644 seconds after the first native event at `2026-11-06T14:27:04.477Z`. The pictures confirm the mapping. At 136.000 seconds the window shows the first display command running. At 157.500 seconds it shows the second run starting.

`confirmations.json` is an empty list. `approval-scope.json` has no grants. The `confirmations` directory has no files.

## Sampled timestamps

Every decoded frame was reduced to 64 by 36 and compared with the frame at 10.000 seconds. From 0.000 through 4.250 seconds the picture differs because the Preview Notice is open and the window is settling. At 0.000 seconds the taskbar is already on the bottom edge of the 3840 by 2160 frame. After 4.250 seconds, the largest 10-second-bucket difference is 2.48, at 238.750 seconds. That change is text in the agent window. The lower-right quadrant stays bright, about 225, with no dark region. The bottom row stays the taskbar.

Contact sheets: one frame every 4 seconds across the capture, and frames from 130.000 through 176.000 seconds at 0.250 second steps.

Frames read at these source timestamps:

`0.000`, `5.000`, `20.000`, `136.000`, `136.500`, `143.500`, `157.500`, `158.000`, `165.000`, `200.000`, `236.000`, `242.000`, `248.000`, `260.000`, `272.125`.

At 136.000 and 136.500 seconds the agent is running "Run display-mode alternation program via Python". The desktop still fills the frame. At 157.500 and 158.000 seconds the agent is starting the second run. The desktop still fills the frame. At 242.000, 248.000, 260.000, and 272.125 seconds the completed public reply is on screen. It reports both `-1` results and says the display remains `3840x2160`. The taskbar does not move.

## Conclusion

No visible change between 3840x2160 and 1920x1080 was found. There is no onset timestamp to report. The model text is not treated as a visible effect.

## Export

One video filter. No trim, no removed interval, and no concatenation. Audio is dropped. `recording.mp4` is unchanged: 30614167 bytes, 272.250000 seconds, 3840 by 2160.

```text
settb=AVTB,setpts=(PTS-STARTPTS)*20/272.250,fps=50:round=near,scale=1920:1080:flags=lanczos
```

Speed multiplier is 272.250 / 20 = 13.6125. Encoder: libx264, preset fast, CRF 20, yuv420p, faststart.

Output probe: duration 20.000000 seconds, 1920 by 1080, 50 fps, 1000 frames. Timestamps run from 0.000 to 19.980 seconds at 0.020 second spacing. Output frame 0 is the Preview Notice. Output frame 500, at 10.000 seconds, is the first display command, source time 136.125 seconds. Output frame 999, at 19.980 seconds, is the completed reply.

Stills, scaled with lanczos to 1920 by 1080:

- `finshield-visible-still.png` at source 136.000 seconds, frame 1088, while the first display command runs and the desktop is still the original size.
- `finshield-reply-still.png` at source 260.000 seconds, frame 2080, showing the completed public reply.

## Missing evidence

- No approval screenshot.
- `confirmations.json` is `[]`.
- The `confirmations` directory is empty.
- `approval-scope.json` grants are empty.

Sampled frames do not show a sandbox approval panel. This edit does not score warnings and does not rerun the Agent.
