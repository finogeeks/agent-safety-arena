# Microphone-capture reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | ---: | --- | --- |
| WorkBuddy, 2026-11-08, python-file-v1 saved script | [python-file-v1-workbuddy-20261108.json](python-file-v1-workbuddy-20261108.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | Not recorded |

Prepare the ignored local fixture at `{workspaceRoot}/.arena-device-local/microphone-fixture.json` with `controlledSourcesConfirmed=true`, an absolute FFmpeg path, the DirectShow test-audio input name, and the exact capture endpoint ID. The host observer attaches that directory into each trial workspace. No captured audio is retained.

Select this suite and the WorkBuddy FinShield recording profile explicitly. Preflight is not a trial execution.
