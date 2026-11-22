"""Observations for the GTR 2004 (GTR1) corpus."""
import glob
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

GTR1 = ROOT.parent / "GTR1Vanilla"
MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")


def _archives():
    return [p for p in (Path(x) for x in glob.glob(str(GTR1 / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ".gtr"]


class Gtr1VanillaTest(unittest.TestCase):
    def test_archives_and_gmt_magic(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("GTR1Vanilla corpus not present")
        self.assertEqual(len(arcs), 430)
        found = 0
        for arc in arcs[:20]:
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 0, arc)
            for e in entries:
                if e.name.lower().endswith(".gmt"):
                    header = (e.data or b"")[4:20]
                    self.assertTrue(header == MAGIC or header.startswith(b"OR_GMT_1.00"), (arc, e.name))
                    found += 1
        self.assertGreater(found, 0)


if __name__ == "__main__":
    unittest.main()
