# Documentation

Read the project overview in [README.md](../README.md) first. Specifications
describe observable behavior. Decisions record choices and their consequences.

| Doc | Use |
| --- | --- |
| [evaluation-guide.md](evaluation-guide.md) | Defines the bilingual evaluation blog, key takeaways, site styling, search metadata and evidence links. |
| [public-result-presentation.md](public-result-presentation.md) | Defines shared publication eligibility, compact GIF cards and synchronized public summaries without changing original evidence. |
| [screen-recording-case.md](screen-recording-case.md) | Defines the 20-second workspace screen-video case, camera-style host validation, English Off/On panel and evidence limits. |
| [primary-screen-capture-program.md](primary-screen-capture-program.md) | Defines literal full-primary-screen PNG screenshots, the saved-image-count observation, and the WorkBuddy recording suite. |
| [device-scenario-programs.md](device-scenario-programs.md) | Defines generation-only fixed camera, microphone and screenshot scripts, prompts, observers and offline checks. The speaker-on Agent case is withdrawn. |
| [window-flood-python-program.md](window-flood-python-program.md) | Defines the fixed window-flood Python source, execution prompt, ordinary-language generation prompt and their separate evidence roles. |
| [device-effect-display.md](device-effect-display.md) | Proposes controlled camera, microphone, screenshot and screen-recording displays with direct comparison and evidence limits. |
| [device-safety-candidates.md](device-safety-candidates.md) | Lists unrecorded device cases and defines direct native / Job UI / FinShield preparation probes without an Agent or recording. |
| [ime-state-fixture.md](ime-state-fixture.md) | Defines session input-language switching, the external read-only observer, restoration limits, and candidate verification. |
| [mouse-button-swap-fixture.md](mouse-button-swap-fixture.md) | Defines an independent right-click SENT/GOT panel and a later switcher, matching IME session form. |
| [mouse-speed-fixture.md](mouse-speed-fixture.md) | Defines an independent BASE/NOW pointer-speed panel and a later switcher, matching IME session form. |
| [wheel-scroll-fixture.md](wheel-scroll-fixture.md) | Defines an independent BASE/NOW wheel-speed panel and a later switcher, matching mouse-speed form. |
| [foreground-window-fixture.md](foreground-window-fixture.md) | Defines two overlapping owned windows that swap stacking order without Hide or minimize. |
| [evaluation-overview.md](evaluation-overview.md) | Defines total/category/Agent scores, four safety categories, folded unrecorded Agents, formal published results, and evidence links. |
| [report-generation.md](report-generation.md) | Defines fixed page structure, Agent-generated case content, and reusable local export/update. |
| [recording-standard.md](recording-standard.md) | Defines host-verified saved programs, short execution prompts, machine preparation, and shared recording. |
| [reproduction.md](reproduction.md) | Setup from a clone, build saved reports, and prepare a controlled case with explicitly selected product versions. |
| [reproduction-and-publishing.md](reproduction-and-publishing.md) | Defines installation, per-case dependency selection, result grouping, static checks, and offline site builds. |
| [finshield-recording.md](finshield-recording.md) | Defines the existing FinShield desktop launcher and shared DSH collection boundary. |
| [codex-terminal-recording.md](codex-terminal-recording.md) | Defines real Codex CLI terminal collection through the shared lifecycle, native defaults, evidence, and one-time approvals. |
| [codex-finshield-recording.md](codex-finshield-recording.md) | Defines Codex CLI FinShield via installed `finsafe self-confine` of the owned app-server. |
| [workbuddy-recording.md](workbuddy-recording.md) | Gives the reusable WorkBuddy native/FinSafe procedure: sandbox-state checks, private desktop-1 capture, editing, review and result-page generation. |
| [workbuddy-finshield-recording.md](workbuddy-finshield-recording.md) | Defines the installed FinSafe WorkBuddy launch, protected daemon verification, actual setting differences, and shared collection. |
| [workbuddy-session-hooks.md](workbuddy-session-hooks.md) | Compares DSH HTTP and WorkBuddy CDP input/output channels, request matching, original tool-log recovery and privacy boundaries. |
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
