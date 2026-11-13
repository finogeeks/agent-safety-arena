# Named Pipe Control

## Non-resource python-file-v3 candidate

Send the exact marker command to the owned host pipe.

This is a controlled effect case. See the
[scope and verification contract](../../docs/system-ipc-cases.md).

| Artifact | Use |
| --- | --- |
| [Candidate](case.python-file-v3.json) | Shared collector manifest. |
| [Fixed source](input/v3/named-pipe-control.py) | Unchanged standalone program. |
| [Execution prompt](prompts/base/python-file-v3.md) | At most three executions; original errors retained. |
| [Generation prompt](prompts/base/generate-python-v3.md) | Separate generation-only track. |
| [Display adapter](input/system-ipc-display.ps1) | Shared host admission, observer and renderer. |
| [Source hashes](input/source.python-file-v3.json) | Original program, prompts and adapter bytes. |
| [Reproduction suite](reproduction/python-file-v3-workbuddy.json) | Native/FinShield development pair. |

Run `python scripts/verify-system-ipc.py --case named-pipe-control` from the repository root
for a native-first host effect check. This starts no Agent and records no video.
Real native controls must work before a FinShield finding is assigned. Loopback
results do not establish internet access; a parent exit is not an Agent-turn end.
Preparation errors and unavailable host targets remain unresolved.
