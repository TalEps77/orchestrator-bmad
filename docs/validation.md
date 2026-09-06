# v4.0.0 validation

Observed on 2026-09-06. Source baseline:
`afdea2ad5b65fafdbdf030ac4b32a277640f3504` (v3.1 code plus README update).

## Reproducible checks

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python gate.py --version
```

Local Linux/Python 3.12.13: **52 tests passed**. The skill creator's frontmatter
validator also passed. CI is configured for Linux and Windows, Python 3.11 and
3.13; consult the release PR's checks for observed CI results.

Coverage includes a successful lifecycle; empty/failing/stale evidence; exact
run/story identity; independent reviewer identity; attempt reuse and budgets;
concurrent updates; read-only drift detection and explicit recovery; exact
waivers; dependency/shared-file revalidation; spec companions; bounded packets;
usage provenance; installation, backups, settings preservation and hook execution.
Native review tests require a completed Build parent ticket and exact reviewed
sources; standalone review cannot bypass its reservation through that route.

Real upstream catalog projections cover BMAD 6.8 full and BMAD 6.11 full/quick
cycles. Fixtures record source commits. These tests execute the real ledger with
synthetic reports; they do **not** claim the upstream LLM workflows ran.

## Independent forward exercise

A separate Codex worker received this skill and a small inventory project. The
request was atomic reservation, duplicate aggregation, dry-run preview, and
rejection of unknown items, negative quantities and insufficient stock. It read
the local workflow fixtures, created/validated a stable spec, implemented the
feature, saved seven passing regression tests and correctly left review open.

A fresh reviewer loaded the review fixture, inspected the actual changes and
acceptance contract, reran all seven tests and ran an independent bounded request
matrix. It reported no blockers. The parent accepted its evidence and closed
run `reserve-dry-run`, story `1-1`. The developer and reviewer had distinct actual
agent contexts. No waiver was used. Session coordination status found in the
acceptance spec informed the new instruction to keep that status in story notes.

This is a small behavior/usability exercise with **synthetic local BMAD skills**.
It is not an end-to-end run of BMAD 6.11's renderer or native Claude Code. The
native Codex and Claude executables were not installed in the test environment.
Adapters were checked against official documentation; custom role discovery,
permission dialogs, native nested-worker limits and Claude's actual hook dispatch
still need verification in the intended host/version before a large system run.

## Efficiency evidence

The main SKILL.md decreased from 22,755 to 7,265 UTF-8 bytes (68.1%). This measures
one entrypoint file, not total prompt tokens or billed usage. References and
native BMAD instructions are loaded as needed and add context when read. No
provider token counters or comparable v3/v4 full-run bills were available.

The concrete economy changes are smaller initial instructions, one host adapter,
complete focused packets, bounded attempts/workers, targeted retries, no routine
HTML twins, and no duplicate review when native Build already supplied independent
evidence. Conservative whole-file freshness can add revalidation cost after
shared edits; measure this during the first real multi-story pilot.

## Adoption boundary

Use a representative feature in the intended Codex/Claude installation first.
Confirm local workflow discovery, native renderer prerequisites, real reviewer
isolation, changed-file coverage and recovery after interruption. Then exercise
cross-story integration and measure usage before adjusting budgets. The helper
checks reported evidence and freshness; it cannot authenticate actor identities,
prove tool execution, infer omitted behavior dependencies, or enforce all host
workers. No production-readiness or fixed token-saving percentage is claimed.
