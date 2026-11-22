"""Tests for the partial RaceGMT header parser."""
import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import race_gmt  # noqa: E402


class RaceGmtTest(unittest.TestCase):
    def test_real_headers(self):
        files = [p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"), recursive=True)
                 if Path(p).is_file() and Path(p).read_bytes()[:8] == race_gmt.MAGIC]
        if not files:
            self.skipTest("RaceGMT files not present")
        self.assertGreater(len(files), 600)
        for p in files[:20]:
            h = race_gmt.parse_header(Path(p).read_bytes())
            self.assertTrue(h.name)
            self.assertEqual(h.flags, race_gmt.FLAGS)
            self.assertEqual(len(h.floats), 12)

    def test_record_strides_from_same_size_pair(self):
        a = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        b = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_02.gmt"
        if not (a.is_file() and b.is_file()):
            self.skipTest("PEOPLE_STAND pair not present")
        report = race_gmt.diff_strides(a.read_bytes(), b.read_bytes())
        distances = report["distances"]
        self.assertGreater(distances.get(36, 0), 10)
        self.assertGreater(distances.get(64, 0), 10)

    def test_rejects_other_gmt(self):
        with self.assertRaises(ValueError):
            race_gmt.parse_header(b"NOPE" + b"\0" * 64)


if __name__ == "__main__":
    unittest.main()
