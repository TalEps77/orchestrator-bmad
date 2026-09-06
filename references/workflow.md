# BMAD workflow and completion

## Select the scope once

A run represents a bounded user objective, not the lifetime of a repository.
Resume its exact ID across sessions. New goals get new IDs. Default to full for
a new system; use lite for one understood epic and quick for standalone changes.
Do not use quick to bypass an existing sprint's story lifecycle. Check the
actual sprint tracker before selecting it. The CLI additionally rejects quick
when a conventional active tracker is detected; unusual layouts need inspection.

`doctor` lists workflows from the project's BMAD help CSV. Use those installed
names, not an assumed BMAD release. Unknown required workflows remain required
and need explicit evidence. A malformed/missing catalog requires repairing the
install. Required catalog entries are the minimum; add task-specific gates.
An optional workflow is considered when its trigger matters, not at every phase
boundary. Record meaningful run/skip decisions once; don't log every nonexistent
need on every story.

## Match the installed lifecycle

| Installed catalog | Story/spec and implementation | Review |
|---|---|---|
| BMAD 6.8 style | create-story + dev-story; quick-dev for standalone work | Separate installed code-review |
| BMAD 6.11 style | bmad-spec for validated acceptance; bmad-build for implementation in any lane | Accept independent review already performed inside Build; extra code-review only when needed |

These are tested catalog shapes, not a version-number switch. Inspect the local
catalog and loaded skill. Do not call create-story/quick-dev on installs that no
longer expose them. In 6.11 sprint planning includes readiness; don't invent an
extra readiness workflow absent from that catalog.

Native workflow entrypoints are authoritative. For example, 6.11 Build requires
its renderer to produce a resolved workflow snapshot. Invoke its installed
SKILL.md exactly as directed, read the returned snapshot and its current step,
and halt on a renderer failure as instructed. Never substitute the unresolved
source workflow, skip required steps, or load all steps just to compress them.
Preserve actual user checkpoints and existing authorization.

Use the native SPEC as the stable contract when available. Its frontmatter
`companions:` files are equally binding and are automatically included in CLI
fingerprints/packets, relative to SPEC.md. Fully absorbed `sources:` remain audit
references according to the native spec workflow. Additional stable requirement
files can be registered with `story --input`. Never drop a companion to meet a
packet target; enlarge the packet or select a genuinely bounded story contract.
Keep mutable execution status in a separate story/dispatch note; create a small
note if that install has no separate story file. Keep native memlog and story
breakdown conventions intact.

## Plan

- Brownfield: map relevant code, conventions, and build/test commands. Reuse a
  current project context; make a slim task-relevant view with source links.
- Unsettled scope: discovery/product brief; PRFAQ or research only when it would
  resolve an actual decision. Ask material questions before committing to scope.
- PRD: create and validate in the same worker; persist the validation findings.
- Architecture: reuse if current, otherwise resolve interfaces/data/contracts.
- UI as a primary surface: require UX evidence even in lite (`require --gate ux`).
- Epics/stories and readiness: follow applicable installed BMAD workflows.
  Lite may exempt readiness; full must account for it. Never silently waive it.
- Sprint planning: use the real tracker and dependencies; filenames are not
  proof that a workflow succeeded. Register planning results with their source
  requirements so later edits make the gate stale.

Research, multiple-persona discussion and extra adversarial passes are optional
when their decision/risk justifies them. Avoid duplicating review lenses already
inside the installed code-review workflow.

## Story lifecycle

1. The creator writes the BMAD story and a separate stable acceptance spec,
   then validates that both agree. The spec records behavior, constraints,
   acceptance criteria, dependencies, and source references. This small extra
   artifact separates requirements from mutable BMAD dev notes/status.
2. Register exact story/spec paths and dependency IDs. Record validation using
   its structured report. A changed spec needs fresh validation, dev and review;
   do not silently replace the spec to make old checks pass.
3. Build the context packet. Reserve dev only after required planning gates,
   validation and dependencies pass. Put the returned ticket in the worker brief.
4. Invoke the installed dev workflow; write code and relevant regression checks.
   Save full check output and the exit status. Capture pipeline exit codes
   correctly: piping through a successful formatter is not a passing test.
5. Finish dev with its report and complete changed/behavior-relevant file list,
   including deletions. Verification evidence must describe what actually ran.
6. If Build already ran an independent native reviewer, preserve its actual
   identity, findings and `reviewed_sources` fingerprints. After finishing dev,
   use `accept-review` to register that report. This is one review, not a second
   model call. Require fresh review if fixes changed the reviewed snapshot.
   Otherwise reserve a different agent/session for installed code-review.
   Give it acceptance criteria, source paths and current changes without the
   developer's private reasoning. Confirm the reported file list matches the
   actual diff, and inspect affected callers/contracts. The CLI fingerprints
   listed files; it cannot detect an omitted dependency by semantic inference.
7. On findings, resume the developer for targeted fixes, reserve a new dev
   attempt, rerun affected checks and return to independent review. A new dev
   pass invalidates old review. Reuse the reviewer for a delta check when its
   original scope still holds. After the attempt budget is exhausted, diagnose
   before extending it; a lower-cost model is useful only if it can finish well.
8. Close after current evidence passes. Update BMAD lifecycle notes and tracker
   through the installed workflow. Exclude mutable tracker/notes from code
   fingerprints unless their content affects behavior. Evidence reports and
   saved logs are immutable; use new paths for each attempt.

## Integration and recovery

Parallel code changes require explicit file ownership. For shared files, choose
sequential writers or isolated worktrees. Whole-file hashes are deliberately
conservative: extending a shared file can make an earlier story stale even when
its behavior still works. Dev may edit dependency code; it freezes acceptance
contracts instead. Before dependent close, reopen/revalidate affected earlier
stories against the combined code, with targeted checks and independent delta
review. Preserve implementation; do not rebuild working code just to refresh a
record. Reuse real test logs and one reviewer across compatible checks, but write
exact story-scoped reports. If this repeats, choose more cohesive story boundaries
and measure the revalidation cost. Separate worktree ledgers do not share
a global concurrency limit: the parent must count workers across worktrees.
Revalidate the merged result in the integration checkout before marking the epic
complete. Do not copy a passing record from one worktree as proof of another.

At epic close register an explicit integration gate (`require --gate integration`)
and evidence from the appropriate installed QA/test workflow. Exercise critical
user journeys and cross-story contracts; perform targeted security, permission,
state-machine and migration checks when touched. Run retrospective/status updates
when relevant to the next epic. No mandatory HTML twins or per-story rendering.

A stopped worker leaves an active ticket until the parent confirms it stopped
and cancels it. Resume usable context, preserve unfinished files, and never
restart destructive operations blindly. Dependency/spec changes invalidate
related evidence. Keep failed reports for diagnosis. For metadata drift,
review workflow compatibility before `ack-version`; it invalidates old accepted
records and waivers while leaving source reports and event history intact.

Waivers document actual user authorization with exact run, gate and optional
story scope. They are not generated to satisfy a failing command. Report waived
quality gates as waived in the final outcome. Approval records and actor IDs
are auditable assertions, not an independent authentication/security system.
