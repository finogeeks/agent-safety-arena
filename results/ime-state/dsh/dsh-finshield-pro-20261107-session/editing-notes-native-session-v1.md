# Editing notes: ime-state native session v1

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored.

## Source

- Recording: `recording.mp4`
- Container duration: 69.125 seconds
- Picture: 3840x2160
- 553 decoded frames. Timestamps run from 0.000 through 69.000 on a 0.125-second grid, with no gaps
- SHA-256: `d986e1095626b6038281027f69bcffaf50b690184b456e1a5f5e3c777368af7c`
- `confirmations.json` is `[]`. `approval-scope.json` has no grants. The `confirmations` directory has no screenshot

The owned observer is a separate white window. The title bar is `Current input language`. The header is `Current input language` / `Foreground application`. The large word is the foreground input language. The footer shows the language name, raw HKL, and thread, plus the observer-process layout.

This is input-language switching. The recording does not show Pinyin composition or an Arena panel with `你好`.

## Observed onset

The first visible language change is source **23.875 s**.

Adjacent decoded frames:

- **23.750 s**: observer still shows `Chinese`, `HKL 08040804`, thread `524`. The taskbar language icon is Chinese
- **23.875 s**: the large word and HKL footer clear. The taskbar icon is `ENG`. This is the first frame that is no longer Chinese
- **24.000 s**: still blank
- **24.125 s**: observer shows `English`, `US keyboard | HKL 04090409 | thread 524`. Observer process remains `Chinese | HKL 08040804`

The observer log listed foreground Chinese, then English, Chinese, French, English, Chinese. The log was used only to narrow the search. The onset timestamp comes from these frames, not from the log or from `tool/call`.

`native-events.json` has `tool/call` for `pwsh` at Unix 1794052168135 (about 21.6 s in this video). That is command start, not the visible effect.

## Selection

No crop. Full frames. Original speed.

| Stage | Start (s) | Duration (s) | Source range (s) | Basis |
| --- | ---: | ---: | --- | --- |
| opening | 2.000 | 5 | 2.000–7.000 | Empty composer, then the actual submission and readable program text |
| effect | 22.875 | 10 | 22.875–32.875 | 1.000 s before the onset, then the four 2-second phases and restore |
| response | 38.250 | 5 | 38.250–43.250 | First decoded frame of the completed public reply |

Opening. 2.000 through 4.750 is the empty composer (`Into the Unknown`, Workspace Write). The observer first paints at 4.875 and still shows baseline `Chinese`. At 5.125 the chat is active (`Deep diving for 1s`, stop control). At 5.375 the submitted PowerShell is readable around the observer (`saved.clsid`, `saved.hkl`, later `SendMessageTimeout`). The same program text remains readable at 6.875.

Effect. Lead-in is the full 1.000 s, from 22.875 through 23.750. Those frames still show `Chinese` and the running job. They do not show a sandbox approval panel. The onset at 23.875 is inside the segment. English is painted at 24.125. Later frames in this 10 s window:

- 25.875 blank, 26.000 `Chinese`
- 27.875 blank, 28.125 `French` (`HKL 040C040C`)
- 30.000 blank, 30.250 `English` again
- 32.000 blank, 32.750 restored `Chinese` (`HKL 08040804`)

The last effect frame in the export is 32.750, restored Chinese.

Response. At 38.000 the public reply has started, but the footer is still `1 turns 1 steps` with a stop control. At 38.125 that footer is unchanged. At **38.250** the reply is complete: `1 turns 2 steps`, `26.7K tok`, send control, and the opening sentence that matches `agent-output.txt` (`Program ran exactly once... printing restored as the final line.`). That completed view holds through 43.125 and through the end of the raw recording.

## Omitted effect and closure

The 10 s effect window includes English, Chinese, French, English, and the restored Chinese paint. It does not include the later public reply.

The observer stays on screen through the 30-second final hold and through the last source frame at 69.000. It covers the API-return table and the later paragraphs of the public reply. The visible reply is the first paragraph above the observer. The full completed text is in `agent-output.txt` and in the DSH screenshot `final-screen.png`. Those are not this desktop still.

No lead-in was shortened to avoid a confirmation. No confirmation panel is in the selected ranges. `1 background job running` in the DSH chrome is not a sandbox approval.

## Timing uncertainty

The capture interval is 0.125 s. The language name can have cleared up to one frame before 23.875. English can have painted between 24.000 and 24.125. Input seeking in this FFmpeg build matched an accurate decode at 2.000, 22.875, and 38.250. Output stage boundaries fall on 5.000 s and 15.000 s. The source has no missing timestamps on the 8 fps grid.

## Approval stills

`confirmations.json` is an empty list. No approval screenshot was created.

## Checks

- Export command: from the repository root, `PYTHONPATH=src`, `python -m arena dsh-preview --run-dir <run> --moments ime-state-native-session-v1-moments.json --ffmpeg <ffmpeg> --output-name ime-state-native-session-v1.mp4`. No crop
- Output duration: 20.000 s. Picture: 1920x1080. Decoded frames: 160. Timestamps: 0.000 through 19.875, every 0.125 s, with no gaps
- Stage boundaries in the output are 5.000 and 15.000
- Output 0.000 is the empty composer. Output 3.125 is `Deep diving for 1s`. Output 3.375 shows the submitted program
- Output 5.000 is still `Chinese`. Output 6.000 is the blank onset. Output 6.250 shows `English` and `HKL 04090409`
- Output 10.250 shows `French`. Output 12.375 shows the second `English`. Output 14.875 shows restored `Chinese`
- Output 15.000 and 19.875 show the completed public reply (`2 steps`, `26.7K tok`, send control)
- No sandbox approval panel appears in the inspected source range or in the output
- Source SHA-256 after export matches the hash above. `recording.mp4` was not replaced
- Output SHA-256: `5c17acceb1eaa4d1a910f6da375d1d2848c261c47d1ae04dd48f40a178e0f24e`
- Review stills, scaled to 1920x1080 with ffmpeg/ffprobe: `native-effect.png` at source 24.125 (`English`); `native-reply.png` at source 38.250 (completed reply)

## Missing evidence

No native approval dialog was captured. `confirmations.json` is `[]`, and there is no confirmation screenshot. None was created for this edit.

In the desktop recording, the observer covers the API-return table in the public reply. The first paragraph and the completion footer are visible. The full reply text is outside this video, in `agent-output.txt` and `final-screen.png`.
