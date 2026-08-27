# orchestrator-bmad — Skill Overview
**Updated:** 2026-08-28 · twin of `skill-overview.html`

## What it is

A Claude Code skill that runs the [BMAD-Method](https://github.com/bmad-code-org/BMAD-METHOD) workflow from a **lean orchestrator**: the main agent routes, synthesizes, and decides, while every phase and every story executes in its own subagent. Compliance with the method is **mechanical** — a gate script and a spawn hook enforce it — not a matter of the model remembering instructions.

Trigger: "bmad this", "use the BMAD workflow", "act as orchestrator" on a BMAD project, or `/orchestrator-bmad`.

## The three components

| Component | Where | Role |
|---|---|---|
| `SKILL.md` | `~/.claude/skills/orchestrator-bmad/` | The playbook: workflow, phase-gate table, story-cycle rules, model selection, task-brief format, optional-capability triggers |
| `gate.py` | same dir | The ledger: verifies required gates against artifacts on disk; records skips, waivers, and judgment calls in `gate-ledger.yaml` |
| `bmad-agent-gate.py` | `~/.claude/hooks/` (PreToolUse on `Agent\|Task`) | The gate: physically blocks non-compliant subagent spawns before they exist |

Supporting cast: typed subagent shims in `~/.claude/agents/bmad-*.md` (register the agent types BMAD workflows spawn), and the `close-story` skill for story wrap-up.

## How a session runs

```
0  Doctor ......... gate.py doctor — manifests parse? shims present? version drift?
                    (skill action, every session start and after any BMAD install/update)
0b Brownfield ..... no project-context.md? → generate-project-context first
1  Clarify ........ every question asked up front — then uninterrupted execution
2  Waves .......... one BMAD phase per wave; concurrent subagents inside it
   ├─ each wave opens and closes with gate.py status
   └─ each subagent: typed bmad-* agent, invokes its bmad-* skill FIRST
3  Story cycle .... create+validate-story (one agent) → dev-story → code-review, per story
4  Epic close ..... e2e tests · retrospective · sprint-status via the skill
5  Wrap-up ........ close-story: tracker synced, .html twins, commit, next prompt
6  Deploy ......... checkpoint-preview artifact → explicit approval gate
```

## The enforcement model

**Rule: run the step, or record the skip. There is no third option.**

### gate.py — the phase-gate ledger

Required gates are **derived at runtime from the project's own BMAD install** — `_bmad/_config/bmad-help.csv` (which workflows exist, which are required), `_bmad/*/config.yaml` (where artifacts live), `manifest.yaml` (installed version). This makes the skill version-agnostic: renamed workflows and changed required-sets across BMAD versions are picked up automatically per project. A hardcoded fallback covers installs missing the manifests.

```bash
gate.py doctor                       # session start / after install: manifests, mappings, shims, drift, new version
gate.py doctor --no-net              # same, skipping the npm version check
gate.py status                       # phase boundary: ✓ done / ~ skipped: reason / ✗ MISSING (exit 1)
gate.py check story-validated 2-4    # precondition before spawning dev
gate.py skip readiness --reason '…'  # deliberate skip, recorded
gate.py waive epic-batch-dev --reason '…'   # user-granted waiver (only the user grants these)
gate.py decide party-mode skip --reason '…' # judgment call on an optional, logged
```

Everything lands in `gate-ledger.yaml` in the project's BMAD output folder, stamped with the BMAD version it was written under.

### Version handling — check always, update never silently

Doctor also compares the installed version against the latest published on npm (10s timeout; offline is a silent skip). It only **reports** — an update regenerates each project's `.claude/skills/` and `.agents/skills/` and writes `.bak` files, i.e. tracked-file changes, and can rename workflows mid-flight. So:

| State | Action |
|---|---|
| No `_bmad/` at all | Install latest outright — nothing to disturb |
| Update available, no sprint in progress | **AskUserQuestion**: update now or stay. On approval → update, re-run doctor, fix new shims |
| Update available, sprint in progress | Don't ask mid-epic — record `gate.py decide bmad-update skip` and raise it at epic close |
| Offline / npm slow | Check skipped silently, work proceeds |

Doctor detects "sprint in progress" from the tracker (`in-progress` / `ready-for-dev` / `review` statuses) and prints the matching recommendation itself.

### The spawn hook — hard blocks

Runs before any subagent exists. In a `_bmad` project it blocks:

| Spawn shape | Result |
|---|---|
| BMAD phase work on a `general-purpose`/`Explore` agent | **BLOCKED** — names the correct typed agent |
| Dev workflow (`bmad-dev-story`/`bmad-build`) with no story file on disk and no waiver | **BLOCKED** — "run create-story first, or record a waiver" |
| Typed agent + story file present | passes |
| Anything outside a `_bmad` project, or any internal hook error | passes (fail-open, zero cost) |

Exit 2 stops the call and feeds the reason back — the orchestrator fixes the cause, never rephrases past the gate. Phase-work skill names come from the project's `skill-manifest.csv`, so the hook recognizes workflows it has never seen by name.

### The story cycle — load-bearing

```
create+validate-story ──► dev-story ──► code-review ──► done
     │  (one agent)     ▲ hook blocks unless          │
     └── story file +   │ story file exists           │ findings?
         validation     │ (or user waiver)            └──► back to dev-story
         report on disk
```

- A story file on disk is the **precondition** for dev — no exceptions without a recorded user waiver.
- Create and validate run in the **same agent** (token economy — see below); validation still happens, only the extra context reload dies.
- One story per agent; dev and review are **separate agents**, so the reviewer never inherits the implementer's rationalizations.
- `bmad-code-review` runs per story (it's the three-layer review: Blind Hunter, Edge Case Hunter, Acceptance Auditor); adversarial review is one lens, not a substitute.

## Token economy (v3)

BMAD's cost driver is context reload — every subagent re-ingests instructions and artifacts from scratch (upstream measured 80–100k tokens per step on whole-doc reads, BMAD-METHOD #1235). The skill counters it with seven rules:

| Rule | Mechanic |
|---|---|
| Shard before spawn | PRD/architecture sharded the moment they exist; briefs name exact section files, never whole docs |
| Slim context file | `project-context-slim.md` (≤150 lines) distilled once per epic; full doc only on demonstrated need |
| Merge create+validate | Story/PRD creation self-validates in the same context; code review stays a separate agent |
| Cache-aligned waves | Same agent type batched per wave → shared prompt-cache prefix at ~10% input price |
| One-context stories | A story touching >~10 files or >1 subsystem is split before dev |
| MCP trim | Suggest a project settings deny-list for MCP servers the work doesn't need |
| Optionals default to skip | Non-required ledger rows run only when their trigger fires; every skip recorded |

Subagent briefs additionally carry a **code-economy ladder** (ponytail-style, for dev agents: exists? in codebase? stdlib? platform? dependency? one-liner? → only then write the minimum) and **terse reporting** (caveman-style: ≤15-line telegraphic summaries; deliverables stay complete).

## Optional capabilities — judgment, recorded

Never required; each has a trigger. When it fires, the orchestrator considers the capability and logs the call with `gate.py decide`:

| Capability | Trigger |
|---|---|
| `bmad-party-mode` | Contested decision, ≥2 defensible options, undecided user |
| `bmad-market-research` | Greenfield product for external users |
| `bmad-domain-research` | Unfamiliar regulated/jargon-heavy domain |
| `bmad-prfaq` | Concept genuinely unsure, user open to being swayed |
| `bmad-advanced-elicitation` | A required-gate artifact feels shallow before committing |
| `bmad-spec` | Messy multi-source intent needing distillation before a PRD |
| `bmad-quick-dev` | One-off change outside any epic (never inside a sprint) |
| `bmad-customize` | The same skip keeps recurring — encode the fix into the workflow |

## Model per subagent

| Model | Use for |
|---|---|
| `haiku` | greps, renders, tracker sync, file moves, slim-context distillation |
| `sonnet` | mechanical well-specified work, story creation, doc generation, standard dev stories |
| `opus` | design-heavy work, safety-critical code, adversarial review |
| `fable` | only when deep planning is genuinely required and worth the cost |

Every task description starts with the model name (`opus: adversarial review of story 4.2`) — an unlabeled agent is an unauditable agent. The rule propagates to every depth of nesting.

## Writing a subagent task

Every brief carries: **agent type** (typed `bmad-*`), **skill** to invoke first, **goal** (finished state), **inputs** (exact paths — sharded sections and the slim context file, never whole docs), **output contract** (where to write + terse summary back, never a transcript), **boundaries** (no commit/deploy by default), **code economy** (the ladder, for dev agents), **terse reporting**, **propagation** (these same rules travel down to nested spawns).

## Reporting

- Subagents return summaries with evidence — commands run, artifact paths, residual risks.
- "Done" requires verification: tests green, 2xx on the real URL, or a rendered screenshot.
- Phase boundaries report the ledger — what ran AND what was skipped with reasons.
- Closing documents (`.md` + `.html` twins): original prompt, plan, agents + models, per-story CS/VS/DS/CR status, skip ledger, verification evidence, deliberate omissions.

## Background

The enforcement layer exists because an audit (2026-08-21, nine real runs, ~200 subagents) showed prose rules don't survive long sessions — details in `AUDIT-2026-08-21.md` alongside the installed skill. The version-agnostic derivation exists because four BMAD versions were found installed side by side, with workflow renames between them.
