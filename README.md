# 🏗️ Orchestrator (BMAD)

**Drive the [BMAD-Method](https://github.com/bmad-code-org/BMAD-METHOD) workflow from a lean control plane — inside [Claude Code](https://claude.com/claude-code).**

A skill that makes the main agent an orchestrator for BMAD projects: it routes, synthesizes, and decides, while each phase and each story runs in its own subagent that invokes its own `bmad-*` skill. The main context never fills with PRDs, story files, and review reports — so the routing stays sharp through an entire epic.

---

## Why BMAD needs this most

BMAD is document-heavy by design: a PRD, an architecture doc, a story file per unit of work, a review report per story. That is exactly the material that destroys a main thread — every artifact read inline is context you don't get back, and BMAD sessions are long.

The fix isn't reading less. It's reading elsewhere.

| | Inline BMAD run | Orchestrated BMAD run |
|---|---|---|
| PRD / architecture docs | Read into the session context | Read by the agent that needs them, then discarded |
| Stories | One at a time, in the main thread | Fanned out, one agent per story |
| Dev + review | Same context — reviewer inherits the implementer's reasoning | Separate agents; the reviewer starts clean |
| Model | One for everything | Chosen per agent, per phase |
| Late-epic judgment | Degraded | Intact |

---

## The workflow

```
Check install ..... no _bmad/ ? → npx bmad-method install
Wave 0 ............ brownfield? generate-project-context first
Discovery ......... investigate, gather, scope
Planning .......... PRD (create + validate) + architecture, documented
Solutioning ....... epics & stories + implementation-readiness gate
Stories ........... CS → VS → DS → CR, one story file per unit of work
Dev ............... one agent per story, in parallel — typed bmad-agent-dev
Review ............ code-review per story + adversarial — a different agent
Epic close ........ e2e tests, retrospective, sprint-status via the skill
Wrap-up ........... tracker synced, .html regenerated, committed, next prompt emitted
Deploy ............ checkpoint-preview artifact, then an explicit approval gate
```

Phases the task doesn't need are skipped — **but every skip is recorded in the
gate ledger with a reason.** Nothing is skipped silently.

---

## Every subagent invokes its BMAD skill first

Each agent's **first action** is calling the relevant skill by name:

`bmad-create-story` · `bmad-dev-story` · `bmad-code-review` · `bmad-correct-course` · `bmad-investigate` · `bmad-review-adversarial-general` · `bmad-sprint-planning` · `bmad-retrospective`

(`bmad-help` first, when the right one isn't obvious.)

An agent that skips this improvises the method instead of following it — which looks like BMAD in the transcript and isn't in the artifacts.

**One story per agent**, and dev separated from adversarial review, so the reviewer never inherits the implementer's rationalizations.

Phase work is spawned on **typed BMAD subagents** (`bmad-agent-dev`, `bmad-agent-pm`, `bmad-agent-architect`, `bmad-review-adversarial-general`, …) — never `general-purpose`. A generic agent asked to "run bmad-dev-story" is the failure mode the enforcement layer exists to stop.

---

## Mechanical enforcement — not prose

An audit of nine real orchestrator runs found the "invoke your skill first" rule held in **one**. Prose doesn't survive long sessions; scripts do. Two pieces ship with the skill:

**`gate.py` — the phase-gate ledger.** Maintains `gate-ledger.yaml` in the project's BMAD output folder. Required gates are **derived at runtime from the project's own install** (`_bmad/_config/bmad-help.csv`) and verified against **artifacts on disk**, not against the model's memory of having run them. Renamed workflows and changed required-sets across BMAD versions (6.6 → 6.11 tested) are picked up automatically; hardcoded 6.8 conventions remain only as a fallback.

```bash
python3 gate.py status                      # gates from the installed bmad-help.csv: done / skipped / MISSING
python3 gate.py doctor                      # manifests parse? workflows mapped? shims present? version drift?
python3 gate.py check story-validated 2-4   # precondition before spawning dev
python3 gate.py skip readiness --reason '…' # deliberate skip, recorded
python3 gate.py waive epic-batch-dev --reason '…'   # user-granted waiver
python3 gate.py decide party-mode skip --reason '…' # judgment on an optional
```

**`hooks/bmad-agent-gate.py` — a PreToolUse hook** on the Agent tool. Registered in `~/.claude/settings.json`, it physically blocks two spawns in any `_bmad` project:

1. BMAD phase work on a `general-purpose`/`Explore` agent → blocked, suggests the typed agent.
2. A dev-workflow spawn (`bmad-dev-story` / 6.11's `bmad-build`) with no story file on disk and no recorded waiver → blocked.

Exit 2 stops the spawn and feeds the reason back to the model. Fail-open on internal errors — enforcement is best-effort, the work is not. Non-BMAD projects fast-exit at zero cost.

---

## Optional capabilities — judgment, recorded

Optionals (`party-mode`, `market-research`, `prfaq`, `advanced-elicitation`, …) each carry a trigger in the skill. When the trigger fires, the orchestrator considers the capability and records the call with `gate.py decide` — one line, so skipping is a decision, not a blind spot.

---

## Model per subagent

| Model | Use for |
|---|---|
| `sonnet` | mechanical, well-specified work; rendering; doc generation; searches |
| `opus` | design-heavy work, safety-critical code, adversarial review |
| `fable` | only when deep planning is genuinely required and worth the cost |

Every task description **starts with the model name** — that string is what shows in the background-tasks panel:

```
opus: adversarial review of story 4.2
sonnet: create story 4.3 from the PRD
fable: plan the epic-5 architecture split
```

An unlabeled agent is an unauditable agent.

This holds at every depth. A subagent that spawns its own subagents picks *their*
models from the same table — it is not stuck at its own tier — and labels their
tasks the same way. Subagents inherit nothing, so the rule has to travel in the
task brief.

---

## How a session runs

```
1  Clarify ....... every question asked up front — then uninterrupted execution
2  Wave .......... one BMAD phase per wave, concurrent agents inside it
3  Synthesize .... read summaries, not transcripts; open the next phase
4  Verify ........ "done" needs tests green / 2xx / a screenshot
```

- **Track and resume.** Agents killed by usage limits go on a list and get resumed when the window resets — never restarted from scratch.
- **Approval gates.** Deploys, migrations, deletes, real messages, `git push`, real spend — each asked separately. Never two irreversible steps behind one approval.

---

## Writing a subagent task

A subagent starts with none of the orchestrator's context, so every task carries:

- **Skill** — the `bmad-*` skill to invoke as its first action
- **Goal** — the finished state, usually one story to done
- **Inputs** — exact paths: story file, PRD section, architecture doc, scratchpad
- **Output contract** — where to write, and what to return (a summary, never a transcript)
- **Boundaries** — what it must not touch; may it commit or deploy (default: no)

---

## Install

```bash
git clone https://github.com/TalEps77/orchestrator-bmad.git ~/.claude/skills/orchestrator-bmad
```

Or copy `SKILL.md` + `gate.py` into `~/.claude/skills/orchestrator-bmad/`.

To arm the spawn gate, copy the hook and register it:

```bash
cp hooks/bmad-agent-gate.py ~/.claude/hooks/
```

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Agent|Task", "hooks": [
  { "type": "command", "command": "python3 \"$HOME/.claude/hooks/bmad-agent-gate.py\"", "timeout": 10 }
] } ] } }
```

The skill works without the hook — you just lose the hard block and fall back to the ledger discipline alone.

BMAD itself is installed per project, and the skill checks for it before starting:

```bash
npx bmad-method install
```

---

## Use

Just ask, in plain language:

> "bmad this feature"
> "use the BMAD workflow to ship the billing epic"
> "act as orchestrator and run the stories in parallel"

The skill auto-triggers on those. Or invoke it directly:

```
/orchestrator-bmad
```

---

## When *not* to use it

If the project isn't running BMAD-Method — or you want a fleet of agents without its phases, story files, and review gates — use [orchestrator](https://github.com/TalEps77/orchestrator) instead. For a single edit or a quick question, skip orchestration entirely.

---

## License

MIT
