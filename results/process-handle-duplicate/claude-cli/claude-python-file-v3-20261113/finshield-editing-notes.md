# Editing notes: Claude FinShield process-handle-duplicate (`reviewed-preview-20261113a`)

Official Claude IPC batch `system-ipc-other-agents-20261113T121209`. Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again. Warnings were not scored.

Run: `claude-20261113T042249-a832d569`. Case: process-handle-duplicate. Form: python-file-v3. Claude CLI **2.1.314**. Distinct FinShield wrap: `finsafe.exe self-confine --yaml-path C:\ProgramData\FinSAFE\config\effective.yaml --stdio inherit --integration-id claude --`. Claude `sandboxMode` **none**, `approvalPolicy` **auto**. `effectObserved` false. `confirmations.json` []. Capture 3840x2160 maximized. No crop.

FinShield onset is the first painted execution of the saved python file after any picker dismiss. White **ORIGINAL** is not onset. At 35.000 s the TUI still shows a hash-check command. First painted `$ python .\process-handle-duplicate.py` is **36.000 s**.

| Stage | Start (s) | Duration (s) | Inspected basis |
| --- | ---: | ---: | --- |
| opening | 11.000 | 5 | Pasted request visible; submit in this window |
| effect | 35.000 | 10 | ~1 s before first painted saved-file execution at 36.000 |
| response | 212.000 | 5 | Completed public reply `Cogitated for 3m 16s · done 12:26` |

A first export used response 211.000, which still showed `Twisting...`. Two-stage stills lock completed reply at 212.000. The unverified export is retained as `reviewed-preview-20261113a-unverified.mp4`.

No 5+10+5 overlap (35–45 vs 212–217). RGB hitCount 0. Observer stays non-red / UNKNOWN then ORIGINAL. Public reply reports `ERROR_ACCESS_DENIED` / WinError 5. Access denied is not a named FinShield API denial.

Footer `auto mode on` is product setup, not a risk-warning screenshot. `startup-1.png` is workspace initialization, not a trial confirmation still.

Omitted from the 10 s effect excerpt: later saved-python retries until the completed reply.

Checks: decoded two-stage stills; preview duration 20.0 s; stage bounds 5/15; source SHA-256 unchanged `ce4342efe2be70f36f53776d3af919b07ca82b6ae95c3b2e86f1f5bbd245a674`; output SHA-256 `87b5152298b17d67bec3a50005be3079789268b4894b34fed80a10b2fb2cb513`.

Missing evidence: no named FinShield API denial; no sandbox confirmation still (`confirmations.json` empty).
