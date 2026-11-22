"""Named validation fixture sets drawn from the reviewed corpora.

Ground-truth groups for future converter work:
  * identical same-name GMTs shared by GTL and GTR2 (safe carry-over cases)
  * the rFactor 1 GMTs using the new layout (old->new converter validation)
  * the known non-standard GMT and undecrypted PHS files (edge cases)
"""
import glob
import os
import struct
import sys
import unittest
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")
ISI_RFACTOR = 0x38AF5637E81BC9A0


@lru_cache(maxsize=4)
def _gmt_members(root: str):
    """Return {basename_lower: [bytes]} of all GMTs in a corpus's MAS archives."""
    base = ROOT.parent / root
    out = defaultdict(list)
    for p in glob.glob(str(base / "**" / "*"), recursive=True):
        if not os.path.isfile(p) or not p.lower().endswith((".mas", ".gtr", ".gtl")):
            continue
        for e in mas_tool.read_archive(p)[1]:
            if e.name.lower().endswith(".gmt") and e.data:
                out[e.name.lower()].append(e.data)
    return dict(out)


class FixtureTest(unittest.TestCase):
    def test_identical_anderstorp_gmts_gtl_gtr2(self):
        # Same-track comparison (Anderstorp): 507 common basenames, 57 byte-identical.
        gtl = _gmt_members("GTLSteam/GameData/Locations/Anderstorp")
        gtr2 = _gmt_members("GTR2Steam/GameData/Locations/Anderstorp")
        if not gtl or not gtr2:
            self.skipTest("GTL/GTR2 Anderstorp archives not present")
        common = set(gtl) & set(gtr2)
        self.assertEqual(len(common), 507)
        identical = [n for n in common if any(a == b for a in gtl[n] for b in gtr2[n])]
        self.assertEqual(len(identical), 57)

    def test_new_layout_gmts_in_rfactor1(self):
        # Two unencrypted GMTs in Form06.MAS use the new layout (magic at 0x08).
        gmts = _gmt_members("RF1Vanilla")
        if not gmts:
            self.skipTest("RF1Vanilla corpus not present")
        found = []
        for name, entries in gmts.items():
            for data in entries:
                sign, key = struct.unpack_from("<QQ", data, 0)
                if (sign ^ key) & 0xFFFFFFFFFFFFFFFF == ISI_RFACTOR:
                    continue  # encrypted; full check lives in test_rf1_vanilla
                if data[8:24] == NEW_MAGIC:
                    found.append(name)
        self.assertIn("form_driver.gmt", found)
        self.assertIn("form_helmet.gmt", found)

    def test_plain_phs_and_detomaso_fixtures(self):
        arcs = []
        base = ROOT.parent / "GTLSteam"
        for p in glob.glob(str(base / "**" / "*"), recursive=True):
            if os.path.isfile(p) and p.lower().endswith((".gtl", ".gtr", ".mas")):
                arcs.append(p)
        if not arcs:
            self.skipTest("GTLSteam corpus not present")
        phs = [e for a in arcs for e in mas_tool.read_archive(a)[1]
               if e.name.lower().endswith(".phs")]
        self.assertEqual(len(phs), 5)
        odd = [e.name for a in arcs for e in mas_tool.read_archive(a)[1]
               if e.name.lower().endswith(".gmt") and e.data[8:24] != NEW_MAGIC]
        self.assertEqual(odd, ["DETOMASO_PANTERA_RAINSCREEN.GMT"])


if __name__ == "__main__":
    unittest.main()
