"""Tests for the GTTF/IRSR structural reader (29 GTT + 13 VCR files)."""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simbin_events_tool as setool  # noqa: E402


def _files(ext):
    base = ROOT.parent / "GTR2Steam"
    return [p for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext.lower()]


class SimbinEventsToolTest(unittest.TestCase):
    def test_gtt_headers(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        self.assertEqual(len(files), 29)
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "GTTF")
                self.assertEqual(e.version, 1.0)
                self.assertTrue(e.trk.lower().endswith(".trk"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))

    def test_vcr_headers(self):
        files = _files(".vcr")
        if not files:
            self.skipTest("GTR2 VCR files not present")
        self.assertGreater(len(files), 0)
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertAlmostEqual(e.version, 1.05, places=4)
                self.assertTrue(e.trk.lower().endswith(".trk"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))

    def test_driver_and_car_strings_extracted(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        e = setool.parse_file(files[0])
        joined = " ".join(s for _, s in e.strings)
        self.assertIn("Henrik Roos", joined)
        self.assertIn(".CAR", joined)


if __name__ == "__main__":
    unittest.main()
