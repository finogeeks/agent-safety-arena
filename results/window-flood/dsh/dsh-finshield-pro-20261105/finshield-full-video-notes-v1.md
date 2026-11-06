# Complete FinShield capture accelerated to 20 seconds

The operator requested the complete captured recording at a faster playback
speed. This export uses the whole `recording.mp4` from run
`dsh-20261105T124356-75deef93`. It does not use the selected opening, effect, and
reply excerpts in `overview-v2.mp4`.

## Source and output

| Property | Source | Output |
| --- | --- | --- |
| Duration | 113.000 seconds | 20.000 seconds |
| Dimensions | 3840 by 2160 | 1920 by 1080 |
| Decoded frames | 902 | 1000 |
| Frame rate | nominal 8 fps, variable timestamps | 50 fps |
| First frame timestamp | 0.000 seconds | 0.000 seconds |
| Last frame timestamp | 112.875 seconds | 19.980 seconds |
| Audio streams | 0 | 0 |

Output: [finshield-full-20s-v1.mp4](media/finshield-full-20s-v1.mp4), 1259131 bytes.
The speed multiplier is exactly 113 divided by 20, or 5.65. The whole source
interval from 0 to 113 seconds is processed continuously. There are no trims,
selected segments, concatenation, crops, inserted pictures, titles, or overlays.

The filter is:

```text
settb=AVTB,setpts=(PTS-STARTPTS)*20/113,fps=50:round=near,scale=1920:1080:flags=lanczos
```

The encoder is H.264 through `libx264`, fast preset, CRF 20, yuv420p, with MP4
faststart. The output limit is 20 seconds, which is the complete source duration
after the continuous timestamp transform, not a selected source interval.

## Frame preservation

The source's actual decoded count is 902. Older notes said 904; 904 is the count
expected from 113 seconds at exactly 8 fps, before the two missing timestamps.
The original source has no frames at 62.750 and 63.000 seconds. Those gaps are
preserved; this export cannot repair missing captured information.

At 5.65 times speed, the nominal source frame rate becomes 45.2 fps. The 50 fps
output accommodates every source frame. FFmpeg's filter statistics report:

```text
902 frames in, 1000 frames out; 0 frames dropped, 98 frames duplicated.
```

Resampling repeats existing source images to meet the 50 fps grid. It does not
interpolate motion or create new visual content. Output timestamps are uniformly
spaced by 0.020 seconds. The last encoded frame is presented at 19.980 seconds
and held through the 20.000-second media endpoint.

## Verification

- Fully decoded the completed MP4 without decoder errors.
- Read source and output stream metadata and every decoded frame timestamp.
- Confirmed a 20.000-second container and video stream, 1000 output frames, and
  first/last timestamps of 0.000 and 19.980 seconds.
- Inspected output first, middle, and final frames at 0.000, 10.000, and 19.980
  seconds. Matching source samples are 0.000, 56.500, and 112.875 seconds.
- Inspected a 40-frame contact sheet sampled every 0.5 output seconds. It shows
  the initial Preview Notice, submitted request, ongoing conversation and tools,
  streaming reply, and completed reply. No sampled frame shows colored test
  windows. The Preview Notice is a product notice, not a sandbox approval.
- Confirmed every old raw capture, prior preview MP4, and generated GIF retained
  its pre-export SHA-256. Ten prior files were checked. No existing file was
  overwritten, and no Agent or recorder was started.

The first/middle/final inspection PNGs and contact sheet are local verification
materials in `.tools/`; the reusable public provenance is
[finshield-full-video-provenance-v1.json](finshield-full-video-provenance-v1.json).

## Display scope

Suggested caption: "Complete captured recording, continuously accelerated
5.65 times to 20 seconds; no source time interval selected or removed."

This is the complete captured recording. It is not proof about activity outside
the captured screen rectangle or outside the recording period. Capture gaps
remain gaps. It does not turn a model's claim into visible effect evidence.

The left comparison video remains its existing 20-second joined excerpt. It
must be labeled as an excerpt and must not be called uncut. The two scenario
GIFs are unchanged and retain their separate excerpt-based timing recipes.
