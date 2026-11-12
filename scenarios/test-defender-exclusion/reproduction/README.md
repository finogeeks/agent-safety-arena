# test-defender-exclusion reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| WorkBuddy, corrected python-file-v3 | [python-file-v3-workbuddy.json](python-file-v3-workbuddy.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | Host validation passed; Agent comparison not run |
| WorkBuddy, historical python-file-v2 | [python-file-v2-workbuddy.json](python-file-v2-workbuddy.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | Stored records require reassessment |

Use v3 for new saved-program collection. Preserve v2 sources and recordings;
its ABSENT panel does not establish prevention. V3 must first pass a host
positive control with successful modification and independent successful reads.
Read [the v3 specification](../../../docs/defender-exclusion-verification.md).

Each suite selects an explicit English prompt. It does not describe
a formal frozen trial. Allowed resources are one trial-owned process tree and,
where declared, one read-only observer panel. The evaluated Agent runs the
saved Python file unchanged. Historical imported prompts stay available and
are not this revision.

Before a new execution, use [the common reproduction guide](../../../docs/reproduction.md).
Select this suite and its dependency file explicitly.
