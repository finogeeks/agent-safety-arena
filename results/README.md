# Saved results

Store comparisons at `<scenario-id>/<agent-id>/<comparison-id>/record.json`.
Result JSON is the canonical source for report builds. Keep only reviewed text,
selected display media, and provenance here. Raw video, full event logs, browser
profiles, and temporary scripts belong outside Git.

The maintainer confirmed the committed live reports as formal published results on
2026-11-09. Report `phase` records this classification. Original run-condition
snapshots, prompts, replies, assessments, and media remain unchanged. Historical
phase values in run snapshots do not change the publication classification.

| Scenario | Agent | Saved result | Kind |
| --- | --- | --- | --- |
| camera-capture | WorkBuddy | [2026-11-08 python-file-v1 comparison](camera-capture/workbuddy/workbuddy-python-file-v1-20261108/record.json) | Live formal; native and FinShield |
| microphone-capture | WorkBuddy | [2026-11-08 python-file-v1 comparison](microphone-capture/workbuddy/workbuddy-python-file-v1-20261108/record.json) | Live formal; native and FinShield |
| screen-capture | WorkBuddy | [2026-11-08 desktop-file-v2 comparison](screen-capture/workbuddy/workbuddy-desktop-file-v2-20261108/record.json) | Live formal; native and FinShield |
| window-flood | WorkBuddy | [2026-11-08 fixed Python file comparison](window-flood/workbuddy/workbuddy-python-file-v2-20261108/record.json) | Live formal; python-file-v2; native and FinShield |
| ime-state | DSH | [2026-11-07 comparison](ime-state/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| mouse-speed | DSH | [2026-11-08 BASE/NOW comparison](mouse-speed/dsh/dsh-finshield-pro-20261108-en-v2/record.json) | Live formal; native and FinShield |
| mouse-speed | DSH | [2026-11-07 orange-block comparison](mouse-speed/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; historical orange SPEED 1 en-v1 |
| mouse-button-swap | DSH | [2026-11-07 comparison](mouse-button-swap/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| wheel-scroll | DSH | [2026-11-08 BASE/NOW comparison](wheel-scroll/dsh/dsh-finshield-pro-20261108-en-v2/record.json) | Live formal; native and FinShield |
| wheel-scroll | DSH | [2026-11-07 orange-block comparison](wheel-scroll/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; historical orange WHEEL 20 en-v1 |
| foreground-window | DSH | [2026-11-07 two-window comparison](foreground-window/dsh/dsh-finshield-pro-20261107-en-v2/record.json) | Live formal; native and FinShield |
| foreground-window | DSH | [2026-11-07 one-window comparison](foreground-window/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; historical one-window en-v1 |
| window-visibility | DSH | [2026-11-07 comparison](window-visibility/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| window-minimize | DSH | [2026-11-07 comparison](window-minimize/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| window-resize | DSH | [2026-11-07 comparison](window-resize/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| window-shake | DSH | [2026-11-07 comparison](window-shake/dsh/dsh-finshield-pro-20261107/record.json) | Live formal; native and FinShield |
| cursor-recenter | DSH | [2026-11-06 comparison](cursor-recenter/dsh/dsh-finshield-pro-20261106/record.json) | Live formal; native and FinShield |
| display-resolution | DSH | [2026-11-06 comparison](display-resolution/dsh/dsh-finshield-pro-20261106/record.json) | Live formal; native and FinShield |
| screen-overlay | DSH | [2026-11-06 comparison](screen-overlay/dsh/dsh-finshield-pro-20261106/record.json) | Live formal; native and FinShield |
| window-flood | WorkBuddy | [2026-11-08 comparison](window-flood/workbuddy/workbuddy-finshield-pro-20261108/record.json) | Live formal; native and FinShield |
| window-flood | DSH | [2026-11-05 comparison](window-flood/dsh/dsh-finshield-pro-20261105/record.json) | Live formal; native and FinShield |
| window-flood | DSH | [2026-11-05 native record](window-flood/dsh/dsh-deepseek-pro-20261105/record.json) | Live formal; earlier single-group record |
| window-flood | Codex CLI | [2026-10-30 record](window-flood/codex-cli/codex-deepseek-pro-20261030/record.json) | Live formal |
| window-shake | reference-agent | [Completed replay](window-shake/reference-agent/synthetic-window-completed/result.json) | Synthetic evaluator fixture |
| service-stop | reference-agent | [Incomplete replay](service-stop/reference-agent/synthetic-service-incomplete/result.json) | Synthetic evaluator fixture |

The DSH single-group and paired records reuse the same native trial. They are
separate saved presentations, not additional executions. Do not count catalog
entries as trial executions. Replay `result.json` files retain their existing
schema; the comparison site builder lists them as excluded.

See [directory ownership](../docs/repository-structure.md),
[reproduction](../docs/reproduction.md), and
[static publishing](../docs/reproduction-and-publishing.md).
