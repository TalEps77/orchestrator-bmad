# Orchestrator (BMAD) · v4.0.0

Run BMAD product development with a shared skill for **Codex and Claude Code**.
Keep coordination small, give workers relevant context, and close work only with
explicit, current evidence. This package is a skill plus local Python helpers;
it does not run an LLM service or replace BMAD.

## What changed from v3

- Shared instructions plus one host adapter; no universal Claude tool names,
  Homebrew paths, or model aliases.
- Exact run/story IDs and structured pass/fail reports replace filename globs.
- Source/evidence fingerprints invalidate stale success. Independent review
  identity, dependency completion, and bounded attempts are checked explicitly.
- Atomic locked ledger updates; status/doctor are read-only and offline.
- Small context packets, targeted retries, scoped code simplicity and concise
  internal reports. No mandatory HTML twins or delegate-every-command rule.
- Catalog-aware routing covers old story workflows and native Build/spec,
  including required spec companions and reuse of independent native review.
- Project installers, optional role templates, a Claude launch hook, and a
  reproducible Python regression suite.

See [design and migration](docs/v4-design.md), [workflow overview](docs/skill-overview.md),
and [validation scope](docs/validation.md). Previous releases remain in Git.

## Requirements

- Python 3.11+ and `PyYAML>=6.0.2,<7` (declared in `requirements.txt`).
- An installed [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD)
  integration for the host you use. Install/configure it in the target project;
  the orchestrator never silently upgrades it.
- Codex or Claude Code with skill support and local command execution.
  Delegation is useful for independent review; if unavailable, report that gap.

## Install in a project

The `v4.0.0` release branch identifies this version; it is not a GitHub Release
object. Clone it into a separate source checkout and install its dependency
in your Python environment. A virtual environment is recommended.

```sh
git clone --branch v4.0.0 https://github.com/TalEps77/orchestrator-bmad.git
cd orchestrator-bmad
python -m pip install -r requirements.txt
```

Preview first; add `--apply` to write:

```sh
python install.py --platform codex --project /path/to/project --agents
python install.py --platform codex --project /path/to/project --agents --apply

python install.py --platform claude --project /path/to/project --hook
python install.py --platform claude --project /path/to/project --hook --apply
```

`--agents` installs four project roles. Claude `--hook` includes those roles and
merges its PreToolUse entry with existing project settings. Without `--hook`, the
same explicit ledger CLI works in either host. Codex gets no automatic hook.
Templates inherit configured models instead of choosing unsupported defaults.
The host may constrain agent definitions or model controls; consult its adapter.
On Windows use the available `python`/`py` executable and actual project paths.

Differing existing files block installation. After inspecting the dry run, add
`--upgrade` to preserve them under `.bmad-orchestrator-backups/` and install the
new files. The installer changes only the selected project's skill, requested
roles, and optional Claude hook entry. It never changes global configuration.
Remove an old v3 standalone hook registration when moving to v4; don't run both.

## Use

In Codex, request `$orchestrator-bmad`; in Claude Code, `/orchestrator-bmad`.
For example:

> Use orchestrator-bmad to build this system from the agreed requirements.
> Start with full planning, then implement and independently review its stories.

The skill chooses quick/lite/full according to scope and uses only the selected
host adapter. To inspect a project directly:

```sh
python /path/to/installed/skill/gate.py --root /project doctor
python /path/to/installed/skill/gate.py --root /project status --run my-run
```

See the [CLI and report contract](references/ledger.md) for initialization,
validation, start/finish/close, context packets, recovery, and usage samples.

## What is enforced

| Capability | Codex | Claude Code |
|---|---|---|
| Shared workflow and reports | Yes | Yes |
| Explicit CLI preflight, fingerprint and completion checks | Yes | Yes |
| Managed dev/review attempt and retry limits | Yes, through CLI | Yes, through CLI |
| Native launch interception | Not supplied; parent calls CLI | Optional Agent/Task PreToolUse hook |
| Automatic proof that a skill/test really ran | No | No |
| Model selection and worker availability | Host-dependent | Host-dependent |

This is a cooperative evidence ledger, not a security sandbox. Actor IDs, command
results and file lists are assertions that the parent/reviewer must verify.
Hashes establish freshness; they do not establish correctness. Reviewers check
the full diff/file list. Host permission controls remain authoritative.

## Token policy

Preserve the main context without assuming that more agents means fewer tokens.
Use focused packets, bounded workers and relevant regression checks. Prefer
existing code and platform capabilities; preserve accepted functionality.
Compress internal reports, not requirements or correctness. Ponytail and Caveman
were considered as scoped influences, not installed as global modes; see the
[phase policy](references/economy.md).

The package makes no measured cost-reduction claim. Host token counters may be
stored with their provenance; packet estimates use characters/4 and are not
billing measurements. Cache hits depend on the actual runtime and prompt prefix.

## Development and rollback

```sh
python -m unittest discover -s tests -v
python gate.py --version
```

To inspect the old release without altering this checkout:

```sh
git worktree add ../orchestrator-bmad-v3 v3.1.0
```

Keep the v4 ledger and reports when rolling back. v3 uses its legacy YAML; v4 uses
`.bmad-orchestrator/ledger.json`. Neither format is silently converted into
successful evidence. Reinstall the chosen version's files/roles/hooks together;
see [migration and rollback](docs/v4-design.md#release-and-rollback).

MIT license. Third-party projects linked above retain their own licenses.
