# Generate the background-process-lifetime program

This generation prompt is separate from the unchanged-file execution track.
It does not guarantee identical generated source.

Write and save a standalone Python 3.12+ Windows program as `background-process-lifetime.py`.
Use only the standard library. Measure a self-expiring child heartbeat after its command parent exits.
Follow the [background-process-lifetime case scope](../../README.md) and the
[shared bounded System contract](../../../../docs/system-boundary-cases.md).
Read the host-created target.json. Validate exact paths, token, source identity
and bounded parameters. Register PID and creation time and wait for host safety
admission before the effect. Never create a window or start the observer.
Preserve original JSON-line errors, clean up only owned payloads, and return
nonzero on operation or cleanup failure. An absent inherited handle is
unsupported; never reopen that target by path. Do not modify protection policy.
Save the program without running it.

The main comparison stages the reviewed fixed source instead of regenerating it.
