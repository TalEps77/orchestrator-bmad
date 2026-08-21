#!/opt/homebrew/bin/python3
"""PreToolUse hook on Agent/Task: deterministic BMAD spawn gate.

Blocks (exit 2, stderr fed back to the model) when, in a _bmad project:
  1. A BMAD phase task is being spawned on a generic agent type
     (general-purpose/Explore) instead of the typed bmad-* subagent.
  2. A bmad-dev-story spawn has no story file on disk and no recorded waiver.

Fast-exits 0 for everything else. Never crashes the session: any internal
error exits 0 (fail-open) — enforcement is best-effort, work is not.
"""
import json, os, re, sys, glob

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

    # --- rule 1: typed agents for BMAD phase work -------------------------------
    PHASE = {"bmad-dev-story": "bmad-agent-dev",
             "bmad-create-story": "bmad-agent-dev",
             "bmad-code-review": "bmad-agent-dev",
             "bmad-prd": "bmad-agent-pm",
             "bmad-create-architecture": "bmad-agent-architect",
             "bmad-create-epics-and-stories": "bmad-agent-pm",
             "bmad-ux": "bmad-agent-ux-designer",
             "bmad-review-adversarial-general": "bmad-review-adversarial-general",
             "bmad-review-edge-case-hunter": "bmad-review-edge-case-hunter"}
    for skill, want in PHASE.items():
        if skill in text and atype and not atype.startswith("bmad-"):
            print(f"BLOCKED by bmad-agent-gate: '{skill}' work must run on a typed BMAD "
                  f"subagent (suggested: subagent_type='{want}'), not '{atype}'. "
                  f"Re-spawn with the typed agent.", file=sys.stderr)
            return 2

    # --- rule 2: dev-story needs a story file (or explicit waiver) --------------
    if "bmad-dev-story" in text:
        # waiver recorded?
        lp = os.path.join(r, "_bmad-output", "gate-ledger.yaml")
        if os.path.exists(lp):
            led = open(lp, encoding="utf-8", errors="replace").read().lower()
            if "waiver" in led and ("dev" in led or "batch" in led or "epic" in led):
                return 0
        # any .md path mentioned in the prompt that exists on disk?
        for m in re.finditer(r"[\w./ _-]+\.md", str(ti.get("prompt", ""))):
            p = m.group(0).strip()
            full = p if os.path.isabs(p) else os.path.join(r, p)
            if os.path.exists(full) and ("_bmad-output" in full or "stor" in full.lower()):
                return 0
        # or does any story file exist at the tracked story location?
        if glob.glob(os.path.join(r, "_bmad-output", "**", "stories", "*.md")) or \
           glob.glob(os.path.join(r, "_bmad-output", "implementation-artifacts", "*-*.md")):
            return 0
        print("BLOCKED by bmad-agent-gate: bmad-dev-story spawn but no story file exists "
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
