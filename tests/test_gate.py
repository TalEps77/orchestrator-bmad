"""Behavioral regression tests. Real CLI calls, isolated project files, no model/network."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "gate.py"
HOOK = ROOT / "hooks" / "bmad-agent-gate.py"


class Project(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bmad-v4-")
        self.p = Path(self.temp.name)
        self.write("_bmad/_config/manifest.yaml", "installation:\n  version: 6.11.0\n")
        self.write("_bmad/_config/bmad-help.csv", "skill,required,outputs\nbmad-prd,true,PRD\nbmad-create-story,true,Story\nbmad-dev-story,true,Code\nbmad-code-review,false,Review\nbmad-quick-dev,false,Code\nbmad-ux,false,UX\n")
        self.call("init", "--run", "test", "--lane", "quick", "--reason", "Standalone change")
        self.write("stories/2-1.md", "# Story\nAcceptance: counter is idempotent.\n")
        self.write("specs/2-1.md", "# Contract\nDuplicate calls must not increment twice.\n")
        self.call("story", "--run", "test", "--story", "2-1", "--file", "stories/2-1.md", "--spec", "specs/2-1.md")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        p = self.p / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def call(self, *args, ok=True):
        x = subprocess.run([sys.executable, str(GATE), "--root", str(self.p), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(x.returncode, 0, x.stderr)
            return json.loads(x.stdout)
        self.assertNotEqual(x.returncode, 0, x.stdout)
        return x

    def report(self, name, actor="creator", workflow="bmad-create-story", story="2-1", **extra):
        self.write("evidence/" + name + ".md", "Observed result for " + name)
        body = dict(schema_version=1, run="test", story=story, actor=actor, workflow=workflow,
                    verdict="pass", blockers=[], summary="Verified behavior", evidence=["evidence/" + name + ".md"])
        body.update(extra)
        self.write("reports/" + name + ".json", json.dumps(body))
        return "reports/" + name + ".json"

    def validate(self):
        f = self.report("validation")
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f)

    def start(self, phase="dev", actor="dev", ok=True, workflow=None):
        return self.call("start", "--run", "test", "--story", "2-1", "--phase", phase,
                         "--actor", actor, "--workflow", workflow or ("bmad-quick-dev" if phase == "dev" else "bmad-code-review"), ok=ok)

    def dev(self, workflow="bmad-quick-dev"):
        self.validate()
        t = self.start(workflow=workflow)["ticket"]
        self.write("counter.py", "VALUE = 1\n")
        self.write("reports/test.log", "Ran 1 test\nOK\n")
        f = self.report("dev", actor="dev", workflow=workflow, files=["counter.py"],
                        checks=[dict(command="python -m unittest", exit_code=0, log="reports/test.log")])
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        return t

    def review(self):
        self.dev()
        t = self.start("review", "reviewer")["ticket"]
        f = self.report("review", actor="reviewer", workflow="bmad-code-review")
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        self.call("close", "--run", "test", "--story", "2-1")

    def hook(self, prompt, role="bmad-worker", code=0):
        x = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(dict(tool_name="Agent", cwd=str(self.p),
            tool_input=dict(subagent_type=role, prompt=prompt))), text=True, capture_output=True)
        self.assertEqual(x.returncode, code, x.stderr)

    def test_complete_cycle_and_read_only_status(self):
        self.review()
        ledger = self.p / ".bmad-orchestrator/ledger.json"
        before = ledger.read_bytes()
        self.assertTrue(self.call("check", "done", "--run", "test", "--story", "2-1")["pass"])
        self.call("doctor"); self.call("status", "--run", "test")
        self.assertEqual(before, ledger.read_bytes())

    def test_empty_validation_rejected(self):
        self.write("empty.json", "")
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", "empty.json", ok=False)

    def test_empty_evidence_rejected(self):
        f = self.report("validation")
        self.write("evidence/validation.md", "")
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f, ok=False)

    def test_fail_report_never_passes(self):
        f = self.report("validation", verdict="fail", blockers=["Missing acceptance criterion"])
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f)
        self.call("check", "story-validated", "--run", "test", "--story", "2-1", ok=False)
        self.start(ok=False)

    def test_pass_with_blockers_rejected(self):
        f = self.report("validation", blockers=["Critical failure"])
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f, ok=False)

    def test_identity_and_prefix_do_not_match(self):
        f = self.report("validation", story="2-10")
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f, ok=False)
        self.call("check", "story-validated", "--run", "test", "--story", "2-10", ok=False)

    def test_existing_story_does_not_authorize_another(self):
        self.validate()
        self.call("start", "--run", "test", "--story", "9-9", "--phase", "dev", "--actor", "dev", "--workflow", "bmad-quick-dev", ok=False)

    def test_changed_spec_invalidates_validation(self):
        self.validate()
        self.write("specs/2-1.md", "Changed accepted behavior")
        self.start(ok=False)

    def test_mutable_story_notes_do_not_invalidate_spec(self):
        self.validate()
        self.write("stories/2-1.md", "# Story\nStatus: in-progress\nDev Notes: started")
        self.start()

    def test_changed_code_invalidates_done(self):
        self.review()
        self.write("counter.py", "VALUE = 999\n")
        self.call("check", "done", "--run", "test", "--story", "2-1", ok=False)

    def test_review_cannot_change_underneath_reviewer(self):
        self.dev()
        t = self.start("review", "reviewer")["ticket"]
        self.write("counter.py", "VALUE = 2\n")
        f = self.report("review", actor="reviewer", workflow="bmad-code-review")
        self.call("finish", "--run", "test", "--ticket", t, "--report", f, ok=False)

    def test_same_actor_review_rejected(self):
        self.dev(); self.start("review", "dev", ok=False)

    def test_failing_test_cannot_pass(self):
        self.validate(); t = self.start()["ticket"]
        self.write("reports/test.log", "FAIL")
        f = self.report("dev", actor="dev", workflow="bmad-quick-dev", files=["counter.py"],
                        checks=[dict(command="python -m unittest", exit_code=1, log="reports/test.log")])
        self.call("finish", "--run", "test", "--ticket", t, "--report", f, ok=False)

    def test_attempt_cannot_finish_twice(self):
        t = self.dev()
        self.call("finish", "--run", "test", "--ticket", t, "--report", "reports/dev.json", ok=False)

    def test_exact_waiver_and_no_inheritance(self):
        self.call("waive", "--run", "test", "--gate", "prd", "--reason", "epic dev batch", "--approval", "user quote")
        self.start(ok=False)
        self.call("waive", "--run", "test", "--gate", "story-validated", "--story", "2-1", "--reason", "approved", "--approval", "user quote")
        self.start()
        self.call("init", "--run", "new", "--lane", "full", "--reason", "New task")
        self.call("check", "prd", "--run", "new", ok=False)

    def test_unknown_waiver_scope_rejected(self):
        self.call("waive", "--run", "test", "--gate", "epic-batch-dev", "--reason", "anything", "--approval", "user quote", ok=False)

    def test_drift_is_not_acknowledged_by_doctor(self):
        ledger = self.p / ".bmad-orchestrator/ledger.json"
        before = ledger.read_bytes()
        self.write("_bmad/_config/manifest.yaml", "version: 6.12.0\n")
        self.call("doctor", ok=False); self.call("doctor", ok=False)
        self.assertEqual(before, ledger.read_bytes())

    def test_can_cancel_during_drift_and_ack_invalidates(self):
        self.validate(); t = self.start()["ticket"]
        self.write("_bmad/_config/manifest.yaml", "version: 6.12.0\n")
        self.call("ack-version", "--run", "test", "--reason", "reviewed", ok=False)
        self.call("cancel", "--run", "test", "--ticket", t, "--reason", "stopped")
        self.call("ack-version", "--run", "test", "--reason", "reviewed")
        self.call("check", "story-validated", "--run", "test", "--story", "2-1", ok=False)

    def test_full_gate_does_not_accept_filename(self):
        self.call("lane", "--run", "test", "--lane", "full", "--reason", "expanded")
        self.write("prd.md", "# PRD")
        self.validate(); self.start(ok=False)

    def test_planning_result_invalidated_by_source_change(self):
        self.write("requirements.md", "approved requirements")
        f = self.report("prd", workflow="bmad-prd", story=None)
        self.call("record", "prd", "--run", "test", "--report", f, "--source", "requirements.md")
        self.call("check", "prd", "--run", "test")
        self.write("requirements.md", "changed requirements")
        self.call("check", "prd", "--run", "test", ok=False)

    def test_budget_and_cancel(self):
        self.validate()
        for i in range(3):
            t = self.start()["ticket"]
            self.start(ok=False)
            self.call("cancel", "--run", "test", "--ticket", t, "--reason", "worker stopped")
        self.start(ok=False)
        self.call("extend-budget", "--run", "test", "--max-attempts", "4", "--reason", "Diagnosed and repaired environment")
        self.start()

    def test_no_downgrade_or_run_overwrite(self):
        self.call("lane", "--run", "test", "--lane", "full", "--reason", "expanded")
        self.call("lane", "--run", "test", "--lane", "quick", "--reason", "cheaper", ok=False)
        self.call("init", "--run", "test", "--lane", "quick", "--reason", "reset", ok=False)

    def test_quick_blocked_inside_sprint(self):
        self.write("_bmad-output/implementation-artifacts/sprint-status.yaml", "development_status:\n  story-1: in-progress\n")
        self.call("init", "--run", "new", "--lane", "quick", "--reason", "bypass", ok=False)

    def test_explicit_gate_overrides_lane(self):
        self.call("require", "--run", "test", "--gate", "ux", "--reason", "Primary UI")
        status = self.call("status", "--run", "test")
        self.assertEqual(status["gates"]["ux"], "missing/stale")

    def test_packet_bounds_and_traversal(self):
        self.call("packet", "--run", "test", "--story", "2-1", "--output", "packet.json", "--max-chars", "1", ok=False)
        self.assertFalse((self.p / "packet.json").exists())
        self.call("packet", "--run", "test", "--story", "2-1", "--output", "packet.json")
        self.call("packet", "--run", "test", "--story", "2-1", "--output", "../escape.json", ok=False)

    def test_legacy_yaml_preserved(self):
        old = self.write("_bmad-output/gate-ledger.yaml", "waivers:\n- scope: epic-batch-dev\n")
        before = old.read_bytes()
        self.call("doctor"); self.start(ok=False)
        self.assertEqual(before, old.read_bytes())

    def test_concurrent_updates_survive(self):
        def update(i):
            return self.call("decide", "--run", "test", "--step", f"decision-{i}", "--decision", "skip", "--reason", "not needed")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(update, range(16)))
        events = self.call("history", "--run", "test")
        self.assertEqual(len([x for x in events if x["action"] == "decide"]), 16)

    def test_hook_valid_and_invalid_tickets(self):
        self.hook("Use bmad-quick-dev", code=2)
        self.validate(); t = self.start()["ticket"]
        self.hook("Use bmad-quick-dev BMAD_TICKET:" + t)
        self.hook("Use bmad-quick-dev BMAD_TICKET:" + t, role="general-purpose", code=2)
        self.hook("Use bmad-quick-dev BMAD_TICKET:" + t, role="bmad-reviewer", code=2)
        self.call("cancel", "--run", "test", "--ticket", t, "--reason", "stopped")
        self.hook("Use bmad-quick-dev BMAD_TICKET:" + t, code=2)

    def test_hook_chores_and_planning(self):
        self.hook("Count files", role="general-purpose")
        self.hook("Use bmad-prd", role="bmad-planner")
        self.hook("Implement the assigned task", role="bmad-worker", code=2)

    def test_invalid_ledger_fails_without_overwrite(self):
        p = self.write(".bmad-orchestrator/ledger.json", "not-json")
        self.call("decide", "--run", "test", "--step", "x", "--decision", "skip", "--reason", "x", ok=False)
        self.assertEqual(p.read_text(), "not-json")

    def test_usage_unknown_and_duplicate(self):
        self.write("usage.json", json.dumps(dict(sample_id="1", source="host", input_tokens=123, cache_read_tokens=None)))
        self.call("usage", "--run", "test", "--file", "usage.json")
        self.call("usage", "--run", "test", "--file", "usage.json", ok=False)


    def test_companions_in_packet_and_stale_acceptance(self):
        self.write("specs/2-1.md", "---\ncompanions: [rules.md, ../contracts/api.md]\n---\n# Contract\n")
        self.write("specs/rules.md", "Idempotency rules")
        self.write("contracts/api.md", "Accepted interface")
        self.review()
        self.call("packet", "--run", "test", "--story", "2-1", "--output", "packet.json")
        packet = json.loads((self.p / "packet.json").read_text())
        self.assertIn("Accepted interface", packet["content"])
        self.write("contracts/api.md", "Changed interface")
        self.call("check", "done", "--run", "test", "--story", "2-1", ok=False)

    def test_missing_and_escaping_companions_block(self):
        for companion in ("missing.md", "../../escape.md"):
            self.write("specs/2-1.md", f"---\ncompanions: [{companion}]\n---\nContract\n")
            f = self.report("validation")
            self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f, ok=False)
            self.call("packet", "--run", "test", "--story", "2-1", "--output", "packet.json", ok=False)

    def test_waiver_invalidated_by_spec_change(self):
        self.call("waive", "--run", "test", "--story", "2-1", "--gate", "story-validated",
                  "--reason", "Approved scope", "--approval", "User quote")
        self.write("specs/2-1.md", "New behavior")
        self.start(ok=False)

    def test_review_waiver_bound_to_developed_sources(self):
        self.dev()
        self.call("waive", "--run", "test", "--story", "2-1", "--gate", "code-review",
                  "--reason", "Host unavailable", "--approval", "User quote")
        self.call("close", "--run", "test", "--story", "2-1")
        self.write("counter.py", "VALUE = 2\n")
        self.call("check", "code-review", "--run", "test", "--story", "2-1", ok=False)

    def test_done_requires_current_validation_and_planning(self):
        self.review()
        self.call("require", "--run", "test", "--gate", "prd", "--reason", "Scope added")
        self.call("check", "done", "--run", "test", "--story", "2-1", ok=False)
        self.write("requirements.md", "Accepted")
        f = self.report("prd", workflow="bmad-prd", story=None)
        self.call("record", "prd", "--run", "test", "--report", f, "--source", "requirements.md")
        self.call("check", "done", "--run", "test", "--story", "2-1")
        self.write("evidence/validation.md", "Invalidated")
        self.call("check", "done", "--run", "test", "--story", "2-1", ok=False)

    def test_added_config_causes_drift(self):
        self.write("_bmad/config.user.toml", '[core]\noutput_folder = "output"\n')
        self.call("doctor", ok=False)
        self.call("status", "--run", "test", ok=False)

    def native_dev(self):
        catalog = (self.p / "_bmad/_config/bmad-help.csv").read_text()
        self.write("_bmad/_config/bmad-help.csv", catalog + "bmad-build,true,Code\n")
        self.call("ack-version", "--run", "test", "--reason", "Build installed")
        return self.dev(workflow="bmad-build")

    def test_native_review_requires_identity_and_exact_snapshot(self):
        ticket = self.native_dev()
        refs = self.call("fingerprint", "--file", "specs/2-1.md", "counter.py")
        for actor, snapshot in (("dev", refs), ("native-reviewer", [])):
            f = self.report("native", actor=actor, workflow="bmad-build", parent_ticket=ticket, reviewed_sources=snapshot)
            self.call("accept-review", "--run", "test", "--story", "2-1", "--report", f, ok=False)
        f = self.report("native", actor="native-reviewer", workflow="bmad-build", parent_ticket=ticket, reviewed_sources=refs)
        self.call("accept-review", "--run", "test", "--story", "2-1", "--report", f)
        self.call("close", "--run", "test", "--story", "2-1")
        self.call("check", "done", "--run", "test", "--story", "2-1")

    def test_native_fail_does_not_close(self):
        ticket = self.native_dev()
        refs = self.call("fingerprint", "--file", "specs/2-1.md", "counter.py")
        f = self.report("native-fail", actor="native-reviewer", workflow="bmad-build", parent_ticket=ticket,
                        reviewed_sources=refs, verdict="fail", blockers=["Bug"])
        self.call("accept-review", "--run", "test", "--story", "2-1", "--report", f)
        self.call("close", "--run", "test", "--story", "2-1", ok=False)

    def catalog_cycle(self, version, lane):
        import csv
        catalog = (ROOT / "tests/fixtures" / f"bmad-{version}-help.csv").read_text()
        self.write("_bmad/_config/bmad-help.csv", catalog)
        self.write("_bmad/_config/manifest.yaml", f"installation:\n  version: {version}\n")
        self.call("ack-version", "--run", "test", "--reason", "Reviewed actual upstream catalog")
        self.call("lane", "--run", "test", "--lane", lane, "--reason", "Test installed routing")
        doctor = self.call("doctor")
        if lane == "full":
            mapping = {"bmad-prd": "prd", "bmad-create-architecture": "architecture", "bmad-architecture": "architecture",
                       "bmad-create-epics-and-stories": "epics", "bmad-sprint-planning": "sprint",
                       "bmad-check-implementation-readiness": "readiness"}
            for row in csv.DictReader(catalog.splitlines()):
                if row["required"] == "true" and row["skill"] in mapping:
                    g = mapping[row["skill"]]
                    f = self.report(g, workflow=row["skill"], story=None)
                    self.call("record", g, "--run", "test", "--report", f, "--source", "specs/2-1.md")
        modern = "bmad-build" in doctor["workflows"]
        f = self.report("validation", workflow="bmad-spec" if modern else "bmad-create-story")
        self.call("record", "story-validated", "--run", "test", "--story", "2-1", "--report", f)
        workflow = "bmad-build" if modern else "bmad-dev-story"
        t = self.call("start", "--run", "test", "--story", "2-1", "--phase", "dev", "--actor", "dev", "--workflow", workflow)["ticket"]
        if modern:
            prompt = "Required bmad-build review substep BMAD_PARENT_TICKET:" + t
            self.hook(prompt, role="general-purpose")
            self.hook(prompt, role="bmad-worker", code=2)
        self.write("counter.py", "VALUE = 1\n"); self.write("test.log", "OK\n")
        f = self.report("dev", actor="dev", workflow=workflow, files=["counter.py"],
                        checks=[dict(command="python -m unittest", exit_code=0, log="test.log")])
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        refs = self.call("fingerprint", "--file", "specs/2-1.md", "counter.py")
        f = self.report("review", actor="reviewer", workflow="bmad-build" if modern else "bmad-code-review", reviewed_sources=refs, parent_ticket=t)
        if modern:
            self.call("accept-review", "--run", "test", "--story", "2-1", "--report", f)
        else:
            t = self.start("review", "reviewer")["ticket"]
            self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        self.call("close", "--run", "test", "--story", "2-1")
        self.call("check", "done", "--run", "test", "--story", "2-1")
        if modern:
            self.hook(prompt, role="general-purpose", code=2)

    def test_actual_68_full_catalog_cycle(self):
        self.catalog_cycle("6.8.0", "full")

    def test_actual_611_full_catalog_cycle(self):
        self.catalog_cycle("6.11.0", "full")

    def test_actual_611_quick_catalog_cycle(self):
        self.catalog_cycle("6.11.0", "quick")


    def test_native_route_cannot_skip_standalone_review_reservation(self):
        ticket = self.dev()
        refs = self.call("fingerprint", "--file", "specs/2-1.md", "counter.py")
        f = self.report("native", actor="reviewer", workflow="bmad-code-review", parent_ticket=ticket, reviewed_sources=refs)
        self.call("accept-review", "--run", "test", "--story", "2-1", "--report", f, ok=False)

    def test_shared_dependency_code_can_change_but_requires_revalidation(self):
        self.review()
        self.write("stories/2-2.md", "Extend counter")
        self.write("specs/2-2.md", "Preserve idempotency and add reset")
        self.call("story", "--run", "test", "--story", "2-2", "--file", "stories/2-2.md", "--spec", "specs/2-2.md", "--depends", "2-1")
        f = self.report("validation2", story="2-2")
        self.call("record", "story-validated", "--run", "test", "--story", "2-2", "--report", f)
        t = self.call("start", "--run", "test", "--story", "2-2", "--phase", "dev", "--actor", "dev2", "--workflow", "bmad-quick-dev")["ticket"]
        self.write("counter.py", "VALUE = 1\ndef reset(): pass\n")
        f = self.report("dev2", story="2-2", actor="dev2", workflow="bmad-quick-dev", files=["counter.py"],
                        checks=[dict(command="python -m unittest", exit_code=0, log="reports/test.log")])
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        self.call("check", "dev", "--run", "test", "--story", "2-2")
        self.call("check", "done", "--run", "test", "--story", "2-1", ok=False)
        t = self.call("start", "--run", "test", "--story", "2-2", "--phase", "review", "--actor", "reviewer2", "--workflow", "bmad-code-review")["ticket"]
        f = self.report("review2", story="2-2", actor="reviewer2", workflow="bmad-code-review")
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        self.call("close", "--run", "test", "--story", "2-2", ok=False)
        self.call("reopen", "--run", "test", "--story", "2-1", "--reason", "Revalidate accepted contract after shared-file extension")
        t = self.start()["ticket"]
        f = self.report("dev-recheck", actor="dev", workflow="bmad-quick-dev", files=["counter.py"],
                        no_changes_reason="Rechecked existing behavior", checks=[dict(command="python -m unittest", exit_code=0, log="reports/test.log")])
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        t = self.start("review", "reviewer")["ticket"]
        f = self.report("review-recheck", actor="reviewer", workflow="bmad-code-review")
        self.call("finish", "--run", "test", "--ticket", t, "--report", f)
        self.call("close", "--run", "test", "--story", "2-1")
        self.call("close", "--run", "test", "--story", "2-2")
        self.call("check", "done", "--run", "test", "--story", "2-2")


if __name__ == "__main__":
    unittest.main()
