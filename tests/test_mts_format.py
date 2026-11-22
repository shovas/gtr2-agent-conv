"""Tests for the partial CUBE MTS header parser."""
import glob
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402
import mts_format as mf  # noqa: E402


class MtsFormatTest(unittest.TestCase):
    def test_magic_constants(self):
        self.assertEqual(mf.MAGIC_410[:11], b"CUBE_MTS_4.")
        self.assertIn(b"4.20", mf.MAGIC_420)

    def test_real_headers_both_variants(self):
        counts = Counter()
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                if not e.name.lower().endswith(".mts"):
                    continue
                h = mf.parse_header(e.data)
                counts[h.variant] += 1
                self.assertGreater(h.object_count, 0)
                self.assertTrue(h.name)
            if sum(counts.values()) >= 500:
                break
        if not counts:
            self.skipTest("CUBE MTS corpus not present")
        self.assertIn("4.10", counts)
        self.assertIn("4.20", counts)


if __name__ == "__main__":
    unittest.main()
