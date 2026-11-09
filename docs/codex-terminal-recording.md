# Codex CLI terminal recording

Status: Accepted for the operator's Codex CLI window-flood development trial.

## Problem

The shared controller currently records only DSH. Codex needs its real interactive
terminal interface, default policies, original approvals, and a record of actual
effects. A noninteractive `exec` check cannot substitute for an interactive trial.

## Behavior

```mermaid
flowchart LR
  C[Existing case manifest and English prompt] --> R[Shared batch and trial controller]
  R --> A[Codex terminal adapter]
  D[Existing CLI defaults and model-only profile] --> A
  A --> S[Owned local Codex app server]
  S <--> P[Transparent loopback observation proxy]
  P <--> T[Actual Codex CLI terminal UI]
  T <--> V[Owned Windows Terminal window]
  V --> E[Desktop recording and original terminal evidence]
  S --> N[Codex native Windows sandbox]
  E --> X[Shared 5 plus 10 plus 5 second preview exporter]
```

Use the CLI's native terminal interface in Windows Terminal, as requested by the
operator. Do not add a browser terminal, replacement chat interface, or synthetic
approval panels. Read native console text and send console input to the owned
CLI process only. Use a unique temporary Windows Terminal fragment profile for
white appearance and large text; do not edit the user's default terminal profile.
Maximize the owned window on Desktop 1 and restore the operator desktop after
collection. There is no browser or translation control in this route.
If the operator switches desktops, suspend the owned recorder and wait without
answering approvals. Resume only on the declared desktop. Preserve interruption
times and mark recording continuity as incomplete; never capture another desktop
as if it were the trial. An operator stop file still ends the run.

The CLI's supported remote-terminal transport connects to an owned loopback
app server. A transparent proxy observes native requests and responses. It does
not answer approvals. Only the actual CLI's native one-time choice can answer an
approval, after capture and a recording checkpoint. This experimental transport
is disclosed in evidence. Neither native Agent process receives sandbox, approval,
instruction, tool, reasoning, search, or catalog overrides. The app server uses
the same existing base configuration and model-only connection settings.
The FinShield TUI sandbox flag is specified in
[Codex FinShield recording](codex-finshield-recording.md).

`arena collect-batch --case <case.json> --profile <profile.json>` shares
`collect_batch` and `run_trial` with DSH. Its optional `--preflight` records
presentation without submitting a prompt. Optional `--environment finshield`
selects the installed FinShield `self-confine` wrap of the owned app-server;
see [Codex FinShield recording](codex-finshield-recording.md). Recording profile
schema 2 selects `agent: "codex-cli"` and machine-local Node, launch
module/configuration, terminal, recorder, and desktop paths. Optional
`workspaceRoot` selects a policy-allowed parent for saved-program device cases
so the host observer can attach `.arena-device-local`. Optional `finshield` and
`finshieldConfig` name the installed FinShield files; the native route ignores
them. Omit `workspaceRoot` only when the case does not need that prepared
fixture. The case owns no execution script. Older DSH schema 1 and
commands remain supported.

Initialize only the declared synthetic workspace. If the CLI asks whether this
owned workspace is trusted, retain the original startup text and screenshot
before selecting its native trust choice. Record this setup separately from a
task approval. Do not mark startup trust as one-time command approval. Unmatched
startup screens stop before prompt submission.

Native conversation events are retained privately and mapped into the shared
collection event contract. Keep original native message types alongside the
normalized view. Do not log account/configuration responses or HTTP auth headers.
Credentials are resolved in the existing local launcher and stay in child memory.
The exact admitted prompt is saved separately if the native composer changes
trailing whitespace. No additional requests or prompt tuning occur during a run.

For a matched native command approval, save original terminal text, choices,
native request/command, screenshot, and video offset. A unique displayed one-time
choice and pending native request must match. Reuse the existing local command
scope review file. Missing frames, unmatched panels, changed text, and commands
outside the resource boundary remain unresolved and receive no automatic input.
Native long-command panels can show only a prefix. Retain the truncation marker
and full native command separately. Match one unique request by its exact visible
reason when the full command is not visible. Confirm the actual CLI response is
one-time `accept`, not a session-wide permission change.

For a captured panel, schedule its one-time choice five seconds after the first
matched screen observation. Capture and encode the pending panel during this
interval. Poll without a blocking delay. Do not restart the timer after a scope
grant arrives. If scope review takes longer, retain that factual delay; a timer
does not authorize an unknown command. Recheck the recording desktop before input.
The shared recording profile may set `approvalDelaySeconds` from 0 to 60;
the default is 5. Record the selected delay and the scheduled video offset.

Use the owned process Job Object for adapter recovery and observation. Disclose
that native sandbox service workers can have a different process boundary and
private Windows desktop. Do not attribute unrelated windows or kill shared
services. Record visible effects on the selected desktop separately from native
tool success and final claims. The requested windows must use synthetic test
text and close after the declared prompt duration. Native sandbox isolation stays active.

| ID | Acceptance criterion |
| --- | --- |
| T-1 | Real Codex interactive CLI output is displayed and recorded; no `exec` substitution. |
| T-2 | Launch arguments contain only model connection settings and required owned transport paths, with native default policies inherited. |
| T-3 | Preflight submits no prompt. The same shared trial lifecycle handles collection, completion, recording, and recovery. |
| T-4 | Native approval text and an encoded pending frame precede a scope-matched one-time CLI choice; unresolved evidence receives no approval. |
| T-5 | The original English case, terminal/native events, actual settings, effect observations, and recovery remain distinguishable. |
| T-6 | The shared preview exporter produces the requested 20-second excerpt with provenance; failures remain available. |

## Out of scope

Claude recording, AppSeam `app launch`, Codex suite planning, formal paired
conclusions, factory-reset CLI settings, warning scoring during collection, and
publication. FinShield `self-confine` of the owned app-server is specified in
[codex-finshield-recording.md](codex-finshield-recording.md).

## Decisions

Use the existing Windows desktop recorder and installed Windows Terminal.
Use the installed `ws` package for the transparent local observation bridge.
Record versions. The terminal and observation bridge are Agent adapters, not a second
case lifecycle. Keep suite routes pending until their condition planning and
recording contracts have been verified; this development batch route is explicit.

## Tests

Test native-event mapping, completion correlation, one-time panel matching,
rejection of session-wide choices, profile validation, no policy overrides,
preflight without submission, and preservation of existing DSH capture behavior.
Run a real no-prompt terminal preflight before the requested development trial.
Verify the final recording, shared preview, native settings, and recovery.

Verification on 2026-10-30:

- RED: `python -m unittest discover -s tests -p test_dsh_recording.py -k five_second`
  failed two timing assertions before implementation: collection blocked in
  `sleep(2)`, and a late grant retained `pending-review` status.
- RED: the native profile test rejected `approvalDelaySeconds` before support
  was added.
- GREEN: `python -m unittest discover -s tests` passed all 94 tests with the
  installed Node, Chrome, and FFmpeg enabled. No tests were skipped.
- VERIFY: 19 changed-document local links and seven canonical skill/index
  entries passed. `git diff --check` passed.
- LIVE: trial `codex-20261030T113812-e7de40ef` completed. Original capture and
  native one-time acceptance were recorded. A late scope grant caused 28.364
  seconds between screenshot completion and input, so the strict five-second
  live target remains unverified. The declared timer itself is covered by tests.

## References

- [Codex native remote terminal interface](https://learn.chatgpt.com/docs/app-server)
- [Codex default configuration and profiles](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [Existing shared lifecycle](dsh-batch.md)
- [Existing recording and review contract](dsh-recording.md)
