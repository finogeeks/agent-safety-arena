# ADR 0003: Record the real DSH Web interface

Status: Accepted on 2026-10-28 for revised Issue #6.

## Context

The user selected DSH as the Agent under test. Codex operates Arena. The first
workflow must record the real DSH page and native default-sandbox confirmations.
The installed local POC demonstrates loopback RPC and a dedicated Chrome view.
The installed DSH is 0.2.1-rc.2. Python 3.12, Node 24.22.1, Chrome, and FFmpeg
7.1 with `gdigrab` are available on this host.

## Decision

Use Python standard-library orchestration and HTTP RPC. Use one small Node
helper with the built-in WebSocket client for Chrome DevTools operations.
Launch an owned DSH Web process and a temporary Chrome profile. Use FFmpeg for
encoding of Chrome viewport frames by default, and `gdigrab` for an explicitly
selected desktop rectangle. GDI window capture produced black video on this
host and is not used for the default. Chrome screenshots preserve unmodified
DSH confirmation panels. Select a real blank conversation in DSH, preserve its defaults, submit
one prompt, and match the request and native turn end using HTTP session pages.
The helper observes clicks without suppressing or replaying them.

Keep every trial private and separate. Generate a review form and a Markdown
analysis from evidence. Do not couple this workflow to the offline evaluator.
Executable paths are configurable; no machine-specific path is a runtime
default. Installed DSH code and the external POC remain read-only references.

## Consequences

- There is no new Python package dependency or copied POC runtime.
- Chrome DevTools access is restricted to the newly created browser profile.
- DSH API and DOM contracts are version-specific and must fail clearly when
  they change.
- The operator handles all native confirmations. Fast answers can cause
  screenshot gaps, which remain explicit in the run evidence.
- Desktop video may contain unrelated visible content; keep it private and
  arrange the selected recording region before submission.
- Recording does not establish sandbox enforcement or a hazardous effect.
