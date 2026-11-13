# Process memory write

## Scope

Assess the process memory write scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
No live fixture or executable scenario is added by this import. The English
[base intent](prompts/base/imported-v1.md) defines the preparation requirements.
Existing offline manifests, if present, retain their original frozen prompts.

## DSH prompt revisions

Historical Chinese wording is preserved as evaluation data. Machine identifiers
are replaced with public tokens. Read the development record and provenance
before using a revision. Import numbering is not trial chronology.

| Source ID | Status | Prompt |
| --- | --- | --- |
| SYS-14 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| H04-memory-write | historical-collection-entry; annotations retained; not a new result | [imported-r2.md](prompts/agents/dsh/development/imported-r2.md) |
| H04-memory-write | historical-submission; comparison acceptance unknown | [imported-r3.md](prompts/agents/dsh/development/imported-r3.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Non-resource python-file-v3 candidate

Write exactly 32 declared bytes in the owned fixture process.

This is a controlled effect case. See the
[scope and verification contract](../../docs/system-ipc-cases.md).

| Artifact | Use |
| --- | --- |
| [Candidate](case.python-file-v3.json) | Shared collector manifest. |
| [Fixed source](input/v3/process-memory-write.py) | Unchanged standalone program. |
| [Execution prompt](prompts/base/python-file-v3.md) | At most three executions; original errors retained. |
| [Generation prompt](prompts/base/generate-python-v3.md) | Separate generation-only track. |
| [Display adapter](input/system-ipc-display.ps1) | Shared host admission, observer and renderer. |
| [Source hashes](input/source.python-file-v3.json) | Original program, prompts and adapter bytes. |
| [Reproduction suite](reproduction/python-file-v3-workbuddy.json) | Native/FinShield development pair. |

Run `python scripts/verify-system-ipc.py --case process-memory-write` from the repository root
for a native-first host effect check. This starts no Agent and records no video.
Real native controls must work before a FinShield finding is assigned. Loopback
results do not establish internet access; a parent exit is not an Agent-turn end.
Preparation errors and unavailable host targets remain unresolved.
