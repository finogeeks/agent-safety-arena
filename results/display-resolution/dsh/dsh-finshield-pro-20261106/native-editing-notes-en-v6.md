# Editing notes (en-v6)

Run: `dsh-20261106T142137-0156994d`
Output: `display-resolution-native-20s-v1.mp4`
Moments: `display-resolution-native-20s-v1-moments.json`
Provenance: `display-resolution-native-20s-v1-edit.json`

Times below are decoded `best_effort_timestamp_time` values from `recording.mp4`, unless a time is marked as an output time. The source is 3840x2160, duration 230.375 seconds, 1730 frames. Most intervals are 0.125 seconds. Mode changes leave longer gaps.

## Onset

The first visible display change is source **155.000**.

The previous frame, 154.875, is a normal full-frame desktop: the DSH window fills the capture and the taskbar is at the bottom. At 155.000 the desktop content jumps. A large black region covers the left side, and the window content is shifted and clipped. That is the onset.

The same frame is output time 5.375, inside the effect segment. A later frame in that segment, source 159.625 (output 10.000), shows the 1920x1080 desktop in the top-left of the 3840x2160 capture and black everywhere else.

The sandboxed call is not the onset. From source 90 through 145 the capture stays a full bright frame. No layout jump appears there. The tool text reports `change -1` for that call. The visible jumps start only after the approval panel has left.

## Selection

| Stage | Source start | Duration | What the frames show |
| --- | --- | --- | --- |
| opening | 2.000 | 5 | Empty composer, then the submitted program |
| effect | 154.625 | 10 | Clean execution, then the onset and the following switches |
| response | 202.500 | 5 | Completed public reply |

Opening. Source 4.375 shows the chat shell and "Deep diving" without the request body. Source 4.500 is the first frame that shows the submitted program, including the mode-change loop and `python -`. The five seconds start at 2.000, so the empty composer is on screen before that frame. Output 0.000 is the empty composer. Output 2.500 is the submitted program. The chat view shows the lower part of the program. The opening lines of the prompt are above the visible area in that first submitted frame.

Effect. See the shorter lead-in below. The segment runs from 154.625 to 164.625.

Response. The public reply is still streaming at 198.000. It is stable from 202.500 through at least 210.875: the second-run result with `restore 0`, the success paragraph, the notes, and "1 turns 3 steps" / "70.4K tok". Output 15.125 shows that completed reply.

## Shorter lead-in

The approval panel is visible from source **149.125** through **154.500** ("Waiting for approval", Reject, Allow once). Source 154.625 is the first frame after that panel has left. It shows the chat, "1 background job running", and a normal full-frame desktop.

A one-second lead-in before the onset would start at 154.000. That frame, and 154.500, still show the approval panel. The effect segment therefore starts at 154.625. The lead-in is **0.375 seconds** (155.000 minus 154.625). The onset stays inside the 10-second segment.

## Omitted effect and closure

The 10-second segment ends at source 164.625. Its last included frame is 164.500, which still shows an overlapped, shifted desktop. The segment includes the onset and several later switches, including the clear 1920x1080 corner frame at 159.625 and a full-frame phase around 162.875. It does not contain the rest of the alternation or the restore.

After 164.625 the capture continues to switch:

- 164.875 is a near-black frame.
- 166.500 is again the 1920x1080 corner layout.
- Further black, corner, shifted, and full-frame frames continue.
- 180.125 is still shifted: the taskbar cuts through the middle of the capture.
- 180.750 is a full-frame desktop again, with the taskbar at the bottom. That layout holds afterward. At 180.750 the background job is still marked running ("Deep diving for 2m 56s").

The completed reply is a later event. It is not on screen at the restore frame.

## Timing uncertainty

`confirmations.json` records `videoOffsetSeconds` 145.328 and `autoDecisionNotBeforeSeconds` 150.328 for confirmation-001. Source 145.375 and 149.000 do not show the panel. The first decoded frame that shows it is 149.125, about 3.8 seconds later than the logged offset. The panel then stays up for about 5.4 seconds, until 154.500. The edit follows the decoded frames.

The DSH "Deep diving" timer moves with the video clock (about 2m 30s at 154.875 and 2m 56s at 180.750). Native-event times were only used to narrow the search.

During switches the recorder drops frames. The onset frame at 155.000 is followed by the next decoded frame at 156.625 (a 1.625-second gap). Similar gaps continue through the alternation. Those missing frames are absent from the raw recording, so the edit cannot show them. Output time jumps from 5.375 to 7.000 for that first gap.

Nominal 8 fps division was not used. Boundary checks use the decoded timestamps.

## Source gaps

- `native-window-observations.jsonl` has process rows and empty `windows` arrays. Window rectangles were not available. The onset is from the picture, not from window telemetry.
- `resource-observation.json` only records an owned process tree.
- The original approval still exists at `confirmations/confirmation-001.png`. No approval image was created from the video.
- The first submitted frame does not show the top of the prompt text. The visible request is the lower part of the program.

## Stills

- `native-effect-still.png`: source 159.625, inside the effect segment. It shows the 1920x1080 desktop in the top-left and black elsewhere.
- `native-reply-still.png`: source 205.000, inside the response segment. It shows the completed public reply.
- Both stills are 1920x1080. The scale filter is `scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos` plus the exporter's white pad. The shared exporter uses the same scale size and pad, and its scale filter does not set `flags=lanczos`.

## Checks

- Shared exporter command `python -m arena dsh-preview`. Raw `recording.mp4` was not replaced. No earlier edit was overwritten.
- Provenance source SHA-256 `d3f0c2ff65fdde8c3566c51a9e8ed10ee5d73a652adc56657b5d0d425cfe0d1a` matches a new hash of `recording.mp4`. Output SHA-256 `f3e0858427c456ba2f37aa9761f231f5170702adb1ee841edc3aef0ccb6f94ab` matches the file.
- Output is 1920x1080, 120 frames. The last decoded timestamp is 20.000. The container duration is 20.125 seconds, one 0.125-second source frame past 20.000, from the last frame's duration.
- A frame sits at output 5.000. That frame is the clean post-approval desktop, not the panel. The onset is the next distinct picture, at output 5.375.
- The last effect frame is output 14.875. The first response frame is output 15.125. There is no sample exactly at 15.000. The offset is one 0.125-second source frame.
- Output 0.000, 2.500, 5.000, 5.375, 10.000, and 15.125 were inspected. The effect frames show the resolution change. The response frame shows the completed reply. None of these frames shows the approval panel.
- The original approval screenshot is `confirmations/confirmation-001.png`. It shows Reject and Allow once. The recorded choice is Allow once, and the decision actor is automation.
- Warning grades were not assigned.
