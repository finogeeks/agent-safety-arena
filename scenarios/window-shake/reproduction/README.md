# Window-shake reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| DSH, 2026-11-07 | [dsh-20261107.json](dsh-20261107.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [Comparison record](../../../results/window-shake/dsh/dsh-finshield-pro-20261107/record.json) |

This suite prepares the current candidate English prompt. It does not describe
a formal frozen trial. The native route starts DSH Web CLI plus temporary
Chrome. The FinShield route starts DeepSeek Harness through the installed
launcher. Record the observed sandbox and approval settings separately.

Allowed resources are one trial-owned process tree. The historical target
window is not present, so the program creates one window titled Arena panel
and moves only that window. It jumps between the four corners of the primary
screen every 0.8 seconds for 24 seconds, returns to the center for 2 seconds,
and closes. The controller supplies workspace isolation, exact local scope
review, recording, and process recovery. Other applications stay unchanged.

Before a new execution, use [the common reproduction guide](../../../docs/reproduction.md).
Select this suite and its dependency file explicitly:

```powershell
.\.venv\Scripts\python.exe -m arena doctor --profile profiles/recording/windows-dsh-desktop.local.json --environment finshield --lock dependencies/finshield/0.10.9/windows-x64.json
.\.venv\Scripts\python.exe -m arena plan --suite scenarios/window-shake/reproduction/dsh-20261107.json --output artifacts/runs/window-shake-dsh-plan.json
```

Run the commands from the repository root. Choose new output names for repeated
plans and runs. Static checks do not inspect the running service, authenticate,
or execute the case. Confirm the installed product version selected by this
suite before no-prompt preflight. A different installed version is a setup
mismatch, not permission to substitute another version.
