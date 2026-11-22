"""Observations from the NASCAR Thunder 2004 (ISI, pre-ISImotor) corpus (../NT2004).

This early ISI title uses MAS type 3 and CUBE MTS meshes, like F1 2002/F1C.
"""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

NT = ROOT.parent / "NT2004"
MTS_MAGIC = b"CUBE_MTS_4.10\x00\x00\x00"


def _archives():
    if not NT.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(NT / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class NascarThunder2004Test(unittest.TestCase):
    def test_type3_archives_and_cube_mts(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("NT2004 corpus not present")
        self.assertEqual(len(arcs), 136)
        total = mts = 0
        for arc in arcs:
            sig, entries = mas_tool.read_signature(arc), mas_tool.read_archive(arc)[1]
            self.assertEqual(sig, mas_tool.MAS_TYPE3, arc)
            total += len(entries)
            for e in entries:
                if e.name.lower().endswith(".mts"):
                    mts += 1
                    self.assertEqual((e.data or b"")[:16], MTS_MAGIC, (arc, e.name))
        self.assertEqual(total, 20414)
        self.assertEqual(mts, 14250)

    def test_other_formats_observed(self):
        if not NT.is_dir():
            self.skipTest("NT2004 corpus not present")
        # .djs audio starts with an MPEG frame sync; .skn skins are plain text.
        djs = [Path(p) for p in glob.glob(str(NT / "**" / "*"), recursive=True)
               if os.path.isfile(p) and p.lower().endswith(".djs")]
        self.assertEqual(len(djs), 14)
        for p in djs:
            self.assertEqual(p.read_bytes()[:2], b"\xff\xfb", p)
        skn = [Path(p) for p in glob.glob(str(NT / "**" / "*"), recursive=True)
               if os.path.isfile(p) and p.lower().endswith(".skn")]
        self.assertEqual(len(skn), 81)
        self.assertTrue(any(p.read_bytes().startswith(b"////") for p in skn))


if __name__ == "__main__":
    unittest.main()
