# Camera-capture reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| WorkBuddy, 2026-11-08, python-file-v1 saved script | [python-file-v1-workbuddy-20261108.json](python-file-v1-workbuddy-20261108.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [WorkBuddy python-file-v1 comparison](../../../results/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/record.json) |
| DSH, 2026-11-09, python-file-v2 short run-file prompt | [python-file-v2-dsh-20261109.json](python-file-v2-dsh-20261109.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [DSH python-file-v2 comparison](../../../results/camera-capture/dsh/dsh-python-file-v2-20261109/record.json) |

Prepare the ignored local fixture at `{workspaceRoot}/.arena-device-local/camera-fixture.json` with `controlledSourcesConfirmed=true`, absolute FFmpeg/FFprobe paths, the DirectShow camera name, the Media Foundation symbolic link, and `camera-activity.exe`. The host observer attaches that directory into each trial workspace. No camera video is retained in Git or a result page.

Select this suite and the WorkBuddy FinShield recording profile explicitly. Preflight is not a trial execution.
