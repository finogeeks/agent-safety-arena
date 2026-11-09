# Screen-recording reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| WorkBuddy, 2026-11-09, python-file-v1 saved script | [python-file-v1-workbuddy-20261109.json](python-file-v1-workbuddy-20261109.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [WorkBuddy python-file-v1 comparison](../../../results/screen-recording/workbuddy/workbuddy-python-file-v1-20261109/record.json) |
| DSH, 2026-11-09, python-file-v2 short run-file prompt | [python-file-v2-dsh-20261109.json](python-file-v2-dsh-20261109.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [DSH python-file-v2 comparison](../../../results/screen-recording/dsh/dsh-python-file-v2-20261109/record.json) |
| Codex CLI, 2026-11-09, python-file-v2 short run-file prompt | local Codex recording profile | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [Codex CLI python-file-v2 comparison](../../../results/screen-recording/codex-cli/codex-python-file-v2-20261109/record.json) |

Prepare the ignored local fixture at `{workspaceRoot}/.arena-device-local/screen-recording-fixture.json` with `controlledSourcesConfirmed=true`, `captureScope=primary-screen`, and absolute FFmpeg/FFprobe paths. The host observer attaches that directory into each trial workspace. Do not publish the workspace MP4.

Select this suite and the DSH FinShield recording profile explicitly. Preflight is not a trial execution.
