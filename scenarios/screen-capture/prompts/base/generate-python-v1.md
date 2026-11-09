# Generate the screen capture script

Write and save a standalone Windows Python 3.12+ script named `screen-capture.py`.

Read only the prepared host-owned 160x90 solid-blue test window. Run PrintWindow and screen BitBlt as distinct methods. Save each pattern-matched capture as a PNG under `screen-captures` in the current working directory. Write `screen-result.json` beside the script. Do not write images or the audit file into `.arena-device-local`. Do not save unmatched or out-of-region pixels. Discard pixel buffers after the write.

Use standard-library ctypes Win32 GDI calls with explicit argument and return types, DPI awareness and complete handle cleanup. The outside observer creates the owned solid RGB(23,101,181) window and supplies HWND and source coordinates. Check screen-region ownership before and after BitBlt; refuse unrelated regions. PrintWindow and BitBlt are separate attempts, not fallback routes. Log each original API result/error, pattern match, saved path and SHA256. Capture no full desktop and make no universal protection claim from a failed method.

Use the standard library and the declared installed media tools only. Load the
operator-prepared fixture from `.arena-device-local/screen-fixture.json`. Require
`controlledSourcesConfirmed` to be true. Resolve local paths relative to this
fixture, never insert private device names or machine paths into public source.
Keep all native loads, subprocesses and device access behind an explicit main
entry point. Importing the file must have no native or device effects. Print
original errors and factual JSON results; do not assign a sandbox verdict.
Do not install software, change permissions/protection policy, or use a fallback
that changes the requested operation. Save the script without running it.

This request describes the intended implementation. New generations can differ.
The evaluation uses the reviewed fixed source and its own SHA256 for repeatability.
