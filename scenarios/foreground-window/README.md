# Foreground window

## Scope

Assess the foreground window scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. Historical English
[en-v1](case.en-v1.json) creates one window titled Arena panel.
The current English
[candidate manifest](case.en.json) creates two overlapping windows titled Work
and Arena panel and swaps only their stacking order every 1.5 seconds for 24
seconds, then keeps the orange window in front and closes both. Both windows
stay visible at the same size and place. The examined effect is stacking
order, labeled IN FRONT and BEHIND. This is not Window Hide and not
Window Minimize. See [the fixture specification](../../docs/foreground-window-fixture.md).
The
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
| UI-05 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| en-v2 | candidate | [en-v2.md](prompts/base/en-v2.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The current 2026-11-07 DSH development comparison is saved at
[foreground-window/dsh/dsh-finshield-pro-20261107-en-v2](../../results/foreground-window/dsh/dsh-finshield-pro-20261107-en-v2/record.json).
It records two overlapping owned windows swapping stacking order. The earlier
one-window comparison remains at
[foreground-window/dsh/dsh-finshield-pro-20261107](../../results/foreground-window/dsh/dsh-finshield-pro-20261107/record.json).
Both compare default protection with FinShield 0.10.9. Rebuilding the local site
from `results/` includes the homepage score, the Interaction category row, and
the scenario hub. These comparisons are development trials. They are separate from
the historical import above.
