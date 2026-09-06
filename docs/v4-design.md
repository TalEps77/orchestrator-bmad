# v4 design and migration

## Objective and acceptance

Ship one maintainable BMAD orchestration skill for Codex and Claude Code that can
support a real system build. Preserve the previous Git release. Improve actual
work control and evidence reliability before making cost-saving claims.

Accepted invariants:

1. IDs match exactly; an unrelated story/file never satisfies a gate.
2. A pass needs a structured verdict, no blockers and nonempty evidence.
3. Recorded sources/evidence must still match their fingerprints.
4. Dev and review use different reported agent/session identities.
5. Concurrent cooperating writers cannot lose ledger updates.
6. Read-only commands cannot acknowledge metadata drift.
7. Waivers are exact, explicitly authorized and local to a run.
8. Host-specific tools/models stay in adapters; unsupported capabilities are
   disclosed rather than simulated.
9. The parent owns lifecycle mutations; workers return reports and evidence.
10. Constraints and quality survive both code and communication compression.

## Architecture decisions

Keep `SKILL.md` as the routing/operating contract. Load one host adapter plus
workflow/evidence/economy references only when needed. Keep `gate.py` as the
portable executable entry point; Python stdlib handles JSON, hashing and atomic
writes, and PyYAML handles BMAD metadata rather than another handwritten parser.

Use `.bmad-orchestrator/ledger.json` at an explicit project root. This deliberately
separates orchestration state from variable BMAD artifact locations. Reports
reference exact project-relative files in any configured BMAD output directory;
there is no discovery-by-filename inference. Catalog/config fingerprints detect
version/installation changes. No network check runs on session start.

Keep a stable acceptance spec alongside the mutable BMAD story. A validation
binds the spec's bytes, while BMAD can update its story's dev notes and status.
Native SPEC companions are part of that contract and are loaded/fingerprinted
automatically. Session coordination status stays outside acceptance. The parent
verifies that the story still implements the accepted contract.
Dev fingerprints include the spec and complete relevant source file list;
review snapshots those same sources. Source-list completeness remains a review
responsibility, not an impossible promise of static semantic inference.

Cooperating writers use a short mkdir lock and atomic JSON replacement. Lock
recovery is manual after confirming no writer remains. This is intended for a
local filesystem; separate worktrees each have independent ledgers, and the
parent handles cross-worktree scheduling and integration evidence.

Attempt reservations enforce registered dev/review concurrency and per-phase
retry limits. They do not claim to count arbitrary host workers or nested agents.
Small tasks run directly; larger independent tasks use bounded workers. Work is
scheduled by real dependencies and file ownership, not rigid global wave barriers.

Reports retain raw logs and actual exit codes. JSON validates structure and
freshness but cannot prove execution, authenticate a model, or audit a hidden
reasoning trace. The same honest limit applies to the optional Claude launch
hook. Codex uses the explicit CLI contract; no assumed Claude-compatible hook.

## Native BMAD compatibility

Inspect the installed catalog rather than hard-code a version threshold. The
6.8 catalog uses create-story/dev-story and a separate readiness workflow. The
6.11 catalog uses spec/Build, renames architecture, and puts readiness in sprint
planning. Build already includes review: accept a real independent child report
bound to the completed Build ticket and exact source snapshot. Standalone review
keeps its own reserved attempt. Required native children use the parent budget;
the Claude hook has a distinct parent-ticket route. Runtime rendering and step
checkpoints remain the native workflow's responsibility.

## Ponytail and Caveman decision

Considered upstream SKILL.md versions on 2026-09-06:
- Ponytail blob `02c0712c86277d49d18a77da3a2b825657bf02d1`.
- Caveman blob `ea8bf271fc89cb783a19c54d9d0b5fdaec48a482`.

Adopt the ideas of reusing proven capabilities, avoiding speculative complexity,
and concise evidence handoffs. Write a narrow policy ourselves instead of copying
or loading their persistent global modes. Reject forced one-liners, test ceilings,
reduced requested functionality, suppression of progress, and compressed human
requirements/consent. Phase-specific details live in references/economy.md.

## Release and rollback

This is a major version because the ledger/CLI and installation contract change.
The source baseline is `afdea2ad5b65fafdbdf030ac4b32a277640f3504`; the prior
`v3.1.0` tag remains intact. The baseline only adds README changes after that tag.

1. Build/test v4 on `release/v4.0.0` and publish a reviewable Git commit/PR.
2. Preserve existing history; merge the tested PR and create the `v4.0.0` release
   branch at that version. This release reference is a branch, not a GitHub
   Release object or tag. Do not advance it with unrelated development.
3. Install v4 into a clean project, or use the installer upgrade backup after
   reviewing conflicts. Remove the old standalone Claude hook registration.
4. Start a new v4 run. Leave `_bmad-output/gate-ledger.yaml` and any custom legacy
   output folder untouched. Reassess existing artifacts and record evidence;
   never import old filename-based successes or broad waivers automatically.
5. Roll back by checking out `v3.1.0` in another source worktree and restoring
   the installation's backed-up files/configuration. For former manual global
   installs, restore their original skill directory and hook registration.
   Do not run a v3 hook against a partially restored v4 installation.
6. Preserve the v4 ledger and reports for audit. Rolling back the skill does not
   roll back product code, deployments or database migrations.

No global automatic installation is included. This repository is the source of
truth; publishing it does not mean a particular Codex/Claude installation has
already activated it.

## Validation and limitations

See validation.md for observed checks, host coverage and outstanding boundaries.
Measure representative real BMAD quick/lite/full runs before tuning the default
budgets or asserting a total token saving. Correctness and completion are the
acceptance criteria; a shorter transcript alone is not success.
