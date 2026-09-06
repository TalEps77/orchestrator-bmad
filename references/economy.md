# Context, code, and reporting economy

## Scoped influence, not global modes

The design considers [Ponytail](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)
and [Caveman](https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman/SKILL.md).
These are independently written, bounded rules, not imports or installations of
their persistent modes. Do not invoke either entire skill automatically.

| Phase | Simplicity | Communication |
|---|---|---|
| Discovery, PRD, acceptance | Distinguish required scope from speculative features; preserve all agreed needs | Clear complete statements with constraints and uncertainty |
| Architecture | Prefer existing components and proven platform features; document real tradeoffs | Concise rationale, explicit decisions and consequences |
| Story creation/validation | One coherent behavior per story; split by coupling/context, not a fixed file count | Complete acceptance criteria and dependencies |
| Implementation | Reuse project code, appropriate stdlib/platform/dependencies; write the smallest maintainable correct change | Brief progress and evidence summaries |
| Review, security, migration | Detect root causes and necessary safeguards; simplicity never overrides correctness | Exact findings, severity, location, reproduction, impact |
| Internal handoff | Avoid relaying logs/docs already on disk | Usually 5-12 lines; expand if a blocker or uncertainty needs it |
| User documents/approvals | Preserve requested deliverables | Normal language; no broken grammar or compressed consent |

Do not adopt forced one-liners, smallest-file-count goals, arbitrary deletion,
“ship less than requested and ask later”, a one-test ceiling, or suppression of
progress updates. Simplicity does not remove authorization checks, concurrency
handling, input validation, accessibility, error recovery, or required tests.
Do not compress instructions into images, rewrite every installed skill, change
the user's language, or discard qualifying words to save tokens.

## Worker brief contract

Keep shared rules in the worker definition. Pass only changing task facts:

- Run/story ID, phase, attempt ticket, and actual BMAD workflow.
- Goal and acceptance spec path; exact context packet/source-section paths.
- Allowed files, dependencies, and current base revision/worktree.
- Report and evidence paths; commands that establish success.
- Actual model/effort where supported; a bounded stopping condition.
- Return: result; files changed; checks/results; blockers; report path.

Start with the spec and relevant sections. Use the packet's source paths to
expand when a dependency is missing. Retain shared constraints (authorization,
data integrity, migrations, API contracts) even when they live outside the
story's immediate section. A cheap summarizer must not invent or drop them.
The `packet` helper rejects oversized inputs instead of silently truncating.
Its character budget is a control on text size, not an exact token limit.
The runtime's BMAD workflow may require extra context; respect that and record
why expansion was needed. Repeated irrelevant full-doc loads warrant a targeted
project BMAD customization, not a misleading claim that the packet is enforced.

## Cache and actual cost

Keep stable instructions stable and put task-specific details after them.
Same-type workers do not guarantee shared caches: model, prefix, tools, TTL,
working directory, and runtime behavior matter. Do not sacrifice correct
worktree isolation for cache reuse. The skill does not control API cache flags.
MCP schemas may already be deferred; inspect actual context overhead before
changing project settings, and preserve required tools.

Compare representative quick, lite, and full tasks at the same starting commit
and acceptance criteria. Record actual model, host version, input/output tokens,
cache reads/writes, elapsed time, attempts, and test outcome. Use unique raw
usage sample IDs, distinguish incremental from cumulative counters, and never
sum overlapping samples. Unknown fields stay null. Evaluate cost per accepted
result; no fixed saving percentage is claimed by this skill.

Sources checked for v4 on 2026-09-06:
- [Claude Code context/costs](https://code.claude.com/docs/en/costs)
- [Claude Code caching](https://code.claude.com/docs/en/prompt-caching)
- [Anthropic caching conditions](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
