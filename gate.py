#!/usr/bin/env python3
"""Portable BMAD v4 ledger. Explicit evidence; no filename inference or network calls."""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import time
import uuid

VERSION = "4.0.0"
STATE = ".bmad-orchestrator"
ALIASES = {
    "bmad-prd": "prd", "bmad-create-prd": "prd",
    "bmad-create-architecture": "architecture", "bmad-architecture": "architecture",
    "bmad-create-epics-and-stories": "epics", "bmad-epics": "epics",
    "bmad-check-implementation-readiness": "readiness", "bmad-ux": "ux",
    "bmad-sprint-planning": "sprint", "bmad-retrospective": "retro",
}
CYCLE = {"bmad-create-story", "bmad-dev-story", "bmad-build", "bmad-code-review"}
EXEMPT = {"quick": {"prd", "architecture", "epics", "readiness", "sprint", "ux"},
          "lite": {"readiness", "ux"}, "full": set()}
PHASE_WORKFLOWS = {"dev": {"bmad-dev-story", "bmad-build", "bmad-quick-dev"},
                   "review": {"bmad-code-review"}}


class GateError(Exception):
    pass


def need(condition, message):
    if not condition:
        raise GateError(message)


def identifier(value):
    need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value),
         "IDs use 1-96 letters, digits, dots, underscores or hyphens")
    return value


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def root(value=None):
    p = Path(value or os.getcwd()).resolve()
    if value:
        need(p.is_dir(), "Project root is not a directory")
        return p
    for candidate in (p, *p.parents):
        if (candidate / "_bmad").is_dir() or (candidate / STATE).is_dir():
            return candidate
    raise GateError("No BMAD project found; pass --root PATH explicitly")


def path_in(project, value):
    p = (project / value).resolve()
    need(p.is_relative_to(project), f"Path escapes project: {value}")
    return p


def file_ref(project, value, nonempty=True):
    p = path_in(project, value)
    need(p.is_file(), f"Missing file: {value}")
    if nonempty:
        need(p.stat().st_size > 0, f"Empty file: {value}")
    return {"path": p.relative_to(project).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def snapshot(project, files):
    need(isinstance(files, list) and all(isinstance(x, str) for x in files), "files must be a list of paths")
    result = []
    for name in sorted(set(files)):
        p = path_in(project, name)
        need(not p.is_dir(), f"Source is a directory: {name}")
        result.append({"path": p.relative_to(project).as_posix(),
                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None})
    return result


def fresh(project, refs):
    return snapshot(project, [x["path"] for x in refs]) == sorted(refs, key=lambda x: x["path"])


def contract_refs(project, story):
    """BMAD SPEC companions are requirements, not optional context compression."""
    import yaml
    spec = path_in(project, story["spec"])
    text = spec.read_text(encoding="utf-8-sig")
    companions = []
    if text.startswith("---\n") or text.startswith("---\r\n"):
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        need(match is not None, "Unclosed spec frontmatter")
        try:
            header = yaml.safe_load(match[1]) or {}
        except yaml.YAMLError as e:
            raise GateError(f"Invalid spec frontmatter: {e}") from e
        need(isinstance(header, dict), "Spec frontmatter must be a mapping")
        companions = header.get("companions", [])
        need(isinstance(companions, list) and all(isinstance(p, str) and p.strip() for p in companions),
             "Spec companions must be a list of relative file paths")
    files = [story["spec"], *story.get("context", [])]
    for name in companions:
        need(not Path(name).is_absolute(), "Spec companions must be relative to the spec")
        files.append(str(spec.parent / name))
    refs = [file_ref(project, p) for p in files]
    return snapshot(project, [r["path"] for r in refs])


def read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise GateError(f"Cannot read JSON {p}: {e}") from e


def atomic_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Store:
    def __init__(self, project):
        self.project = project
        self.path = project / STATE / "ledger.json"

    def read(self):
        need(self.path.is_file(), "No v4 ledger. Run init; legacy YAML is never auto-approved or overwritten")
        d = read_json(self.path)
        need(isinstance(d, dict) and d.get("schema_version") == 4 and isinstance(d.get("runs"), dict),
             "Invalid ledger schema; restore a known good copy, do not reset it")
        return d

    @contextlib.contextmanager
    def transaction(self, create=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.parent / "write.lock"
        deadline = time.monotonic() + 10
        while True:
            try:
                lock.mkdir()
                break
            except FileExistsError:
                need(time.monotonic() < deadline, f"Ledger busy: {lock}. Check writers before recovering a stale lock")
                time.sleep(0.05)
        try:
            data = self.read() if self.path.exists() else None
            need(data is not None or create, "No v4 ledger. Run init first")
            data = data if data is not None else {"schema_version": 4, "runs": {}}
            yield data
            atomic_json(self.path, data)
        finally:
            lock.rmdir()


def sprint_active(project):
    """Inspect standard/configured BMAD output trackers; unfamiliar layouts stay a host check."""
    import yaml
    bases = {project / "_bmad-output"}
    for cfg in (project / "_bmad").glob("*/config.yaml"):
        raw = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        need(isinstance(raw, dict), f"Invalid BMAD config: {cfg}")
        for key in ("output_folder", "implementation_artifacts"):
            value = raw.get(key)
            if isinstance(value, str):
                value = value.replace("{project-root}", str(project))
                need("{" not in value, f"Unresolved path in {cfg}: {key}")
                bases.add(path_in(project, value))
    for cfg in (project / "_bmad" / "config.toml", project / "_bmad" / "config.user.toml"):
        if cfg.is_file():
            raw = tomllib.loads(cfg.read_text(encoding="utf-8"))
            for group in raw.values():
                if isinstance(group, dict):
                    for key in ("output_folder", "implementation_artifacts"):
                        value = group.get(key)
                        if isinstance(value, str):
                            value = value.replace("{project-root}", str(project))
                            need("{" not in value, f"Unresolved path in {cfg}: {key}")
                            bases.add(path_in(project, value))
    for base in bases:
        for tracker in base.rglob("sprint-status.yaml"):
            raw = yaml.safe_load(tracker.read_text(encoding="utf-8")) or {}
            def active(value):
                if isinstance(value, dict):
                    return any(active(x) for x in value.values())
                if isinstance(value, list):
                    return any(active(x) for x in value)
                return value in ("in-progress", "ready-for-dev", "review")
            if active(raw):
                return True
    return False


def metadata(project):
    try:
        import yaml
    except ImportError as e:
        raise GateError("PyYAML is required for BMAD manifests: python -m pip install -r requirements.txt") from e
    config = project / "_bmad" / "_config"
    need(config.is_dir(), "BMAD is not installed here. Install its Claude Code or Codex integration first")
    manifest = config / "manifest.yaml"
    help_file = config / "bmad-help.csv"
    need(manifest.is_file() and help_file.is_file(), "BMAD manifest.yaml or bmad-help.csv missing; repair the install")
    try:
        raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        need(isinstance(raw, dict), "BMAD manifest must be a mapping")
        version = raw.get("installation", {}).get("version") if isinstance(raw.get("installation"), dict) else None
        version = version or raw.get("version")
        need(isinstance(version, (str, float, int)), "BMAD version is missing")
        with help_file.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        skills = {}
        required = set()
        for row in rows:
            skill = (row.get("skill") or row.get("command") or "").strip().lstrip("/")
            if not skill.startswith("bmad-"):
                continue
            skills[skill] = ALIASES.get(skill, skill)
            if str(row.get("required", "")).lower().strip() == "true" and skill not in CYCLE:
                required.add(skills[skill])
        need(skills, "No BMAD workflows found in bmad-help.csv; unsupported manifest schema")
    except (ValueError, OSError, yaml.YAMLError) as e:
        raise GateError(f"Invalid BMAD metadata: {e}") from e
    refs = [file_ref(project, manifest), file_ref(project, help_file)]
    refs += [file_ref(project, p) for p in sorted((project / "_bmad").glob("*/config.yaml"))]
    refs += [file_ref(project, p) for p in (project / "_bmad").glob("config*.toml")]
    refs += [file_ref(project, p) for p in (project / "_bmad" / "custom").rglob("*.toml")]
    return {"version": str(version), "refs": refs, "skills": skills, "required": sorted(required)}


def run_of(data, run_id):
    identifier(run_id)
    need(run_id in data["runs"], f"Unknown run: {run_id}")
    return data["runs"][run_id]


def story_of(run, story_id):
    need(story_id in run["stories"], f"Unknown story: {story_id}")
    return run["stories"][story_id]


def event(run, action, **details):
    run["events"].append({"at": now(), "action": action, **details})


def version_ok(project, run):
    need(metadata_current(project, run), "BMAD manifests changed: doctor, review compatibility, then ack-version")


def metadata_current(project, run):
    return sorted(metadata(project)["refs"], key=lambda x: x["path"]) == sorted(run["bmad"]["refs"], key=lambda x: x["path"])


def evidence_ok(project, record):
    return bool(record and record["verdict"] == "pass" and not record["blockers"]
                and fresh(project, record["refs"]) and fresh(project, record["sources"]))


def waived(project, run, gate, story=None):
    # Exact scope. Never inspect the reason text or import previous-run waivers.
    return any(w["gate"] == gate and w.get("story") == story and not w.get("revoked")
               and fresh(project, w.get("sources", [])) for w in run["waivers"])


def exemptions(run):
    return EXEMPT[run["lane"]] - set(run.get("extra_required", []))


def gate_ok(project, run, gate, story=None):
    if story is None:
        return evidence_ok(project, run["gates"].get(gate)) or waived(project, run, gate)
    s = story_of(run, story)
    if gate == "story":
        return path_in(project, s["file"]).is_file() and path_in(project, s["spec"]).is_file()
    if gate == "done":
        return (s["closed"] and planning_ok(project, run)
                and gate_ok(project, run, "story-validated", story) and gate_ok(project, run, "dev", story)
                and gate_ok(project, run, "code-review", story)
                and all(gate_ok(project, run, "done", dep) for dep in s["depends"]))
    return evidence_ok(project, s["gates"].get(gate)) or waived(project, run, gate, story)


def planning_ok(project, run):
    return all(x in exemptions(run) or gate_ok(project, run, x) for x in run["required"])


def plan_ready(project, run):
    missing = [x for x in run["required"] if x not in exemptions(run) and not gate_ok(project, run, x)]
    need(not missing, "Planning gates missing/stale: " + ", ".join(missing))


def load_report(project, report_path, workflow=None, actor=None, require_checks=False):
    report = read_json(path_in(project, report_path))
    need(isinstance(report, dict) and report.get("schema_version") == 1, "Report schema_version must be 1")
    for field in ("actor", "workflow", "summary"):
        need(isinstance(report.get(field), str) and report[field].strip(), f"Report needs {field}")
    need(report.get("verdict") in ("pass", "fail"), "Report verdict must be pass or fail")
    need(isinstance(report.get("blockers"), list), "Report needs blockers list (empty when none)")
    if actor:
        need(report["actor"] == actor, "Report actor does not match the reserved attempt")
    if workflow:
        need(report["workflow"] == workflow, "Report workflow does not match the reserved attempt")
    need(report["verdict"] != "pass" or not report["blockers"], "A pass cannot contain blockers")
    paths = report.get("evidence")
    need(isinstance(paths, list) and paths and all(isinstance(x, str) for x in paths), "Report needs evidence file paths")
    refs = [file_ref(project, report_path)] + [file_ref(project, p) for p in paths]
    checks = report.get("checks", [])
    need(isinstance(checks, list), "checks must be a list")
    if require_checks and report["verdict"] == "pass":
        need(checks, "Passing dev work needs runnable verification with a saved log")
    for check in checks:
        need(isinstance(check, dict) and isinstance(check.get("command"), str) and check["command"].strip()
             and type(check.get("exit_code")) is int, "Each check needs command and integer exit_code")
        refs.append(file_ref(project, check.get("log", "")))
        need(report["verdict"] != "pass" or check["exit_code"] == 0, "A failing check cannot produce a pass")
    return {"verdict": report["verdict"], "actor": report["actor"], "workflow": report["workflow"],
            "summary": report["summary"], "blockers": report["blockers"], "refs": refs,
            "sources": [], "recorded": now()}, report


def check_ticket(project, data, ticket):
    matches = [(r, a) for r in data["runs"].values() for a in r["attempts"].values() if a["id"] == ticket]
    need(len(matches) == 1, "Unknown attempt ticket")
    run, attempt = matches[0]
    need(attempt["state"] == "active", "Attempt is no longer active")
    version_ok(project, run)
    need(fresh(project, attempt["inputs"]), "Attempt inputs changed; cancel and reserve again")
    # Dev may legitimately extend a dependency's code. Acceptance stays frozen;
    # affected dependencies must be revalidated before final close, not mid-edit.
    if attempt["phase"] == "dev":
        plan_ready(project, run)
        need(gate_ok(project, run, "story-validated", attempt["story"]), "Story validation is missing/stale")
    else:
        need(gate_ok(project, run, "dev", attempt["story"]), "Dev evidence is missing/stale")
    return run, attempt


def execute(args):
    project = root(args.root)
    store = Store(project)
    cmd = args.cmd
    if cmd == "fingerprint":
        return snapshot(project, args.file), False
    if cmd == "doctor":
        info = metadata(project)
        issues = []
        if store.path.exists():
            data = store.read()
            for run_id, run in data["runs"].items():
                if not metadata_current(project, run):
                    issues.append(f"{run_id}: BMAD metadata drift; review then ack-version")
        return {"version": VERSION, "bmad": info["version"], "workflows": sorted(info["skills"]),
                "required": info["required"], "issues": issues, "read_only": True}, bool(issues)
    if cmd in ("status", "check", "history"):
        data = store.read()
        run = run_of(data, args.run)
        version_ok(project, run)
        if cmd == "history":
            return run["events"], False
        if cmd == "check":
            need(args.gate in run["required"] or args.gate in run["gates"] or args.gate in
                 ("story", "story-validated", "dev", "code-review", "done"), "Unknown gate")
            ok = gate_ok(project, run, args.gate, args.story)
            return {"gate": args.gate, "story": args.story, "pass": ok}, not ok
        gates = {g: ("exempt" if g in exemptions(run) else "pass" if gate_ok(project, run, g) else "missing/stale")
                 for g in run["required"]}
        stories = {sid: {g: gate_ok(project, run, g, sid) for g in ("story-validated", "dev", "code-review", "done")}
                   for sid in run["stories"]}
        active = [a["id"] for a in run["attempts"].values() if a["state"] == "active"]
        return {"run": args.run, "lane": run["lane"], "gates": gates, "stories": stories,
                "active": active, "waivers": run["waivers"], "usage_samples": len(run["usage"])}, False
    if cmd == "packet":
        data = store.read()
        run = run_of(data, args.run)
        version_ok(project, run)
        story = story_of(run, args.story)
        files = list(dict.fromkeys([r["path"] for r in contract_refs(project, story)] + [story["file"], *args.input]))
        refs = [file_ref(project, p) for p in files]
        content = "\n\n".join(f"FILE: {ref['path']}\n" + path_in(project, ref["path"]).read_text(encoding="utf-8") for ref in refs)
        need(len(content) <= args.max_chars, f"Packet is {len(content)} characters; budget {args.max_chars}. Select smaller sections; nothing was truncated")
        packet = {"run": args.run, "story": args.story, "sources": refs, "characters": len(content),
                  "estimated_tokens": (len(content) + 3) // 4, "estimate_method": "characters/4; not a tokenizer or bill",
                  "content": content}
        out = path_in(project, args.output)
        need(out not in [path_in(project, p) for p in files] and out != store.path, "Packet output must not overwrite an input or ledger")
        atomic_json(out, packet)
        return {k: v for k, v in packet.items() if k != "content"} | {"output": str(out)}, False

    with store.transaction(create=cmd == "init") as data:
        if cmd == "init":
            identifier(args.run)
            need(args.run not in data["runs"], "Run already exists; resume it or choose a new run ID")
            info = metadata(project)
            need(args.lane != "quick" or not sprint_active(project), "An active sprint cannot use quick; use lite/full")
            run = {"id": args.run, "lane": args.lane, "reason": args.reason,
                   "bmad": info, "required": info["required"], "extra_required": [], "gates": {}, "stories": {},
                   "attempts": {}, "waivers": [], "events": [], "usage": [],
                   "max_active": args.max_active, "max_attempts": args.max_attempts}
            need(args.max_active > 0 and args.max_attempts > 0, "Budgets must be positive")
            data["runs"][args.run] = run
            event(run, "init", lane=args.lane, reason=args.reason)
            return {"run": args.run, "lane": args.lane}, False
        run = run_of(data, args.run)
        if cmd == "ack-version":
            need(not any(a["state"] == "active" for a in run["attempts"].values()), "Finish/cancel active attempts before acknowledging drift")
            run["bmad"] = metadata(project)
            run["required"] = sorted(set(run["required"]) | set(run["bmad"]["required"]))
            # Prior success must be reassessed against the changed workflows.
            run["gates"] = {}
            run["waivers"] = []
            for s in run["stories"].values():
                s["gates"] = {}
                s["closed"] = False
            event(run, cmd, reason=args.reason)
            return {"acknowledged": True, "evidence_requires_rerecording": True}, False
        if cmd != "cancel":
            version_ok(project, run)
        if cmd == "lane":
            order = {"quick": 0, "lite": 1, "full": 2}
            need(order[args.lane] >= order[run["lane"]], "Do not downgrade an active run; start a new scoped run")
            run["lane"] = args.lane
            event(run, cmd, lane=args.lane, reason=args.reason)
        elif cmd == "require":
            identifier(args.gate)
            run["required"] = sorted(set(run["required"]) | {args.gate})
            run["extra_required"] = sorted(set(run["extra_required"]) | {args.gate})
            event(run, cmd, gate=args.gate, reason=args.reason)
        elif cmd == "story":
            identifier(args.story)
            need(args.story not in run["stories"], "Story ID already registered; use a new ID for a replacement spec")
            story_ref = file_ref(project, args.file)
            spec_ref = file_ref(project, args.spec)
            need(story_ref["path"] != spec_ref["path"], "Use a separate stable acceptance spec; BMAD may update story lifecycle notes")
            for dep in args.depends:
                need(dep in run["stories"] and dep != args.story, f"Register dependency first: {dep}")
            run["stories"][args.story] = {"file": story_ref["path"], "spec": spec_ref["path"],
                                         "context": args.input, "depends": args.depends, "gates": {}, "closed": False}
            contract_refs(project, run["stories"][args.story])
            event(run, cmd, story=args.story)
        elif cmd == "waive":
            allowed = set(run["required"]) if args.story is None else {"story-validated", "code-review"}
            need(args.gate in allowed, "Waiver must name an exact required gate or a scoped story validation/review")
            sources = []
            if args.story:
                s = story_of(run, args.story)
                sources = contract_refs(project, s)
                if args.gate == "code-review":
                    need(gate_ok(project, run, "dev", args.story), "Review waiver requires current dev evidence")
                    sources = s["gates"]["dev"]["sources"]
            need(args.approval.strip(), "Waiver needs an actual user approval reference/quote")
            run["waivers"].append({"gate": args.gate, "story": args.story, "reason": args.reason,
                                   "approval": args.approval, "at": now(),
                                   "sources": sources})
            event(run, cmd, gate=args.gate, story=args.story, reason=args.reason)
        elif cmd == "record":
            if args.story:
                s = story_of(run, args.story)
                need(args.gate == "story-validated", "Dev/review reports require start + finish")
                allowed = {"bmad-create-story", "bmad-quick-dev", "bmad-spec", "bmad-build"} & run["bmad"]["skills"].keys()
                sources = contract_refs(project, s)
                target = s["gates"]
            else:
                need(args.gate in run["required"] or args.gate in ALIASES.values(), "Register an additional gate with require first")
                allowed = {k for k, v in run["bmad"]["skills"].items() if v == args.gate}
                # Explicitly required project gates (e.g. integration) use an available workflow.
                allowed = allowed or set(run["bmad"]["skills"])
                sources = snapshot(project, args.source)
                need(sources, "Planning evidence needs --source paths to detect stale requirements")
                target = run["gates"]
            record, report = load_report(project, args.report)
            need(report.get("run") == args.run and report.get("story") == args.story,
                 "Report run/story identity mismatch")
            need(record["workflow"] in allowed, "Report must identify an applicable installed BMAD workflow")
            record["sources"] = sources
            target[args.gate] = record
            event(run, cmd, gate=args.gate, story=args.story, verdict=record["verdict"])
        elif cmd == "start":
            s = story_of(run, args.story)
            need(args.actor.strip(), "Actor must identify an actual agent/session")
            need(not s["closed"], "Story is closed; use reopen with a reason")
            need(args.workflow in run["bmad"]["skills"] and args.workflow in PHASE_WORKFLOWS[args.phase], "Choose an installed workflow for this phase")
            if args.phase == "dev":
                if run["lane"] == "quick":
                    need(args.workflow in ("bmad-quick-dev", "bmad-build"), "Use installed quick-dev or build for quick work")
                else:
                    need(args.workflow != "bmad-quick-dev", "quick-dev cannot bypass lite/full story work")
            plan_ready(project, run)
            need(gate_ok(project, run, "story", args.story), "Story/spec files missing")
            if args.phase == "dev":
                for dep in s["depends"]:
                    need(gate_ok(project, run, "done", dep), f"Dependency is not done/current: {dep}")
            active = [a for r in data["runs"].values() for a in r["attempts"].values() if a["state"] == "active"]
            need(len(active) < run["max_active"], "Project active-attempt budget reached; finish/cancel existing work")
            need(not any(a["story"] == args.story and a["run"] == args.run for a in active), "Story already has an active attempt")
            previous = [a for a in run["attempts"].values() if a["story"] == args.story and a["phase"] == args.phase]
            need(len(previous) < run["max_attempts"], "Attempt budget reached: diagnose, then extend-budget with a reason")
            dependency_sources = []
            if args.phase == "dev":
                need(gate_ok(project, run, "story-validated", args.story), "Story validation missing/stale")
                inputs = contract_refs(project, s)
                for dep in s["depends"]:
                    prerequisite = story_of(run, dep)
                    inputs.extend(contract_refs(project, prerequisite))
                    dependency_sources.extend(r["path"] for r in prerequisite["gates"]["dev"]["sources"])
                inputs = snapshot(project, [x["path"] for x in inputs])
                s["gates"].pop("dev", None)
                s["gates"].pop("code-review", None)
            else:
                need(gate_ok(project, run, "dev", args.story), "Dev evidence missing/stale")
                need(s["gates"]["dev"]["actor"] != args.actor, "Reviewer must be a different agent/session from the developer")
                inputs = s["gates"]["dev"]["sources"]
            ticket = uuid.uuid4().hex
            run["attempts"][ticket] = {"id": ticket, "run": args.run, "story": args.story, "phase": args.phase,
                                        "actor": args.actor, "model": args.model, "workflow": args.workflow,
                                        "dependency_sources": sorted(set(dependency_sources)),
                                        "state": "active", "inputs": inputs, "started": now()}
            event(run, cmd, ticket=ticket, story=args.story, phase=args.phase)
            return {"ticket": ticket, "marker": "BMAD_TICKET:" + ticket}, False
        elif cmd == "accept-review":
            s = story_of(run, args.story)
            need(not s["closed"], "Story is closed; use reopen with a reason")
            need(not any(a["state"] == "active" and a["story"] == args.story for a in run["attempts"].values()), "Finish active story work before accepting native review")
            need(gate_ok(project, run, "dev", args.story), "Dev evidence missing/stale")
            dev = s["gates"]["dev"]
            need(dev["workflow"] == "bmad-build", "Only a completed Build attempt can supply native review; use start/finish for standalone review")
            record, report = load_report(project, args.report)
            need(report.get("parent_ticket") == dev.get("ticket") and bool(dev.get("ticket")), "Native review must identify its completed Build parent ticket")
            need(report.get("run") == args.run and report.get("story") == args.story, "Report run/story identity mismatch")
            need(record["actor"] != s["gates"]["dev"]["actor"], "Native review must identify a different actual agent/session")
            need(record["workflow"] in {"bmad-build", "bmad-code-review"} & run["bmad"]["skills"].keys(), "Use an installed native review workflow")
            sources = s["gates"]["dev"]["sources"]
            need(report.get("reviewed_sources") == sources, "Native reviewer must attest the exact reviewed source fingerprints")
            record["sources"] = sources
            s["gates"]["code-review"] = record
            event(run, cmd, story=args.story, verdict=record["verdict"])
        elif cmd == "finish":
            checked_run, a = check_ticket(project, data, args.ticket)
            need(checked_run is run, "Ticket belongs to a different run")
            s = story_of(run, a["story"])
            record, report = load_report(project, args.report, a["workflow"], a["actor"], a["phase"] == "dev")
            record["ticket"] = a["id"]
            need(report.get("run") == args.run and report.get("story") == a["story"], "Report run/story identity mismatch")
            if a["phase"] == "dev":
                files = report.get("files", [])
                need(files or report.get("no_changes_reason"), "Dev report must list changed/checked files or explain no changes")
                record["sources"] = snapshot(project, [x["path"] for x in a["inputs"]] + a.get("dependency_sources", []) + files)
                gate = "dev"
            else:
                record["sources"] = a["inputs"]
                gate = "code-review"
            s["gates"][gate] = record
            a["state"] = record["verdict"]
            event(run, cmd, ticket=args.ticket, verdict=record["verdict"])
        elif cmd == "cancel":
            need(args.ticket in run["attempts"], "Unknown attempt")
            a = run["attempts"][args.ticket]
            need(a["state"] == "active", "Attempt is already inactive")
            a["state"] = "cancelled"
            event(run, cmd, ticket=args.ticket, reason=args.reason)
        elif cmd in ("close", "reopen"):
            s = story_of(run, args.story)
            need(not any(a["state"] == "active" and a["story"] == args.story for a in run["attempts"].values()), "Story has active work")
            if cmd == "close":
                plan_ready(project, run)
                for dep in s["depends"]:
                    need(gate_ok(project, run, "done", dep), f"Revalidate affected dependency before close: {dep}")
                for gate in ("story-validated", "dev", "code-review"):
                    need(gate_ok(project, run, gate, args.story), f"Cannot close: {gate} missing/stale")
                s["closed"] = True
            else:
                s["closed"] = False
                s["gates"].pop("dev", None)
                s["gates"].pop("code-review", None)
            event(run, cmd, story=args.story, reason=getattr(args, "reason", None))
        elif cmd == "extend-budget":
            need(args.max_attempts > run["max_attempts"], "New budget must exceed the old one")
            run["max_attempts"] = args.max_attempts
            event(run, cmd, max_attempts=args.max_attempts, reason=args.reason)
        elif cmd == "decide":
            event(run, cmd, step=args.step, decision=args.decision, reason=args.reason)
        elif cmd == "usage":
            sample = read_json(path_in(project, args.file))
            need(isinstance(sample, dict) and sample.get("source") in ("host", "estimate"), "usage source must be host or estimate")
            need(isinstance(sample.get("sample_id"), str) and sample["sample_id"], "usage needs a unique sample_id")
            need(not any(x["sample_id"] == sample["sample_id"] for x in run["usage"]), "Duplicate usage sample")
            for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                v = sample.get(key)
                need(v is None or (type(v) is int and v >= 0), f"Invalid {key}; use null for unknown")
            run["usage"].append(sample)
            event(run, cmd, sample_id=sample["sample_id"])
        else:
            raise GateError("Unknown command")
    return {"recorded": cmd, "run": args.run}, False


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", help="Project root; otherwise search parents")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    def command(name, run=True, reason=False, story=False):
        c = sub.add_parser(name)
        if run:
            c.add_argument("--run", required=True)
        if reason:
            c.add_argument("--reason", required=True)
        if story:
            c.add_argument("--story", required=True)
        return c
    command("doctor", run=False)
    c = command("fingerprint", run=False); c.add_argument("--file", nargs="+", required=True)
    c = command("init", reason=True); c.add_argument("--lane", required=True, choices=EXEMPT)
    c.add_argument("--max-active", type=int, default=3); c.add_argument("--max-attempts", type=int, default=3)
    command("status"); command("history"); command("ack-version", reason=True)
    c = command("lane", reason=True); c.add_argument("--lane", required=True, choices=EXEMPT)
    c = command("require", reason=True); c.add_argument("--gate", required=True)
    c = command("check"); c.add_argument("gate"); c.add_argument("--story")
    c = command("story", story=True); c.add_argument("--file", required=True); c.add_argument("--spec", required=True)
    c.add_argument("--depends", nargs="*", default=[])
    c.add_argument("--input", nargs="*", default=[], help="Additional stable requirement files; SPEC frontmatter companions are included automatically")
    c = command("waive", reason=True); c.add_argument("--gate", required=True); c.add_argument("--story")
    c.add_argument("--approval", required=True)
    c = command("record"); c.add_argument("gate"); c.add_argument("--story"); c.add_argument("--report", required=True)
    c.add_argument("--source", nargs="*", default=[])
    c = command("start", story=True); c.add_argument("--phase", required=True, choices=PHASE_WORKFLOWS)
    c.add_argument("--actor", required=True); c.add_argument("--workflow", required=True); c.add_argument("--model", default="inherited")
    c = command("accept-review", story=True); c.add_argument("--report", required=True)
    c = command("finish"); c.add_argument("--ticket", required=True); c.add_argument("--report", required=True)
    c = command("cancel", reason=True); c.add_argument("--ticket", required=True)
    command("close", story=True); command("reopen", story=True, reason=True)
    c = command("extend-budget", reason=True); c.add_argument("--max-attempts", type=int, required=True)
    c = command("decide", reason=True); c.add_argument("--step", required=True); c.add_argument("--decision", choices=("run", "skip"), required=True)
    c = command("packet", story=True); c.add_argument("--input", nargs="*", default=[])
    c.add_argument("--output", required=True); c.add_argument("--max-chars", type=int, default=32000)
    c = command("usage"); c.add_argument("--file", required=True)
    return p


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if hasattr(args, "reason"):
            need(args.reason.strip(), "A nonempty reason is required")
        result, failed = execute(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return int(failed)
    except (GateError, OSError, KeyError, TypeError, ValueError) as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
