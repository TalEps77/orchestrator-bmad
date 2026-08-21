#!/opt/homebrew/bin/python3
"""PreToolUse hook on Agent/Task: deterministic BMAD spawn gate — version-agnostic.

Blocks (exit 2, stderr fed back to the model) when, in a _bmad project:
  1. A BMAD phase task is being spawned on a generic agent type
     (general-purpose/Explore) instead of a typed bmad-* subagent.
  2. A dev-workflow spawn (bmad-dev-story / bmad-build) has no story file
     on disk and no recorded waiver.

Phase-work skill names are derived from the project's own
_bmad/_config/skill-manifest.csv, so renames across BMAD versions
(e.g. 6.8 bmad-create-architecture -> 6.11 bmad-architecture,
6.11's new bmad-build) are picked up automatically. A curated set
covers installs missing the manifest.

Fast-exits 0 for everything else. Never crashes the session: any internal
error exits 0 (fail-open) — enforcement is best-effort, work is not.
"""
import csv, glob, json, os, re, sys

# skills that are phase work when the manifest is unavailable (6.6–6.11 names)
CURATED_PHASE = {
    "bmad-dev-story", "bmad-build", "bmad-create-story", "bmad-code-review",
    "bmad-prd", "bmad-create-prd", "bmad-create-architecture", "bmad-architecture",
    "bmad-create-epics-and-stories", "bmad-ux",
    "bmad-review-adversarial-general", "bmad-review-edge-case-hunter",
}
# regex that classifies a manifest skill id as phase work (survives renames)
PHASE_RE = re.compile(
    r"^bmad-(dev-story|build|create-story|code-review|prd|create-prd|"
    r"create-architecture|architecture|create-epics-and-stories|epics|ux|review-.+)$")
# dev workflows that require a story file
DEV_SKILLS = {"bmad-dev-story", "bmad-build"}

def suggest_agent(skill):
    if re.search(r"review", skill):
        shim = os.path.expanduser(f"~/.claude/agents/{skill}.md")
        return skill if os.path.exists(shim) else "bmad-review-adversarial-general"
    if re.search(r"dev-story|build|create-story|code-review", skill):
        return "bmad-agent-dev"
    if re.search(r"architecture", skill):
        return "bmad-agent-architect"
    if re.search(r"ux", skill):
        return "bmad-agent-ux-designer"
    return "bmad-agent-pm"  # prd / epics / planning

def phase_skills(r):
    """Phase-work skill ids for THIS project's installed BMAD version."""
    skills = set(CURATED_PHASE)
    p = os.path.join(r, "_bmad", "_config", "skill-manifest.csv")
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                cid = (row.get("canonicalId") or row.get("name") or "").strip()
                if cid and PHASE_RE.match(cid):
                    skills.add(cid)
    except Exception:
        pass
    return skills

def impl_dir(r):
    """implementation_artifacts dir from _bmad/*/config.yaml, default fallback."""
    for mod in ("bmm", "core", "gds", "cis"):
        p = os.path.join(r, "_bmad", mod, "config.yaml")
        if not os.path.exists(p):
            continue
        m = re.search(r"^\s*implementation_artifacts:\s*(.+)$",
                      open(p, encoding="utf-8", errors="replace").read(), re.M)
        if m:
            v = m.group(1).strip().strip("'\"").replace("{project-root}", r)
            return v if os.path.isabs(v) else os.path.join(r, v)
    return os.path.join(r, "_bmad-output", "implementation-artifacts")

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Agent", "Task"):
        return 0
    ti = data.get("tool_input") or {}
    text = " ".join(str(ti.get(k, "")) for k in ("prompt", "description")).lower()
    if "bmad-" not in text:
        return 0

    # only enforce inside a BMAD project
    cwd = data.get("cwd") or os.getcwd()
    r = cwd
    while r != "/" and not os.path.isdir(os.path.join(r, "_bmad")):
        r = os.path.dirname(r)
    if r == "/":
        return 0

    atype = (ti.get("subagent_type") or "").lower()
    mentioned = set(re.findall(r"bmad-[a-z][a-z-]*[a-z]", text))
    phase = phase_skills(r)

    # --- rule 1: typed agents for BMAD phase work -------------------------------
    for skill in sorted(mentioned & phase):
        if atype and not atype.startswith("bmad-"):
            print(f"BLOCKED by bmad-agent-gate: '{skill}' work must run on a typed BMAD "
                  f"subagent (suggested: subagent_type='{suggest_agent(skill)}'), "
                  f"not '{atype}'. Re-spawn with the typed agent.", file=sys.stderr)
            return 2

    # --- rule 2: dev workflow needs a story file (or explicit waiver) -----------
    if mentioned & DEV_SKILLS:
        # waiver recorded?
        for lp in glob.glob(os.path.join(r, "*", "gate-ledger.yaml")) + \
                  glob.glob(os.path.join(r, "_bmad-output", "gate-ledger.yaml")):
            led = open(lp, encoding="utf-8", errors="replace").read().lower()
            if "waiver" in led and ("dev" in led or "batch" in led or "epic" in led):
                return 0
        # any .md path mentioned in the prompt that exists on disk?
        for m in re.finditer(r"[\w./ _-]+\.md", str(ti.get("prompt", ""))):
            p = m.group(0).strip()
            full = p if os.path.isabs(p) else os.path.join(r, p)
            if os.path.exists(full) and (impl_dir(r) in full or "stor" in full.lower()
                                         or "_bmad-output" in full):
                return 0
        # or does any story file exist at the tracked story location?
        base = impl_dir(r)
        if glob.glob(os.path.join(base, "**", "stories", "*.md"), recursive=True) or \
           glob.glob(os.path.join(base, "*-*.md")):
            return 0
        dev = sorted(mentioned & DEV_SKILLS)[0]
        print(f"BLOCKED by bmad-agent-gate: {dev} spawn but no story file exists "
              "on disk and none is referenced in the prompt. Run bmad-create-story (+ "
              "validate) first, pass the story file path in the prompt, or record a "
              "user waiver: gate.py waive 'epic-batch-dev' --reason '...'.",
              file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open
