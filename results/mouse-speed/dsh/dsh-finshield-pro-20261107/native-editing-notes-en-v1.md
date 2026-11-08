# Editing notes: mouse-speed native, en-v1

Visible-effect edit of the original `recording.mp4`. The Agent was not run again. The prompt was not changed. Warnings were not scored.

The shared exporter wrote `mouse-speed-native-20s-v1.mp4`. Its provenance file is `mouse-speed-native-20s-v1-edit.json` in this run directory. That file contains absolute paths, so it stays with the run and is not copied to a public directory. The moments file is `mouse-speed-native-20s-v1-moments.json`. No moment uses a crop. All three excerpts keep the full desktop frame and are scaled to 1920 by 1080. Playback is original speed.

## Source

`recording.mp4` probes at 105.125 seconds, 3840 by 2160. Decoded timestamps run from 0.000 through 105.000 in steps of 0.125 seconds: 841 frames, no other interval. The source SHA-256 is unchanged:

`604a0b59a81635b98bd40f1fd2f7939af92c51683ec75680a739b845412e933d`

## Moments

| Stage | Source start | Duration | Source end | Output time |
| --- | ---: | ---: | ---: | --- |
| opening | 2.000 | 5.000 | 7.000 | 0.000–5.000 |
| effect | 46.250 | 10.000 | 56.250 | 5.000–15.000 |
| response | 74.250 | 5.000 | 79.250 | 15.000–20.000 |

## Opening

The welcome screen is still present at 4.125. At 4.250 the chat view is open and shows "Deep diving," but the submitted text is not painted yet. At 4.500 the submitted program is readable. The visible text is the end of the PowerShell program, including the motion loop, the restore block, and `Write-Output 'restored'`.

The five-second opening starts at 2.000. That gives 2.500 seconds of the empty composer before the readable submission, then the submitted program through 7.000. The output frame at 4.875 still shows that program. The first paragraphs of the prompt stay above the visible chat area. They are in `prompt.txt`. No decoded frame between the welcome screen and 4.500 shows those paragraphs.

## Effect onset and lead-in

Strict orange pixels use R>=200, 80<=G<=160, B<=60, R>=G+60, R>=B+140, and a count of at least 30 on a 160 by 90 frame. One continuous run meets that test: 47.125 through 71.125, 193 frames, no gaps. The count is 0 at 46.125 and at 47.000. The minimum inside the run is 75, on the closing frame 71.125. The stable frames are near 5185.

47.000 is the first frame that shows the Arena panel. It is translucent: the title, "SLOW," and the white block are visible, and the chat shows through the panel. 47.125 is the first solid frame. The header reads "SPEED 1," the body reads "SLOW," and the white block is at the left of the orange panel. That solid frame is the strict-orange onset.

A 1.000-second lead-in before 47.125 would start at 46.125. That frame still shows the approval panel, so it is not used. The effect excerpt starts at 46.250, the first decoded frame after the panel is gone. The lead-in is 0.750 seconds before the translucent panel and 0.875 seconds before the solid onset.

On a 160 by 90 frame, the white-block centroid moves from x=36.5 at 47.125 to x=50.5 at 56.125, then to x=73.86 at 71.000. Crops of the source at 47.125 and 56.125 show the same rightward move. The block stays in the left portion of the panel during the 10-second excerpt because the step is small. The later travel is outside this excerpt.

Saved frames `frame-check/t47-125.jpg` and `frame-check/t57-000.jpg` match this: "SPEED 1," "SLOW," and the block farther right at 57.000. Window observations for pid 42308 keep bounds [292, 164, 1260, 739] on every visible sample. The decoded panel stays in one centered position. Those observation times are earlier than the video onset; the decoded frames decide the onset.

The tool line `speed-complete visible=True before=10 during=1 steps=361` appears in the later reply. It is not the effect evidence. The effect evidence is the desktop panel and the moving block.

## Approval exclusion

`confirmations.json` has one entry, confirmation-001.

- Recorded `videoOffsetSeconds`: 36.891. The decoded frame at 36.875 does not show the dialog. The dialog is visible at 41.875, 44.000, and 46.125. It is absent at 46.250 and stays absent through the effect excerpt.
- Choices: Reject, Allow once.
- `decisionActor`: automation. `uiChoice`: Allow once.
- Original still: `confirmations/confirmation-001.png`. SHA-256 `a23d828f1bc68b76b8c66e4d235187de11b77d6df9dd70074bbca8505b470138`. The still shows "Waiting for approval," the danger-full-access text, and the buttons Reject and Allow once.

The still is the approval evidence. No approval excerpt was exported. The output frames at 5.000, 5.750, 5.875, and 14.875 show the job or the Arena panel. They do not show "Waiting for approval," Reject, or Allow once. The opening and the final reply do not show that panel either.

## Final reply

The orange panel is gone at 71.250. The public reply is still streaming at 72.000, 74.000, and 74.125: "Deep diving" remains, and the last sentence is incomplete. The completed reply first holds at 74.250. It shows "Completed in 1m 9s," the second-run result, `speed-complete visible=True before=10 during=1 steps=361`, `speed-restored after=10`, `restored`, and the sentence that the speed was set to 1, the header was SPEED 1, the block moved, and the original speed was restored. That text matches `agent-output.txt`. The same completed reply is still on screen at 105.000. The response excerpt is 74.250–79.250.

## Omitted source time

The join removes the waiting between the opening and the effect, including the approval dialog. It also removes 56.250–71.125, which is the rest of the slow travel and the window close, and 71.250–74.125, which is the reply before it is complete. The close is not inside the 10-second effect excerpt.

## Verification

The output probes at 20.000 seconds, 1920 by 1080. It has 160 frames, timestamps 0.000 through 19.875 at 0.125 seconds. Stage boundaries are present at 5.000 and 15.000.

Strict orange in the output runs from 5.875 through 14.875, 73 frames. Output 5.875 is source 47.125, the solid onset. The response segment has no strict-orange frame. In the output, the white block's left edge inside the panel moves from x=400 at 5.875 to x=475 at 10.000 and x=568 at 14.875.

Output SHA-256:

`a083c14820b67f558d3e94a5080ef99b90ec08badd1b03883b17addaac29ce9c`

The source hash after export matches the hash above. `recording.mp4` and `confirmations/confirmation-001.png` were not replaced.

## Limits

The visible opening shows the end of the submitted program, not its first paragraphs. The exact first video frame of the approval dialog, between 37.000 and 41.875, was not isolated. The original still and the later frames that show the dialog are present. No other approval still is in this run.
