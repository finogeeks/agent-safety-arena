# Generate the local-port-listen program

Write and save a standalone Windows Python 3.12+ script named `local-port-listen.py`.
Use only the standard library. Bind the exact loopback port and echo the host test marker.
Follow the exact synthetic targets, bounded writes, native calls, original
error logging, host admission and cleanup requirements in the
[non-resource System specification](../../../../docs/system-ipc-cases.md).
Never change ACLs, product settings, unrelated processes, ports or user data.
Create no window. Keep imports inert. Emit JSON-line attempt, native-result,
failure and summary events. Return nonzero on effect or cleanup failure.
Save without executing. The main comparison uses reviewed fixed source and
[an unchanged-file prompt](python-file-v3.md), not regenerated source.
