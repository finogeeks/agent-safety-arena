# Process memory allocate

## Scope

Assess the process memory allocate scenario using an owned, disposable fixture and independent observations.

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
| SYS-15 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| SYS-15 | historical-development | [imported-r2.md](prompts/agents/dsh/development/imported-r2.md) |
| H04-memory-operation | historical-collection-entry; annotations retained; not a new result | [imported-r3.md](prompts/agents/dsh/development/imported-r3.md) |
| H04-memory-operation | historical-submission; comparison acceptance unknown | [imported-r4.md](prompts/agents/dsh/development/imported-r4.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.
