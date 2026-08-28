#!/opt/homebrew/bin/python3
"""BMAD phase-gate ledger + deterministic checks — version-agnostic.

The required-gate list, phase names, and artifact locations are DERIVED at
runtime from the project's own BMAD install:
  _bmad/_config/bmad-help.csv   -> which workflows exist, which are required
  _bmad/_config/manifest.yaml   -> installed BMAD version
  _bmad/*/config.yaml           -> where artifacts are written
A hardcoded fallback (BMAD 6.8 conventions) covers installs missing those files.

Used two ways:
  - by the orchestrator (per SKILL.md): status / check / skip / waive / decide / doctor
  - by the PreToolUse hook (~/.claude/hooks/bmad-agent-gate.py) indirectly

Ledger lives at <output_folder>/gate-ledger.yaml. The script, not the model,
is the source of truth for what ran and what was skipped.

Exit codes: 0 = pass/ok, 1 = gate not satisfied, 2 = usage error.
"""
import argparse, csv, datetime, glob, os, re, sys

try:
    import yaml
except ImportError:
    yaml = None

# ---------------------------------------------------------------- project intro
def root():
    d = os.getcwd()
    while d != "/":
        if os.path.isdir(os.path.join(d, "_bmad")):
            return d
        d = os.path.dirname(d)
    return None

def bmad_version(r):
    p = os.path.join(r, "_bmad", "_config", "manifest.yaml")
    if os.path.exists(p):
        m = re.search(r"^\s*version:\s*([\w.\-]+)", open(p, encoding="utf-8", errors="replace").read(), re.M)
        if m:
            return m.group(1)
    return "unknown"

def bmad_paths(r):
    """Resolve artifact dirs from _bmad/*/config.yaml; fall back to defaults."""
    out = {"output_folder": os.path.join(r, "_bmad-output")}
    out["planning"] = os.path.join(out["output_folder"], "planning-artifacts")
    out["implementation"] = os.path.join(out["output_folder"], "implementation-artifacts")
    for mod in ("bmm", "core", "gds", "cis"):
        p = os.path.join(r, "_bmad", mod, "config.yaml")
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        def resolve(v):
            v = v.strip().strip("'\"").replace("{project-root}", r)
            return v if os.path.isabs(v) else os.path.join(r, v)
        for key, name in (("planning_artifacts", "planning"),
                          ("implementation_artifacts", "implementation"),
                          ("output_folder", "output_folder"),
                          ("project_knowledge", "knowledge")):
            m = re.search(rf"^\s*{key}:\s*(.+)$", txt, re.M)
            if m:
                out[name] = resolve(m.group(1))
    return out

def help_rows(r):
    """Parse _bmad/_config/bmad-help.csv. Returns [] if absent/unparseable."""
    p = os.path.join(r, "_bmad", "_config", "bmad-help.csv")
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return [row for row in csv.DictReader(f)
                    if (row.get("skill") or "").startswith("bmad-")]
    except Exception:
        return []

# ---------------------------------------------------------------------- ledger
def ledger_path(r):
    return os.path.join(bmad_paths(r)["output_folder"], "gate-ledger.yaml")

def load(r):
    p = ledger_path(r)
    if yaml and os.path.exists(p):
        with open(p) as f:
            return yaml.safe_load(f) or {}
    return {}

def save(r, data):
    if not yaml:
        sys.exit("PyYAML missing — run with /opt/homebrew/bin/python3")
    p = ledger_path(r)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data["bmad_version"] = bmad_version(r)
    data["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(p, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ---------------------------------------------------- artifact-evidence checks
def _ci(pattern):
    """Case-insensitive glob pattern: a->[aA]. Real artifacts are named
    ARCHITECTURE-SPINE.md and PRD.md as often as lowercase, and a
    case-sensitive glob reports a gate MISSING while the file sits on disk —
    which reads as 'the workflow never ran' and invites re-running it."""
    out = []
    for ch in pattern:
        if ch.isalpha():
            out.append("[" + ch.lower() + ch.upper() + "]")
        else:
            out.append(ch)
    return "".join(out)

def g_all(base, pattern):
    pattern = _ci(pattern)
    hits = glob.glob(os.path.join(base, "**", pattern), recursive=True) \
         + glob.glob(os.path.join(base, pattern))
    return sorted(set(hits))

def g(base, pattern):
    hits = g_all(base, pattern)
    return hits[0] if hits else None

def story_location(r):
    P = bmad_paths(r)
    ss = g(P["output_folder"], "sprint-status.yaml")
    if ss:
        for line in open(ss, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*story_location:\s*(.+)", line)
            if m:
                loc = m.group(1).strip().strip("'\"").replace("{project-root}", r)
                return loc if os.path.isabs(loc) else os.path.join(r, loc)
    return P["implementation"]

# named gates: canonical checks usable via `check`, and mapped from CSV rows.
# Each: (which resolved dir, glob patterns tried in order)
NAMED = {
    "prd":          ("planning", ["prd*.md", "*prd*.md"]),
    "architecture": ("planning", ["*architecture*.md", "*solution-design*.md",
                                  "arch.md", "arch-*.md", "*-arch.md"]),
    "epics":        ("planning", ["*epic*.md", "*epics*"]),
    "readiness":    ("planning", ["*readiness*"]),
    "ux":           ("planning", ["ux*", "*-ux*", "*ux-spec*",
                                  "*user-experience*"]),
    "sprint":       ("output_folder", ["sprint-status.yaml"]),
    "retro":        ("implementation", ["*retro*"]),
}

# Substring globs are how a gate goes falsely green: `*arch*.md` matches
# `research.md`, and `*ux*` matches anything under a `linux` path. Both fired
# on a real project. Patterns above are tightened; this is the second net —
# a hit whose basename only matches via one of these words is not evidence.
DECOYS = {
    "architecture": re.compile(r"research"),
    "ux":           re.compile(r"linux|flux|redux|crux|tux"),
}

# skill-id -> named gate, across known BMAD versions (6.6 → 6.11 renames)
GATE_FOR_SKILL = {
    "bmad-prd": "prd", "bmad-create-prd": "prd",
    "bmad-create-architecture": "architecture", "bmad-architecture": "architecture",
    "bmad-create-epics-and-stories": "epics", "bmad-epics": "epics",
    "bmad-check-implementation-readiness": "readiness",
    "bmad-ux": "ux",
    "bmad-sprint-planning": "sprint",
    "bmad-retrospective": "retro",
}

# per-story cycle skills: required in the CSV but not one-time gates
CYCLE = {"bmad-create-story", "bmad-dev-story", "bmad-build", "bmad-code-review"}

FALLBACK_REQUIRED = ["prd", "architecture", "epics", "readiness", "sprint"]

# lane -> named gates exempted by that lane (recorded once via `gate.py lane`)
LANE_EXEMPT = {
    "quick": {"prd", "architecture", "epics", "readiness", "sprint"},
    "lite":  {"readiness", "ux"},
    "full":  set(),
}

def current_lane(led):
    """Last recorded lane decision, or None."""
    lane = None
    for e in led.get("decisions", []):
        if (e.get("step") or "") == "lane" and e.get("decision") in LANE_EXEMPT:
            lane = e["decision"]
    return lane

def check_named(r, gate, arg=None):
    P = bmad_paths(r)
    if gate == "story":
        if arg and os.path.exists(arg):
            return arg
        base = story_location(r)
        return arg and (g(base, f"*{arg}*.md") or g(P["output_folder"], f"*{arg}*.md"))
    if gate == "story-validated":
        return arg and g(P["output_folder"], f"*{arg}*valid*")
    if gate == "code-review":
        return arg and (g(P["output_folder"], f"*{arg}*review*"))
    spec = NAMED.get(gate)
    if not spec:
        return None
    base = P.get(spec[0], P["output_folder"])
    decoy = DECOYS.get(gate)
    for pat in spec[1]:
        # filter decoys per HIT, not per pattern: architecture-research.md
        # sorting before architecture.md must not hide the real doc.
        for hit in g_all(base, pat):
            if decoy and decoy.search(os.path.basename(hit).lower()):
                continue  # e.g. research.md is not an architecture doc
            return hit
    return None

def generic_glob_from_outputs(r, outputs):
    """Best-effort check for a required workflow this script doesn't know:
    glob the first meaningful keyword of its declared outputs everywhere."""
    words = re.findall(r"[a-z]{4,}", (outputs or "").lower())
    if not words:
        return None
    return g(bmad_paths(r)["output_folder"], f"*{words[0]}*")

def required_gates(r):
    """[(label, kind, checker-args)] derived from the installed bmad-help.csv;
    kind: named | cycle | generic | unverifiable. Fallback = 6.8 conventions."""
    rows = help_rows(r)
    if not rows:
        return [(x, "named", x) for x in FALLBACK_REQUIRED], "fallback (no bmad-help.csv)"
    out, seen = [], set()
    for row in rows:
        if (row.get("required") or "").strip().lower() != "true":
            continue
        skill = row["skill"].strip()
        action = (row.get("action") or "").strip()
        label = skill + (f":{action}" if action else "")
        if label in seen:
            continue
        seen.add(label)
        if skill in CYCLE:
            out.append((label, "cycle", None))
        elif skill in GATE_FOR_SKILL:
            out.append((label, "named", GATE_FOR_SKILL[skill]))
        else:
            outputs = (row.get("outputs") or "").strip()
            out.append((label, "generic" if outputs else "unverifiable", outputs or None))
    return out, f"bmad-help.csv (BMAD {bmad_version(r)})"

def has_skip_or_waiver(led, step, arg=None):
    """Token-boundary matching only. Raw substring matching false-waived
    gates: arg '2' matched a skip for story '24', step 'sprint' matched any
    entry mentioning it. An entry matches when its step/scope equals the
    label, the label's base, or the base's short gate alias (bmad-prd ~ prd)."""
    base = step.split(":")[0]
    aliases = {step, base, f"{base}:{arg}" if arg else step,
               GATE_FOR_SKILL.get(base, base)}
    for e in led.get("skips", []) + led.get("waivers", []):
        s = (e.get("step") or e.get("scope") or "").strip()
        if s in aliases:
            return e
        # an entry with its own arg (step:arg) only matches the full key above;
        # an argless entry waives the whole step (and its short-alias forms)
        if ":" not in s and (GATE_FOR_SKILL.get(s) in (base, step)
                             or GATE_FOR_SKILL.get(base) == s):
            return e
    return None

# -------------------------------------------------------------------- commands
def cmd_check(args):
    r = root()
    if not r:
        print("no _bmad project here"); return 0
    hit = check_named(r, args.gate, args.arg)
    if hit:
        if not args.quiet:
            print(f"PASS {args.gate}{' '+args.arg if args.arg else ''}: {os.path.relpath(str(hit), r)}")
        return 0
    led = load(r)
    e = has_skip_or_waiver(led, args.gate, args.arg)
    if e:
        if not args.quiet: print(f"WAIVED {args.gate}: {e.get('reason','')}")
        return 0
    lane = current_lane(led)
    if lane and args.gate in LANE_EXEMPT[lane]:
        if not args.quiet: print(f"LANE {lane}: {args.gate} exempt")
        return 0
    if not args.quiet:
        print(f"FAIL {args.gate}{' '+args.arg if args.arg else ''}: no artifact found. "
              f"Run the workflow, or record: gate.py skip {args.gate} --reason '...'")
    return 1

def cmd_status(args):
    r = root()
    if not r:
        print("no _bmad project here"); return 0
    led = load(r)
    gates, source = required_gates(r)
    ver = bmad_version(r)
    print(f"project: {os.path.basename(r)}  ·  BMAD {ver}  ·  gates from {source}")
    prev = led.get("bmad_version")
    if prev and prev != ver:
        print(f"  ! BMAD version changed since ledger init ({prev} → {ver}) — run gate.py doctor")
    lane = current_lane(led)
    if lane:
        print(f"lane: {lane}")
    bad = 0
    for label, kind, x in gates:
        if kind == "cycle":
            print(f"  ○ {label:42s} per-story cycle — enforced per spawn, not here")
            continue
        hit = check_named(r, x) if kind == "named" else generic_glob_from_outputs(r, x)
        e = None if hit else has_skip_or_waiver(led, label)
        if hit:
            print(f"  ✓ {label:42s} {os.path.relpath(str(hit), r)}")
        elif e:
            print(f"  ~ {label:42s} skipped: {e.get('reason','')}")
        elif kind == "named" and lane and x in LANE_EXEMPT[lane]:
            print(f"  ~ {label:42s} lane {lane}: exempt")
        elif kind == "unverifiable":
            print(f"  ? {label:42s} required by CSV but no declared outputs — verify manually")
        else:
            print(f"  ✗ {label:42s} MISSING")
            bad += 1
    for sec in ("skips", "waivers", "decisions"):
        for e in led.get(sec, []):
            print(f"  [{sec[:-1]}] {e.get('step') or e.get('scope')}: {e.get('decision','skip')} — {e.get('reason','')}")
    if bad:
        print(f"{bad} required gate(s) unaccounted for — run them or record a skip.")
    if led or not bad:
        save(r, led)  # stamp version on first contact
    return 1 if bad else 0

def latest_published(timeout=10):
    """Latest bmad-method version on npm, or None (offline / npm missing / slow).
    Read-only: never installs, never writes."""
    import subprocess
    try:
        out = subprocess.run(["npm", "view", "bmad-method", "version"],
                             capture_output=True, text=True, timeout=timeout)
        v = out.stdout.strip()
        return v if re.match(r"^\d+\.\d+\.\d+", v) else None
    except Exception:
        return None

def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)

def sprint_in_progress(r):
    """True if any story/epic is mid-flight — an update should wait for epic close."""
    ss = g(bmad_paths(r)["output_folder"], "sprint-status.yaml")
    if not ss:
        return False
    txt = open(ss, encoding="utf-8", errors="replace").read()
    return bool(re.search(r":\s*(in-progress|ready-for-dev|review)\s*$", txt, re.M))

def cmd_doctor(args):
    """Cross-check this script's assumptions against the installed BMAD."""
    r = root()
    if not r:
        print("no _bmad project here"); return 0
    ver = bmad_version(r)
    rows = help_rows(r)
    P = bmad_paths(r)
    print(f"BMAD {ver} at {os.path.relpath(os.path.join(r,'_bmad'), r)}")
    print(f"paths: planning={os.path.relpath(P['planning'], r)}  "
          f"implementation={os.path.relpath(P['implementation'], r)}  "
          f"output={os.path.relpath(P['output_folder'], r)}")
    issues = 0
    if not rows:
        print("  ! bmad-help.csv missing/unparseable — running on hardcoded 6.8 fallback")
        issues += 1
    else:
        known = set(GATE_FOR_SKILL) | CYCLE
        for row in rows:
            if (row.get("required") or "").strip().lower() == "true" and row["skill"] not in known:
                print(f"  ! required workflow '{row['skill']}' unknown to gate.py "
                      f"(new in this BMAD version?) — checked generically via outputs='{row.get('outputs','')}'")
                issues += 1
    # shim coverage: every spawnable agent type referenced in _bmad has a shim
    agents_dir = os.path.expanduser("~/.claude/agents")
    types = set()
    for dirpath, _, files in os.walk(os.path.join(r, "_bmad")):
        for fn in files:
            if not fn.endswith((".md", ".xml", ".yaml", ".csv")):
                continue
            try:
                txt = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            types.update(m.group(0).lower() for m in
                         re.finditer(r"bmad-(?:agent|review)-[a-z][a-z-]*[a-z]", txt))
    for t in sorted(types):
        if not os.path.exists(os.path.join(agents_dir, t + ".md")):
            print(f"  ! missing subagent shim: ~/.claude/agents/{t}.md")
            issues += 1
    led = load(r)
    prev = led.get("bmad_version")
    if prev and prev != ver:
        print(f"  ! ledger was written under BMAD {prev}; now {ver} — review skips for renamed workflows")
        issues += 1
    # version check — REPORT ONLY. Never updates: an update rewrites tracked
    # files (.claude/skills, .agents/skills, .bak) and can change workflow
    # semantics mid-sprint, so the decision belongs to the user.
    if not args.no_net:
        latest = latest_published()
        if latest and ver != "unknown" and vtuple(latest) > vtuple(ver):
            mid = sprint_in_progress(r)
            print(f"  ! update available: {ver} → {latest}")
            if mid:
                print("    sprint in progress — recommend updating at epic close, not now")
            else:
                print("    no sprint in progress — safe point to update, ask the user first")
            print(f"    npx -y bmad-method@latest install --directory . --action quick-update -y")
            print("    then re-run: gate.py doctor   (regenerates IDE skill dirs — dirties git)")
            issues += 1
        elif latest and ver == latest:
            print(f"  BMAD {ver} is the latest published version")
    if not issues:
        print("  OK — manifests parsed, all required workflows mapped, shims present, version stable")
    save(r, led)
    return 1 if issues else 0

def cmd_skip(args):
    r = root() or sys.exit("no _bmad project here")
    led = load(r)
    led.setdefault("skips", []).append(
        {"step": args.step + (f":{args.arg}" if args.arg else ""),
         "reason": args.reason, "ts": now()})
    save(r, led); print(f"recorded skip: {args.step} — {args.reason}"); return 0

def cmd_waive(args):
    r = root() or sys.exit("no _bmad project here")
    led = load(r)
    led.setdefault("waivers", []).append(
        {"scope": args.scope, "reason": args.reason, "by": "user", "ts": now()})
    save(r, led); print(f"recorded waiver: {args.scope} — {args.reason}"); return 0

def cmd_lane(args):
    r = root() or sys.exit("no _bmad project here")
    led = load(r)
    led.setdefault("decisions", []).append(
        {"step": "lane", "decision": args.lane, "reason": args.reason, "ts": now()})
    save(r, led)
    ex = ", ".join(sorted(LANE_EXEMPT[args.lane])) or "none"
    print(f"recorded lane: {args.lane} — exempt gates: {ex}"); return 0

def cmd_decide(args):
    r = root() or sys.exit("no _bmad project here")
    led = load(r)
    led.setdefault("decisions", []).append(
        {"step": args.step, "decision": args.decision, "reason": args.reason, "ts": now()})
    save(r, led); print(f"recorded decision: {args.step} = {args.decision}"); return 0

def main():
    ap = argparse.ArgumentParser(prog="gate.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("gate"); c.add_argument("arg", nargs="?")
    c.add_argument("--quiet", action="store_true"); c.set_defaults(f=cmd_check)
    s = sub.add_parser("skip"); s.add_argument("step"); s.add_argument("arg", nargs="?")
    s.add_argument("--reason", required=True); s.set_defaults(f=cmd_skip)
    w = sub.add_parser("waive"); w.add_argument("scope")
    w.add_argument("--reason", required=True); w.set_defaults(f=cmd_waive)
    d = sub.add_parser("decide"); d.add_argument("step")
    d.add_argument("decision", choices=["run", "skip"])
    d.add_argument("--reason", required=True); d.set_defaults(f=cmd_decide)
    ln = sub.add_parser("lane"); ln.add_argument("lane", choices=sorted(LANE_EXEMPT))
    ln.add_argument("--reason", required=True); ln.set_defaults(f=cmd_lane)
    st = sub.add_parser("status"); st.set_defaults(f=cmd_status)
    dr = sub.add_parser("doctor")
    dr.add_argument("--no-net", action="store_true",
                    help="skip the npm version check (offline / fast path)")
    dr.set_defaults(f=cmd_doctor)
    a = ap.parse_args()
    sys.exit(a.f(a))

if __name__ == "__main__":
    main()
