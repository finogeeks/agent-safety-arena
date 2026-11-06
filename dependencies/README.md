# External dependencies

[Common tools](runtime.json) describe capabilities. Cases select product versions
through their reproduction suites and version-specific dependency files.
There is no repository-wide FinShield version or `latest` alias.

For new and existing case recordings, the Agent follows the
[recording standard](../docs/recording-standard.md). Inspect and reuse compatible
installed programs before acquiring missing dependencies. Record actual paths,
versions, acquisition/verification commands and gaps privately with the run;
machine paths do not belong in these portable requirements.

| Dependency file | Use |
| --- | --- |
| [FinShield 0.10.9, Windows x64](finshield/0.10.9/windows-x64.json) | Installed-file baseline for the 2026-11-05 window-flood comparison. |

FinShield source and installers remain external. Keep downloaded installers in
ignored `.tools/`. Install the version selected by the case, using the product's
documented procedure. Do not substitute a newer installed version. A host may
need a separate prepared machine or VM for a different service version; storing
two executable directories does not establish which service is running.

The saved 0.10.9 executable and runtime hashes were measured from the current
host. The installer URL and installer SHA-256 have not been supplied. Automatic
product download and a verified fresh-machine installation are therefore not
available yet. Do not infer an installer checksum from an installed executable.

When an installer is made available, record its immutable version-specific
source and SHA-256 here before adding download automation. Preserve an existing
dependency baseline when adding another product version or platform.

See [reproduction and publishing](../docs/reproduction-and-publishing.md) for the
checks and [the DSH case reproduction notes](../scenarios/window-flood/reproduction/README.md)
for the first selected version.
