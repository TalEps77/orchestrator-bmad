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
Discovery ......... investigate, gather, scope
Planning .......... PRD + architecture, documented
Stories ........... one story file per unit of work
Dev ............... one agent per story, in parallel
Review ............ adversarial review — a different agent than the one that built it
Wrap-up ........... tracker synced, .html regenerated, committed, next prompt emitted
Deploy ............ behind an explicit approval gate
```

Phases the task doesn't need are skipped; phases BMAD doesn't have are not invented.

---

## Every subagent invokes its BMAD skill first

Each agent's **first action** is calling the relevant skill by name:

`bmad-create-story` · `bmad-dev-story` · `bmad-code-review` · `bmad-correct-course` · `bmad-investigate` · `bmad-review-adversarial-general` · `bmad-sprint-planning` · `bmad-retrospective`

(`bmad-help` first, when the right one isn't obvious.)

An agent that skips this improvises the method instead of following it — which looks like BMAD in the transcript and isn't in the artifacts.

**One story per agent**, and dev separated from adversarial review, so the reviewer never inherits the implementer's rationalizations.

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

Or copy `SKILL.md` into `~/.claude/skills/orchestrator-bmad/`.

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
