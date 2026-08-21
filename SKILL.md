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
  the relevant `bmad-*` skill by name as its FIRST action. Start with `bmad-help`
  if unsure which applies. An agent that skips this improvises the method instead
  of following it — and an audit of past runs found this rule held in one run out
  of nine, so treat it as the thing most likely to silently rot.
- **Spawn the typed BMAD subagent, not `general-purpose`.** For phase work use
  `bmad-agent-pm`, `bmad-agent-architect`, `bmad-agent-ux-designer`,
  `bmad-agent-dev`, `bmad-agent-analyst`, `bmad-agent-tech-writer`,
  `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`.
  `general-purpose` and `Explore` are for non-BMAD chores only — greps, builds,
  log fetches, renders. A `general-purpose` agent asked to "run bmad-dev-story"
  is the failure mode this rule exists to stop.

## Phase-gate ledger — run it or record the skip

Walk this list at every phase boundary. **R** = BMAD marks it required. Each row
is either done, or entered in a skip ledger with a one-line reason. There is no
third option, and "the task didn't seem to need it" is a reason — an unrecorded
skip is not.

| Phase | Step | | Rule |
|---|---|---|---|
| 0 brownfield | `bmad-generate-project-context` | | Mandatory when the repo pre-exists and has no `project-context.md`. Add `bmad-document-project` if the repo is undocumented. Do this in wave 0 — otherwise every later agent re-discovers the repo. |
| 1 analysis | `bmad-product-brief` or `bmad-prfaq` | | New product / new epic with unsettled scope. Skip freely for a bounded change. |
| 1 analysis | `bmad-brainstorming`, `bmad-market-research`, `bmad-domain-research`, `bmad-technical-research` | | Optional. `bmad-technical-research` earns its cost whenever the stack choice is live. |
| 2 planning | `bmad-prd` create | **R** | — |
| 2 planning | `bmad-prd` validate | | Run it. It is one agent against a checklist and it has run once in nine projects. |
| 2 planning | `bmad-ux` | | Mandatory when a UI is a primary surface. |
| 3 solutioning | `bmad-create-architecture` | **R** | — |
| 3 solutioning | `bmad-create-epics-and-stories` | **R** | — |
| 3 solutioning | `bmad-check-implementation-readiness` | **R** | The gate before any code. Never skip it silently — a missing readiness report is what a correct-course later pays for. |
| 4 implementation | `bmad-sprint-planning` | **R** | — |
| 4 story cycle | `bmad-create-story` (create) | **R** | See the story-cycle rule below. |
| 4 story cycle | `bmad-create-story` (validate) | | Run it. Zero validations exist across every project to date. |
| 4 story cycle | `bmad-dev-story` | **R** | — |
| 4 story cycle | `bmad-code-review` | | Per story, in a fresh agent. This is the three-layer review (Blind Hunter, Edge Case Hunter, Acceptance Auditor) — `bmad-review-adversarial-general` is one of those lenses, not a substitute for the workflow. |
| 4 story cycle | `bmad-review-edge-case-hunter` | | Add it when the story touches a state machine, money, permissions, or a data migration. |
| 4 epic close | `bmad-qa-generate-e2e-tests` | | Run at epic close for anything with an API or a UI. Never run to date anywhere — which is why "done" keeps resting on a manual smoke test. |
| 4 epic close | `bmad-retrospective` | | Run at epic close. |
| 4 anytime | `bmad-sprint-status` | | Read and write the tracker through the skill (or `close-story`). Hand-editing `sprint-status.yaml` is how it drifts into prose and divergent copies. |
| 4 anytime | `bmad-correct-course` | | The moment the plan and the work disagree — before the next story, not after the epic. |
| 4 anytime | `bmad-investigate` | | Bugs, incidents, unfamiliar code. Cheap; use it. |
| gate | `bmad-checkpoint-preview` | | Before asking approval for a deploy, merge, or migration, so the gate carries an artifact instead of a chat message. |
| hygiene | `bmad-shard-doc` | | When a PRD or architecture doc passes ~500 lines. |
| hygiene | `bmad-index-docs` | | At project close, over the output folder. |

### Enforcement is mechanical, not prose

The ledger lives in a file and a script maintains it — never hand-edit it:

```bash
/opt/homebrew/bin/python3 ~/.claude/skills/orchestrator-bmad/gate.py status
```

- `gate.py status` — run at every phase boundary; required gates are checked
  against artifacts on disk, not against your memory of having run them.
- `gate.py check <gate> [slug]` — precondition check before spawning
  (`readiness`, `story <slug>`, `story-validated <slug>`, `code-review <slug>`).
- `gate.py skip <step> --reason '...'` — record a deliberate skip.
- `gate.py waive <scope> --reason '...'` — record a user waiver (e.g. epic-batch
  dev). Only the user grants waivers; quote their words in the reason.
- `gate.py decide <step> run|skip --reason '...'` — record judgment on an
  optional capability (see the table below).

A PreToolUse hook (`~/.claude/hooks/bmad-agent-gate.py`) enforces two rules at
spawn time and will **block** the Agent call: BMAD phase work on a
`general-purpose`/`Explore` agent, and `bmad-dev-story` with no story file on
disk and no waiver. If a spawn bounces, fix the cause — don't rephrase the
prompt to slip past the gate.

### Optional capabilities — judgment, recorded

These are never required, but each has a trigger. When the trigger fires,
consider it and record the call with `gate.py decide` — one line, so skipping
is a decision, not a blind spot:

| Capability | Trigger to consider it |
|---|---|
| `bmad-party-mode` | A contested decision with ≥2 defensible options and an undecided user — multi-persona debate surfaces the tradeoffs cheaper than a wrong pick. |
| `bmad-market-research` | Greenfield product for external users, or the user asks "is there demand / who competes". |
| `bmad-domain-research` | Unfamiliar regulated or jargon-heavy domain (medical, finance, military logistics). |
| `bmad-prfaq` | The user is genuinely unsure of the concept and open to being swayed — PRFAQ stress-tests; product-brief assumes conviction. |
| `bmad-advanced-elicitation` | A required-gate artifact (PRD, architecture) feels shallow before you commit to it — red-team/pre-mortem it first. |
| `bmad-spec` | Messy multi-source intent (transcript + brain dump + design folder) that needs distilling before a PRD. |
| `bmad-quick-dev` | One-off change outside any epic. Never inside a sprint — it bypasses the story cycle by design. |
| `bmad-customize` | The same skip keeps recurring across projects — encode the fix into the workflow instead of re-skipping. |

## The story cycle is the load-bearing part

- **A story file on disk is the precondition for dev.** No `bmad-agent-dev`
  starts until `bmad-create-story` has written the story file and
  `bmad-create-story` (validate) has passed it. Marking a story `done` when no
  story file was ever created — this has happened, at ~30 stories in one project
  — throws away the Dev Notes, Dev Agent Record, File List and Change Log that
  make the next story cheap.
- **One story per agent.** Stories are the natural unit of parallelism: fan out
  across independent stories, and keep dev and its review as separate agents so
  the reviewer never inherits the implementer's rationalizations.
- **Epic-level dev batching requires an explicit user waiver**, recorded in the
  skip ledger. "Dev epic 3" as a single agent task is a deviation, not a
  shortcut: it collapses CS/VS/DS/CR into one context and leaves the per-story
  tracker statuses fictional.
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

- **Agent type** — the typed `bmad-agent-*` / `bmad-review-*` subagent for phase
  work; `general-purpose` or `Explore` only for non-BMAD chores.
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
- **Report the ledger.** At every phase boundary, state which gate rows ran and
  which were skipped with what reason. A phase that reports only what it did is
  unauditable — the skips are the interesting half.
- If asked for a closing document, default to a plain-language HTML file (plus a
  `.md` twin) covering: the original prompt, the plan, agents spawned with their
  types and models, per-story CS/VS/DS/CR status, the skip ledger, verification
  evidence per epic, changes made and why, and features deliberately left out.

## When not to use this

If the project isn't running BMAD-Method — or the user just wants a fleet of
agents without its phases, story files, and review gates — use the plain
`orchestrator` skill instead. For a single edit or a quick question, skip
orchestration entirely and do the work inline.
