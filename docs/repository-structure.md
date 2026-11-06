# Repository structure

Status: Accepted; updated on 2026-11-06 for clone setup and case/Agent results.
This document owns directory responsibilities. The
[reproduction and publishing specification](reproduction-and-publishing.md)
owns setup and static build behavior.

## Problem

The repository began with project documents and task procedures and now also
contains an offline implementation and a DSH recorder.
The Agent Safe proof of concept contains useful lifecycle, evidence, recovery, and
reporting behavior, but it also mixes reusable tools with case output, private
records, fixed Windows paths, DSH assumptions, and historical layouts.

The project needs one structure that keeps reusable evaluation behavior separate
from scenarios, agent profiles, environment profiles, prompt development,
private evidence, reviewed results, generated sites, and temporary migration
sources.

## Behavior

The repository uses this logical structure. Create a directory when its first
owned file is added. Do not add empty placeholder directories.

```text
agent-safety-arena/
├── AGENTS.md
├── README.md
├── README.zh-CN.md
├── pyproject.toml
├── scripts/
│   └── bootstrap.ps1
├── dependencies/
│   ├── runtime.json
│   └── finshield/<version>/<platform>.json
├── skills/
│   └── arena-*/SKILL.md
├── docs/
│   ├── README.md
│   ├── first-evaluation.md
│   ├── repository-structure.md
│   └── adr/
├── scenarios/
│   └── <scenario-id>/
│       ├── reproduction/<trial-revision>.json
│       └── prompts/
│           ├── base/<version>.md
│           └── agents/<agent-id>/
│               ├── development/<revision>.md
│               └── frozen/<version>.md
├── profiles/
│   ├── agents/<agent-id>/
│   ├── environments/<environment-id>/
│   │   └── <version>/evaluation.json
│   ├── suites/<suite-id>.json
│   └── recording/<shared-profile>.json
├── src/arena/
│   ├── runner/
│   ├── adapters/agents/
│   ├── adapters/environments/
│   ├── evidence/
│   ├── fixtures/
│   ├── assessment/
│   └── reporting/
├── templates/
├── tests/
├── migration/agent-safe-poc/
├── results/
│   └── <scenario-id>/<agent-id>/<comparison-id>/
│       ├── record.json
│       └── media/
└── artifacts/
    ├── runs/<run-id>/
    └── site/
```

`dependencies/` owns external tool requirements and immutable version-specific
product baselines. It does not contain a global selected FinShield version.
Each case's `reproduction/` suite selects the environment profile version;
its README links the matching dependency file. Different cases and revisions
can reuse different versions. Keep downloaded installers in ignored `.tools/`.
Keep Arena's editable installation in ignored `.venv/`.

Version-independent environment profiles, such as `native/evaluation.json`,
remain directly under their environment directory. Synthetic replay results
keep `result.json` instead of `record.json`, under the same Agent grouping.
`profiles/suites/` owns shared multi-case plans; case-owned suites belong in the
case's `reproduction/`. Local executable paths remain under ignored
`profiles/recording/*.local.json`.

```mermaid
flowchart LR
  B[Versioned scenario base prompt] --> T[Agent-specific development]
  A[Agent profile] --> T
  T --> F[Frozen prompt version]
  F --> R[Common runner]
  E[Environment profile] --> R
  R --> V[Private raw run evidence]
  V --> D[Separate assessments]
  D --> C[Reviewed result and edited media]
  C --> P[Generated public site]
```

### Prompt lifecycle

Each scenario owns the common prompt intent and the Agent-specific wording for
that scenario. An Agent profile owns vendor-default configuration, adapter
behavior, and general prompt constraints. It does not own copies of every
scenario prompt.

1. Add a versioned base prompt under
   `scenarios/<scenario-id>/prompts/base/`.
2. Develop wording for one Agent under
   `scenarios/<scenario-id>/prompts/agents/<agent-id>/development/`. Record the
   base version, model, fixture conditions, change reason, and trial status.
3. Copy the accepted wording to an immutable version under `frozen/`. A formal
   comparison for the same Agent uses the same frozen prompt, model, and fixture
   conditions in each environment.
4. Store the exact submitted prompt and its SHA256 value in
   `artifacts/runs/<run-id>/`. The reviewed result identifies the frozen prompt
   version and the actual prompt hash.

Different Agents can use different tuned wording. The report discloses the
difference and does not claim that cross-Agent results used identical wording.
Development trials remain separate from frozen formal runs.

New primary trials use English. Suite files select Agent/environment pairs and
repetitions; report language does not add trial entries. Agent and environment
`evaluation.json` files declare identities and known conditions; recording
profiles hold machine/presentation settings. Existing offline `profile.json`
contracts remain separate. See [multi-Agent evaluation](multi-agent-evaluation.md).

English and Chinese reports use one shared reviewed evidence/media set. A
translation is display content, not a new original submission or recording.

Imported DSH requests follow the same base, development, and frozen layout.
Each scenario owns its README and prompt provenance. Historical collection IDs
identify source revisions within that scenario; they do not create a collective
archive scenario or a separate case tree. See [prompt-library.md](prompt-library.md).

### Result lifecycle

`artifacts/runs/<run-id>/` contains raw and private evidence, including original
recordings, native logs, actual prompts, configuration snapshots, approvals,
observations, and recovery proof. This directory is local evidence and is not
committed.

`results/<scenario-id>/<agent-id>/<comparison-id>/` contains the reviewed result that
the project keeps in Git. A result can reference one or more run IDs. It includes
the report data, source hashes, review status, limitations, and selected public
media. Exact reviewed text and condition gaps remain in JSON. HTML is generated.
Edited display MP4 files and selected screenshots belong under its
`media/` directory. Raw recordings do not.

`artifacts/site/` is a generated website assembled from reviewed results and
templates. It is not the canonical result and is not committed. A publication
workflow can regenerate it without access to raw recordings.

### Acceptance criteria

| ID | Observable criterion |
| --- | --- |
| AC-1 | `skills/` is the only skill tree. Each project skill uses the `arena-` namespace and appears in both skill indexes. |
| AC-2 | `docs/` owns requirements, measurement rules, migration plans, report contracts, and accepted technical decisions. Draft documents identify unresolved decisions. |
| AC-3 | Each `scenarios/<scenario-id>/` directory owns task boundaries, synthetic resources, untrusted inputs, expected observations, recovery requirements, supported evaluation tracks, and versioned prompt variants. It does not own a duplicate runner. |
| AC-4 | A scenario prompt has a versioned base, Agent-specific development revisions, and an immutable frozen version. Each formal run stores the actual submitted prompt and SHA256 value. |
| AC-5 | `src/arena/runner/` owns the common lifecycle. Agent and environment differences enter through adapters. Evidence, fixtures, assessment, and reporting remain separate modules. |
| AC-6 | `profiles/agents/` and `profiles/environments/` keep Agent behavior separate from environment enforcement. Agent profiles do not duplicate scenario prompts. |
| AC-7 | `migration/agent-safe-poc/` contains only reviewed source copies with provenance, SHA256 values, dependencies, extraction work, and a removal plan. It is not a second permanent implementation. |
| AC-8 | Reusable code does not depend on historical case directories, browser profiles, live credentials, installed binaries, or fixed user-specific paths. Unresolved dependencies remain documented gaps. |
| AC-9 | Direct-operation and prompt-injection evaluations use the same lifecycle and result model. The scenario metadata identifies the track; directory placement does not change the measurement meaning. |
| AC-10 | `artifacts/runs/<run-id>/` owns raw private evidence and is not committed. `results/<scenario-id>/<agent-id>/<comparison-id>/` owns reviewed JSON, selected display media, provenance, and stated evidence limits and is committed. |
| AC-11 | `artifacts/site/` is generated only from reviewed results and templates. It is not the canonical saved result and is not committed. |

## Out of scope

- Selecting Python, Node.js, or another application stack.
- Defining package APIs, a command-line interface, or result schemas.
- Defining prompt or result file formats before their contracts are agreed.
- Copying the full Agent Safe POC, records, browser profiles, credentials, or binaries.
- Starting DSH, Agent Safe, live agents, fixtures, background queues, or experiments.
- Creating a hosted service, account system, or leaderboard. Static build behavior
  is defined in the reproduction and publishing specification.

## Decisions

- Keep the existing `AGENTS.md` and one canonical `skills/` tree.
- Use the `arena-` namespace for repository task skills.
- Organize scenarios by stable scenario identifier. Store the evaluation track in
  scenario metadata instead of encoding it in the directory hierarchy.
- Keep versioned base and Agent-specific prompt variants with the scenario.
  Separate development revisions from frozen prompts used in formal runs.
- Keep agent decisions and environment enforcement in separate profiles,
  adapters, assessments, and report fields.
- Use one common runner. Do not create one execution script per case.
- Treat `migration/agent-safe-poc/` as temporary provenance-preserving staging.
- Keep raw private run evidence, committed reviewed results, and generated sites
  in three separate locations.
- Commit reviewed result metadata, edited display MP4 files, and selected public
  screenshots under `results/`. Do not commit raw recordings.
- Add planned directories only when the project adds their first reviewed file.

The maintained runner uses the Python stack in ADR 0002 and the DSH recording
adapter in ADR 0003. New interfaces still require a specification before code.

## Tests

| Criteria | Required evidence |
| --- | --- |
| AC-1 | List `skills/*/SKILL.md`; compare names, directories, `AGENTS.md`, and `skills/README.md`; search for the retired namespace. |
| AC-2, AC-3, AC-5, and AC-6 | Review each new file against this ownership table and reject duplicated lifecycle, prompt, or mixed Agent/environment responsibilities. |
| AC-4 | Verify that each frozen prompt references a base and development record. Compare actual prompt bytes and SHA256 values across environments in the same formal comparison. |
| AC-7 and AC-8 | Record source hashes, imports, file dependencies, fixed paths, platform limits, extraction work, and removal plans before staging a source file. |
| AC-9 | Use deterministic synthetic completed and incomplete results to verify separate task, agent, approval, effect, enforcement, and evidence outcomes. |
| AC-10 | Check Git ignore rules and result contents. Confirm that raw recordings remain untracked and edited public media is present under the reviewed result. |
| AC-11 | Generate a site from reviewed results without reading raw run evidence. Check local links and confirm that no private artifact is exported. |

The files under `migration/agent-safe-poc/legacy/` remain temporary reference
sources, not runtime dependencies. Maintained code is under `src/arena/`.
Use the reproduction specification for installation and static-build tests.
