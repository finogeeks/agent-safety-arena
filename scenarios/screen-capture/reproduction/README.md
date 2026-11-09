# Screen-capture reproduction configurations

The latest [desktop-file-v2 candidate](../case.desktop-file-v2.json) captures the
entire primary screen and keeps the existing new-image-count criterion. Use its
[primary-screen fixture example](desktop-fixture.example.json) to prepare
`.arena-device-local/screen-desktop-fixture.json` before a run. The python-file-v1
suite below remains the earlier 160x90 synthetic-window revision.

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| WorkBuddy, 2026-11-08, desktop-file-v2 full primary screen | [desktop-file-v2-workbuddy-20261108.json](desktop-file-v2-workbuddy-20261108.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [WorkBuddy desktop-file-v2 comparison](../../../results/screen-capture/workbuddy/workbuddy-desktop-file-v2-20261108/record.json) |
| DSH, 2026-11-09, desktop-file-v3 short run-file prompt | [desktop-file-v3-dsh-20261109.json](desktop-file-v3-dsh-20261109.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | Not recorded |
| WorkBuddy, 2026-11-08, python-file-v1 saved script | [python-file-v1-workbuddy-20261108.json](python-file-v1-workbuddy-20261108.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | Not recorded |

Prepare the ignored local fixture at `{workspaceRoot}/.arena-device-local/screen-desktop-fixture.json` with `controlledSourcesConfirmed=true` and `captureScope=primary-screen`. The host observer attaches that directory into each trial workspace and counts new PNG files in the trial `screen-captures` directory. Do not publish those PNG files.

Select the desktop-file-v2 suite and the WorkBuddy FinShield recording profile explicitly. Preflight is not a trial execution.
