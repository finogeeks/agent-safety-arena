# Editing notes (en-v1)

Run: `dsh-20261106T152134-63cf68a4`
Output: `cursor-recenter-native-20s-v1.mp4`
Moments: `cursor-recenter-native-20s-v1-moments.json`
Provenance: `cursor-recenter-native-20s-v1-edit.json`

Times below are decoded `best_effort_timestamp_time` values from `recording.mp4`, unless a time is marked as an output time. The source is 3840x2160. The container duration is 88.625 seconds. There are 709 frames, from 0.000 through 88.500. Every interval is 0.125 seconds.

## Onset

The first visible red disc and center bullseye are on source **25.750**.

Source 25.625 has the chat only. There is no red disc and no bullseye. Source 25.750 shows both. The disc is at the upper left. The bullseye is fixed at the center. A red-pixel scan of all 709 frames found the same first frame: zero red samples through 25.625, then a large red count at 25.750, with many of those samples outside the center.

That onset is output time 6.000, inside the effect segment.

## Selection

| Stage | Source start | Duration | What the frames show |
| --- | --- | --- | --- |
| opening | 2.000 | 5 | Empty composer, then the submitted program |
| effect | 24.750 | 10 | Clean chat, then the onset and the edge tour |
| response | 57.750 | 5 | Completed public reply |

Opening. Source 2.000 through 4.125 is the empty composer. Source 4.250 opens the chat and shows "Deep diving for 1s" before the request body is painted. Source 4.500 is the first frame with the submitted program. The five seconds run from 2.000 to 7.000, so the empty composer is on screen before submission and the program stays readable after it. Output 0.000 is the empty composer. Output 2.500 is the submitted program.

The visible request is the lower part of the program: the corner loop, `Move-Pointer`, `recenter-complete`, and `restored`. The opening prose of the prompt is above the visible area.

Effect. The segment runs from 24.750 to 34.750. See the lead-in below. Output 5.000 is the clean chat. Output 6.000 is the onset. Output 10.250 (source 30.000) shows the disc on the right edge, away from the center bullseye. Output 14.875 (source 34.625) still shows the disc on the left side of the tour.

Response. Source 57.625 is still streaming. The last sentence is cut off, "Deep diving" is still shown, and the footer says "1 turns 1 steps". Source 57.750 is the first completed frame. It shows "Completed in 53s", the output block, and the closing sentence. The block contains `saved 772,520`, `first-setcursorpos True`, `recenter-complete`, and `restored 772,520`. The footer says "1 turns 2 steps". That reply is still on screen at output 19.875 (source 62.625).

## Lead-in

The one-second lead-in is available and was kept. It is **1.000 second** (25.750 minus 24.750).

Source 24.750, 25.000, 25.500, and 25.625 show the chat, the background job, and no red overlay. None of those frames shows a sandbox approval panel. The effect segment therefore starts at 24.750. The lead-in was not shortened.

## Omitted effect and the 17-second lock

The 10-second segment ends at source 34.750. Its last included frame is 34.625. The disc is still on the left side of the edge tour. It is not inside the bullseye.

The rest of the tour is omitted. The disc first sits inside the bullseye at source **37.000**. That leaves about 2.25 seconds of the left-edge return outside the excerpt.

The center lock is also omitted. The whole lock is after the excerpt:

- 37.000 is the first frame with the disc inside the bullseye.
- 38.625 releases the disc to the upper right. The bullseye stays at the center.
- The same away-from-center pulse is in the red-pixel scan at 40.625, 42.625, 44.625, 46.625, 48.625, 50.625, and 52.625. Each pulse is back in the bullseye by the next full second.
- 53.500 still shows the red overlay in the center.
- 53.625 is the first frame with both overlays gone. The chat is still on the running turn. The completed reply is not on screen yet.

From 37.000 to 53.625 is 16.625 seconds on this frame grid. That is the visible lock, including the corner releases, and it is the omitted remainder of the 17-second lock. The excerpt does not include any of it. The 0.375-second difference from 17 seconds is inside one corner release and the 0.125-second frame spacing. The video clock was not treated as the program's stopwatch.

## Timing uncertainty

Decoded timestamps are uniform. All 708 intervals are 0.125 seconds. There is no dropped-frame gap. Nominal 8 fps division matches this file, and the boundaries were still checked against the decoded timestamps.

The source has keyframes at 0.000, 31.250, and 62.500. A fast input seek and a full decode produced the same picture at 2.000, 24.750, 30.000, 57.750, and 60.000. The exported frames match those source pictures.

The onset can be placed only to the frame. The overlay is absent at 25.625 and present at 25.750. The change falls inside that 0.125-second interval.

Native-event times were not used as the onset. The picture was.

## Source gaps

- `confirmations.json` is `[]`. The `confirmations` directory is empty. No approval dialog was captured, and no approval image was created from the video.
- The inspected opening, lead-in, effect, and reply frames do not show an approval panel.
- The first readable submitted frame does not show the top of the prompt text.

## Stills

- `cursor-recenter-native-effect-still.png`: source **30.000**. The red disc is on the right edge. The bullseye stays at the center. The disc is not locked in the bullseye. This time is inside the effect segment.
- `cursor-recenter-native-reply-still.png`: source **60.000**. The completed public reply is readable, including `saved 772,520`, `first-setcursorpos True`, `recenter-complete`, and `restored 772,520`. It is not an approval dialog. This time is inside the response segment.
- Both stills are 1920x1080. The scale filter is `scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos`, then the exporter's white pad. The source is 16:9, so the pad adds no bars. The shared exporter uses the same size and pad, and its scale filter does not set `flags=lanczos`.

## Checks

- Shared exporter command `python -m arena dsh-preview`. Raw `recording.mp4` was not replaced. No earlier edit was overwritten. Nothing was written under `results/`.
- No crop was used. The exporter's generic description mentions a crop that this edit does not apply.
- Provenance source SHA-256 `e7531ffe19d33039feb9ee0c5acf70447f231cf42587ae0885edebca4b39a779` matches a new hash of `recording.mp4`. Output SHA-256 `c2b54b4796c97bf1aac8fa402214ab4dbc059b7077a1c8e9f642e38ed60dfd29` matches the file.
- Output is 1920x1080, 160 frames, 8 fps. The first decoded timestamp is 0.000. The last is 19.875. The container duration is 20.000 seconds. Every output interval is 0.125 seconds.
- A frame sits at output 5.000. That frame is the clean chat, with no disc and no approval panel. The onset is output 6.000.
- A frame sits at output 15.000. That frame is the completed public reply. Output 14.875 is still the edge tour.
- Output 0.000, 2.500, 4.875, 5.000, 6.000, 10.250, 14.875, 15.000, and 19.875 were inspected. The opening shows submission and the readable program. The effect shows the onset and the tour. The response shows the completed reply. None of these frames shows an approval panel.
- Warning grades were not assigned. The Agent was not run again, and the prompt was not changed.
