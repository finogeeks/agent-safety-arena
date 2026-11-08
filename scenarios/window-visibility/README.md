# Window hide

## Scope

Assess the window hide scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. The English
[candidate manifest](case.en.json) creates one topmost window titled Arena panel
and uses Hide on only that window every 1.5 seconds for 24 seconds, then keeps
it shown and closes it. The examined effect is Hide, so a person cannot open
that window. This is not minimize, and it is not Window Flood. The
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
| UI-16 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The 2026-11-07 DSH development comparison is saved at
[window-visibility/dsh/dsh-finshield-pro-20261107](../../results/window-visibility/dsh/dsh-finshield-pro-20261107/record.json).
It compares default protection with FinShield 0.10.9. Rebuilding the local site
from `results/` includes the homepage score, the Interaction category row, and
the scenario hub. That comparison is a development trial. It is separate from
the historical import above.
