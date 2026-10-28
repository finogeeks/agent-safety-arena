---
name: groundwork-workspace
description: >-
  Maps the project, discovers task skills, and guides initialization. Use on
  the first session or when a user asks how to start this repository.
---

# Orient in the project

Follow the communication and documentation rules in `AGENTS.md`.

This repository uses the groundwork collaboration template. Read `README.md`
for the current project purpose. Select the application stack from its requirements.

## Start

1. Read `AGENTS.md`, `README.md`, and `skills/README.md`.
2. List `skills/*/SKILL.md`. Read each name and description.
3. Load skills that match the task. State which files you read.
4. Read the relevant specifications and decisions if the project has them.
5. For a new project, follow `README.md`. Record project details,
   the first requirement, and the stack decision before implementation.
6. Use established local commands. If no application toolchain exists,
   establish and verify it from the specification before writing application code.

## Facts

- Keep one skill tree at `skills/`. Do not create tool-specific copies.
- Write a specification before you define an API, CLI, or architecture.
- Use the current repository context. Do not assume a remote address,
  development environment, or access method.

| Path | Content |
| --- | --- |
| `AGENTS.md` | Session rules and skill selection |
| `README.md` | Project purpose and setup |
| `skills/<name>/SKILL.md` | Task procedures |
