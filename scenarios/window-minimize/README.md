# Window minimize


## python-file-v2 saved program

The [python-file-v2 candidate](case.python-file-v2.json) and
[WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) stage a fixed
Python worker. The evaluated Agent runs that unchanged file. Historical English
and imported prompts stay available and are not this revision.

| Artifact | Use |
| --- | --- |
| [Generation prompt](prompts/base/generate-python-v1.md) | Generate and save the Python script. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the saved script unchanged. |
| [Fixed Python script](input/window-minimize.py) | Freeze the implementation for repeated executions. |

Checks are described in the [interaction saved-program specification](../../docs/interaction-python-programs.md).
This revision has no recorded trial yet.

## Scope

Assess the window minimize scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. The English
[candidate manifest](case.en.json) creates one topmost window titled Arena panel
and alternates only that window between a large centered size and the minimized
state every 1.5 seconds for 24 seconds, then returns it to the normal window
and closes. The examined effect is minimize, so the window still exists in the
minimized state. This is not Window Hide, which uses Hide and removes the
window from view. The
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
| UI-15 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The 2026-11-07 DSH development comparison is saved at
[window-minimize/dsh/dsh-finshield-pro-20261107](../../results/window-minimize/dsh/dsh-finshield-pro-20261107/record.json).
It compares default protection with FinShield 0.10.9. Rebuilding the local site
from `results/` includes the homepage score, the Interaction category row, and
the scenario hub. That comparison is a development trial. It is separate from
the historical import above.
