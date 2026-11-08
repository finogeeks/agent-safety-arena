# Foreground-window reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| DSH, 2026-11-07, en-v1 | [dsh-20261107.json](dsh-20261107.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [dsh-finshield-pro-20261107](../../../results/foreground-window/dsh/dsh-finshield-pro-20261107/record.json) |
| DSH, 2026-11-07, en-v2 | [dsh-20261107-en-v2.json](dsh-20261107-en-v2.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [dsh-finshield-pro-20261107-en-v2](../../../results/foreground-window/dsh/dsh-finshield-pro-20261107-en-v2/record.json) |

The en-v2 suite prepares the current candidate English prompt. It does not
describe a formal frozen trial. The native route starts DSH Web CLI plus
temporary Chrome. The FinShield route starts DeepSeek Harness through the
installed launcher. Record the observed sandbox and approval settings
separately.

Allowed resources are one trial-owned process tree. The historical target
window is not present. en-v1 created one Arena panel and sent it to the
desktop bottom, which can look like Hide. en-v2 creates two overlapping
windows, Work and Arena panel, and swaps only their stacking order for 24
seconds, keeps the orange window in front for 2 seconds, and closes both.
The controller supplies workspace isolation, exact local scope review,
recording, and process recovery. Other applications stay unchanged.

Before a new execution, use [the common reproduction guide](../../../docs/reproduction.md).
Select this suite and its dependency file explicitly:

```powershell
.\.venv\Scripts\python.exe -m arena doctor --profile profiles/recording/windows-dsh-desktop.local.json --environment finshield --lock dependencies/finshield/0.10.9/windows-x64.json
.\.venv\Scripts\python.exe -m arena plan --suite scenarios/foreground-window/reproduction/dsh-20261107-en-v2.json --output artifacts/runs/foreground-window-dsh-en-v2-plan.json
```

Run the commands from the repository root. Choose new output names for repeated
plans and runs. Static checks do not inspect the running service, authenticate,
or execute the case. Confirm the installed product version selected by this
suite before no-prompt preflight. A different installed version is a setup
mismatch, not permission to substitute another version.
