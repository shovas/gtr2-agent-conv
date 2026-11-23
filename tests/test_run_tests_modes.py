"""Tests for the deterministic Quick/Normal/Full test-mode selection."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_tests  # noqa: E402


class TestModesTest(unittest.TestCase):
    def test_progressive_coverage(self):
        quick = set(run_tests.select("quick"))
        normal = set(run_tests.select("normal"))
        full = set(run_tests.select("full"))
        self.assertTrue(quick)
        self.assertTrue(quick <= normal <= full)
        self.assertEqual(run_tests.select("normal"), run_tests.QUICK + run_tests.NORMAL_EXTRA)

    def test_deterministic_order(self):
        for mode in ("quick", "normal", "full"):
            self.assertEqual(run_tests.select(mode), run_tests.select(mode))
        self.assertEqual(run_tests.select("full"), tuple(sorted(run_tests.select("full"))))

    def test_all_modules_exist(self):
        for name in run_tests.select("full"):
            self.assertTrue((ROOT / "tests" / f"{name}.py").is_file(), name)


if __name__ == "__main__":
    unittest.main()
