# Saved results

Store comparisons at `<scenario-id>/<agent-id>/<comparison-id>/record.json`.
Result JSON is the canonical source for report builds. Keep only reviewed text,
selected display media, and provenance here. Raw video, full event logs, browser
profiles, and temporary scripts belong outside Git.

| Scenario | Agent | Saved result | Kind |
| --- | --- | --- | --- |
| window-flood | DSH | [2026-11-05 comparison](window-flood/dsh/dsh-finshield-pro-20261105/record.json) | Live development; native and FinShield |
| window-flood | DSH | [2026-11-05 native record](window-flood/dsh/dsh-deepseek-pro-20261105/record.json) | Live development; earlier single-group record |
| window-flood | Codex CLI | [2026-10-30 record](window-flood/codex-cli/codex-deepseek-pro-20261030/record.json) | Live development |
| window-shake | reference-agent | [Completed replay](window-shake/reference-agent/synthetic-window-completed/result.json) | Synthetic evaluator fixture |
| service-stop | reference-agent | [Incomplete replay](service-stop/reference-agent/synthetic-service-incomplete/result.json) | Synthetic evaluator fixture |

The DSH single-group and paired records reuse the same native trial. They are
separate saved presentations, not additional executions. Do not count catalog
entries as trial executions. Replay `result.json` files retain their existing
schema; the comparison site builder lists them as excluded.

See [directory ownership](../docs/repository-structure.md),
[reproduction](../docs/reproduction.md), and
[static publishing](../docs/reproduction-and-publishing.md).
