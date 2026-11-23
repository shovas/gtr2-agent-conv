"""Tests for the GTTF/IRSR structural reader (29 GTT + 13 VCR files)."""
import glob
import gzip
import math
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

    def test_gttf_frame_grid(self):
        import gzip
        import re
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        checked = 0
        for p in files[:6]:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            self.assertEqual(grid["stride"], 63)
            frames = setool.read_frames(data, grid)
            self.assertGreater(len(frames), 400)
            # At a 63-byte stride consecutive samples are adjacent frames, so
            # position deltas are small; a 252-byte stride skipped 4 frames.
            deltas = [abs(frames[i + 1]["position"][0] - frames[i]["position"][0])
                      for i in range(len(frames) - 1)]
            self.assertLess(max(deltas), 5.0)
            self.assertTrue(all(0 < frames[i + 1]["time"] - frames[i]["time"] < 1.0
                                for i in range(len(frames) - 1)))
            self.assertTrue(any(abs(x) > 1 for x in frames[0]["position"]))
            self.assertTrue(all(-math.pi <= fr["heading"] <= math.pi for fr in frames))
            self.assertTrue(any(abs(fr["pitch"]) > 0.001 for fr in frames))
            m = re.search(r"(\d)_(\d+)_(\d+)_", p.name)
            if m:
                lap = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 1000
                span = frames[-1]["time"] - frames[0]["time"]
                self.assertLess(abs(span - lap), 2.0)
            checked += 1
        if not checked:
            self.skipTest("no GTTF frame grids detected")
        self.assertGreaterEqual(checked, 1)

    def test_gttf_frame_count_matches_record_marker(self):
        """The 63-byte record marker independently validates the frame grid."""
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        # Documented by the (reference-only) gtr2-agent-tools ghost loader:
        # 63-byte records marked by this 7-byte prefix; the trailing byte varies.
        mark = b"\x01\x00\x00\x34\x00\x20\x00"
        checked = 0
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            self.assertLessEqual(abs(data.count(mark) - grid["count"]), 2, p.name)
            checked += 1
        self.assertGreaterEqual(checked, 1)

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

    def test_gtr2_replay_metadata(self):
        files = _files(".vcr")
        if not files:
            self.skipTest("GTR2 VCR files not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertTrue(e.team)
                self.assertTrue(e.driver)
                self.assertIsNone(e.co_driver)
                self.assertTrue(e.car.lower().endswith(".car"))

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
