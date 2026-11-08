# Editing notes: wheel-scroll native, en-v1

Run: `dsh-20261106T191913-2dc6a08d`. Output: `wheel-scroll-native-20s-v1.mp4`.
This edit uses the raw recording only. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

## Selection

Source frames are 0.125 seconds apart from 0.000 through 100.875. The container duration is 101.000 seconds. Offsets below are decoded frame times.

| Stage | Source start | Duration | What the frames show |
| --- | --- | --- | --- |
| opening | 2.000 | 5 | Ready composer, then the submitted program |
| effect | 42.750 | 10 | Clean chat, then the orange Arena panel |
| response | 70.375 | 5 | Completed public reply |

Opening: at 4.000 the composer is still empty. At 4.250 the chat is active ("Deep diving for 1s"). At 4.375 the submitted PowerShell program is readable. The 5-second opening starts 2.250 seconds before that chat and keeps the program text on screen through 7.000.

Effect onset: strict orange (`R>=200`, `80<=G<=160`, `B<=60`, `R>=G+60`, `R>=B+140`) is absent at 43.500 (4 sampled pixels at 480×270) and fills the Arena panel at 43.625 (44,700 pixels). It stays continuous through 67.750 and is gone at 67.875. The first orange frame shows the window titled Arena panel, header `WHEEL 20`, and rows starting near `ROW 22`. No approval dialog is in that frame. This is the window from the run after approval. The earlier sandboxed call had already failed in the chat.

Lead-in: 0.875 seconds, from 42.750 to 43.625. A 1.000-second lead-in would start at 42.625. That frame still shows the native approval panel (`Waiting for approval`, `Reject`, `Allow once`). The next frame, 42.750, is the first frame without that panel. The effect therefore starts there.

Inside this 10 seconds the rows jump at least once: `ROW 22` at 43.625 and 44.000, `ROW 03` at 46.000, and `ROW 22` again at 52.625. Playback stays at original speed.

Response: at 70.000 the reply is still streaming and does not yet show `after=3`. At 70.375 the completed reply is on screen, including `before=3`, `during=20`, `steps=16`, and `after=3`, and it is still there at 75.250.

## Omitted effect

The orange window continues from 52.750 through 67.750. Those later jumps stay in `recording.mp4`. Checked samples outside the excerpt: rows near `ROW 03` at 55.000 and near `ROW 22` at 66.000. The window is closed by 67.875. The first painted frame is already near `ROW 22`; a separate `ROW 01` frame was not found.

## Approval still

`confirmations.json` has one dialog, `confirmation-001`. The original screenshot is `confirmations/confirmation-001.png`. Its text is the pending native approval, with choices `Reject` and `Allow once`. `videoOffsetSeconds` is 33.266. The recorded choice is `allowed-once`, actor `automation`, UI label `Allow once`. That dialog is not in the edited video.

## Checks

- Exporter provenance keeps source SHA-256 `cbf69f346ba57be720fd1a0dab51582bc48a8ef3574c23cba453915441a6ab7c`. A later hash of `recording.mp4` matches. The output hash matches the provenance.
- Output duration is 20.000 seconds, 1920×1080, 160 frames at 8 fps. Decoded timestamps are 0.000 through 19.875. Stage boundaries are frame 40 at 5.000 and frame 120 at 15.000.
- In the output, strict orange begins at 5.875 (source 43.625) and continues through 14.875. It is absent in the opening and in the response.
- Output frame at 5.000 (source 42.750) has no approval panel. Output frame at 5.875 shows `WHEEL 20` and `ROW 22`. Output frame at 8.250 shows `ROW 03`. Output frames at 15.000 and 19.875 show the completed reply with `before=3`, `during=20`, `steps=16`, and `after=3`.
- No crop was applied. Effect frames keep the full desktop.

## Gaps

No source gap blocks this edit. The approval screenshot, the onset, the row jump, and the completed reply are in the recording. The part of the jump sequence after 52.750 is omitted because the effect excerpt is 10 seconds, not because those frames are missing.
