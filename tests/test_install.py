import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

import yaml

SOURCE = Path(__file__).resolve().parents[1]


class Install(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bmad install spaces ")
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def install(self, *flags, ok=True):
        x = subprocess.run([sys.executable, str(SOURCE / "install.py"), "--project", str(self.project), *flags],
                           text=True, capture_output=True)
        self.assertEqual(x.returncode == 0, ok, x.stderr)
        return x

    def test_dry_run_creates_nothing(self):
        self.install("--platform", "codex", "--agents")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_codex_install_has_parseable_agents(self):
        self.install("--platform", "codex", "--agents", "--apply")
        target = self.project / ".agents/skills/orchestrator-bmad"
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertTrue((target / "references/codex.md").is_file())
        for p in (self.project / ".codex/agents").glob("*.toml"):
            agent = tomllib.loads(p.read_text())
            self.assertTrue(agent["name"] and agent["developer_instructions"])
            self.assertNotIn("model", agent)

    def test_claude_preserves_settings_and_hook_runs(self):
        p = self.project / ".claude/settings.json"
        p.parent.mkdir()
        p.write_text(json.dumps({"permissions": {"deny": ["Bash(rm:*)"]}, "hooks": {"Stop": []}}))
        self.install("--platform", "claude", "--hook", "--apply")
        settings = json.loads(p.read_text())
        self.assertEqual(settings["permissions"]["deny"], ["Bash(rm:*)"])
        self.assertEqual(settings["hooks"]["Stop"], [])
        hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        x = subprocess.run([hook["command"], *hook["args"]], input=json.dumps({"tool_name": "Agent", "cwd": str(self.project),
            "tool_input": {"subagent_type": "general-purpose", "prompt": "List files"}}), text=True, capture_output=True)
        self.assertEqual(x.returncode, 0, x.stderr)
        for p in (self.project / ".claude/agents").glob("*.md"):
            agent = yaml.safe_load(p.read_text().split("---")[1])
            self.assertEqual(agent["model"], "inherit")
            self.assertIn("Agent", agent["tools"].split(", "))

    def test_directory_conflict_preflight_writes_nothing(self):
        p = self.project / ".agents/skills/orchestrator-bmad/VERSION"
        p.mkdir(parents=True)
        self.install("--platform", "codex", "--apply", "--upgrade", ok=False)
        self.assertFalse((p.parent / "SKILL.md").exists())
        self.assertFalse((self.project / ".bmad-orchestrator-backups").exists())

    def test_idempotent_hook_registration(self):
        for _ in range(2):
            self.install("--platform", "claude", "--hook", "--apply")
        data = json.loads((self.project / ".claude/settings.json").read_text())
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)

    def test_conflict_requires_upgrade_and_backs_up(self):
        self.install("--platform", "codex", "--apply")
        p = self.project / ".agents/skills/orchestrator-bmad/SKILL.md"
        p.write_text("User customized this skill")
        self.install("--platform", "codex", "--apply", ok=False)
        self.assertEqual(p.read_text(), "User customized this skill")
        self.install("--platform", "codex", "--apply", "--upgrade")
        saved = list((self.project / ".bmad-orchestrator-backups").rglob("SKILL.md"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), "User customized this skill")

    def test_no_claude_hook_in_codex(self):
        self.install("--platform", "codex", "--hook", "--apply", ok=False)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_invalid_settings_leave_project_untouched(self):
        p = self.project / ".claude/settings.json"; p.parent.mkdir(); p.write_text("bad-json")
        self.install("--platform", "claude", "--hook", "--apply", ok=False)
        self.assertFalse((self.project / ".claude/skills").exists())
        self.assertEqual(p.read_text(), "bad-json")


if __name__ == "__main__":
    unittest.main()
