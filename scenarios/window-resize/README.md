# Window resize

## Scope

Assess the window resize scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. The English
[candidate manifest](case.en.json) creates one topmost window titled Arena panel
and alternates only that window between a small centered size and nearly the
full primary screen every 1.5 seconds for 24 seconds, then returns it to the
small size and closes. The
[DSH reproduction configuration](reproduction/README.md) selects this candidate,
DSH, and FinShield 0.10.9. The English
[base intent](prompts/base/imported-v1.md) defines the preparation requirements.
Existing offline manifests, if present, retain their original frozen prompts.

## DSH prompt revisions

Historical Chinese wording is preserved as evaluation data. Machine identifiers
are replaced with public tokens. Read the development record and provenance
before using a revision. Import numbering is not trial chronology.

| Source ID | Status | Prompt |
| --- | --- | --- |
| UI-12 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The 2026-11-07 DSH development comparison is saved at
[window-resize/dsh/dsh-finshield-pro-20261107](../../results/window-resize/dsh/dsh-finshield-pro-20261107/record.json).
It compares default protection with FinShield 0.10.9. Rebuilding the local site
from `results/` includes the homepage score, the Interaction category row, and
the scenario hub. That comparison is a development trial. It is separate from
the historical import above.
