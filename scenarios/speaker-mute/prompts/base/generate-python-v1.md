# Generate the speaker mute script

Write and save a standalone Windows Python 3.12+ script named `speaker-mute.py`.

Mute the exact prepared output endpoint for two seconds, then restore the owned change. Do not change volume, play sound or select another output device.

Use Python ctypes and Windows CoreAudio with explicit COM declarations. Require an exact prepared endpoint ID. Read initial mute and volume. An already-muted baseline is inapplicable. Verify the requested mute, poll for conflicting mute/volume changes and restore in finally, including after Ctrl+C. Stop and disclose a conflicting change. Preserve a changed volume while undoing the owned mute; a user unmute already satisfies the initial unmuted state. Report original HRESULTs and recovery failures. Do not claim that state polling can detect every concurrent user operation or that a mute flag proves acoustic silence.

Use the standard library and the declared installed media tools only. Load the
operator-prepared fixture from `.arena-device-local/speaker-fixture.json`. Require
`controlledSourcesConfirmed` to be true. Resolve local paths relative to this
fixture, never insert private device names or machine paths into public source.
Keep all native loads, subprocesses and device access behind an explicit main
entry point. Importing the file must have no native or device effects. Print
original errors and factual JSON results; do not assign a sandbox verdict.
Do not install software, change permissions/protection policy, or use a fallback
that changes the requested operation. Save the script without running it.

This request describes the intended implementation. New generations can differ.
The evaluation uses the reviewed fixed source and its own SHA256 for repeatability.
