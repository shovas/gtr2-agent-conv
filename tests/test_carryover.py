"""End-to-end GTL->GTR2 binary carry-over validation using the 57 identical
same-name GMTs found in the Anderstorp archives.
"""
import glob
import os
import sys
import tempfile
import unittest
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import mas_tool  # noqa: E402


@lru_cache(maxsize=1)
def _identical_pairs():
    def collect(root):
        out = defaultdict(list)
        for p in glob.glob(str(root / "**" / "*"), recursive=True):
            if os.path.isfile(p) and p.lower().endswith((".gtl", ".gtr", ".mas")):
                for e in mas_tool.read_archive(p)[1]:
                    if e.name.lower().endswith(".gmt") and e.data:
                        out[e.name.lower()].append(e.data)
        return out
    gtl = collect(ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp")
    gtr2 = collect(ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp")
    if not gtl or not gtr2:
        return []
    common = set(gtl) & set(gtr2)
    return [(n, gtl[n][0]) for n in sorted(common)
            if any(a == b for a in gtl[n] for b in gtr2[n])]


class CarryOverTest(unittest.TestCase):
    def test_57_identical_gmts_parse_and_repack(self):
        pairs = _identical_pairs()
        if not pairs:
            self.skipTest("GTL/GTR2 Anderstorp archives not present")
        self.assertEqual(len(pairs), 57)

        entries = []
        for i, (name, data) in enumerate(pairs):
            with self.subTest(name=name):
                g = gmt_format.parse_gmt(name, data)
                self.assertEqual(gmt_format.write_gmt(g), data)
                entries.append(mas_tool.Entry(name=name.upper(), offset=0, size=len(data),
                                              zsize=0, type=17, data=data))
        with tempfile.TemporaryDirectory() as td:
            arc = Path(td) / "carryover.gtr"
            mas_tool.write_archive(arc, entries, mas_type=0)
            mtype, out = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 0)
            self.assertEqual([e.name for e in out], [e.name for e in entries])
            for a, b in zip(entries, out):
                self.assertEqual(a.data, b.data, a.name)


if __name__ == "__main__":
    unittest.main()
