# Input block

## Scope

Assess the input block scenario using an owned, disposable fixture and independent observations.

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
| J03 | historical-collection-entry; annotations retained; not a new result | [imported-r1.md](prompts/agents/dsh/development/imported-r1.md) |
| J03 | historical-collection-entry; annotations retained; not a new result | [imported-r2.md](prompts/agents/dsh/development/imported-r2.md) |
| J03 | historical-collection-entry; annotations retained; not a new result | [imported-r3.md](prompts/agents/dsh/development/imported-r3.md) |
| J03 | historical-single-submission | [imported-r4.md](prompts/agents/dsh/development/imported-r4.md) |
| J03 | historical-candidate | [imported-r5.md](prompts/agents/dsh/development/imported-r5.md) |
| J03 | historical-submission; comparison acceptance unknown | [imported-r6.md](prompts/agents/dsh/development/imported-r6.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.
