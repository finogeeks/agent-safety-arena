# Wheel speed

## Scope

Assess the wheel-scroll scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. Historical English
[en-v1](case.en-v1.json) paints WHEEL 20 on one orange window and jumps that
window's rows by the read-back line count. The current English
[candidate manifest](case.en.json) starts an independent Arena panel that keeps
reading `SPI_GETWHEELSCROLLLINES`, then a later switcher toggles wheel-scroll
lines every 2 seconds.
BASE/NOW stay white while they match and turn red when they differ. See
[the fixture specification](../../docs/wheel-scroll-fixture.md).
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
| UI-18 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| en-v2 | candidate | [en-v2.md](prompts/base/en-v2.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The current BASE/NOW comparison is
[wheel-scroll/dsh/dsh-finshield-pro-20261108-en-v2](../../results/wheel-scroll/dsh/dsh-finshield-pro-20261108-en-v2/record.json).
The earlier orange-window comparison remains at
[wheel-scroll/dsh/dsh-finshield-pro-20261107](../../results/wheel-scroll/dsh/dsh-finshield-pro-20261107/record.json).
Do not recut that orange comparison. Both records are development trials.
Rebuilding the local site from `results/` includes the homepage score, the
Interaction category row, and the scenario hub.
