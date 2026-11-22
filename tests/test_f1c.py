"""Observations from the F1 Challenge 99-02 (ISI, 2003) reference corpus (../F1C).

F1C is the direct predecessor of rFactor and shares F1 2002's MAS type-3 /
CUBE MTS format family. These tests record verified structural evidence only.
"""
import glob
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

F1C = ROOT.parent / "F1C"
MTS_MAGIC = b"CUBE_MTS_4.10\x00\x00\x00"


def _archives():
    if not F1C.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(F1C / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class F1ChallengeTest(unittest.TestCase):
    def test_type3_mas_archives_read(self):
        # Observed: all 197 .mas files use the MAS type-3 CUBEMAS4.10 signature.
        arcs = _archives()
        if not arcs:
            self.skipTest("F1C corpus not present")
        self.assertEqual(len(arcs), 197)
        total = 0
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), mas_tool.MAS_TYPE3, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 3, arc)
            total += len(entries)
        self.assertEqual(total, 21977)

    def test_mts_magic_variants_observed(self):
        # Observed: 13,769 of 14,834 .mts members have the standard magic;
        # 1,065 start with an object-level record (name/count), semantics unconfirmed.
        arcs = _archives()
        if not arcs:
            self.skipTest("F1C corpus not present")
        standard = variant = 0
        for arc in arcs:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".mts"):
                    continue
                if (e.data or b"")[:16] == MTS_MAGIC:
                    standard += 1
                else:
                    variant += 1
        self.assertEqual(standard, 13769)
        self.assertEqual(variant, 1065)

    def test_type3_member_roundtrip(self):
        arcs = sorted(_archives())
        if not arcs:
            self.skipTest("F1C corpus not present")
        arc = arcs[0]
        mtype, entries = mas_tool.read_archive(arc)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mas"
            mas_tool.write_archive(out, entries, mas_type=mtype)
            m2, e2 = mas_tool.read_archive(out)
        self.assertEqual(m2, mtype)
        self.assertEqual([e.name for e in e2], [e.name for e in entries])
        for a, b in zip(entries, e2):
            self.assertEqual((a.size, a.data), (b.size, b.data), a.name)


if __name__ == "__main__":
    unittest.main()
