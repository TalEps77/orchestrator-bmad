# Claude Code adapter

Read only in Claude Code. Install the skill under a supported `.claude/skills`
directory, and BMAD's Claude Code integration in the target project. The shared
installer adds four project agent definitions and can register the optional hook
without replacing unrelated settings. Prefer existing matching definitions when
appropriate; never overwrite local customization without the upgrade option.

## Workers

Use installed `bmad-planner`, `bmad-worker`, `bmad-reviewer`, and
`bmad-researcher` agent types with the native Agent tool. The templates are
workflow-neutral: the task brief names the actual installed BMAD skill. Invoke
it through Skill before phase work, or use its content when already preloaded.
Do not preload every BMAD skill into every role. Templates allow Agent for
substeps explicitly required by a loaded native workflow. The parent counts all
live workers and allocates a nested-worker budget. No arbitrary story fan-out;
run Build at top level if the host cannot support its required nesting.

Templates use `model: inherit`. Select actual supported model/effort controls
when useful and authorized, rather than merely prefixing a task title. Host
configuration can override a requested model; record the effective model when
visible. Keep dev and independent review in different contexts; do not use a
fork that carries the developer's reasoning into review. Resume the same worker
for targeted retries. Background interaction/tool availability varies by host
version; choose foreground when the required workflow needs interaction.

## Optional launch hook

`hooks/bmad-agent-gate.py` matches `Agent|Task` through PreToolUse. Register its
absolute path IN the skill package, not a copied standalone hook. It imports the
adjacent gate module. The installer uses current Claude exec-form hooks:
`command` is the Python executable, `args` contains the absolute script path.
This avoids shell quoting on Windows and POSIX. A host without exec-form hook
support should use the explicit CLI until its hook is adapted and verified.

For managed v4 projects:
- Outer managed work uses one of the supplied roles.
- Required native Build/code-review substeps use their actual native role plus
  `BMAD_PARENT_TICKET:<outer-ticket>` and the parent workflow name. This validates
  the active parent reservation, not a separate attempt or recursive quota.
  The parent must observe child counts and preserve reviewer identities.
- Dev/review briefs require exactly one `BMAD_TICKET:<id>` obtained from start.
- The role, workflow and active ticket must agree; its inputs remain current.
- Managed hook errors block with diagnostics; non-managed projects pass through.

The ticket is a workflow reservation, not a credential. The hook does not prove
that the worker invoked a skill, enforce its first action, intercept every edit,
or authenticate actor/model assertions. It does not govern inline phase work or
unlabelled generic tasks; the parent must still follow the common lifecycle.
Do not rephrase a blocked spawn to evade it. Fix the report/precondition/role,
or record a user-authorized scoped exception through the CLI.

Review permission prompts using Claude Code's actual permission system.
AskUserQuestion is useful for optional product choices, not a way to bypass a
permission denial or demand repeated authorization already given.

Official sources checked 2026-09-06:
- [Subagents, models, skills, inheritance](https://code.claude.com/docs/en/sub-agents)
- [Skills](https://code.claude.com/docs/en/skills)
- [Hook input and decision behavior](https://code.claude.com/docs/en/hooks)
- [Prompt cache scope and limits](https://code.claude.com/docs/en/prompt-caching)
