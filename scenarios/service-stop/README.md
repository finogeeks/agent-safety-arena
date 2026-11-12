# Service stop


## Authored candidates

The [en-v1 candidate](case.en-v1.json) submits the English SYS-form text prompt.
The host writes `target.json` after the fixture is visible. Historical imported
prompts stay unchanged.

The [python-file-v2 candidate](case.python-file-v2.json) and
[WorkBuddy suite](reproduction/python-file-v2-workbuddy.json) stage a fixed
Python worker. The evaluated Agent runs that unchanged file.

| Artifact | Use |
| --- | --- |
| [Text prompt](prompts/base/en-v1.md) | English SYS-form request: read target.json and call the named APIs. |
| [Generation prompt](prompts/base/generate-python-v1.md) | Generate and save the Python script. |
| [Execution prompt](prompts/base/python-file-v2.md) | Run the saved script unchanged. |
| [Fixed Python script](input/service-stop.py) | Freeze the implementation for repeated executions. |
| [Service-status display](input/service-status-display.ps1) | Host observer starts owned ArenaStopSvc. Shows RUNNING/STOPPED. White while running; red after it is ended. |

Checks are described in the [system saved-program specification](../../docs/system-python-programs.md).
This revision has no recorded trial yet.

## Scope

Assess the service stop scenario using an owned, disposable fixture and independent observations.

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
| SYS-18 | adopted-source-case-snapshot | [imported-v1.md](prompts/agents/dsh/frozen/imported-v1.md) |
| H05-service-stop | historical-collection-entry; annotations retained; not a new result | [imported-r2.md](prompts/agents/dsh/development/imported-r2.md) |
| H05-service-stop | historical-submission; comparison acceptance unknown | [imported-r3.md](prompts/agents/dsh/development/imported-r3.md) |

[Development record](prompts/agents/dsh/development/r1.md) ·
[Source conditions and hashes](prompt-provenance.json) ·
[Case index](../README.md)

Historical approval text does not authorize a future run. Freeze new comparison
conditions explicitly. Source results and missing observations remain historical;
this migration does not establish a successful Arena comparison.
