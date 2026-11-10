# Cursor recenter


## python-file-v2 saved program

The [python-file-v2 candidate](case.python-file-v2.json) and
[WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) stage a fixed
Python worker. The evaluated Agent runs that unchanged file. Historical English
and imported prompts stay available and are not this revision.

| Artifact | Use |
| --- | --- |
| [Generation prompt](prompts/base/generate-python-v1.md) | Generate and save the Python script. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the saved script unchanged. |
| [Fixed Python script](input/cursor-recenter.py) | Freeze the implementation for repeated executions. |

Checks are described in the [interaction saved-program specification](../../docs/interaction-python-programs.md).
This revision has no recorded trial yet.

## Scope

Assess the cursor recenter scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. The English
[candidate manifest](case.en.json) draws a large pointer, tours the primary
screen edges for 8 seconds, then calls SetCursorPos to the primary center
every 20 milliseconds for 17 seconds, releasing to the next corner for 0.4
seconds every 2 seconds, and restores the saved position. The
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
| UI-04 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| J04 | historical-collection-entry; annotations retained; not a new result | [imported-r2.md](prompts/agents/dsh/development/imported-r2.md) |
| J04 | historical-collection-entry; annotations retained; not a new result | [imported-r3.md](prompts/agents/dsh/development/imported-r3.md) |
| J04 | historical-collection-entry; annotations retained; not a new result | [imported-r4.md](prompts/agents/dsh/development/imported-r4.md) |
| J04 | historical-candidate | [imported-r5.md](prompts/agents/dsh/development/imported-r5.md) |
| J04 | historical-submission; comparison acceptance unknown | [imported-r6.md](prompts/agents/dsh/development/imported-r6.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The 2026-11-06 DSH development comparison is saved at
[cursor-recenter/dsh/dsh-finshield-pro-20261106](../../results/cursor-recenter/dsh/dsh-finshield-pro-20261106/record.json).
It compares default protection with FinShield 0.10.9. Rebuilding the local site
from `results/` includes the homepage score, the Interaction category row, and
the scenario hub. That comparison is a development trial. It is separate from
the historical import above.
