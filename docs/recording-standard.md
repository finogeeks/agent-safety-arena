# Recording standard

Status: Accepted procedure, 2026-11-06. Applies to new cases and new executions
of existing cases. This document does not claim a verified fresh-machine run.

## Problem

A recording Agent must be able to work from a clone without the previous
operator's machine paths or chat history. Copying an example profile leaves
required paths empty. Installing software that is already present wastes work.
Both new cases and repeated trials need the same preparation and evidence rules.

## Behavior

The repository defines the experiment. The recording Agent prepares the current
machine, uses the shared controller, and records what it actually used. Local
configuration is an output of preparation, not a prerequisite supplied by the
previous operator. Use the [recording skill](../skills/arena-record-trial/SKILL.md)
and [task prompt](../templates/recording-task-prompt.md) for either task.

```mermaid
flowchart TD
  A[Recording request] --> B[Define case revision and controlled scope]
  B --> C[Inspect current machine and existing installations]
  C --> D{Requirements met?}
  D -->|Missing dependencies| E[Obtain declared versions from verified sources]
  E --> C
  D -->|Unresolved prerequisite| F[Record exact gap and required input]
  D -->|Yes|   G[Generate local profile and environment record]
  G --> V[Verify saved program outside the evaluated Agent]
  V --> H[Plan, static checks and no-prompt preflight]
  H --> I{Ready within declared scope?}
  I -->|No| F
  I -->|Yes| J[Evaluated Agent runs the saved file]
  J --> K[Complete evidence and recovery records]
  K --> L[Separate editing, assessment and report]
```

### 1. Define the recording

For a new case, create its case data under `scenarios/<id>/` before collection.
Specify the English primary prompt, revision, category, synthetic resources,
allowed actions, observation method, stop conditions, and recovery. Select the
Agent integration, model, reasoning effort, product versions, protection tracks,
locale, and intervention policy. Save the suite and dependency references.
Use the existing [case and suite contracts](multi-agent-evaluation.md); add
controller behavior only through the normal specification and code workflow.
Imported case wording alone is not an executable scope declaration.
For a saved-program case, verify the program on the host first. Then write the
execution prompt in the window-flood `python-file-v2` form. The evaluated Agent
runs that unchanged file. It does not write or debug the program during the trial.

For an existing case, select an explicit revision and suite. If the request is
to repeat a saved trial, compare its exact submitted prompt hash and actual
conditions with the suite. A current candidate prompt is not automatically the
historical submitted prompt. Resolve differences before submission, or label the
requested changed experiment as a new revision. Never rewrite the saved result.

A case revision selects its own FinShield version. There is no global selected
version and no implicit upgrade to `latest`. Freeze required conditions before
the first prompt; record actual conditions separately. Preserve launcher-induced
differences and unknowns rather than editing policy to obtain a matched label.

Before each new logical preflight or collection run, close the owned Agent and
check its documented default sandbox and approval settings. Restore any prior
trial changes through the documented preparation procedure, and record the
changed fields without credentials. Record actual runtime settings again after
launch: a launcher can change them. Do not assume a direct launch restores
defaults. Keep launcher-induced differences explicit and do not weaken a
protection setting to force an effect. After collection, restore and verify the
native default state before returning the machine.

### 2. Prepare the current machine

Inspect before installing. Use the current process PATH, validated existing
local profiles, package metadata, OS installation records, and standard product
locations. Check that candidate files exist and meet the selected requirements.
A command missing from PATH is not proof that the program is absent. A different
Agent process may inherit a different PATH; resolve the actual executable.

Reuse compatible installed programs. For missing dependencies, use the selected
version's documented distributor or package source. Record the source, version,
download hash where available, command, and outcome. Verify declared checksums
before use. For new dependency declarations, establish the source and version
before installation; do not invent a URL or installer hash. An unresolved source
remains a setup gap. Follow the documented installation procedure within the
recording request's scope. Do not silently replace a shared service version.

Do not send the user a path checklist when the Agent can discover the files.
Ask only for information or access that cannot be obtained, such as product
login, an unavailable installer, or a material unresolved experiment choice.
Keep routine discovery, configuration, and retries within the task.

Bootstrap installs Arena and copies a profile template; it does not discover
products or install them. The recording Agent performs these preparation steps.
Read [dependencies](../dependencies/README.md), the selected adapter document,
and [setup commands](reproduction.md). An unsupported integration stays blocked;
do not substitute another Agent or invent a separate case-specific recorder.

### 3. Generate local configuration

Read an existing local profile before changing it. Preserve valid settings and
record corrections. Write resolved machine paths to the adapter's ignored
`profiles/recording/*.local.json`, using the existing profile schema. Keep the
public example portable. Do not copy another host's absolute paths into defaults
or require a particular user name, drive, screen size, or previous workspace.

For DSH, resolve the runtime, CLI entry, browser, recording executable and desktop
tool; FinShield also requires its launcher, effective configuration, and desktop
Agent entry. Read actual physical capture bounds and DPI scaling, identify the
recording monitor/desktop, and verify them in preflight. A copied logical size
does not establish the physical recording rectangle.

Select a dedicated trial workspace under a directory already allowed by the
installed policy. Check its availability without changing the policy. Even when
a drive root is allowed, the test owns only its declared subdirectory and
resources. Broad host write permission does not expand the case scope.

Verify product authentication through its normal setup; keep credentials out of
Git, profile JSON, environment notes, and published evidence. Record readiness
without storing tokens or dumping the process environment. Preserve the existing
launch contract, product configuration, native controls, and service lifecycle.
For DSH/FinShield use [the desktop launch contract](finshield-recording.md).
For WorkBuddy desktop use [the WorkBuddy recording contract](workbuddy-recording.md).
For Codex CLI FinShield use [the self-confine contract](codex-finshield-recording.md).
For Claude CLI native collection use [the Claude terminal contract](claude-terminal-recording.md).

### 4. Save preparation and actual conditions

Start a private preparation directory under ignored `artifacts/runs/` with a
unique name. Use [the environment template](../templates/recording-environment.md)
for an Agent-written `environment.md` there. This is a human-readable companion
record, not a new runner input or a field added to the recording profile.

Record the repository commit and relevant uncommitted changes; case/suite and
dependency references with hashes; intended and observed settings; resolved
paths, versions, and available runtime hashes; OS/display/desktop information;
workspace boundary; and discovery/install/check commands with status and time.
Include failures, unresolved items, and interventions. Keep secret-bearing output
out of the notes. Do not mark a planned command as executed.

Preserve the prepared profile and its SHA-256 privately. After the controller
allocates a run, place a companion environment note in its run directory and
link the preparation record and controller-produced evidence. Keep separate run
identities for each actual trial. Update observations after preflight and
collection, without replacing earlier snapshots or the controller's own files.
Observed run settings take precedence over setup intentions in the final report.

### 5. Check, record, and hand off

Run the existing planner and inspect supported entries. Run `arena doctor` with
the explicit local profile and case-specific dependency file where supported.
An exit-zero file check does not certify service health, authentication, loaded
product versions, or screen visibility. Verify those conditions and run the
adapter's no-prompt preflight before submission. Fix discoverable setup errors
and repeat affected checks. Keep unresolved conditions explicit; do not declare
the trial ready while a required condition is missing.

Use the shared recording controller for the requested entries only. Record the
exact submitted request, model/settings, native confirmations, tools, effects,
completion and recovery. Preserve partial evidence on failure. Do not tune the
prompt based on interim safety judgments. Preparation, preflight and report
export are not trial executions or score denominator entries.

Complete collection before editing, warning assessment, or comparison. Display
videos are 20 seconds and every reviewed GIF is 5 seconds; the speed rule is
in [the report contract](report-contract.md). Hand off
through [editing](../skills/arena-edit-recording/SKILL.md),
[assessment](../skills/arena-assess-confirmations/SKILL.md), and
[report generation](../skills/arena-write-report/SKILL.md). Keep raw recordings,
preparation logs and local paths private. Commit portable case requirements and
reviewed results through the existing publication rules. Reuse original evidence
for translated pages. Report observed outcomes even when they differ from an
earlier run; reproduction does not promise identical model output.

| ID | Acceptance criterion |
| --- | --- |
| REC-1 | A fresh Agent can find this procedure from AGENTS.md and both READMEs for either a new or existing case. |
| REC-2 | Case requirements and dependency versions are portable; machine paths and generated profiles remain ignored local data. |
| REC-3 | Compatible existing programs are reused; missing dependencies have a recorded source and verification result, or an explicit blocker. |
| REC-4 | An environment note traces intended conditions, actual machine setup, commands, checks and run identities without credentials. |
| REC-5 | Static checks and no-prompt preflight precede collection; neither is counted as a test execution. |
| REC-6 | New cases declare scope and recovery; repeated trials preserve the selected original prompt and conditions or disclose a new revision. |
| REC-7 | Shared collection, original evidence, partial failures, separate review and existing launch contracts remain intact. |
| REC-8 | Reviewed display videos are 20 seconds. Reviewed GIFs are 5 seconds, each a 4x playback of its 20-second video, including the opening comparison GIF. |
| REC-9 | A saved-program trial verifies the program outside the evaluated Agent, then submits only the short window-flood `python-file-v2` execution prompt. |

## Out of scope

This procedure does not add an automatic installer, a new CLI command, adapter
support, or a new profile schema. It does not record a trial merely by being
added. Missing dependency provenance and unavailable product access remain
visible prerequisites, not completed setup.

## Decisions

Use one recording procedure for new and repeated cases. Keep portable experiment
requirements in Git, generated machine configuration locally, and actual setup
facts with each private run. The Agent performs discovery and preparation using
existing tools. See [repository ownership](repository-structure.md) and
[reproduction and publishing](reproduction-and-publishing.md).

## Tests

For this documentation change, check local links, both skill indexes, template
consistency, language parity of the README entry, and Git whitespace. No live
trial is needed to rename and define the procedure.

To validate REC-1 through REC-9 operationally, give a fresh Agent only a clone,
the recording request, and necessary product access. Test both a host with
compatible programs already installed and a clean supported host. Check reuse,
verified acquisition, profile generation, physical capture, no-prompt preflight,
run/environment records, recovery and report handoff. Exercise a missing source
and version mismatch: each must produce an explicit gap rather than a substituted
version. Validate new-case preparation and a repeated saved revision separately.
Record these checks as not run until actual evidence exists.
