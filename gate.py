#!/opt/homebrew/bin/python3
"""BMAD phase-gate ledger + deterministic checks.

Used two ways:
  - by the orchestrator (per SKILL.md): init / check / skip / waive / status
  - by the PreToolUse hook (~/.claude/hooks/bmad-agent-gate.py): check --quiet

Ledger lives at <project>/_bmad-output/gate-ledger.yaml. The script, not the
model, is the source of truth for what ran and what was skipped.

Exit codes: 0 = pass/ok, 1 = gate not satisfied, 2 = usage error.
"""
import argparse, datetime, glob, os, re, sys

try:
    import yaml
except ImportError:  # hook must never crash the session
    yaml = None

def root():
    d = os.getcwd()
    while d != "/":
        if os.path.isdir(os.path.join(d, "_bmad")):
            return d
        d = os.path.dirname(d)
    return None

def ledger_path(r):
    return os.path.join(r, "_bmad-output", "gate-ledger.yaml")

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
    data["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(p, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def g(r, pattern):
    """First artifact matching glob pattern under project root, else None."""
    hits = glob.glob(os.path.join(r, pattern), recursive=True)
    return hits[0] if hits else None

# ---- artifact-evidence checks (required steps) --------------------------------
def story_location(r):
    ss = g(r, "_bmad-output/**/sprint-status.yaml")
    if ss:
        for line in open(ss, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*story_location:\s*(.+)", line)
            if m:
                loc = m.group(1).strip().strip("'\"")
                return loc if os.path.isabs(loc) else os.path.join(r, loc)
    return os.path.join(r, "_bmad-output", "implementation-artifacts")

CHECKS = {
    "prd":          lambda r, a: g(r, "_bmad-output/planning-artifacts/**/prd*.md") or g(r, "_bmad-output/planning-artifacts/PRD.md"),
    "architecture": lambda r, a: g(r, "_bmad-output/planning-artifacts/**/architecture*.md"),
    "epics":        lambda r, a: g(r, "_bmad-output/planning-artifacts/**/epic*.md"),
    "readiness":    lambda r, a: g(r, "_bmad-output/planning-artifacts/**/*readiness*"),
    "sprint":       lambda r, a: g(r, "_bmad-output/**/sprint-status.yaml"),
    # story <slug>: the story FILE exists (bmad-create-story ran)
    "story":        lambda r, a: a and (g(r, f"_bmad-output/**/*{a}*.md") if not os.path.exists(a) else a),
    # story-validated <slug>: a validation report exists for it
    "story-validated": lambda r, a: a and g(r, f"_bmad-output/**/*{a}*valid*"),
    # code-review <slug>: a persisted review report exists
    "code-review":  lambda r, a: a and (g(r, f"_bmad-output/**/*{a}*review*") or g(r, f"_bmad-output/**/*{a}*code-review*")),
    "retro":        lambda r, a: g(r, f"_bmad-output/**/*{a or ''}*retro*"),
}

REQUIRED = ["prd", "architecture", "epics", "readiness", "sprint"]

def has_skip_or_waiver(led, step, arg=None):
    key = f"{step}:{arg}" if arg else step
    for e in led.get("skips", []) + led.get("waivers", []):
        s = e.get("step") or e.get("scope") or ""
        if s in (step, key) or (arg and arg in s):
            return e
    return None

def cmd_check(args):
    r = root()
    if not r:
        print("no _bmad project here"); return 0
    fn = CHECKS.get(args.gate)
    if not fn:
        print(f"unknown gate '{args.gate}'. gates: {', '.join(CHECKS)}"); return 2
    hit = fn(r, args.arg)
    if hit:
        if not args.quiet: print(f"PASS {args.gate}{' '+args.arg if args.arg else ''}: {os.path.relpath(str(hit), r)}")
        return 0
    e = has_skip_or_waiver(load(r), args.gate, args.arg)
    if e:
        if not args.quiet: print(f"WAIVED {args.gate}: {e.get('reason','')}")
        return 0
    if not args.quiet:
        print(f"FAIL {args.gate}{' '+args.arg if args.arg else ''}: no artifact found. "
              f"Run the workflow, or record: gate.py skip {args.gate} --reason '...'")
    return 1

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

def cmd_decide(args):
    """Record judgment on an OPTIONAL capability (party-mode, market-research, ...)."""
    r = root() or sys.exit("no _bmad project here")
    led = load(r)
    led.setdefault("decisions", []).append(
        {"step": args.step, "decision": args.decision, "reason": args.reason, "ts": now()})
    save(r, led); print(f"recorded decision: {args.step} = {args.decision}"); return 0

def cmd_status(args):
    r = root()
    if not r:
        print("no _bmad project here"); return 0
    led = load(r)
    print(f"project: {os.path.basename(r)}")
    bad = 0
    for gate in REQUIRED:
        hit = CHECKS[gate](r, None)
        e = None if hit else has_skip_or_waiver(led, gate)
        state = "done" if hit else ("skipped: " + e["reason"] if e else "MISSING")
        if state == "MISSING": bad += 1
        print(f"  {'✓' if hit else ('~' if e else '✗')} {gate:14s} {state if not hit else os.path.relpath(str(hit), r)}")
    for sec in ("skips", "waivers", "decisions"):
        for e in led.get(sec, []):
            print(f"  [{sec[:-1]}] {e.get('step') or e.get('scope')}: {e.get('decision','skip')} — {e.get('reason','')}")
    if bad:
        print(f"{bad} required gate(s) unaccounted for — run them or record a skip.")
    return 1 if bad else 0

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
    st = sub.add_parser("status"); st.set_defaults(f=cmd_status)
    a = ap.parse_args()
    sys.exit(a.f(a))

if __name__ == "__main__":
    main()
