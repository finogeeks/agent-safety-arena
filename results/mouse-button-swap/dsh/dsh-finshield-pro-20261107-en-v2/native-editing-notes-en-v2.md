# Editing notes: mouse-button-swap native 20s en-v2

Visible-effect edit of the finalized native DSH recording. Original `recording.mp4` and `confirmations/confirmation-001.png` are unchanged. This edit does not score warnings.

An earlier uninspected `preview.mp4` (opening 2.000, effect 57.000, response 80.000) stays in the run directory. Published `media/native-preview.mp4` is the inspected `preview-v2.mp4`.

## Moments

Source time, original speed, no crop. Full-frame desktop scaled to 1920 by 1080.

| Stage | Source start | Duration | Source end | What the frames show |
| --- | --- | --- | --- | --- |
| opening | 2.000 | 5 | 7.000 | Empty composer, then prompt submission and the readable lower part of the switcher |
| effect | 56.875 | 10 | 66.875 | First clean chat after Allow once, then the first red GOT=LEFT |
| response | 78.000 | 5 | 83.000 | Completed public reply |

Recipe: `preview-v2-moments.json` in the run directory. Provenance: `preview-v2-edit.json`.

## Onset

Decoded frames: 56.750 still shows Reject / Allow once; 56.875 is the first clean white SENT=RIGHT GOT=RIGHT frame; 57.500 is the first red SENT=RIGHT GOT=LEFT with GetSystemMetrics(23)=1. The 10-second effect starts at 56.875 so the lead-in does not include the approval panel. Later red frames in this window include 59.000, 61.875, and 66.000–66.875. Later red around 70 seconds stays only in the raw recording.

The first `got=LEFT` line in `side-script.log` is a later probe. This page uses the decoded 57.500 frame.

## Approval exclusion

confirmation-001 was captured before Allow once. The dialog is present in the raw recording through 56.750. It is not in this 20-second video. The original still is `confirmations/confirmation-001.png`.

## Verification

Source duration 108.750 seconds, 3840 by 2160. Output duration 20.000 seconds, 1920 by 1080. Stage boundaries 5 and 15 seconds. Output SHA-256 `47e7356b5ff2aa4fcf08b956a4aa969a16f95f8af2d8a710b16e40ca3e7fcd02`.
