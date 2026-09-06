#!/usr/bin/env python3
"""Install the shared skill and optional roles into one Codex/Claude Code project.

Dry run by default. --apply writes; --upgrade preserves differing files in backup.
No package installation, model override, global configuration or BMAD update.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from gate import GateError, atomic_json, need

PACKAGE_FILES = ["SKILL.md", "gate.py", "requirements.txt", "VERSION", "references", "hooks"]


def planned_files(source, target):
    result = []
    for item in PACKAGE_FILES:
        origin = source / item
        files = sorted(origin.rglob("*")) if origin.is_dir() else [origin]
        for p in files:
            if p.is_file() and "__pycache__" not in p.parts:
                result.append((p, target / p.relative_to(source)))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", required=True, choices=("codex", "claude"))
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--upgrade", action="store_true")
    ap.add_argument("--agents", action="store_true", help="Install the four project role templates")
    ap.add_argument("--hook", action="store_true", help="Register optional Claude launch hook; implies --agents")
    args = ap.parse_args(argv)
    try:
        project = args.project.resolve()
        need(project.is_dir(), "Project directory must exist")
        need(not args.hook or args.platform == "claude", "--hook applies only to Claude Code")
        source = Path(__file__).resolve().parent
        target = project / (".agents" if args.platform == "codex" else ".claude") / "skills" / "orchestrator-bmad"
        need(target.resolve() != source, "Run installer from a separate source checkout")
        files = planned_files(source, target)
        if args.agents or args.hook:
            agents = project / (".codex" if args.platform == "codex" else ".claude") / "agents"
            files += [(p, agents / p.name) for p in sorted((source / "templates" / args.platform).glob("*")) if p.is_file()]
        for _, dest in files:
            need(dest.resolve().is_relative_to(project), f"Install destination escapes project: {dest}")
            need(not dest.exists() or dest.is_file(), f"Destination is unexpectedly not a file: {dest}")
            for parent in dest.parents:
                if parent == project:
                    break
                need(not parent.exists() or parent.is_dir(), f"Destination parent is not a directory: {parent}")
        conflicts = [dest for src, dest in files if dest.exists() and (not dest.is_file() or dest.read_bytes() != src.read_bytes())]
        settings_file = project / ".claude" / "settings.json"
        settings = None
        if args.hook:
            need(settings_file.resolve().is_relative_to(project), "Settings path escapes project")
            settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
            need(isinstance(settings, dict), "Claude settings must be an object")
            hooks = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
            need(isinstance(hooks, list), "PreToolUse settings must be a list")
            hook_path = str(target / "hooks" / "bmad-agent-gate.py")
            # Current Claude exec-form hooks avoid shell quoting on every OS.
            registration = {"matcher": "Agent|Task", "hooks": [{"type": "command", "command": sys.executable,
                                                                  "args": [hook_path], "timeout": 10}]}
            if registration not in hooks:
                hooks.append(registration)
        plan = {"platform": args.platform, "skill": str(target), "files": len(files),
                "conflicts": [str(p) for p in conflicts], "hook": args.hook, "apply": args.apply}
        if not args.apply:
            print(json.dumps(plan, indent=2))
            return 0
        need(not conflicts or args.upgrade, "Existing files differ; inspect dry run, then use --upgrade to back them up")
        backup = project / ".bmad-orchestrator-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        for path in conflicts + ([settings_file] if args.hook and settings_file.exists() else []):
            dest = backup / path.relative_to(project)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.copytree(path, dest)
            else:
                shutil.copy2(path, dest)
        for src, dest in files:
            need(not dest.is_dir(), f"Destination is unexpectedly a directory: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        if settings is not None:
            atomic_json(settings_file, settings)
        print(json.dumps(plan | {"backup": str(backup) if backup.exists() else None}))
        return 0
    except (GateError, OSError, ValueError, TypeError, AttributeError) as e:
        print(f"Install stopped: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
