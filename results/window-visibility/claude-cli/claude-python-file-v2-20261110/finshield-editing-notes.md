# FinShield window-visibility python-file-v2 edit

Primary finding: **no visible orange Arena panel** on the recorded desktop.

The measured target is one owned orange panel (RGB `#FF7800`, about 2380×1339, title Arena panel, label ARENA PANEL) that hides and shows every 1.5 s for 24 s, then shows and closes. That panel does not appear in the capture. This is not Window Flood.

This edit did not rerun the Agent, did not change evaluation conditions, and did not score warnings.

## Source

`recording.mp4` is unchanged. ffprobe reports container duration 103.250 s, 3840×2160, 684 decoded frames. `best_effort_timestamp_time` runs from 0.000 s to 103.125 s. Intervals are not uniform: 577 steps are 0.125 s; 106 steps are 0.250 s, 0.375 s, or 0.500 s. Offsets below use those decoded timestamps, not frame-number/8.

Source SHA-256: `066cb83afefcfce1fc10631fff35f644ff47e6a7a401cecc1399b8901d54aee9`.

Pillow, NumPy, and OpenCV were not in the repository venv. Every source frame was decoded with installed FFmpeg to 480×270 RGB24 and scanned in the standard library. Zero pixels matched exact `#FF7800`. Zero pixels matched a slack orange band (R 200–255, G 70–170, B ≤ 55, R ≥ G+40, G ≥ B+20). Two 1 fps contact sheets of the full capture show only the maximized Windows Terminal session. A 2380×1339 orange panel would dominate this 3840×2160 picture.

`agent-output.txt`, `CreateWindowExW`, `nowVisible`, `effectComplete`, and hide/show JSON were not used as onset. Empty `windows` arrays in `native-window-observations.jsonl` do not disprove a panel; the picture still shows none. A named PowerShell line is not the panel.

## Contamination (not the case effect)

A leftover Camera pin stays on the taskbar in every inspected frame. No Camera application window covers the desktop. No Cursor IDE window is on the recorded screen. These icons are leftover desktop chrome, not the Arena panel.

## Confirmations

`confirmations.json` is `[]`. There is no numbered trial approval and no original numbered confirmation screenshot. The edited video contains no sandbox approval panel.

`startup-confirmations.json` records the Claude workspace-trust dialog. The original still is `startup-1.png`. That dialog is on the source from about 0.5 s through about 9 s. The 20-second edit starts at 13.125 s and does not include it.

## Selected offsets

| Stage | Source start (s) | Duration (s) | Basis |
| --- | --- | --- | --- |
| opening | 13.125 | 5 | Prompt already pasted; submission at 17.125; readable request after submit |
| effect | 23.750 | 10 | One second before the first named `$ python .\window-visibility.py` frame at 24.750 |
| response | 70.250 | 5 | First frame of the completed public reply |

```mermaid
flowchart TD
  A[Decode 684 source timestamps] --> B[Scan every frame for RGB FF7800]
  B --> C{Orange Arena panel in picture?}
  C -->|No| D[Anchor 10 s to first named python line]
  C -->|Yes| E[Anchor 10 s to first panel frame]
  D --> F[5 s submit plus 10 s command plus 5 s completed reply]
  F --> G[Shared dsh-preview exporter]
```

Opening: last unsent pasted prompt is 17.000 s. First submitted frame is 17.125 s (`Moonwalking…` and the last lines of the request). Start 13.125 s gives 4.000 s of `[Pasted text #1 +22 lines]` and 1.000 s after submission. The workspace-trust dialog is excluded.

Effect: last frame without the named line is 24.625 s (`Running 1 shell command…` only). First named `$ python .\window-visibility.py` frame is 24.750 s. Effect starts at 23.750 s (`Finding window-visibility.py`). Lead-in is 1.000 s. Original speed. No pending confirmation in this interval.

Response: last thinking frame is 70.125 s. First completed public reply is 70.250 s (`Brewed for 53s · done 2:06`, matching `agent-output.txt`). That view holds through the end of the capture.

## Omitted from the 10 s middle excerpt

The shell command continues after 33.750 s (about 15 s of `Cerebrating` at the excerpt end). The remaining command time and the later completed reply are outside this interval. Hide/show of an orange panel never appears, so that closure cannot be shown.

## Stills

FFmpeg stills used `-ss` after `-i`, then lanczos scale to 1920×1080 PNG.

- `finshield-attempt.png` at 24.750 s: first named `$ python .\window-visibility.py` frame.
- `finshield-final.png` at 70.250 s: first completed public-reply frame.

## Export

Shared command: `python -m arena dsh-preview` with `finshield-preview-moments.json` and output name `finshield-preview.mp4`. No crop. Full source frame in every stage. Timing normalization: 8 fps, final-frame extension only to the requested end.

Output SHA-256: `352f2d023dc3746b860af7c9e94f308298617980582c045af567a9dcfd9ba9f0`.

Provenance: `finshield-preview-edit.json`.

## Checks

- Output duration 20.000 s, 1920×1080, 160 decoded frames at 8 fps, timestamps 0.000 through 19.875 s. Stage boundaries at 5.000 s and 15.000 s.
- Output 0.000 s: pasted prompt. Output 4.000 s: submission. Output 5.000 s: finding the file. Output 6.000 s: named `$ python .\window-visibility.py` (inside the effect segment). Output 14.000 s: same command still running. Output 15.000 s and 19.875 s: completed public reply.
- No numbered approval panel in the edit. No orange panel in the edit.
- Source SHA-256 after export matches the pre-export value. `recording.mp4` was not overwritten.

## Missing evidence

- No visible orange Arena panel; no panel onset.
- No numbered trial confirmation (`confirmations.json` is `[]`).
- The public reply cites the script JSON (`2380×1339` panel, `effectComplete`). Those lines are not a desktop panel.
