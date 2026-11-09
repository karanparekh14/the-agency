import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agency.gate import trace

RULES = {"owner": "owner",
         "agents": {"owner": {"kind": "human", "paths": ["**"]},
                    "claude-code": {"kind": "dev-llm", "paths": ["**"]},
                    "operator": {"kind": "own-agent", "paths": ["agents/operator/notes/**"]}},
         "protected": ["PROJECT/ACCESS.json", "agency/gate/**"]}
OK = "Fix x\n\nbody\n\nAgent: claude-code\nWhy: owner asked"


class CheckTest(unittest.TestCase):
    def ok(self, msg, files, rules=RULES):
        return not trace.check(msg, files, rules)

    def test_rules(self):
        self.assertTrue(self.ok(OK, ["agents/ops/a.py"]))
        self.assertFalse(self.ok("Fix x\n\nWhy: because", ["a.py"]))
        self.assertFalse(self.ok("Fix x\n\nAgent: claude-code", ["a.py"]))
        self.assertFalse(self.ok("Fix x\n\nAgent: mystery\nWhy: y", ["a.py"]))
        self.assertTrue(self.ok("Fix x\n\nAgent: claude-code (some model)\nWhy: y", ["a.py"]))
        self.assertFalse(self.ok("n\n\nAgent: claude-code\nWhy: y\n\nmore text", ["a.py"]))

    def test_own_agents_stay_in_their_files(self):
        self.assertTrue(self.ok("n\n\nAgent: operator\nWhy: approved", ["agents/operator/notes/x.md"]))
        self.assertFalse(self.ok("n\n\nAgent: operator\nWhy: y", ["agents/ops/run.py"]))
        self.assertFalse(self.ok("n\n\nAgent: operator\nWhy: y\nApproved-by: owner", ["PROJECT/ACCESS.json"]))

    def test_protected_files(self):
        self.assertFalse(self.ok(OK, ["agency/gate/deploy.py"]))
        self.assertTrue(self.ok(OK + "\nApproved-by: owner", ["agency/gate/deploy.py"]))
        self.assertTrue(self.ok("n\n\nAgent: owner\nWhy: mine", ["agency/gate/deploy.py"]))

    def test_missing_owner_never_approves_everything(self):
        rules = dict(RULES, owner="")
        self.assertFalse(self.ok(OK + "\nApproved-by: someone", ["agency/gate/deploy.py"], rules))

    def test_approval_must_be_exactly_the_owner(self):
        self.assertFalse(self.ok(OK + "\nApproved-by: ownerbot", ["agency/gate/deploy.py"]))

    def test_single_star_stays_inside_one_folder(self):
        rules = dict(RULES, agents=dict(RULES["agents"], ops={"kind": "own-agent", "paths": ["examples/sample_*.json"]}))
        self.assertTrue(self.ok("n\n\nAgent: ops\nWhy: y", ["examples/sample_inbox.json"], rules))
        self.assertFalse(self.ok("n\n\nAgent: ops\nWhy: y", ["examples/sample_x/evil.json"], rules))

    def test_author_identity_is_checked(self):
        self.assertEqual(trace.identity_problems("Dev", "dev@example.com"), [])
        self.assertEqual(trace.identity_problems("Octo Cat", "octocat@users.noreply.github.com"), [])
        self.assertTrue(trace.identity_problems("Someone", "someone" + "@" + "realcompany.com"))

    def test_commit_messages_are_scanned(self):
        link = "https://claude" + ".ai/code/session_" + "0" * 24
        self.assertTrue(trace.message_problems(OK + "\nSee: " + link))
        self.assertTrue(trace.message_problems(OK + "\nReply to " + "sam" + "@" + "acme-corp.com"))
        self.assertEqual(trace.message_problems(OK), [])


@unittest.skipUnless(shutil.which("git"), "git not installed")
class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.root = Path(self.d.name)
        self.git("init", "-q")
        self.git("config", "user.email", "dev@example.com")
        self.git("config", "user.name", "dev")
        self.git("config", "commit.gpgsign", "false")

    def tearDown(self):
        self.d.cleanup()

    def git(self, *a):
        subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)

    def commit(self, files: dict, msg: str):
        for name, text in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def test_rules_in_first_commit(self):
        # A fresh public repo starts with the rules in its root commit; this used to crash.
        self.commit({"PROJECT/ACCESS.json": json.dumps(RULES)}, "Start\n\nAgent: owner\nWhy: new repo")
        self.commit({"a.py": "x = 1\n"}, "Add a\n\nAgent: claude-code\nWhy: owner asked")
        self.assertEqual(trace.history(self.root), [])

    def test_untraced_commit_is_found(self):
        self.commit({"PROJECT/ACCESS.json": json.dumps(RULES)}, "Start\n\nAgent: owner\nWhy: new repo")
        self.commit({"b.py": "y = 2\n"}, "quick fix")
        bad = trace.history(self.root)
        self.assertEqual(len(bad), 1)
        self.assertIn("no 'Agent:' line", bad[0][2])

    def test_commits_before_the_rules_are_not_judged(self):
        self.commit({"old.py": "z = 0\n"}, "before the rules existed")
        self.commit({"PROJECT/ACCESS.json": json.dumps(RULES)}, "Rules\n\nAgent: owner\nWhy: start tracing")
        self.assertEqual(trace.history(self.root), [])

    def test_a_commit_cannot_widen_its_own_access(self):
        self.commit({"PROJECT/ACCESS.json": json.dumps(RULES)}, "Start\n\nAgent: owner\nWhy: new repo")
        wider = json.loads(json.dumps(RULES))
        wider["agents"]["operator"]["paths"] = ["**"]
        wider["protected"] = []
        self.commit({"PROJECT/ACCESS.json": json.dumps(wider), "agents/ops/run.py": "x\n"},
                    "Widen\n\nAgent: operator\nWhy: I want more")
        bad = trace.history(self.root)
        self.assertEqual(len(bad), 1)
        self.assertTrue(any("protected" in p for p in bad[0][2]))


if __name__ == "__main__":
    unittest.main()
