# BMAD Orchestrator v4

One workflow contract for Codex and Claude Code. Use full planning for a new
system, lite for an understood epic, and quick for a standalone bounded change.

## Structure

- SKILL.md: scope, routing, lifecycle, context and worker policy.
- references/: one selected host adapter, workflow, ledger, economy policy.
- gate.py: explicit run/story records, evidence fingerprints, attempts, recovery.
- hooks/bmad-agent-gate.py: optional Claude launch preconditions.
- templates/: optional Claude Markdown and Codex TOML worker roles.
- install.py: project-scoped installation with dry run and upgrade backups.
- tests/: runnable local regression and installation checks.

## Flow

Doctor and scope selection; applicable planning and validation; story plus stable
acceptance spec; focused context packet; bounded dev attempt; independent review;
current evidence check; BMAD tracker update; integration/acceptance at epic close.
A failed or stale result remains incomplete until corrected or explicitly waived
where a scoped waiver is allowed.

## Economy

Direct bounded commands for small chores. Relevant context sections for workers.
Creation and checklist validation share context; code review stays independent.
Targeted retries reuse useful context. Full logs stay in files. No global terse
style, forced one-liners, speculative features, or mandatory HTML rendering.
The package does not claim a measured cost-saving percentage.

## Host differences

Both hosts use the same CLI and evidence schema. Codex runs preflight explicitly;
Claude can also block mismatched Agent/Task launches through a hook. Available
models, tool APIs and custom agent support are discovered at runtime. Neither
adapter overrides existing user authorization or host permissions.

## Evidence limits

Fingerprints establish freshness. Parent/reviewer verification establishes that
reports describe real work and cover the actual diff. This is a cooperative
workflow mechanism, not a security sandbox. Read README.md, references/ledger.md,
and docs/validation.md before adopting the release in a project.
