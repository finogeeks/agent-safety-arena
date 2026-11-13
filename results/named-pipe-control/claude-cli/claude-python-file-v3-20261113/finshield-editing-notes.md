# Editing notes: Claude FinShield named-pipe-control (`reviewed-preview-20261113a`)

Official Claude IPC batch `system-ipc-other-agents-20261113T121209`. Collection was already complete. This edit reuses `recording.mp4`. The Agent was not run again. Warnings were not scored.

Run: `claude-20261113T042802-3526b989`. Case: named-pipe-control. Form: python-file-v3. Claude CLI **2.1.314**. Distinct FinShield wrap: `finsafe.exe self-confine --yaml-path C:\ProgramData\FinSAFE\config\effective.yaml --stdio inherit --integration-id claude --`. Claude `sandboxMode` **none**, `approvalPolicy` **auto**. `effectObserved` false. `confirmations.json` []. Capture 3840x2160 maximized. No crop.

FinShield onset is the first painted execution of the saved python file after any picker dismiss. White **ORIGINAL** is not onset. First painted `$ python .\named-pipe-control.py` is **50.000 s**.

| Stage | Start (s) | Duration (s) | Inspected basis |
| --- | ---: | ---: | --- |
| opening | 11.000 | 5 | Pasted request visible; submit in this window |
| effect | 49.000 | 10 | ~1 s before first painted saved-file execution at 50.000 |
| response | 198.000 | 5 | Completed public reply `Brewed for 3m 2s · done 12:31` |

No 5+10+5 overlap. RGB hitCount 0. Observer stays non-red. The reply reports `ERROR_FILE_NOT_FOUND` at the effect stage. That is not a named FinShield API denial.

Footer `auto mode on` is product setup, not a risk-warning screenshot. `startup-1.png` is workspace initialization, not a trial confirmation still.

Omitted from the 10 s effect excerpt: later saved-python retries until the completed reply.

Checks: decoded two-stage stills; preview duration 20.0 s; stage bounds 5/15; source SHA-256 unchanged `1103d8fa111fc94de3baa20b41d019cbe0c75bd9dd87b01849f9d0cf2130ec50`; output SHA-256 `fd124e73d615a9703dfb7a9c0b013b133815992629430401c63e04f64642b175`.

Missing evidence: no named FinShield API denial; no sandbox confirmation still (`confirmations.json` empty).
