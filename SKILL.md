---
name: orchestrator-bmad
description: >-
  Deliver a feature, epic, or product through BMAD in Codex or Claude Code.
  Use when the user requests BMAD orchestration or an end-to-end BMAD build.
  Coordinate focused workers, explicit evidence gates, and bounded context.
  Ordinary questions and isolated edits do not need this workflow.
---

# BMAD Orchestrator · v4

Complete the user's goal with a small control context, verifiable artifacts,
and proportionate coordination. Support **Codex and Claude Code only**.
User instructions, existing authorization, project rules, and host permissions
remain authoritative. This skill does not grant permissions or activate a
global writing style.

## Start or resume

1. Identify the actual host and available tools. Read **one** adapter:
   [Codex](references/codex.md) or [Claude Code](references/claude-code.md).
   Use the skill directory's absolute path for scripts; run them against the
   target project with `--root`. Never assume a Homebrew/Python location.
2. Read relevant project instructions and the user's accepted scope. Resolve
   only questions that materially block a sound decision; otherwise state
   assumptions and proceed. Preserve authorization already given.
3. Check the project's installed BMAD workflows with
   `python /path/to/skill/gate.py --root /project doctor` (use the available
   Python 3.11+ executable). No install/update or network check happens here.
   If BMAD is missing, install its integration for this host when authorized;
   never invent workflow names, silently upgrade, or pretend BMAD ran.
4. Resume the exact run ID, or initialize a new bounded run and record its lane.
   Read [workflow](references/workflow.md) for lane selection and phase work,
   and [ledger](references/ledger.md) before first use of the CLI.

| Lane | Fit | Work |
|---|---|---|
| quick | Bounded standalone change outside an active sprint | Quick workflow, small acceptance spec, implementation, independent review |
| lite | One epic in an existing, understood product | Applicable planning evidence, stories, implementation, review, integration |
| full | New system, several epics, unsettled architecture | Full applicable BMAD planning and implementation lifecycle |

Escalate when scope grows. Reuse current planning artifacts after checking their
fit. A new run does not inherit old waivers or filenames as proof of success.

## Work and evidence

- Use the installed BMAD skill appropriate to the task **before substantive
  phase work**. Preloaded skill content satisfies loading; do not load it twice.
  Record its real workflow name in the evidence report. Script checks validate
  evidence and sequencing, not whether a model actually obeyed a skill.
- Give each story a BMAD story file and a separate, stable acceptance spec.
  The spec contains behavior, boundaries, acceptance criteria, and relevant
  source references; BMAD may update lifecycle notes in the story file.
  Reuse a native SPEC and include every frontmatter `companions:` file. Keep
  temporary session/coordination status in story notes, outside the contract.
  Requirement changes update the spec and invalidate prior evidence.
- Create and checklist-validate together. Keep implementation and independent
  review in different agents/sessions. If independent execution is unavailable,
  do useful work and report the review gap; never invent a reviewer identity.
- Before dev or review, reserve an attempt with `gate.py start`. Pass its ticket,
  exact workflow, inputs, allowed files, and output paths to the worker.
  If the installed Build workflow includes independent native review, preserve
  that reviewer's evidence and accept it with `accept-review` after dev finish;
  avoid a duplicate external review. See the native route in workflow.md.
  Close the attempt with a structured report using `finish`. Explicitly cancel
  interrupted attempts once the worker has stopped. The parent owns ledger
  mutations; workers write separate reports and evidence.
- `close` requires current validation, dev verification, and independent review.
  Passing means explicit success, no blockers, and unchanged evidence/sources.
  At epic close run integration/acceptance checks over the combined changes.
  Per-story passes do not prove the integrated system works.

## Control cost without weakening the result

- Execute short commands and bounded reads directly. Delegate substantial,
  self-contained work when isolation or concurrency justifies startup cost.
  Batch deterministic chores in scripts instead of spawning a worker per chore.
- Build a small context packet with `gate.py packet`: acceptance spec, story,
  relevant source sections, conventions, and verification commands. Select
  sections by relevance; do not shard tiny documents for ceremony. Expand when
  correctness requires it. Never truncate requirements or hide missing context.
- Read [economy](references/economy.md) before constructing worker briefs.
  Apply code simplicity during design/implementation and concise internal
  reporting at handoffs. Keep requirements, code, review findings, and user
  deliverables complete. Preserve uncertainty, negation, IDs, numbers and units.
- Use the actual available model/effort controls. Map cheap, balanced, and deep
  reasoning roles to supported models; a name in a task description is not a
  model setting. Inherit the host default when selection is unavailable or
  constrained. Record the actual model when the host exposes it.
- Default to at most three active **managed dev/review attempts** per project
  and three attempts per story/phase. Also cap total live workers, including
  planners and nested workers, at three unless the task justifies more. The CLI
  enforces only registered attempts; host limits and prompt discipline cover
  other workers. Allow native workflow subagents when its steps require them,
  within the same total budget; no unbounded story fan-out. Run a native workflow
  at top level when nesting is unsupported. Diagnose repeated failures
  before extending a budget with a reason; never mark a partial result done.
- Schedule by dependencies and file ownership. Independent work may overlap
  phases; a slow story must not hold up an unrelated review. Use separate
  worktrees for overlapping writers when available, or serialize them. Reuse
  the developer for a targeted fix and the reviewer for a delta check; widen
  review when the change affects assumptions or shared behavior.
- Keep full logs on disk and return summaries plus decisive failures. Measure
  host-reported usage when available. Character counts are estimates, cache
  savings are conditional, and lower input size does not prove lower total cost.

## Finish

Verify the actual requested behavior, synchronize BMAD story/tracker status,
and report completed work, remaining gaps, and evidence paths in the user's
language. Keep progress updates useful during long work. Generate HTML only
when requested or already a required deliverable, using deterministic rendering
where practical. Commit/publish as authorized; preserve history. Before an
external action that still needs authorization, prepare a concrete reviewable
result, then use the host's actual approval mechanism.
