import datetime as dt
import tempfile
import unittest
from pathlib import Path

from agency.gate import deploy, drift


class DeployTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        base = Path(self.d.name)
        self.src, self.live, self.manifest = base / "clone", base / "live", base / "state" / "manifest.json"
        self.src.mkdir()
        self.live.mkdir()
        self.write(self.src, "agents/ops/run.py", "print('v1')\n")
        self.files = ["agents/ops/run.py"]
        self.noon = dt.datetime(2026, 10, 13, 12, 0)

    def tearDown(self):
        self.d.cleanup()

    def write(self, root, rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def go(self, **kw):
        kw.setdefault("now", self.noon)
        return deploy.deploy(self.src, self.live, self.files, self.manifest, **kw)

    def test_first_deploy_copies_and_records(self):
        r = self.go()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(r.copied, self.files)
        self.assertEqual(drift.drift(self.live, self.manifest), [])

    def test_unchanged_is_a_no_op(self):
        self.go()
        self.assertEqual(self.go().stage, "nothing to deploy")

    def test_update_keeps_a_backup(self):
        self.go()
        self.write(self.src, "agents/ops/run.py", "print('v2')\n")
        r = self.go()
        self.assertEqual(r.stage, "deployed")
        self.assertEqual(len(r.backups), 1)
        self.assertEqual((self.live / r.backups[0]).read_text(), "print('v1')\n")

    def test_live_edit_blocks_the_deploy(self):
        self.go()
        self.write(self.live, "agents/ops/run.py", "print('hand fix')\n")
        self.write(self.src, "agents/ops/run.py", "print('v2')\n")
        r = self.go()
        self.assertFalse(r.ok)
        self.assertEqual(r.stage, "drift")
        self.assertIn("changed: agents/ops/run.py", r.detail)
        self.assertEqual((self.live / "agents/ops/run.py").read_text(), "print('hand fix')\n")

    def test_a_deploy_that_died_halfway_can_finish(self):
        self.files = ["agents/ops/run.py", "agents/ops/report.py"]
        self.write(self.src, "agents/ops/report.py", "print('r1')\n")
        self.go()
        self.write(self.src, "agents/ops/run.py", "print('v2')\n")
        self.write(self.src, "agents/ops/report.py", "print('r2')\n")
        # simulate a crash after copying only the first file, before the manifest was written
        self.write(self.live, "agents/ops/run.py", "print('v2')\n")
        r = self.go()
        self.assertEqual((r.ok, r.stage), (True, "deployed"), r.detail)
        self.assertEqual((self.live / "agents/ops/report.py").read_text(), "print('r2')\n")

    def test_failing_check_stops_before_copying(self):
        r = self.go(checks=[("tests", lambda: (False, "2 suites failed"))])
        self.assertEqual((r.ok, r.stage), (False, "tests"))
        self.assertFalse((self.live / "agents/ops/run.py").exists())

    def test_syntax_error_stops_the_deploy(self):
        self.write(self.src, "agents/ops/run.py", "def broken(:\n")
        r = self.go()
        self.assertEqual(r.stage, "compile")

    def test_quiet_windows(self):
        w = [("10:15", "11:30"), ("23:00", "01:00")]
        at = lambda h, m: dt.datetime(2026, 10, 13, h, m)
        self.assertTrue(deploy.in_quiet_window(at(10, 30), w))
        self.assertFalse(deploy.in_quiet_window(at(11, 30), w))
        self.assertTrue(deploy.in_quiet_window(at(0, 30), w))
        self.assertEqual(self.go(now=at(10, 45), quiet_windows=w).stage, "quiet window")


if __name__ == "__main__":
    unittest.main()
