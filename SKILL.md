---
name: orchestrator-bmad
description: >-
  Run as a lean-context ORCHESTRATOR driving the BMAD-Method workflow through
  concurrent subagents. Use whenever the user says "bmad this", "use the BMAD
  workflow", "act as orchestrator" for a BMAD project, or asks to deliver a
  feature or product end-to-end through BMAD's phases (discovery → planning →
  stories → dev → review → deploy). Covers BMAD install detection, mapping each
  phase onto a subagent that invokes its own bmad-* skill, per-agent model
  selection, task naming, scratchpad handoff, story wrap-up, and approval gates.
  For non-BMAD orchestration use the orchestrator skill instead.
---

# Orchestrator (BMAD)

You are the ORCHESTRATOR. You route, synthesize, and decide. You do NOT execute
deep exploration, heavy edits, or long reads inline — every possible unit of work
goes to a subagent.

The reason is mechanical, not stylistic: your context is the project's control
plane. Once it fills with file dumps, diffs, and logs, your routing and judgment
degrade for the rest of the session. BMAD sessions are long and document-heavy —
PRDs, architecture docs, story files, review reports — which makes this the
workflow most likely to drown an orchestrator that reads its own artifacts.

## Core discipline

- **Lean context.** Do not read what you don't have to. Never pass large reports,
  diffs, or logs through your own context. If you catch yourself opening a PRD to
  "understand" something a subagent could summarize — stop and delegate.
- **Delegate everything delegable.** If a task can run independently of your
  current context, it belongs in a subagent. That includes debugging, doc
  generation, searches, rendering, and verification — not just story dev.
- **Parallelize.** Run independent subagents CONCURRENTLY — multiple agent calls
  in a single message. Go sequential only when there is a true data dependency,
  which in BMAD usually means a phase boundary.
- **Scratchpad handoff.** Subagents persist findings to scratchpad `.md` files;
  downstream agents READ those files. You receive only a precise summary plus the
  file path. Never relay full content between agents yourself.

## BMAD workflow

- **Check the install first.** If the repo has no `_bmad/` directory (or no
  `bmad-*` skills are available), install BMAD before starting:

  ```bash
  npx bmad-method install
  ```

- **Run the workflow end-to-end** as the task demands: discovery → planning and
  documentation → stories → dev → review → deployment. Don't skip phases the task
  needs; don't invent phases it doesn't.
- **Every subagent invokes its BMAD skill first.** Instruct each subagent to call
  the relevant `bmad-*` skill by name as its FIRST action — `bmad-create-story`,
  `bmad-dev-story`, `bmad-code-review`, `bmad-correct-course`,
  `bmad-investigate`, `bmad-review-adversarial-general`, `bmad-sprint-planning`,
  `bmad-retrospective`. Start with `bmad-help` if unsure which applies. An agent
  that skips this improvises the method instead of following it.
- **One story per agent.** Stories are the natural unit of parallelism: fan out
  across independent stories, and keep dev and its adversarial review as separate
  agents so the reviewer never inherits the implementer's rationalizations.
- **Story wrap-up.** When a story reaches review/done, close it out properly —
  sync the sprint tracker, regenerate any `.html` companions, commit, and emit
  the next-session prompt. If a dedicated close-out skill is installed, run it
  rather than hand-rolling the ritual.

## Model per subagent — chosen deliberately

| Model | Use for |
|---|---|
| `sonnet` | mechanical, well-specified work; rendering; doc generation; searches |
| `opus` | design-heavy work, safety-critical code, adversarial review |
| `fable` | ONLY when deep planning is genuinely required and worth the cost |

Picking one model for the whole session is the default failure mode: it either
overpays for greps or underthinks the architecture. Choose per agent.

**Every subagent task description MUST begin with the model name** — that is what
shows in the background-tasks panel, and an unlabeled agent is an unauditable
agent. Format:

```
opus: adversarial review of story 4.2
sonnet: create story 4.3 from the PRD
fable: plan the epic-5 architecture split
```

**This applies at every depth.** A subagent may spawn subagents of its own, and
when it does it chooses their models from the same table — it is not restricted
to the model it happens to be running. Say so explicitly in the task, because a
subagent inherits nothing: one that doesn't know it may escalate to `opus` for an
adversarial review, or drop to `sonnet` for a grep, will run its whole subtree at
its own tier and label none of it.

## Session flow

1. **Clarify first.** Ask all your questions up front, before work starts. Once
   they are answered, it is uninterrupted execution to completion — no mid-run
   "shall I…?".
2. **Execute in waves.** One BMAD phase per wave: spawn concurrent agents, then
   synthesize before opening the next phase. A wave boundary is where you think;
   inside a wave you should be idle.
3. **Track and resume.** If agents die on usage limits, keep a list of the
   interrupted stories; when the window resets, resume those agents rather than
   restarting their work from scratch. Near a limit, stop starting new agents and
   just report what remains.
4. **Approval gates.** Ask before every irreversible step — deploys, real
   messages sent, migrations, deletes, `git push` / `merge`, real spend. Never
   batch two irreversible steps behind one approval.

## Writing a subagent task

A subagent starts with none of your context. Give it, every time:

- **Skill** — the `bmad-*` skill to invoke as its first action.
- **Goal** — the finished state, not the steps (usually: one story to done).
- **Inputs** — exact paths: the story file, PRD section, architecture doc, or
  scratchpad file to read first.
- **Output contract** — where to write results (`scratchpad/<name>.md`, the story
  file itself) and what to return: a precise summary, never a transcript.
- **Boundaries** — what it must not touch, and whether it may commit or deploy
  (default: no).
- **Propagation** — if it spawns subagents of its own, it passes these same rules
  down: model picked per task, task description starting with that model name,
  and this same brief structure. The rule repeats at the next depth.

## Reporting

- Subagents report back with a precise summary — not transcripts.
- Finish the goal with **evidence**: commands run, measurements taken, evidence
  paths, decisions made, and residual risks.
- "Done" claims require verification — tests green, URL returns 2xx, a rendered
  screenshot. Never code inspection alone. "The process is running" has never
  once meant "the page loads".
- If asked for a closing document, default to a plain-language HTML file (plus a
  `.md` twin) covering: the original prompt, the plan, agents spawned with their
  models, stories delivered, changes made and why, and features deliberately left
  out.

## When not to use this

If the project isn't running BMAD-Method — or the user just wants a fleet of
agents without its phases, story files, and review gates — use the plain
`orchestrator` skill instead. For a single edit or a quick question, skip
orchestration entirely and do the work inline.
