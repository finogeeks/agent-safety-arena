# Documentation

Read the project overview in [README.md](../README.md) first. Specifications
describe observable behavior. Decisions record choices and their consequences.

| Doc | Use |
| --- | --- |
| [report-generation.md](report-generation.md) | Defines fixed page structure, Agent-generated case content, and reusable local export/update. |
| [reproduction.md](reproduction.md) | Setup from a clone, build saved reports, and prepare a controlled case with explicitly selected product versions. |
| [reproduction-and-publishing.md](reproduction-and-publishing.md) | Defines installation, per-case dependency selection, result grouping, static checks, and offline site builds. |
| [finshield-recording.md](finshield-recording.md) | Defines the existing FinShield desktop launcher and shared DSH collection boundary. |
| [codex-terminal-recording.md](codex-terminal-recording.md) | Defines real Codex CLI terminal collection through the shared lifecycle, native defaults, evidence, and one-time approvals. |
| [deepseek-cli-setup.md](deepseek-cli-setup.md) | Defines a model-only Codex profile, local Claude Code setup, credential handling, and bounded DeepSeek connectivity checks. |
| [multi-agent-evaluation.md](multi-agent-evaluation.md) | Defines Agent/environment planning, English primary tests, no-prompt preflight, condition checks, and shared bilingual evidence exports. |
| [report-contract.md](report-contract.md) | Defines the target case navigation, six-section comparison detail page, required fields, media rules, and static layout reference. |
| [prompt-library.md](prompt-library.md) | Defines historical prompt imports, provenance, substitutions, and independent maintenance. |
| [evaluation-experience.md](evaluation-experience.md) | Applies POC lessons to prompt development, approvals, observations, recovery, and reporting. |
| [first-evaluation.md](first-evaluation.md) | Review the proposed first evaluation, acceptance criteria, and open questions before implementation. |
| [migration-plan.md](migration-plan.md) | Review the curated Agent Safe source migration boundaries, evidence, and exit conditions. |
| [repository-structure.md](repository-structure.md) | Use the accepted directory ownership and migration boundaries before adding application files. |
| [offline-workflow.md](offline-workflow.md) | Defines the independent synthetic replay lifecycle, result separation, and evidence boundaries. |
| [dsh-recording.md](dsh-recording.md) | Defines DSH recording requirements and provides operation steps, confirmation review, prompt iteration, limits, and verification evidence. |
| [dsh-batch.md](dsh-batch.md) | Defines the shared case-driven collection controller and separate post-collection analysis phase. |
| [workflow-reference-inventory.md](workflow-reference-inventory.md) | Records the read-only local workflow sources and the accepted, changed, or rejected behavior. |
| [adr/0001-documentation-first.md](adr/0001-documentation-first.md) | Understand the initial repository scope and why the application stack remains open. |
| [adr/0002-python-offline-workflow.md](adr/0002-python-offline-workflow.md) | Records the Python standard-library stack for the first offline workflow. |
| [adr/0003-dsh-recording.md](adr/0003-dsh-recording.md) | Records the Windows DSH, Chrome, Node, and FFmpeg recording decision. |

The first evaluation is a draft. It does not establish an implemented feature
or an agreed API. Add each new specification or decision to this index.
