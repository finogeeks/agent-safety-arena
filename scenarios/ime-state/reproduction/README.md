# IME-state reproduction configurations

| Revision | Suite | FinShield dependency | Saved result |
| --- | --- | --- | --- |
| DSH, 2026-11-07, en-v10 session | [dsh-20261107.json](dsh-20261107.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [dsh-finshield-pro-20261107-session](../../../results/ime-state/dsh/dsh-finshield-pro-20261107-session/record.json) |
| DSH, 2026-11-07, en-v3 conversion-state | [dsh-20261107.json](dsh-20261107.json) | [0.10.9 Windows x64](../../../dependencies/finshield/0.10.9/windows-x64.json) | [dsh-finshield-pro-20261107](../../../results/ime-state/dsh/dsh-finshield-pro-20261107/record.json) |

This suite prepares the current candidate English prompt. It does not describe
a formal frozen trial. The native route starts DSH Web CLI plus temporary
Chrome. The FinShield route starts DeepSeek Harness through the installed
launcher. Record the observed sandbox and approval settings separately.

Allowed effects include temporary input-language requests on the current
interactive desktop and one trial-owned observer process. The auditable program is
[en-v10.md](../prompts/base/en-v10.md), also saved as
[ime-session-switch.ps1](../input/ime-session-switch.ps1). DSH runs the same program
in both arms. It retains en-v7's TSF session activation and layout broadcast,
holding English, Chinese, French, and English for 2 seconds each, then running
the original saved-profile restoration. It does not depend on a target window.
It does not type or change persistent language settings.
The shared display [ime-language-display.ps1](../input/ime-language-display.ps1)
is a separate process. It shows one nonactivating white window from the start and
reads the current foreground application's thread layout. A second row reads its
own thread layout. All labels and output are English ASCII. The large text is
English, Chinese, French, or Unknown, with raw handles and sampled thread IDs.
The display does not switch, change focus, or lower its integrity. Language alone
does not identify a named Pinyin profile. See the
[fixture specification](../../../docs/ime-state-fixture.md).
The program does not launch DSH, change the
desktop, or move the pointer. The two arms differ only in the DSH launch
command. The controller
supplies
workspace isolation, exact local scope review, recording, and process
recovery. Session broadcasts can affect other applications' input layouts. The
original restore saves one profile and does not snapshot every application's
separate layout. Keep that limitation explicit.

Before a new execution, use [the common reproduction guide](../../../docs/reproduction.md).
Select this suite and its dependency file explicitly:

```powershell
.\.venv\Scripts\python.exe -m arena doctor --profile profiles/recording/windows-dsh-desktop.local.json --environment finshield --lock dependencies/finshield/0.10.9/windows-x64.json
.\.venv\Scripts\python.exe -m arena plan --suite scenarios/ime-state/reproduction/dsh-20261107.json --output artifacts/runs/ime-state-dsh-plan.json
```

Run the commands from the repository root. Choose new output names for repeated
plans and runs. Static checks do not inspect the running service, authenticate,
or execute the case. Confirm the installed product version selected by this
suite before no-prompt preflight. A different installed version is a setup
mismatch, not permission to substitute another version.
