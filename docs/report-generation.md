# Generate reports with a fixed layout

Status: Accepted on 2026-11-06 for reusable report preparation.

## Problem

All cases need the same page structure. Editing a generated page or putting a
case conclusion in Python makes later reports inconsistent.

## Behavior

| Fixed in shared code and procedure | Generated from each case's evidence |
| --- | --- |
| Six sections and their order | Case explanation and possible user impact |
| Default protection / FinShield protection columns | Actual versions, settings, dates, and one-line observations |
| One side-by-side overview GIF; two videos below | Reviewed media paths and timing provenance |
| Interception first, then timely warning if unblocked | Reviewed target-effect result and warning assessment |
| Short information icons and expandable evidence | Applicable default-setting and Full Access notes |
| Original-text and evidence controls | Original prompt, replies, tool records, reproduction steps |

```mermaid
flowchart LR
  C[Case and completed evidence] --> A[Agent drafts structured content]
  A --> R[Independent outcome and warning review]
  R --> J[Canonical reviewed record JSON]
  J --> V[Shared validation and fixed renderer]
  V --> S[Staged page and media]
  S --> Q[Content, links and visual checks]
  Q --> O[Local preview update with backup]
```

Use [arena-write-report](../skills/arena-write-report/SKILL.md) and the
[English authoring prompt](../templates/report-authoring-prompt.md). Follow the
content and assessment rules in [report-contract.md](report-contract.md).
Define the target effect and observation boundary before new collection. If a
criterion changes after collection, identify the revision and retain the earlier
review. Do not relabel development evidence as a formal result.

The Agent writes content into the reviewed `record.json`. It must preserve the
configured layout, column roles, section order, and shared CSS. It may not
redesign HTML, change a grade to satisfy a desired conclusion, or replace source
tool results. Case-specific statements belong in the record, not in shared code.
Changing reviewed content is a separate step from rendering a page.

The shared renderer keeps legacy-record compatibility. New comparison reports
use the fixed `comparison-v1` dense presentation and the overview slot described
in the contract. Missing media or evidence stays explicitly missing. Layout
changes require an operator request and shared template updates.

Run the reusable wrapper from a clone after bootstrap:

```powershell
.\scripts\export-report.ps1 -Record '<reviewed-record.json>' -Output 'artifacts/site/<report-id>'
.\scripts\export-report.ps1 -Record '<reviewed-record.json>' -Output 'artifacts/site/<report-id>' -Update
```

Replace the example placeholders. The first command creates a report. The second
regenerates an existing local report from reviewed inputs. The wrapper invokes
`arena report` in a fresh staging directory; it never edits the input record.
An update requires an existing comparison export with matching scenario and
Agent identities. It backs up the previous export under ignored `.tools/`, then
copies staged output. Existing unreferenced public media is retained. Invalid
input fails before the old page changes. Output must be below `artifacts/site/`.
No trial, product launch, or external publication occurs.

| ID | Acceptance criterion |
| --- | --- |
| AC-1 | A second synthetic case and Agent use the same layout with their own text, criterion, versions, and assessments. |
| AC-2 | Generated output retains original evidence and contains no wording copied from an unrelated case. |
| AC-3 | Export/update leaves the source record bytes unchanged, retains a backup, and rejects invalid or mismatched inputs before replacing files. |
| AC-4 | The authoring skill, prompt, indexes, and exporter identify one shared flow and do not require an ignored case-specific script. |

## Out of scope

Live collection, automatic generation of evidence, automatic success judgments,
product installation, and production publication.

## Decisions

Keep layout in the shared renderer, generation instructions in the canonical
skill/prompt, and reviewed case content in result JSON. Use a parameterized
PowerShell wrapper for repeated local preview updates.

## Tests

Run offline regression coverage for another case/Agent, missing evidence,
assessment rules, original text, and media. Verify the wrapper on a current
reviewed record, compare input hashes, and check backup preservation. Check
documentation links, skill indexes, and whitespace. No live trial is required.
