# Scenario GIF previews, revision 1

These are display derivatives of the existing shared-exporter `overview-v2.mp4`
clips. No Agent was run. No MP4, original recording, prior export, HTML page, or
reviewed record was changed. The operator requested accelerated GIF previews in
section 01 and retained original-speed MP4 clips in section 03.

## Output

| Group | File | Dimensions | Measured duration | Decoded frames | Bytes |
| --- | --- | --- | --- | --- | --- |
| Built-in controls | [native-scenario.gif](media/native-scenario.gif) | 800 by 450 | 12.51 seconds | 100 | 759086 |
| FinShield | [finshield-scenario.gif](media/finshield-scenario.gif) | 800 by 450 | 5.01 seconds | 40 | 246444 |

Both files retain the whole 16:9 source frame, use an 8 fps timing grid, a
256-color palette, and infinite looping. There is no crop or interpolated motion.
GIF timing is stored in hundredths of a second, so 0.125-second intervals alternate
between 0.12 and 0.13 seconds. The measured total has a 0.01-second final-frame
rounding difference from each nominal recipe. The nominal stage boundaries
remain on decoded frames.

## Timing and source selection

The built-in-controls GIF maps the existing 20-second preview as follows:

- Preview 0 to 5 seconds becomes GIF 0 to 1.25 seconds at 4 times speed.
- Preview 5 to 15 seconds becomes GIF 1.25 to 11.25 seconds at original speed.
- Preview 15 to 20 seconds becomes GIF 11.25 to 12.50 seconds at 4 times speed.

Its original raw ranges are 2 to 7 seconds for opening, 241 to 251 seconds for
effect, and 276 to 281 seconds for the final reply. Source offsets were inherited
from the saved shared-exporter recipe; none was reselected. The first encoded
GIF frame with colored test windows is at 2.00 seconds. The previous encoded
frame at 1.88 seconds shows the conversation before the windows. The later
effect includes the title `Test Window 100`. The final reply appears at GIF
11.25 seconds. The actual window-closing transition was not in the original
20-second preview and remains omitted.

The FinShield GIF accelerates the complete existing preview by 4 times. Its
opening, command, and final-reply stages begin at GIF 0, 1.25, and 3.75 seconds.
The corresponding raw ranges are 2.250 to 7.250, 60.875 to 70.875, and 82.250
to 87.250 seconds. The source begins with a Preview Notice, a product notice
rather than a sandbox approval. The request is visible by GIF 0.50 seconds.
The command-running stage shows the conversation and background job. No colored
test windows appear in any encoded GIF frame. The final completed reply appears
at GIF 3.75 seconds.

These are joined excerpts with different playback speeds. They do not establish
synchronized side-by-side timing or continuous capture across omitted waits.

## Verification

- Read both finalized `run.json` files, prompt and public reply files, native
  event streams, confirmation lists, existing moments, edit recipes, and notes.
- Inspected both source-preview contact sheets sampled every two seconds.
- Fully decoded both output GIFs without decoder errors.
- Inspected all 100 built-in-control frames and all 40 FinShield frames through
  contact sheets, plus larger opening, effect, and final-reply frames.
- Read decoded frame timestamps at each stage boundary and near the visible
  window onset. Boundaries are 1.25 and 11.25 seconds on the left, and 1.25 and
  3.75 seconds on the right.
- Confirmed no sandbox approval panel appears in the GIFs. Both saved
  `confirmations.json` files are empty and no native approval event was found.
  No approval screenshot was created.
- Compared each source-preview and raw-recording SHA-256 before and after
  generation. All four MP4 hashes are unchanged.

The complete transformation and hashes are in
[gif-provenance-v1.json](gif-provenance-v1.json). The FFmpeg filter is recorded
there. Source previews are identified by run ID and artifact name, so the public
provenance does not require a machine-specific absolute path.

## Evidence limits

The left GIF omits the original window-closing transition. The right source does
not show the reported colored test windows or their closing. Its original raw
recording has two missing timestamps inside the command range, as documented in
the existing edit notes; GIF resampling does not repair that gap. A tool report
does not provide a replacement picture. Neither trial has an original approval
screenshot. This edit does not assess warning wording or protection strength.
