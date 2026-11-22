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

    def test_gtt_metadata_framing(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.driver, "Henrik Roos")
                self.assertEqual(e.co_driver, "Gabriele Gardel")
                self.assertTrue(e.car.lower().endswith(".car"))
                self.assertGreater(e.metadata_offset, 0)

    def test_rf1_replay_metadata(self):
        base = ROOT.parent / "RF1Vanilla"
        files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() == ".vcr"]
        if not files:
            self.skipTest("rF1 replays not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertTrue(e.trk.lower().endswith(".scn"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))
                self.assertEqual(e.driver, "Shovas")
                self.assertTrue(e.car.lower().endswith(".veh"))
                self.assertIsNone(e.co_driver)

    def test_bmw_and_gtl_metadata(self):
        bmw = ROOT.parent / "BMWM3Challenge"
        gtl = ROOT.parent / "GTLSteam"
        cases = []
        for base, kind in ((bmw, "GTTF"), (gtl, "IRSR")):
            if not base.exists():
                continue
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if Path(p).is_file() and Path(p).suffix.lower() in (".gtt", ".vcr"):
                    cases.append((Path(p), kind))
        if not cases:
            self.skipTest("BMW M3 / GTL events not present")
        for p, kind in cases:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, kind)
                self.assertTrue(e.driver)
                self.assertTrue(e.car.lower().endswith((".car", ".veh")))
                if kind == "GTTF":
                    self.assertTrue(e.co_driver)
                else:
                    self.assertIsNone(e.co_driver)

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
