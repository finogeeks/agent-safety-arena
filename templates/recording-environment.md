# Recording environment record

Copy this template into a unique private preparation directory under
`artifacts/runs/`. Replace bracketed values with observations; use `unknown`,
`not run`, or `not applicable` with a reason. Keep this record and profile
snapshots out of Git. Do not include credentials, tokens or full authentication
configuration. Follow [the recording standard](../docs/recording-standard.md).

## Identity and inputs

- Preparation ID and timestamp with time zone: [value]
- Task: [new case / new execution / repeat saved trial]
- Repository commit and relevant uncommitted changes: [value]
- Case revision, suite path and SHA-256: [value]
- Case/prompt source paths, revision and SHA-256: [value]
- Saved trial reference, if repeating: [value]
- Agent and requested protection tracks: [value]
- Agent/environment profiles and dependency references with SHA-256: [value]

## Intended and observed conditions

| Condition | Required | Observed | Check/evidence and time |
| --- | --- | --- | --- |
| Agent integration and version | [value] | [value] | [value] |
| FinShield version, when selected | [value] | [value] | [value] |
| Model/provider and reasoning effort | [value] | [value] | [value] |
| Built-in sandbox and approval policy (product default, not reused local YOLO) | [value] | [value] | [value] |
| Prompt/UI locale | [value] | [value] | [value] |
| Approval/intervention policy | [value] | [value] | [value] |

Keep one observed snapshot per protection track and run. Distinguish installed
file versions from the running Agent/service image and actual session settings.
Record mismatches and unknowns; do not replace intended requirements with them.

## Machine and dependencies

- OS/version/architecture: [value]
- Monitor, physical capture rectangle, DPI/scaling and virtual desktop: [value]
- Trial workspace and resource/cleanup boundaries: [value]
- Local recording profile path and snapshot SHA-256: [value]
- Effective product configuration path and applicable nonsecret policy facts: [value]
- Product/model access check: [ready/failed/unknown and evidence, no credentials]

| Component | Resolved file/location | Actual version/hash | Reused or acquired; discovery/source and verification |
| --- | --- | --- | --- |
| [one row per required tool/runtime/product] | [value] | [value] | [value] |

## Preparation and check log

| Time with zone | Purpose | Actual command/action | Result/exit code | Private evidence reference |
| --- | --- | --- | --- | --- |
| [value] | [discovery/install/static check/preflight] | [secret-free value] | [value] | [value] |

Include failed attempts, fixes and interventions. Distinguish planned actions
from executed actions. Preserve prior snapshots and logs when retrying.

## Run handoff

- Readiness and unresolved prerequisites: [value]
- Plan file/entry and check/preflight evidence: [value]
- Preparation record location: [value]
- Actual run IDs, protection tracks and directories: [value]
- Per-run environment note and retained profile snapshot: [value]
- Controller evidence for actual prompt, settings, tools and observations: [value]
- Completion, failure and recovery evidence: [value]
- Editing/assessment/report handoff and remaining gaps: [value]

This note supplements controller evidence. Preparation and preflight are not
trial results. Publish only reviewed portable facts under the existing report
contract; do not publish this private file directly.
