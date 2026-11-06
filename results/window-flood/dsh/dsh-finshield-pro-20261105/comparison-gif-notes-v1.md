# Combined scenario GIF, revision 1

[comparison-scenario-v1.gif](media/comparison-scenario-v1.gif) is one real
side-by-side GIF. It combines the existing accelerated scenario GIFs without
rerunning either Agent, changing either source, or changing the MP4 videos.

| Property | Value |
| --- | --- |
| Dimensions | 1600 by 450 pixels |
| Left pane | Entire 800 by 450 built-in-control GIF |
| Right pane | Entire 800 by 450 FinShield GIF |
| Duration | 12.51 seconds |
| Decoded frames | 100 |
| Bytes | 928866 |
| Loop | Complete combined GIF repeats |
| Cropping or overlays | None |

## Pane timing

The left pane retains all 100 source GIF frame timestamps exactly. Its opening
and reply stages are accelerated 4 times, while the middle 10-second effect
stage stays at original speed. These are the existing selected excerpts.

The right pane plays its existing 40-frame, 5.01-second GIF once per combined
cycle. Its source is accelerated 4 times throughout. The final source frame
starts at 4.88 seconds and normally ends at 5.01 seconds. The combined GIF holds
that same final image from 5.01 through 12.51 seconds, an additional 7.50 seconds.
The right pane does not restart independently while the left pane is playing.
Both panes restart only when the complete combined GIF loops.

This is a presentation of two separately recorded and edited sequences. It is
not synchronized trial timing and is not an uncut recording. The right final
image hold represents no additional recorded activity.

## Transformation

FFmpeg decoded each source GIF once with its embedded loop ignored, stacked
the full frames horizontally, and repeated the shorter input's final frame.
The combined image uses a regenerated 256-color palette and Bayer dithering.
There is no crop, title overlay, interpolated motion, or further speed change.
The full filter and hashes are stored in
[comparison-gif-provenance-v1.json](comparison-gif-provenance-v1.json).

## Verification

- Fully decoded the combined output without errors.
- Verified its 1600 by 450 dimensions, 12.51-second duration, and 100 frames.
- Compared all decoded output timestamps with the left source GIF timestamps;
  they are identical, including the final frame at 12.38 seconds.
- Decoded the right output pane to RGB frame hashes. Every pane image from
  frame 39, at 4.88 seconds, through the final output frame has the same hash.
  This verifies the final-image hold rather than an independent GIF restart.
- Inspected a contact sheet of every fourth frame and a full-size frame at
  7.50 seconds. The left shows the existing colored test windows while the right
  shows its completed reply. The right pane has no added effect image.
- Verified all eleven existing MP4, raw-capture, and separate-GIF hashes remain
  unchanged. No HTML, reviewed record, startup command, or service was changed.

Coordinator inspection files are local, under `.tools/`:
`comparison-scenario-frame60-v1.png` and `comparison-scenario-contact-v1.jpg`.

The original excerpt evidence limits remain: the left closing transition is
omitted; the right source GIF has no visible colored test windows; neither
source has an original sandbox approval screenshot. This edit makes no warning
or protection assessment.
