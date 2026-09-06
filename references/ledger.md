# Ledger CLI and evidence contract

Contents: setup; planning; stories; attempts; packet/usage; recovery/limits.
Use Python 3.11+ and `requirements.txt`. All commands return JSON on stdout;
blocked/invalid operations exit 1 with a diagnostic. The Claude hook uses exit 2.
Examples use `python gate.py --root /project`; substitute the installed absolute
script path. The ledger is `/project/.bmad-orchestrator/ledger.json`.

## Initialize or resume

```sh
python gate.py --root /project doctor
python gate.py --root /project init --run billing-1 --lane full --reason 'New billing system'
python gate.py --root /project status --run billing-1
```

`init` never overwrites a run. `status` and `doctor` never write or access the
network. The installed BMAD catalog determines required planning gates; legacy
YAML is not imported as evidence. Use one parent to mutate the ledger. Atomic
writes and a bounded interprocess lock protect against cooperating CLI writers.
Do not hand-edit the JSON or put live locks under version control.

## Planning evidence

Create a report after actually running/checking the workflow:

```json
{
  "schema_version": 1,
  "run": "billing-1",
  "story": null,
  "actor": "planner-session-1",
  "workflow": "bmad-prd",
  "verdict": "pass",
  "blockers": [],
  "summary": "PRD matches the approved scope and validation checklist.",
  "evidence": ["_bmad-output/planning-artifacts/prd.md", "reports/prd-validation.md"]
}
```

```sh
python gate.py --root /project record prd --run billing-1 --report reports/prd.json --source requirements.md
python gate.py --root /project require --run billing-1 --gate ux --reason 'UI is the main product surface'
python gate.py --root /project decide --run billing-1 --step market-research --decision skip --reason 'Internal product; market demand is not a decision'
```

`record` hashes the report, evidence and source inputs. Use real installed
workflow names; `doctor` lists them. `--source` names the inputs whose changes
would invalidate the result, not just the output file. Existing documents can
satisfy a gate after fit/validation; a matching filename alone cannot.

## Story validation

```sh
python gate.py --root /project story --run billing-1 --story 1-1 --file stories/1-1.md --spec specs/1-1.md
python gate.py --root /project record story-validated --run billing-1 --story 1-1 --report reports/1-1-validation.json
python gate.py --root /project check story-validated --run billing-1 --story 1-1
```

The validation report uses the same schema, with `story: "1-1"`, the actual
creation/quick/spec/Build workflow, and validation evidence. The acceptance spec must be a
separate file, kept stable through implementation. A validation may be self-
performed by the creator; code review must use a different actor from dev.
SPEC frontmatter `companions:` are included automatically and resolved relative
to the spec. Missing or escaping companions block registration. `story --input`
adds other stable requirement files. Packets and validation/dev fingerprints
include this complete contract. Keep transient coordination status in notes.
Use `--depends 1-1` when registering a later story; register dependencies first
so IDs form an acyclic graph. IDs match exactly (`2-1` never matches `2-10`).

## Reserve, run, finish

```sh
python gate.py --root /project start --run billing-1 --story 1-1 --phase dev --actor dev-session-1 --workflow bmad-dev-story --model inherited
```

Examples above use the 6.8 story route; on a 6.11 catalog use `bmad-build`
instead of `bmad-dev-story`, and `bmad-spec` for prior acceptance validation.
Quick uses installed `bmad-quick-dev` or `bmad-build`; lite/full reject quick-dev.
The response contains `ticket` and `marker`. Include `BMAD_TICKET:<ticket>` in
Claude worker prompts; Codex uses the same ticket through explicit CLI calls.
The parent reserves before spawning and finishes after observing the worker's
report. The CLI does not spawn models or issue provider requests.

A dev report adds exact run/story identity, checks and source files:

```json
{
  "schema_version": 1,
  "run": "billing-1",
  "story": "1-1",
  "actor": "dev-session-1",
  "workflow": "bmad-dev-story",
  "verdict": "pass",
  "blockers": [],
  "summary": "Implemented idempotent invoice creation; regression checks pass.",
  "evidence": ["reports/1-1-dev-notes.md"],
  "checks": [{"command": "python -m unittest", "exit_code": 0, "log": "reports/1-1-tests.log"}],
  "files": ["billing.py", "tests/test_billing.py"]
}
```

```sh
python gate.py --root /project finish --run billing-1 --ticket TICKET --report reports/1-1-dev.json
python gate.py --root /project start --run billing-1 --story 1-1 --phase review --actor review-session-1 --workflow bmad-code-review
python gate.py --root /project finish --run billing-1 --ticket REVIEW_TICKET --report reports/1-1-review.json
python gate.py --root /project close --run billing-1 --story 1-1
```

A review report has the same base schema, its reviewer identity, code-review
workflow, and evidence containing the actual findings/acceptance assessment.
Checks are optional for a review that examines existing test evidence. A failing
command or unresolved blocker cannot accompany `verdict: pass`. Failure reports
are retained and can finish an attempt as failed. Empty evidence files fail.

Dev `files` must include all changed/deleted and relevant behavior-source paths.
For no-change work, provide `no_changes_reason` and verification. The parent/
reviewer checks this list against the actual diff. Listed deletions are hashed as
absent; recreating the file invalidates the result. Changes to listed code, spec,
reports or logs invalidate success. Don't list mutable lifecycle-only artifacts
as behavior sources. Evidence reports/logs are immutable: new attempt, new paths.

A review ticket snapshots the developer's sources. If they change before finish,
the review is blocked. A new dev attempt invalidates old dev/review records. Dev can extend a completed
dependency's code while its acceptance contract remains stable. Those source
paths are captured again on dev finish. `close` requires current dependencies;
reopen/revalidate earlier stories affected by shared edits using targeted checks
and independent delta review. Whole-file hashes can cause conservative
revalidation; they cannot infer unchanged behavior from a changed file.
`check done` also reevaluates the evidence and dependencies; `status` exposes
waivers alongside booleans so an exception is not silently presented as review.

## Accept native Build review once

A Build workflow may perform independent review within its dev attempt. Count
its actual reviewers in the parent worker budget; the launch hook uses
`BMAD_PARENT_TICKET:<dev-ticket>` on required native child briefs. Preserve that
reviewer's identity and findings rather than claiming the developer reviewed
itself. The reviewer must capture the complete reviewed source snapshot, including
contract, dependencies, changed/deleted files and behavior-relevant sources:

```sh
python gate.py --root /project fingerprint --file specs/1-1.md billing.py tests/test_billing.py
```

Add the returned sorted array to the review report as `reviewed_sources`. Include
all companion/dependency sources when present. Record the actual native workflow
(`bmad-build` or `bmad-code-review`), independent reviewer actor, and
`parent_ticket` equal to the Build dev ticket. Only a completed `bmad-build` dev
attempt can use this route; standalone reviews still require start/finish. After dev
`finish`, the parent can accept the report:

```sh
python gate.py --root /project accept-review --run billing-1 --story 1-1 --report reports/1-1-native-review.json
python gate.py --root /project close --run billing-1 --story 1-1
```

The report's snapshot must exactly match current dev evidence. An active story
attempt, wrong parent ticket, same developer identity, missing evidence, or stale
snapshot blocks it.
A fail remains failed. `accept-review` stores a completed native review; it does
not launch work or grant extra retry attempts. If review was not independent or
changes followed it, run a fresh independent review before close. No extra
code-review is required merely because Build's review used a native child role.

## Context and usage

```sh
python gate.py --root /project packet --run billing-1 --story 1-1 --input context-slim.md architecture/invoices.md --output packets/1-1.json --max-chars 32000
python gate.py --root /project usage --run billing-1 --file reports/usage-1.json
```

Packets contain selected text, paths and SHA-256 values; no model is called.
They fail rather than truncate over budget. They are snapshots: rebuild after
source changes. Their `characters/4` token estimate is approximate and never
billing data. Packet bounds do not restrict future worker reads.

Usage schema: `sample_id` (unique), `source` (`host` or `estimate`), and optional
nonnegative `input_tokens`, `output_tokens`, `cache_read_tokens`,
`cache_write_tokens`. Unknown counters are null. Also record model, host version,
attempt ID, duration and counter semantics when available. This ledger stores
samples; it deliberately does not sum overlapping provider counters or pretend
to know subscription pricing.

## Recovery, budgets, and waivers

```sh
python gate.py --root /project cancel --run billing-1 --ticket TICKET --reason 'Worker stopped at usage limit'
python gate.py --root /project reopen --run billing-1 --story 1-1 --reason 'New acceptance requirement'
python gate.py --root /project extend-budget --run billing-1 --max-attempts 4 --reason 'Diagnosed environment failure; repaired dependency'
python gate.py --root /project lane --run billing-1 --lane full --reason 'Scope now requires new architecture'
python gate.py --root /project waive --run billing-1 --gate code-review --story 1-1 --reason 'Independent host unavailable' --approval 'Exact user approval or reference'
python gate.py --root /project ack-version --run billing-1 --reason 'Reviewed workflow changes; will reassess evidence'
```

Only record a waiver after actual user authorization. Exact scope is mandatory;
reason text never controls matching. Missing story files, dev evidence and stale
sources are not blanket-waivable. No cross-run inheritance, silent downgrade,
or automatic retry-budget reset. `ack-version` clears accepted records and
waivers and requires reassessment; it never updates BMAD. Cancel active attempts
before acknowledging drift. A crashed writer may leave `write.lock`: inspect
running processes before removing an abandoned lock; no automatic lock stealing.

## Honest limits

This is a cooperative workflow ledger, not a sandbox or authentication layer.
Actor IDs, commands, results, file lists and skill invocation are supplied by
agents/users. Hashes prove file consistency, not semantic correctness or that a
command really ran. The hook validates launch preconditions, not all later tool
calls, actor identity, or a worker's first action. Codex enforcement is explicit
CLI discipline; no unsupported hook interception is promised. Human review and
host permission controls remain in force.
