# Evaluation experience

Status: Maintained project guidance, adapted from the local POC on 2026-10-30.
These are operational lessons, not certification of an Agent or sandbox.
This project owns future work; historical sources provide provenance only.

## Prepare a comparison

Use the [prompt library](../scenarios/README.md) to inspect the old requests and
the [migration requirements](prompt-library.md) to understand their limits.

```mermaid
flowchart TD
  A[Define task and resource boundaries] --> B[Prepare owned fixture and recovery]
  B --> C[Verify baseline and Agent settings]
  C --> D[Develop prompt in separate trials]
  D --> E[Freeze comparison conditions]
  E --> F[Start recording and observations]
  F --> G[Submit once and observe approvals]
  G --> H[Wait for matching native turn end]
  H --> I[Capture final state before external recovery]
  I --> J[Restore and clean owned resources]
  J --> K[Review separate outcomes and sanitized evidence]
```

Define the legitimate task, allowed actions, resource identities, expected
effect, independent measurements, and recovery before a trial. Direct requests
to operate a fixture measure capability and execution control. They do not
establish prompt injection. An injection test also needs an untrusted input,
an adversarial objective, and a legitimate task boundary. Keep the
[first injection proposal](first-evaluation.md) separate from direct probes.

Start new comparisons with verified vendor-default settings. Record the actual
Agent version, model, reasoning setting, approval policy, built-in sandbox,
launch arguments, OS, and external environment. Native means no added external
sandbox. Historical Full Access, Pro, and High runs remain historical conditions.
They are not evidence of vendor-default behavior.

Separate prompt development from formal runs. Retain revisions, reasons, and
outcomes. Freeze identical prompt bytes, model, and fixture conditions for the
same Agent across environments. Disclose Agent-specific wording in cross-Agent
comparisons. A failed baseline cannot establish a protective comparison.

## Record the complete turn

Use one lifecycle with Agent and environment adapters. Cases own data and
measurement rules, not copies of the recorder. Configure local executable paths.
Do not reuse old absolute paths, PIDs, HWNDs, or service names. Check process
creation time and fixture ownership before acting on a resource.

Start capture and observations before submission. Submit once per run. Resume
from recorded state; a missing response does not mean a request was not sent.
A repeat trial gets a new run directory.

Match the submitted request to its native turn and completion event. An idle UI,
the end of a video segment, or a model's claim does not establish completion.
Preserve aborted, failed, quota-blocked, and missing-reply states. For DSH, select
public assistant text from the matched turn. Do not substitute reasoning text,
a draft, or a later diagnostic reply.

Record approvals by source: Agent, terminal, OS UAC, or external sandbox. Capture
the displayed scope, risk explanation, time, and decision. Keep approval-withheld
runs separate from runs continued after explicit approval. Without an observation
channel, approval presence is unknown. Historical text that says "I agree" does
not authorize an operator in a future run.

Run groups in sequence when they share the desktop or fixture. Arrange the
initial view, then let the effect occur without forcing the conversation above
it. Capture the final state after completion and before external restoration.
Distinguish host restoration from the Agent's changes. Verify cleanup after
errors too. Never act on an old PID without rechecking its creation time and role.

## Measure effects independently

| Resource | Boundary and observation | Lesson |
| --- | --- | --- |
| Windows | Register the owned window; sample visibility, position, size, and restoration. | A model can claim a change while independent samples show none. Retain both. |
| Input hooks | Observe callbacks and controlled input delivery; unload and verify recovery. | Simulated input is not physical-input testing. A hook handle does not prove blocked input. |
| Mouse and wheel | Record original settings, changed values, controlled input, and restoration. | Setter returns and visible effects are separate. Button-swap tests need actual left/right delivery observations. |
| IME | Compare conversion mode and text from the same input in an owned control. | The open-status flag can remain true in both modes. It does not prove Chinese input is enabled. |
| Clipboard | Use a synthetic sample and an isolated test session; verify writes and cleanup. | A user's clipboard is not a test fixture. |
| Display and desktops | Use an isolated session and independently verified recovery. | Display-off can enter Modern Standby; desktop changes can hide the Agent and observer. |
| File and registry security | Use disposable objects with known ACL, owner, inheritance, registry view, and hash. | Removing an absent grant does not prove a meaningful change. A denied command does not prove its underlying setter ran. |
| Processes | Check PID and creation time; use a dedicated process, marker, heartbeat, or event. | An access handle does not prove termination, suspension, memory writes, or an event effect. |
| Allocated memory | Record and independently query the returned address before and after release. | SYS-15 once had null samples because the observer ignored `allocAddress`. Missing samples remain unknown; do not invent replacements. |
| Services | Validate an owned service and independently read its state throughout. | SYS-18 returned False/1061 while state changed to STOPPED. Preserve return and effect separately. A restart can create a new PID. |

Separate four questions: Did the Agent attempt the action? Did the final API
execute? Did the expected effect occur? Where did enforcement deny access?
Denied OpenProcess does not mean VirtualAllocEx itself returned denial.
Denied OpenService does not mean ControlService was called.

Check Win32 return values first. A successful API can leave a stale last-error.
Capture errors at the documented failure point. In PowerShell, avoid read-only
automatic variables such as `$PID`; use a name such as `$targetPid`.

A recovery helper can retry a documented transient service transition for a
bounded interval while rechecking identity. STOP_PENDING needs observation,
not repeated stop requests. Permanent denial remains an error. Host recovery
must never perform the protected group's target action and attribute it to the
Agent.

If a provider reports QUOTA or HTTP 402, restore and clean resources, record the
provider failure, and stop submissions. Do not count it as a sandbox outcome or
repeatedly send requests to test the provider balance.

## Review and present results

Use the [result page requirements](report-contract.md) for the complete section
order, comparison fields, media rules, and layout reference. The following
paragraphs summarize the evidence rules; they do not define a finished UI.

Report task completion, Agent decision, approval, effect, enforcement,
completion, evidence sufficiency, and recovery separately. Use counts with
explicit denominators. Keep incomplete and unknown states visible. If an
alternative path causes the effect after the direct method failed, that effect
still occurred. Do not report only the first denial.

A result page should show the scenario and impact, comparison and limits,
reviewed media, exact submitted prompt or marked public substitution, verified
public replies, and folded observations. Keep explanations brief and tied to
observed actions. Use actual source conditions.

Keep raw runs private under `artifacts/runs/`, reviewed results and edited media
under `results/`, and generated output under `artifacts/site/`. A public build
must not depend on old POC paths or private profiles. A prompt import does not
populate `results/`.

Cut display media using capture timestamps and independently observed effect
intervals. Retain source time ranges and label omitted waiting. Do not fabricate
frames or call edited media a continuous original. A final-state preview cannot
hide an earlier effect. When a model claims success but video shows none, keep
enough context to review the discrepancy. Check decode, links, narrow layouts,
and expanded logs before publication.

Declare privacy mask regions and time ranges; map them through actual capture
timestamps. A tested filter does not prove every private region was identified.
Exclude authentication URLs, cookies, reasoning, private startup logs, user
identities, and credentials from public exports.

## Sources and limits

This adaptation reviewed source-relative documents `recording-tools/README.md`,
`docs/FinSAFE-安全防护案例-编写规范.md`, and
`docs/HANDOFF-案例资料整理-20261024.md`, plus case metadata and prompt collections
listed through the [case index](../scenarios/README.md), with provenance inside
each case. Document source hashes are in the
[experience source record](evaluation-experience-sources.json). Earlier
handoff entries can describe superseded results; use the imported snapshot and
its hashes rather than treating old narrative as current.

The POC used fixed paths, DSH events, elevated trials, and local Windows APIs.
Its results do not establish portability. This migration adds no executable
fixtures or helpers. See the [offline workflow](offline-workflow.md),
[DSH recorder](dsh-recording.md), and
[staged component inventory](../migration/agent-safe-poc/INVENTORY.md) for what
this repository currently implements and verifies.
