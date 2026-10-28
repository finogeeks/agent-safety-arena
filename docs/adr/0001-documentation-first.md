# ADR 0001: Initialize documents and collaboration procedures first

Status: Accepted for repository initialization.

## Context

agent-safety-arena is a new repository for evaluating AI agent safety and
sandbox security. The user requested initial documents and collaboration
rules based on groundwork. No target agent, runtime, or implementation stack
has been agreed.

## Decision

- Adapt groundwork's `AGENTS.md` and seven task skills, with one canonical
  skill tree under `skills/`.
- Record the project purpose in `README.md` and the first evaluation proposal
  in `docs/first-evaluation.md`.
- Keep the first evaluation as a draft until its open questions are resolved.
- Defer application code, dependencies, CI, deployment configuration, and stack
  selection until the agreed specification requires them.

## Consequences

Developers and agents can start from explicit project context and a common
specification, testing, and review workflow. The repository cannot run an
evaluation yet. The next implementation task must settle the first scenario,
record a stack decision, and verify the toolchain before adding application code.

The template source and revision are recorded in the repository
[README.md](../../README.md#template-source).
