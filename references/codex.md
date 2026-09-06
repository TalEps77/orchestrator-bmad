# Codex adapter

Use this adapter only in Codex (CLI, IDE, or a hosted surface exposing Codex
skills/tools). Detect the available capabilities; hosted interfaces can differ.

## Installation and skills

For local/project use install under `.agents/skills/orchestrator-bmad` or a
supported user skill directory. BMAD's Codex integration must expose its own
skills. Invoke them by available skill name (typically `$bmad-…`), or use the
host's skill reader to load their exact installed instructions. Never call
Claude's `Skill`, `Agent`, `AskUserQuestion`, or rely on `~/.claude` paths here.
Use available shell/Python execution for the shared `gate.py` commands.

The installer can add optional project `.codex/agents/bmad-*.toml` definitions.
They omit model/effort overrides and inherit the configured default. If the
host does not expose custom roles, use its available worker/explorer/default
role or bounded `spawn_agent` equivalent with the same brief contract. Keep
subagent history minimal when supported. Review must not inherit the developer's
conversation; do not use a full-history fork for independent review.

Use the host's actual delegate, message/resume, wait and stop APIs. Capability
names and model overrides can differ; never invent tool parameters. If host
instructions disallow delegation, comply and report the independent-review gap.
For no delegation support, execute phase work sequentially and leave independent
review outstanding unless the user authorizes a specifically scoped waiver.

## Evidence, resources, and authorization

The common CLI provides preflight/evidence checks, fingerprints, active-attempt
limits, and exact run/story scope. **No automatic Codex spawn hook is installed
or assumed.** The parent runs start/check/finish explicitly and owns ledger
updates. This is an observable limitation, not equivalent to Claude PreToolUse.

Use supported model/effort overrides only when allowed by user/project/host
instructions; otherwise inherit. Persist actual agent IDs to permit targeted
resume. Optional project agent files are templates, not proof a hosted surface
loaded them. Filesystem/sandbox and approval constraints still apply.

Use worktrees if supported and needed for overlapping writers; otherwise
serialize. Existing permission grants persist. Use the host approval mechanism
for operations that still require authorization; optional question widgets are
not substitutes for permission controls.

Official sources checked 2026-09-06:
- [Skills and discovery](https://learn.chatgpt.com/docs/build-skills)
- [Subagents and custom TOML agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Live host availability is authoritative. This adapter promises a portable skill
and executable CLI, not identical tool schemas across every Codex interface.
