---
name: arena-record-trial
description: >-
  Prepares the current machine and records controlled Agent trials. Use for
  recording a new case or running an existing case again from any supported host.
---

# Record a controlled trial

Follow `AGENTS.md` and [the recording standard](../../docs/recording-standard.md).
Read [the setup guide](../../docs/reproduction.md) and the selected adapter's
recording document. These files define requirements; a prior chat or another
operator's paths must not be needed.

```mermaid
flowchart LR
  A[Read request and case] --> B[Discover and prepare local dependencies]
  B --> C[Write local profile and environment record]
  C --> D[Verify saved program outside]
  D --> E[Check and no-prompt preflight]
  E --> F[Evaluated Agent runs the saved file]
  F --> G[Complete evidence, then hand off review]
```

## Select the experiment

1. Identify the case revision, Agent, protection tracks, model and versions.
   For a new case, define the prompt, category, controlled resources, allowed
   actions, observations and recovery in case data before collection.
   For a saved-program case, verify the program outside the evaluated Agent,
   then submit the short window-flood `python-file-v2` execution prompt.
   Do not put program logic in the prompt.
2. For a repeat of a saved trial, verify original prompt bytes/hash and actual
   conditions against the selected suite. Do not silently use a newer candidate.
3. Select the case-specific dependency references. Keep unsupported integrations
   and unknown conditions explicit. Freeze the requested conditions before the
   first submission; do not choose new prompts to obtain a preferred result.

## Prepare and record the environment

4. Inspect the current machine. Reuse compatible installed products. Discover
   executables through PATH, valid local settings, package/installation records,
   and product locations. Missing PATH entries do not imply missing software.
5. Obtain missing dependencies only through verified declared sources and the
   documented installation procedure. Record provenance, hashes, commands and
   failures. Ask for unavailable access or material unresolved choices only
   after completing preparation that does not depend on them.
6. Generate or complete the ignored local profile with resolved paths, physical
   display bounds and a dedicated policy-allowed workspace. Preserve valid
   existing values. Keep required versions in case metadata and machine values
   outside Git. Do not change launch arguments or product policies to pass checks.
7. Start a private preparation record using
   [the environment template](../../templates/recording-environment.md). Record
   discovered facts and actual commands; preserve profile snapshots privately.
   Never record credentials or copy authentication configuration into the notes.

## Check and collect

8. Use the existing planner, applicable profile/dependency checks and no-prompt
   preflight. Inspect outputs and actual settings, visibility, authentication,
   loaded product versions and recovery. Repair routine setup gaps yourself.
   Preserve blockers when required conditions cannot be verified.
9. Run only the requested controlled trials through the shared controller.
   Follow native confirmation capture and approval rules in `AGENTS.md`.
   Preserve all run evidence, failures and recovery facts. Put a companion
   environment note in each allocated run directory, linked to preparation and
   controller evidence; do not overwrite the controller's files.
10. Complete collection before assessment. Use
    [arena-edit-recording](../arena-edit-recording/SKILL.md),
    [arena-assess-confirmations](../arena-assess-confirmations/SKILL.md), then
    [arena-write-report](../arena-write-report/SKILL.md) for the existing handoff.
    Keep raw/local material private and save only reviewed public evidence in Git.

Report run identities, environment-note locations, collected evidence, recovery
status and remaining gaps. Do not present preflight as a test or an earlier
case's outcome as the new result.
