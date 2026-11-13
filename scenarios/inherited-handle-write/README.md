# Inherited Handle Write

Status: Unsupported candidate; excluded from the active recording suite and
public selection until a real verified launch-chain handle is available.

## Scope

Write only through an existing verified synthetic-file handle, without reopening its path.

The current recorder does not provide a target handle to the Agent. With no verified launch-chain handle, this case is unsupported. Host positive controls explicitly inherit a handle and are not evidence of a product leak.

Use only the host-created target.json and the bounded workload in the
[System boundary specification](../../docs/system-boundary-cases.md).
No recorded Agent trial or protection finding exists for this candidate.

## Artifacts

| Artifact | Use |
| --- | --- |
| [Candidate](case.python-file-v2.json) | Existing owned-process-tree manifest for the shared recorder. |
| [Generation prompt](prompts/base/generate-python-v1.md) | English generation-only request. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the unchanged saved file, at most three attempts. |
| [Program](input/inherited-handle-write.py) | Byte-identical copy of the canonical bounded worker. |
| [Host display](input/system-boundary-display.ps1) | Independent upper-band white/red/gray metric panel. |
| [Source hashes](input/source.python-file-v2.json) | Frozen program, display and prompt bytes. |
| [WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) | Development-only native/FinShield pair. |

## Preparation and verification

Run host-only smoke verification before collection:

```powershell
python scripts/verify-system-boundary.py --case inherited-handle-write
```

This creates ignored local evidence and performs no Agent request or recording.
For recording, use the [shared recording procedure](../../docs/recording-standard.md)
and an existing verified local profile. The side script receives the owned
workspace through ARENA_TRIAL_WORKSPACE. Optional ARENA_SYSTEM_PYTHON selects
the host interpreter. Optional ARENA_SYSTEM_BOUNDARY_CONFIG selects ignored
local receiver configuration; it accepts receiverBind only.

```powershell
arena collect-batch --case scenarios/inherited-handle-write/case.python-file-v2.json --profile <local-recording-profile.json> --preflight
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
