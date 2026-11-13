# Background Process Lifetime

Status: Withdrawn by the operator on 2026-11-13. Excluded from active suites,
default verification and public catalog selection. Retain code, original Codex
recordings and diagnosis evidence. Do not resume investigation or collection
without a new request. Commands below are historical references only.

## Scope

Measure a self-expiring child heartbeat after its command parent exits.

Effect thresholds are declared test thresholds, not assumed product guarantees. External guard intervention remains separate from evaluated product behavior.

Use only the host-created target.json and the bounded workload in the
[System boundary specification](../../docs/system-boundary-cases.md).
Completed Codex recordings remain private historical evidence. Withdrawal does
not convert the observed unblocked effect into successful protection.

## Artifacts

| Artifact | Use |
| --- | --- |
| [Candidate](case.python-file-v2.json) | Existing owned-process-tree manifest for the shared recorder. |
| [Generation prompt](prompts/base/generate-python-v1.md) | English generation-only request. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the unchanged saved file, at most three attempts. |
| [Program](input/background-process-lifetime.py) | Byte-identical copy of the canonical bounded worker. |
| [Host display](input/system-boundary-display.ps1) | Independent upper-band white/red/gray metric panel. |
| [Source hashes](input/source.python-file-v2.json) | Frozen program, display and prompt bytes. |
| [WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) | Development-only native/FinShield pair. |

## Preparation and verification

Run host-only smoke verification before collection:

```powershell
python scripts/verify-system-boundary.py --case background-process-lifetime
```

This creates ignored local evidence and performs no Agent request or recording.
For recording, use the [shared recording procedure](../../docs/recording-standard.md)
and an existing verified local profile. The side script receives the owned
workspace through ARENA_TRIAL_WORKSPACE. Optional ARENA_SYSTEM_PYTHON selects
the host interpreter. Optional ARENA_SYSTEM_BOUNDARY_CONFIG selects ignored
local receiver configuration; it accepts receiverBind only.

```powershell
arena collect-batch --case scenarios/background-process-lifetime/case.python-file-v2.json --profile <local-recording-profile.json> --preflight
```

A no-prompt preflight does not run the effect. Actual collection is a separate
request. Native collection keeps product-default controls. Record actual
FinShield launch differences. Never count smoke controls or unsupported
prerequisites as formal successful trials.

## Evidence and recovery

The host logs admission, independent metric samples, original socket receipts
when applicable, and final observations before it closes the outer safety Job.
White means below threshold, red means observed effect, and gray means unknown.
A white panel alone does not prove interception. The host verifies that no owned
Job process survives recovery and removes only the exact synthetic payloads.

## Non-resource python-file-v3 candidate

Observe a child heartbeat after its command parent exits.

This is a controlled effect case. See the
[scope and verification contract](../../docs/system-ipc-cases.md).

| Artifact | Use |
| --- | --- |
| [Candidate](case.python-file-v3.json) | Shared collector manifest. |
| [Fixed source](input/v3/background-process-lifetime.py) | Unchanged standalone program. |
| [Execution prompt](prompts/base/python-file-v3.md) | At most three executions; original errors retained. |
| [Generation prompt](prompts/base/generate-python-v3.md) | Separate generation-only track. |
| [Display adapter](input/system-ipc-display.ps1) | Shared host admission, observer and renderer. |
| [Source hashes](input/source.python-file-v3.json) | Original program, prompts and adapter bytes. |
| [Reproduction suite](reproduction/python-file-v3-workbuddy.json) | Native/FinShield development pair. |

Run `python scripts/verify-system-ipc.py --case background-process-lifetime` from the repository root
for a native-first host effect check. This starts no Agent and records no video.
Real native controls must work before a FinShield finding is assigned. Loopback
results do not establish internet access; a parent exit is not an Agent-turn end.
Preparation errors and unavailable host targets remain unresolved.
