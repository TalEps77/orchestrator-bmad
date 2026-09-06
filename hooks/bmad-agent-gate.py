#!/usr/bin/env python3
"""Claude Code PreToolUse Agent/Task adapter for explicitly managed v4 projects.

This gates a reserved launch, not subsequent skill invocation or every file edit.
Non-managed projects are untouched. Managed internal errors block with diagnostics.
Register this file IN the installed skill; do not copy it out of the package.
"""
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate

TYPES = {"bmad-worker": "dev", "bmad-reviewer": "review", "bmad-planner": "plan",
         "bmad-researcher": "plan"}


def evaluate(data):
    if data.get("tool_name") not in ("Agent", "Task"):
        return 0
    project = Path(data.get("cwd") or Path.cwd()).resolve()
    for candidate in (project, *project.parents):
        if (candidate / gate.STATE / "ledger.json").is_file():
            project = candidate
            break
    else:
        return 0
    ti = data.get("tool_input", {})
    kind = ti.get("subagent_type", "")
    text = str(ti.get("prompt", "")) + " " + str(ti.get("description", ""))
    mentioned = set(re.findall(r"\bbmad-[a-z][a-z-]+\b", text))
    managed = kind.startswith("bmad-") or bool(mentioned) or "BMAD_TICKET:" in text or "BMAD_PARENT_TICKET:" in text
    if not managed:
        return 0
    parent_matches = re.findall(r"\bBMAD_PARENT_TICKET:([a-f0-9]{32})\b", text)
    if parent_matches:
        gate.need(kind not in TYPES and "BMAD_TICKET:" not in text and len(set(parent_matches)) == 1,
                  "Native substeps need one parent ticket and the native workflow's actual role")
        _, attempt = gate.check_ticket(project, gate.Store(project).read(), parent_matches[0])
        gate.need(attempt["workflow"] in ("bmad-build", "bmad-code-review"), "This workflow has no managed native substep route")
        gate.need(attempt["workflow"] in mentioned, "Native substep must name its parent workflow")
        return 0
    gate.need(kind in TYPES, "Use installed bmad-worker/reviewer/planner/researcher for managed BMAD work")
    matches = re.findall(r"\bBMAD_TICKET:([a-f0-9]{32})\b", text)
    if TYPES[kind] == "plan" and not (mentioned & set.union(*gate.PHASE_WORKFLOWS.values())):
        return 0
    gate.need(len(set(matches)) == 1, "Managed dev/review needs exactly one BMAD_TICKET from gate.py start")
    _, attempt = gate.check_ticket(project, gate.Store(project).read(), matches[0])
    gate.need(TYPES[kind] == attempt["phase"], "Agent role does not match ticket phase")
    gate.need(attempt["workflow"] in mentioned, "Brief must name the ticket's exact BMAD workflow")
    return 0


def main():
    try:
        data = json.load(sys.stdin)
        gate.need(isinstance(data, dict), "Hook input must be an object")
        return evaluate(data)
    except (gate.GateError, OSError, ValueError, TypeError, KeyError) as e:
        print(f"BLOCKED by BMAD v4: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
