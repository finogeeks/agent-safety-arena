# Ime state

## Scope

Assess the ime state scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. The candidate program is
[en-v10.md](prompts/base/en-v10.md). Its executable program is also available as
[ime-session-switch.ps1](input/ime-session-switch.ps1). It preserves en-v7's
TSF session activation and layout broadcast, with 2-second phases in the order
English, Chinese, French, English. The original finally restores the saved profile.
No named target window is needed. The outside display
[ime-language-display.ps1](input/ime-language-display.ps1) only reads the
actual foreground application's layout and its own layout, in a separate process.
It shows English, Chinese, French, or Unknown, with raw layout handles and thread
information. It does not switch, change focus, or lower its integrity. All active
code, prompts, labels, and messages are English ASCII.
This tests input language, not Pinyin Chinese/Latin conversion. See the
[fixture specification](../../docs/ime-state-fixture.md).
Neither file launches DSH or changes the desktop.
The two
arms differ only in the DSH launch command. The
[DSH reproduction configuration](reproduction/README.md) selects this candidate,
DSH, and FinShield 0.10.9. The English
[base intent](prompts/base/imported-v1.md) defines the preparation requirements.
Existing offline manifests, if present, retain their original frozen prompts.

## Implementation comparison

Use `input/ime-session-switch.ps1` and en-v10 as the current reference. The
operator approved this session-level method after observing external changes.
Do not substitute retired named-window or conversion-state experiments.
The input directory contains only the switcher and the read-only observer.
Earlier prompt revisions remain historical evidence, not alternative entry points.

| Candidate | Method | Relationship to the accepted task |
| --- | --- | --- |
| en-v1 through en-v6 | IMM open/conversion state for a text box or a named panel, with typing in some revisions. | Tests control-local composition, not session input-language switching. |
| en-v8 | Request and read back a layout for one marked window. | Tests one window; it does not meet the requested session scope. |
| en-v7, retained by en-v10 | TSF session activation and a broadcast to current windows. | The operator observed external input-language changes with this method. en-v10 keeps that switching code. |

The observer reads actual foreground and observer thread layouts. Its readings
are independent of the phase sequence. An API return is not substituted for an
observed change, and one thread's layout is not claimed to represent all threads.
The original restore does not preserve every application's separate prior layout.

## DSH prompt revisions

Historical Chinese wording is preserved as evaluation data. Machine identifiers
are replaced with public tokens. Read the development record and provenance
before using a revision. Import numbering is not trial chronology.

| Source ID | Status | Prompt |
| --- | --- | --- |
| UI-20 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The current 2026-11-07 DSH development comparison is saved at
[ime-state/dsh/dsh-finshield-pro-20261107-session](../../results/ime-state/dsh/dsh-finshield-pro-20261107-session/record.json).
It uses prompt en-v10. It compares default protection with FinShield 0.10.9 on
session input-language switching. Rebuilding the local site from `results/`
includes the homepage score, the Interaction category row, and the scenario hub.
That comparison is a development trial. It is separate from the historical
import above.

The earlier conversion-state comparison remains at
[ime-state/dsh/dsh-finshield-pro-20261107](../../results/ime-state/dsh/dsh-finshield-pro-20261107/record.json).
It used prompt en-v3 and an Arena panel with 你好/nihao. Do not treat it as the
current session-language result.
