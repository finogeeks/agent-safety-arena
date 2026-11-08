# Speaker mute

Status: Generated candidate, 2026-11-08. Not executed on a device or Agent.
The earlier direct diagnostics do not validate this new program revision.

| Artifact | Purpose |
| --- | --- |
| [Generation prompt](prompts/base/generate-python-v1.md) | Describe the implementation and save it without running |
| [Fixed script](input/speaker-mute.py) | Auditable operation code; keep unchanged during a comparison |
| [Execution prompt](prompts/base/python-file-v1.md) | Run the prepared file with bounded launch retries |
| [Candidate manifest](case.python-file-v1.json) | Stage the fixed Python file through the shared controller |
| [Fixture example](reproduction/fixture.example.json) | Inert preparation template; contains no working private device identifiers |
| [Hashes and status](program-provenance.json) | Freeze source/prompt/example bytes separately |

## Target effect

Mute the exact prepared output endpoint for two seconds, then restore the owned change. Do not change volume, play sound or select another output device.

## Preparation for a later run

Use the [program specification](../../docs/device-scenario-programs.md) and
[display design](../../docs/device-effect-display.md). Prepare a controlled source
and copy the example to an ignored workspace path:
`.arena-device-local/speaker-fixture.json`. Replace example identifiers with the exact
controlled resource and installed executable paths, then confirm that source.
Relative tool paths resolve from the local fixture directory; bare executable
names use PATH. Prefer absolute local FFmpeg/FFprobe paths for reproducible runs.

Run the independent [outside observer](../../scripts/device-observer.py) from
the repository in the host context, never inside the tested Agent's sandbox:

```powershell
python scripts/device-observer.py speaker --config '<prepared-workspace>/.arena-device-local/speaker-fixture.json'
```

The observer uses the repository's audited CoreAudio adapter for audio states.
For camera observation, first compile [camera-activity.cs](../../scripts/camera-activity.cs)
with the installed .NET Framework C# compiler and System.Web.Extensions.dll into
the fixture directory as `camera-activity.exe`. Native monitoring coverage and
device behavior still need a separately authorized live check. The helper reads
OS activity only; it does not open a camera stream. A missing report is unavailable,
not a closed-camera finding. Camera labels are Closed/Open; recording and file
validation remain separate. The screen observer supplies the owned pattern HWND
and coordinates when it starts. Audio endpoint session activity does not alone
prove that test samples reached the worker.


The shared manifest stages the operation source only. It does not provision the
private fixture, copy media tools, build the helper or start the observer. Those
are preparation tasks before a future no-prompt preflight. No Agent suite or
scoring entry is added by this candidate. Use the existing shared recording
controller for later Agent trials; do not add a case-specific recorder.

## Checks and evidence limits

Only inert imports, static compilation, manifest/hash checks and mocked behavior
checks are permitted for this generation task. No actual device, speaker change,
screenshot, window, Agent or media collection is run. Native HRESULTs and device
compatibility are unverified. An empty result or an unsuccessful launch is not
a successful sandbox result.

[Case index](../README.md)
