---
name: groundwork-author-skills
description: >-
  Creates or updates canonical skills and both skill indexes. Use when a
  user requests a skill, agent rule, or tool-specific instruction file.
---

# Author project skills

Follow the communication and documentation rules in `AGENTS.md`.

Put skills only at `skills/<skill-name>/SKILL.md`. Use the `groundwork-`
prefix, lowercase letters, numbers, and hyphens. If a user requests a
tool-specific rule, put the procedure in this canonical tree.

## Rules

- Keep the body under 500 lines.
- Write the description in the third person. State what the skill does and
  when to use it.
- Use YAML front matter with a name that matches the directory and a
  nonempty description. Use the format shown below.
- Do not set `disable-model-invocation`.
- Write a specification before you define APIs, CLIs, or architecture.
- Write skill files in English. Use short, direct instructions.
- Keep supporting material in the skill's references directory, if needed.
  Link each file that the reader must load.

```markdown
---
name: groundwork-example
description: >-
  Performs a defined task. Use when the stated trigger applies.
---
```

When you add, rename, or remove a skill, update these files together:

1. `skills/<name>/SKILL.md`.
2. `skills/README.md`.
3. The Task guides table in `AGENTS.md`.
4. All references to the changed name or path.

Review the text, indexes, and links with `skills/groundwork-verify/SKILL.md`.
Report the result.
