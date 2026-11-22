"""Tests for the same-track corpus diff harness."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import corpus_diff as cd  # noqa: E402


class CorpusDiffTest(unittest.TestCase):
    def test_anderstorp_gmt_ground_truth(self):
        base = ROOT.parent
        a = base / "GTLSteam/GameData/Locations/Anderstorp"
        b = base / "GTR2Steam/GameData/Locations/Anderstorp"
        if not a.is_dir() or not b.is_dir():
            self.skipTest("Anderstorp corpora not present")
        report = cd.compare_trees(a, b, {".gmt"}, archives=True)
        gmt = report["stats"].get(".gmt")
        self.assertIsNotNone(gmt)
        self.assertEqual(gmt["common"], 507)
        self.assertEqual(gmt["identical"], 57)

    def test_other_extensions_reported(self):
        base = ROOT.parent
        a = base / "GTLSteam/GameData/Locations/Anderstorp"
        b = base / "GTR2Steam/GameData/Locations/Anderstorp"
        if not a.is_dir() or not b.is_dir():
            self.skipTest("Anderstorp corpora not present")
        report = cd.compare_trees(a, b)
        self.assertGreater(len(report["stats"]), 1)
        self.assertIn(".trk", report["stats"])
        self.assertIn(".gdb", report["stats"])


if __name__ == "__main__":
    unittest.main()
