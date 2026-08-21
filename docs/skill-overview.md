# orchestrator-bmad v2 — What Changed and How It Works
**Updated:** 2026-08-21 · twin of `skill-overview.html`

## Why v2

An audit of 9 real orchestrator runs (Aug 2026, ~200 subagents) found:

- "Every subagent invokes its BMAD skill first" held in **1 run of 9**.
- All phase work ran on `general-purpose` agents until 08-19; typed `bmad-agent-*` never used before that.
- `validate-story`, `qa-generate-e2e-tests`, `checkpoint-preview`, `sprint-status`: **never ran anywhere**.
- One project marked ~30 stories `done` with **no story files ever created** — the tracker pointed at a directory that didn't exist.
- Required gate `check-implementation-readiness` had not run since May.

Root cause: every rule was prose. Prose doesn't survive a 40-agent session. v2 moves enforcement into a script and a hook.

## The three layers

### 1. `gate.py` — phase-gate ledger (deterministic)

Lives in the skill dir; maintains `_bmad-output/gate-ledger.yaml` per project. Required gates are verified against **artifacts on disk**, never against the model's memory.

| Command | What it does |
|---|---|
| `gate.py status` | Phase-boundary check. Each required gate: ✓ done / ~ skipped-with-reason / ✗ MISSING (exit 1). |
| `gate.py check <gate> [slug]` | Precondition before a spawn: `readiness`, `story 2-4`, `story-validated 2-4`, `code-review 2-4`. |
| `gate.py skip <step> --reason` | Records a deliberate skip. The reason is the point. |
| `gate.py waive <scope> --reason` | User-granted waiver (e.g. epic-batch dev). Only the user grants these. |
| `gate.py decide <step> run\|skip --reason` | Judgment call on an optional capability, logged. |

**Rule: run the step, or record the skip. There is no third option.**

### 2. `bmad-agent-gate.py` — PreToolUse hook (hard block)

Registered in `~/.claude/settings.json` on `Agent|Task`. In any `_bmad` project it blocks, at spawn time, before the agent exists:

1. **Wrong agent type** — BMAD phase work (`bmad-dev-story`, `bmad-code-review`, `bmad-prd`, …) on a `general-purpose`/`Explore` agent. Block message names the correct typed agent.
2. **No story file** — a `bmad-dev-story` spawn when no story file exists on disk, none is referenced in the prompt, and no waiver is recorded.

Exit 2 stops the spawn; the reason is fed back to the model so it fixes the cause instead of retrying. Fail-open on any internal error. Non-BMAD projects: fast-exit, zero cost.

### 3. SKILL.md — judgment layer (prose, but ledger-backed)

- **Phase-gate table**: all 41 BMAD workflows, required-marked, each with its rule.
- **Story cycle is load-bearing**: story file on disk is the precondition for dev; CS → VS → DS → CR per story; epic batching requires an explicit user waiver.
- **Optional-capability triggers**: `party-mode` (contested decision, undecided user), `market-research` (greenfield external product), `prfaq` (concept unsure), `advanced-elicitation` (shallow artifact before a gate), `spec` (messy multi-source intent), `quick-dev` (one-off outside any epic), `customize` (recurring skip → encode it). When a trigger fires, the call is recorded with `gate.py decide`.
- **Reporting contract**: closing docs carry the skip ledger, per-story CS/VS/DS/CR status, verification evidence per epic.

## The story cycle, enforced

```
create-story ──► validate-story ──► dev-story ──► code-review ──► done
     │                │           ▲ blocked by hook          │
     │                │           │ unless story file        │ findings?
     └── story file   └── report  │ exists (or waiver)       └──► back to dev-story
         on disk          on disk
```

## Audit trail per project

`_bmad-output/gate-ledger.yaml`:

```yaml
skips:
  - step: readiness
    reason: brownfield hotfix — PRD/arch unchanged since 05-25 report
    ts: 2026-08-21T10:14:03
waivers:
  - scope: epic-batch-dev
    reason: Tal approved batching epic 7 (3 trivial stories) in chat
    ts: 2026-08-21T11:02:11
decisions:
  - step: party-mode
    decision: skip
    reason: architecture uncontested — single defensible option
```

## Files

| File | Installed at | Repo path |
|---|---|---|
| SKILL.md (207 lines, was 129) | `~/.claude/skills/orchestrator-bmad/` | `SKILL.md` |
| gate.py | `~/.claude/skills/orchestrator-bmad/` | `gate.py` |
| spawn-gate hook | `~/.claude/hooks/bmad-agent-gate.py` | `hooks/bmad-agent-gate.py` |
| hook registration | `~/.claude/settings.json` → `PreToolUse: Agent\|Task` | README snippet |

Installed copy and repo copy are byte-identical (verified with `diff`).

## Verified before shipping

- `gate.py status` on HermesPlus → all 5 required gates green; on local-whisper → correctly flags `readiness MISSING` (matches the audit finding).
- Hook: 5 pipe-tests — both block paths block (exit 2 + actionable stderr), pass paths pass, garbage stdin fails open.
- Skip round-trip: record → status shows `~ skipped: reason` → clean exit.
- `settings.json` schema-validated with `jq -e`; pre-existing hooks untouched.
