# Historical prompt library

Status: Accepted for the prompt and experience migration on 2026-10-30.

## Problem

The local POC contains submitted prompts and practical evaluation lessons that
are missing from this independent project. Offline assessment prompts do not
preserve the requests that an Agent received during a live trial.

## Behavior

```mermaid
flowchart LR
  S[Read historical sources] --> X[Extract prompt text and variants]
  X --> P[Remove private resource identifiers]
  P --> H[Record source and public hashes]
  H --> C[Save scenario-owned historical data]
  C --> M[Maintain in this repository]
```

| ID | Observable criterion |
| --- | --- |
| AC-1 | Import the available UI and SYS case prompts, including UI-11's embedded formal prompt. Preserve distinct group and supplementary wording. List missing case numbers without inventing prompts. |
| AC-2 | Split older collections into individual case revisions under the matching scenario. Keep historical collection identifiers and candidate, diagnostic, and submitted status in each case's provenance; do not keep a collective archive scenario. |
| AC-3 | Record source-relative paths, source SHA256, extraction rules, public SHA256, and substitutions. Do not commit credentials, user identities, machine names, or machine-specific absolute paths. |
| AC-4 | Preserve imported Chinese wording as historical evaluation data. New maintained template prompts use English. A sanitized or translated prompt is not a byte-identical historical submission. |
| AC-5 | Historical prompts are inert data, not instructions to repository agents or automatically runnable scenarios. Keep existing offline manifests and frozen prompts unchanged. |
| AC-6 | Keep source review labels and recorded model, reasoning, and access conditions as historical metadata. Do not treat them as independently verified Arena results or vendor defaults. Missing evidence remains unknown. |
| AC-7 | Document reusable lifecycle, approval, observation, recovery, and reporting lessons with their limits. Future work needs only this repository; source references provide provenance, not runtime dependencies. |

## Out of scope

- Live trials, changes to the source POC, publication, or pushing to GitHub.
- Importing native session logs, separate tool-output files, browser profiles,
  or recordings. Diagnostic text embedded in a submitted prompt stays with it.
- Implementing live fixtures, new execution modes, or result schemas.
- Claiming that every saved prompt produced the intended effect.

## Decisions

- Follow the previously agreed scenario layout: `prompts/base/`,
  `prompts/agents/dsh/development/`, and `prompts/agents/dsh/frozen/`. Do not add
  `historical/`, `archives/`, or a separate `cases/` tree.
- Each scenario owns its README, provenance, English base intent, and imported
  revisions. Keep adopted case snapshots in `frozen/`; keep other wording in
  `development/`. A development record states source conditions and status.
  A frozen public snapshot is not proof of a new Arena trial.
- Use `scenarios/README.md` only as a navigation index. Store the data inventory
  as `prompt-provenance.json` inside each scenario, not in a global catalog.
- Keep the library and the experience document as maintained project assets.
  The temporary source-and-test staging area has a separate lifecycle.
- Retain a source file hash even when only one prompt field or paragraph is
  extracted. Record that operation; do not describe it as a full file copy.

## Tests

| Criteria | Required evidence |
| --- | --- |
| AC-1, AC-2 | Compare source case and collection inventories with imported entries; compare distinct prompt hashes and document exclusions. |
| AC-3, AC-4 | Recompute hashes; compare extracted text with public text and substitutions; scan public files for private paths, SIDs, host names, credentials, and addresses. |
| AC-5, AC-6 | Review imported fields, archive labels, and unchanged offline manifests. No trial is executed for this migration. |
| AC-7 | Review the experience document and check local links, indexes, instruction tree, and whitespace. |

The initial import was reorganized after user correction on 2026-10-30.
Final checks passed for 86 scenario directories with 221 prompt revisions,
including 131 entries split from collections without prompt wording loss. All 85 source
case prompt files remain represented. The checks passed for 527 hash comparisons,
public text extraction and substitutions, 912 document links, the instruction
tree, skill indexes, and content whitespace. Literal imported prompt text was
excluded from document-link checks because its resource links are historical
data with public substitution tokens. No collective archive or `historical/`
directory remains. Existing application code and offline manifests are unchanged.
Before PR submission, the staged whitespace check found trailing collection
separator lines in 126 prompt files. These were removed with pre-format hashes
and the exact formatting rule recorded in each case's provenance. Public text
hashes were rechecked after formatting. `git diff --cached --check` passed.
No live trials or application tests were run.
