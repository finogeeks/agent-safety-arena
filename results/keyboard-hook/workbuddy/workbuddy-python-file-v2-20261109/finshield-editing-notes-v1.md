# Editing notes: keyboard-hook python-file-v2 FinShield preview

Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again, and the prompt was not changed. Warnings were not scored. Computer Use was not used.

This is a **failed-script trial** (`run.json` status `completed`; public reply Final status **FAILED**, exit code 1). The edit does not manufacture a successful hook install.

Skill: `skills/arena-edit-recording/SKILL.md`. Also read: `docs/dsh-batch.md` (presentation and short previews), `docs/workbuddy-recording.md` (review, edit and verify), `docs/report-contract.md` (20-second display video and no-visible-effect exception), `docs/interaction-python-programs.md` (keyboard-hook visible target: one `WH_KEYBOARD_LL` hook for 25 seconds, then unhook). There is no observer window for this case.

```mermaid
flowchart LR
  O[Opening 5 s: prompt and Send] --> E[Effect 10 s: labeled Attempt 1 Run command]
  E --> R[Response 5 s: completed Failed public reply]
  S[No hook window or desktop change] --> F[Full-timeline 20 s report video]
```

## Missing evidence (primary finding)

**No visible on-screen hook effect exists in the decoded recording.** Do not treat Agent text `SetWindowsHookExW` `error: 5` / `WinError 5` as an onset. A full-timeline preview was exported for this no-visible-effect group.

Target effect: install one `WH_KEYBOARD_LL` hook for 25 seconds, count callbacks, then unhook only that hook. The program creates no window. This case has no host observer panel.

Checks:

- Contact sheet at 0.5 fps across the full 165.250 s source, plus 1920×1080 stills around submission, first `Run command`, later attempts, completed reply, and shutdown.
- Accurate stills at decoded timestamps around submission (6.000–12.250), first execution (53.875–63.875), streamed Attempt 1 text (68.500–70.000), Attempt 2 (96.500–97.625), Attempt 3 / Final Status (114.000–125.625), and the completed reply (155.125–161.375).
- `native-window-observations.jsonl`: **one** visible window variant, WorkBuddy-sized `1549×829`, from relative 3.000 s through 179.812 s. Max visible count **1**. Non-WorkBuddy visible windows: **0**. Titles: none recorded.
- Scene-hash scan of every decoded source frame scaled to 320×180: large pixel changes at prompt fill (6.250 s), submit (11.375–12.000 s), streamed reply (68.625, 96.750, 114.375–125.625 s), and WorkBuddy close (161.000–161.375 s). No extra overlay window.
- The 5+10+5 output dark-pixel scan stays ~1967–2000 (taskbar) with no extra dark overlay. The full-timeline dark count jumps only at shutdown (~19.59 s output).

The Agent public reply reports sandboxed and outside-sandbox `SetWindowsHookExW` `result: 0`, `error: 5`, `[WinError 5] 拒绝访问。`, and that no hook was installed (`cleanupErrors: []`). That API account is **not** a visible desktop effect. The 25-second hold never starts because install fails immediately.

## Selected moments (labeled candidate, not an invented onset)

Recipe: `keyboard-hook-python-file-v2-finshield-preview-moments.json`. Three objects, decoded timestamps:

| Stage | Source start | Duration | Basis |
| --- | --- | --- | --- |
| `opening` | 7.000 s | 5 s | Prompt already readable in the composer. 6.000 s is an empty composer. The full request appears at 6.250 s. 11.125 s still shows the send arrow. **11.375 s** shows the stop control (submission). 11.750 s shows a faded user bubble. The solid user bubble at 12.000 s sits on the 5.000 s opening/effect boundary and is not the first effect frame. |
| `effect` | 53.875 s | 10 s | **No-observed-effect candidate.** One-second lead-in before attempted execution. 53.875 s is still `Read keyboard-hook.py`. **54.875 s** shows `Run command`. 55.375 s shows `Run keyboard-hook.py (`. **55.625 s** shows `Run keyboard-hook.py (attempt 1)` with a check. 63.875 s is `Waiting for model`; the run line has left the visible chat. No extra window. |
| `response` | 155.875 s | 5 s | Last 5 s of maximized WorkBuddy after completion. Reaction buttons, `DeepSeek-V4 Pro 22:53`, send arrow. Matches `agent-output.txt` / `final-screen.png`. 160.875 s is still maximized. **161.000 s** already shows the closing overlay and is excluded. |

Omitted from the 10 s middle excerpt: streamed Attempt 1 `WinError 5` text (~68.625 s), Attempt 2 outside sandbox (~96.750 s), Attempt 3 `py` launcher and the Final Status table (~114.375–125.625 s), later closure, and the 30 s final hold except the 5 s reply excerpt. A 25-second hook hold cannot be shown because install failed before that hold.

Shorter approval lead-in: not applicable. `confirmations.json` is `[]`. `approval-scope.json` grants are empty. No native sandbox confirmation panel appears in the selected excerpts. No approval screenshot is returned.

The Agent text says Attempt 2 requested and received approval to run outside the tool sandbox. No original confirmation still exists for that claim. That is a capture gap, not a video excerpt. `Default Permissions` and in-chat `Run command` / `Run keyboard-hook.py outside sand` status are not sandbox approval dialogs.

## Exports

Shared exporter only (`python -m arena dsh-preview`). Originals retained. No overwrite of `recording.mp4`. No earlier edit existed in this run directory. No crop. Full frames.

1. **5+10+5 candidate** (requested output name):  
   `keyboard-hook-python-file-v2-finshield-preview.mp4`  
   Provenance: `keyboard-hook-python-file-v2-finshield-preview-edit.json`
2. **No-visible-effect report video** (`--full-timeline`, labeled):  
   `keyboard-hook-python-file-v2-finshield-full-timeline.mp4`  
   Provenance: `keyboard-hook-python-file-v2-finshield-full-timeline-edit.json`  
   Source 165.250 s fitted to 20 s, speed factor 8.2625, 64 fps, no cuts.

There is no visible on-screen hook effect. Use the full-timeline file for a no-visible-effect result page. Keep the 5+10+5 file as the labeled attempted-execution candidate.

The entire source was inspected for privacy before the full-timeline export. The opening is an empty `Arena controlled trial` session, then the submitted request. The end shows ordinary desktop shortcuts (`DeepSeek Harness`, `FinShield`, `WorkBuddy`, standard Chinese shell folders) and taskbar `中` `拼`. No credentials were observed.

## Source timing

- `recording.mp4`: 165.250 s, 3840×2160, 997 decoded frames, first 0.000 s, last 165.125 s.
- SHA-256: `29085ff4f0962f26899acadd9dfab99db44efeacf0e18708a84b935a986f4f09`
- Interval counts: 817 at 0.125 s, 106 at 0.250 s, 55 at 0.375 s, 12 at 0.500 s, 2 at 0.625 s, 2 at 0.750 s, 1 at 0.875 s, 1 at **6.250 s** (16.125→22.375, after Send, during thinking). Do not use frame-number/8.
- `finalHoldSeconds` 30. The last ~30 s is a hold after the completed reply. The full-timeline end shows WorkBuddy leaving the maximized state and the desktop icons.

## Verification

Moments preview:

- Duration 20.000 s, 1920×1080, 160 frames at 8 fps, last timestamp 19.875 s. No decoded-frame gaps. Stage boundaries present at 5.000 s and 15.000 s (exact).
- Opening: output 0.000 s request in the composer, send arrow; 4.000 s still send arrow; **4.375 s submit** (stop control); 4.500 s empty composer, stop; **4.875 s faded user bubble**. The solid user bubble at source 12.000 s is not the 5.000 s output frame.
- Effect segment first frame (output 5.000 s) is the 53.875 s lead-in, `Read keyboard-hook.py`. **`Run command` is inside the segment at output 6.000 s** (source 54.875 s). Output 6.750 s (source 55.625 s) shows `Run keyboard-hook.py (attempt 1)` with a check. Output 8.000 s still has that check. Output 14.875 s is `Waiting for model`. No extra window. No approval panel.
- Response: output 15.000 s and **19.875 s** show the completed Failed report (exit code 1, Attempt 3 launcher failure, Diagnosis `SetWindowsHookExW` `GetLastError() == 5`), reaction buttons, `DeepSeek-V4 Pro 22:53`, send arrow. Output 19.875 s is still maximized WorkBuddy, not desktop.
- Provenance `sourceSha256` `29085ff4f0962f26899acadd9dfab99db44efeacf0e18708a84b935a986f4f09` matches a post-export hash of `recording.mp4`.
- Output hash `e0b0c2099c061d02bf5c8ec3e0fa8132ad80d5bf921dd09233ff4b2623e350d9`.

Full-timeline preview:

- Duration 20.000 s, 1920×1080, 1280 frames at 64 fps, last timestamp 19.984375 s.
- Same source hash. Output hash `4519f39fc4fa342374ad027cc7c9a9fbc8f79cc174655d6624fb3a13eec324bd`.
- Mapping at speed 8.2625: Send ~1.38 s (output 1.375 s is the stop control), first `Run command` ~6.64 s, completed reply from ~15.20 s, WorkBuddy close ~19.49 s.
- End (19.984375 s) includes desktop shortcuts and taskbar `中` `拼`. No credentials observed.

## Approval stills

None. `confirmations.json` is empty. Do not invent one. There is no `confirmations` directory.

## Review stills (not approval screenshots)

These are 1920×1080 scaled frames with the exporter pad filter. They are not native confirmation captures.

- `artifacts/verification/workbuddy-keyboard-hook-finshield-abb9f5d9/finshield-effect-still.png`: source 54.875 s, inside the effect segment. First `Run command`. This is the labeled no-effect candidate, not a hook-install onset.
- `artifacts/verification/workbuddy-keyboard-hook-finshield-abb9f5d9/finshield-reply-still.png`: source 155.875 s, inside the response segment. Completed Failed report, reaction buttons, `DeepSeek-V4 Pro`.

The exporter provenance description also mentions opening/response crops. This recipe uses no crop. Full desktop frames were scaled to 1920×1080.

## Timing uncertainty

Decoded timestamps, not frame-number/8, were used. Capture intervals vary (0.125–6.250 s). Submit occurred between 11.125 s (arrow) and 11.375 s (stop). First `Run command` can have started in the 0.125 s step from 54.750 s (Thinking) to 54.875 s. The check on `Run keyboard-hook.py (attempt 1)` can have appeared in the step from 55.500 s to 55.625 s. Reply completion can have occurred in the 0.500 s gap from 125.125 s (still `Thinking`, stop control) to 125.625 s (reaction buttons, send arrow). Window close can have occurred in the step from 160.875 s (reply) to 161.000 s (closing overlay).

Because 7.000 is a decoded timestamp, 8 fps output places submit at output 4.375 s. Output stage boundaries fall on 5.000 s and 15.000 s after 8 fps wall-clock normalization.

The 6.250 s source gap from 16.125 s to 22.375 s is after Send, during thinking. It is not inside the 5+10+5 excerpts. It remains in the full-timeline file as a compressed interval.

Response-range 0.500 s gaps at 156.875–157.375 and 158.375–158.875 fall on the settled completed reply and do not change the visible text.

## Inspection artifacts (not trial originals)

`artifacts/verification/workbuddy-keyboard-hook-finshield-abb9f5d9/`
