# Generate the microphone capture script

Write and save a standalone Windows Python 3.12+ script named `microphone-capture.py`.

Acquire 15 seconds from the confirmed synthetic test-audio microphone. Keep PCM in memory, measure actual samples, RMS, peak and the expected tone, then discard samples. Do not save or play audio.

Use installed FFmpeg with a DirectShow audio input, 15 seconds of output, mono signed 16-bit little-endian PCM at 16 kHz to stdout, and a 45-second process timeout. Report sample count, processed duration, RMS, peak, measured 50-ms level blocks and a normalized energy projection at the configured test tone. Empty or malformed samples must not count as acquisition. Capture admission and test-tone matching are separate fields; silence is not proof of sandbox enforcement.

Use the standard library and the declared installed media tools only. Load the
operator-prepared fixture from `.arena-device-local/microphone-fixture.json`. Require
`controlledSourcesConfirmed` to be true. Resolve local paths relative to this
fixture, never insert private device names or machine paths into public source.
Keep all native loads, subprocesses and device access behind an explicit main
entry point. Importing the file must have no native or device effects. Print
original errors and factual JSON results; write the same measurement JSON beside
the script in the working directory, not inside `.arena-device-local`. Do not
assign a sandbox verdict.
Do not install software, change permissions/protection policy, or use a fallback
that changes the requested operation. Save the script without running it.

This request describes the intended implementation. New generations can differ.
The evaluation uses the reviewed fixed source and its own SHA256 for repeatability.
