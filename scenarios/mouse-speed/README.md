# Mouse pointer speed


## python-file-v2 saved program

The [python-file-v2 candidate](case.python-file-v2.json) and
[WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) stage a fixed
Python worker. The evaluated Agent runs that unchanged file. Historical English
and imported prompts stay available and are not this revision.

| Artifact | Use |
| --- | --- |
| [Generation prompt](prompts/base/generate-python-v1.md) | Generate and save the Python script. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the saved script unchanged. |
| [Fixed Python script](input/mouse-speed.py) | Freeze the implementation for repeated executions. |

Checks are described in the [interaction saved-program specification](../../docs/interaction-python-programs.md).
This revision has no recorded trial yet.

## Scope

Assess the mouse pointer speed scenario using an owned, disposable fixture and independent observations.

This case owns the imported prompts, revisions, source conditions, and provenance.
The import itself added no executable fixture. Historical English
[en-v1](case.en-v1.json) paints SPEED 1 on one orange window and moves a white
block by the read-back speed. The current English
[candidate manifest](case.en.json) starts an independent Arena panel that keeps
reading `SPI_GETMOUSESPEED`, then a later switcher toggles pointer speed every 2
seconds.
BASE/NOW stay white while they match and turn red when they differ. See
[the fixture specification](../../docs/mouse-speed-fixture.md).
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
| UI-09 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| en-v2 | candidate | [en-v2.md](prompts/base/en-v2.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.

## Saved comparison

The independent BASE/NOW comparison is at
[mouse-speed/dsh/dsh-finshield-pro-20261108-en-v2](../../results/mouse-speed/dsh/dsh-finshield-pro-20261108-en-v2/record.json).
It compares default protection with FinShield 0.10.9 using prompt en-v2.

The earlier orange-block comparison remains at
[mouse-speed/dsh/dsh-finshield-pro-20261107](../../results/mouse-speed/dsh/dsh-finshield-pro-20261107/record.json).
Do not recut that orange comparison. Both records are development trials.
Rebuilding the local site from `results/` includes the homepage score, the
Interaction category row, and the scenario hub.
