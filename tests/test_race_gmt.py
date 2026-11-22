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

    def test_rejects_other_gmt(self):
        with self.assertRaises(ValueError):
            race_gmt.parse_header(b"NOPE" + b"\0" * 64)


if __name__ == "__main__":
    unittest.main()
