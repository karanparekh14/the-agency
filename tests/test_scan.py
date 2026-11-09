import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agency.gate import scan

# Every sensitive-looking value below is assembled at runtime, so this file never contains one, and every
# value is one that cannot exist: US exchanges never start with 1, London numbers never start with 0.
FAKE_ANTHROPIC = "sk-ant-" + "a1B2" * 6
FAKE_GITHUB = "gh" + "p_" + "Z9" * 15
FAKE_PRIVATE = "-----BEGIN " + "RSA PRIVATE KEY-----"
FAKE_CHAT_LINK = "https://claude" + ".ai/code/session_" + "0" * 24


class ScanTest(unittest.TestCase):
    def kinds(self, text, allow=frozenset(), deny=()):
        return [(f.level, f.kind) for f in scan.scan_text(text, "x.py", allow, deny)]

    def test_secrets_block(self):
        self.assertIn(("BLOCK", "anthropic-key"), self.kinds(f'KEY = "{FAKE_ANTHROPIC}"'))
        self.assertIn(("BLOCK", "github-token"), self.kinds(FAKE_GITHUB))
        self.assertIn(("BLOCK", "private-key"), self.kinds(FAKE_PRIVATE))
        self.assertIn(("BLOCK", "assigned-secret"), self.kinds('password = "' + "q" * 20 + '"'))
        self.assertIn(("BLOCK", "private-chat-link"), self.kinds("see " + FAKE_CHAT_LINK))
        self.assertIn(("BLOCK", "app-password"), self.kinds('app_pass = "' + "abcd efgh " + "ijkl mnop" + '"'))

    def test_ordinary_quoted_words_are_not_app_passwords(self):
        self.assertEqual(self.kinds('print("make sure your code")'), [])

    def test_blocked_values_are_masked(self):
        out = str(scan.scan_text(FAKE_ANTHROPIC, "x.py")[0])
        self.assertNotIn(FAKE_ANTHROPIC, out)

    def test_real_looking_contacts_need_review(self):
        self.assertIn(("REVIEW", "email"), self.kinds("write to " + "jane" + "@" + "acme-corp.com"))
        n = "2210"
        for phone in ["+44 20 0" + "123 4567", "(800) 164-" + n, "800-164-" + n, "800.164." + n]:
            self.assertIn(("REVIEW", "phone"), self.kinds(f"call {phone} today"), phone)
        self.assertIn(("REVIEW", "whatsapp-id"), self.kinds("120363" + "1" * 12 + "@g.us"))

    def test_placeholders_pass(self):
        for text in ["pat@vendor.test", "ops@example.com", "(800) 555-0142", "+1 800 555 0199", "+44 20 7946 0123",
                     "120363" + "0" * 12 + "@g.us", "noreply@anthropic.com"]:
            self.assertEqual(self.kinds(text), [], text)

    def test_allow_list_and_reviewed_files(self):
        email = "lead" + "@" + "acme-corp.com"
        self.assertEqual(self.kinds(email, frozenset({email})), [])
        self.assertEqual(self.kinds(email, frozenset({"file:x.py"})), [])

    def test_denylist_blocks_private_names_as_whole_words(self):
        deny = ("acme widgets", "zed")
        self.assertIn(("BLOCK", "denylisted"), self.kinds("built for Acme Widgets in 2026", deny=deny))
        self.assertIn(("BLOCK", "denylisted"), self.kinds("thanks, Zed!", deny=deny))
        self.assertEqual(self.kinds("a zedonk is not a name", deny=deny), [])

    def test_denylist_catches_squeezed_and_hyphenated_forms(self):
        deny = ("acme widgets",)
        for text in ["AcmeWidgets", "Acme-Widgets", "Acme  Widgets", "Acme\u00a0Widgets", "acme_widgets"]:
            self.assertIn(("BLOCK", "denylisted"), self.kinds(text, deny=deny), text)

    def test_more_private_chat_links(self):
        for path in ["/project/" + "a" * 12, "/artifact/" + "b" * 12]:
            self.assertIn(("BLOCK", "private-chat-link"), self.kinds("claude" + ".ai" + path))

    def test_denylist_file_from_environment(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "deny.txt"
            f.write_text("# private\nAcme Widgets\n", encoding="utf-8")
            old = os.environ.get("AGENCY_SCAN_DENYLIST")
            os.environ["AGENCY_SCAN_DENYLIST"] = str(f)
            try:
                self.assertEqual(scan.load_denylist(), ("acme widgets",))
                self.assertTrue(scan.scan_text("for Acme Widgets", "x.md", frozenset()))
            finally:
                if old is None:
                    os.environ.pop("AGENCY_SCAN_DENYLIST")
                else:
                    os.environ["AGENCY_SCAN_DENYLIST"] = old

    def test_dates_and_ids_are_not_phones(self):
        self.assertEqual(self.kinds("on 2026-10-13 at 10:30, run 42, v0.1.0"), [])

    def test_scan_paths_reads_files_and_allow_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("contact: " + "sam" + "@" + "acme-corp.com\n", encoding="utf-8")
            self.assertEqual(len(scan.scan_paths([root / "a.md"], root)), 1)
            (root / "scan-allow.txt").write_text("# reviewed\nfile:a.md\n", encoding="utf-8")
            self.assertEqual(scan.scan_paths([root / "a.md"], root), [])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_staged_copy_is_what_gets_scanned(self):
        # A key that was staged and then removed from the working copy must still be caught.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "cfg.py").write_text(f'KEY = "{FAKE_ANTHROPIC}"\n', encoding="utf-8")
            subprocess.run(["git", "add", "cfg.py"], cwd=root, check=True)
            (root / "cfg.py").write_text("KEY = None\n", encoding="utf-8")
            self.assertEqual(scan.scan_paths([root / "cfg.py"], root), [])
            self.assertEqual([f.kind for f in scan.scan_staged(["cfg.py"], root)], ["anthropic-key"])


if __name__ == "__main__":
    unittest.main()
