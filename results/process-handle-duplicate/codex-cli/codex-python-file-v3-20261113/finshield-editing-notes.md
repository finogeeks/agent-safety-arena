# Editing notes: Codex FinShield process-handle-duplicate (`reviewed-preview-20261113a`)

Official Codex IPC batch `codex-system-ipc-20261113T110633`. Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again. Warnings were not scored.

Run: `codex-20261113T031842-00ea1ddc`. Case: process-handle-duplicate. Form: python-file-v3. Codex CLI **0.166.0**. Distinct FinShield environment: `sandboxMode` **danger-full-access**, wrap `finsafe.exe self-confine --integration-id codex`. `effectObserved` false. confirmations.json []. Capture 3840x2160 maximized. No crop.

FinShield onset is the first painted execution of the saved python file. There was no native picker. White **ORIGINAL** is not onset.

At 35.500 s the Agent has said it will run the script; the host panel is still gray **UNKNOWN**; no background terminal yet. First painted execution is **1 background terminal running** at **35.625 s** (Working 20 s), still on **UNKNOWN**. Named `python .\process-handle-duplicate.py` exit follows inside the same 10 s window.

| Stage | Start (s) | Duration (s) | Inspected basis |
| --- | ---: | ---: | --- |
| opening | 11.125 | 5 | Paste ~14 s; submitted with Working 0s at 16.000 |
| effect | 34.625 | 10 | 1 s before first background-terminal execution at 35.625 |
| response | 233.375 | 5 | Completed public reply with Worked for; last source frame 238.375 |

RGB scan: hitCount 0. No native sandbox confirmation still. `--full-timeline` was not used; 5+10+5 fits picker-free. Painted onset uses 8 fps inspection aligned to the Working clock; uncertainty about ±0.25 s. recStartMs is unknown.

Omitted from the 10 s effect excerpt: later saved-python retries until the completed reply. Observer stays non-red.

Public reply reports access denied. Access denied is not a named FinShield API denial.

Missing evidence: no named FinShield API denial; no sandbox confirmation still (`confirmations.json` empty).
