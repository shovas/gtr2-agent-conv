"""Tests for the pre-push safety/privacy checker."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pre_push_check as ppc  # noqa: E402


class ScanTextTest(unittest.TestCase):
    def test_clean_text_with_allowlisted_identity(self):
        text = "Author: shovas <shovas@users.noreply.github.com>\nPath: ../GTR2Steam/GameData\n"
        self.assertEqual(ppc.scan_text(text, "sample.md"), [])

    def test_flags_secret_and_home_path_and_email(self):
        text = (
            'api_key = "abcdefgh12345678"\n'
            'ROOT="/home/someone/rfactortools"\n'
            "Contact: alice@example.com\n"
        )
        issues = ppc.scan_text(text, "sample.md")
        kinds = {i.kind for i in issues}
        self.assertIn("SECRET", kinds)
        self.assertIn("PII", kinds)
        self.assertTrue(any("home path" in i.detail for i in issues))
        self.assertTrue(any("email address" in i.detail for i in issues))

    def test_flags_github_token(self):
        issues = ppc.scan_text("token = ghp_" + "a" * 36, "config.py")
        self.assertTrue(any(i.kind == "SECRET" for i in issues))

    def test_repository_is_clean(self):
        issues = ppc.check_repo(allow_untracked=True)
        self.assertEqual(issues, [], "\n".join(str(i) for i in issues))


if __name__ == "__main__":
    unittest.main()
