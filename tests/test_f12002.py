"""Observations from the F1 2002 (ISI, 2002) reference corpus (../F12002).

F1 2002 sits between Sports Car GT and F1 Challenge/rFactor in the ISIMotor
lineage. Its archives are MAS type 3 (CUBEMAS4.10) and its meshes are CUBE MTS.
These tests record verified structural evidence only.
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

F1 = ROOT.parent / "F12002"
MTS_MAGIC = b"CUBE_MTS_4.10\x00\x00\x00"


def _archives():
    if not F1.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(F1 / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class F12002Test(unittest.TestCase):
    def test_type3_mas_archives_read(self):
        # Observed: all 63 .mas files use the CUBEMAS4.10 (MAS type 3) signature.
        arcs = _archives()
        if not arcs:
            self.skipTest("F12002 corpus not present")
        self.assertEqual(len(arcs), 63)
        total = 0
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), mas_tool.MAS_TYPE3, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 3, arc)
            total += len(entries)
        self.assertEqual(total, 19235)

    def test_mts_magic_variants_observed(self):
        # Observed: 12,640 of 13,100 .mts members start with CUBE_MTS_4.10;
        # 460 use a different header (object-level records; semantics unknown).
        arcs = _archives()
        if not arcs:
            self.skipTest("F12002 corpus not present")
        standard = other = 0
        for arc in arcs:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".mts"):
                    continue
                if (e.data or b"")[:16] == MTS_MAGIC:
                    standard += 1
                else:
                    other += 1
        self.assertEqual(standard, 12640)
        self.assertEqual(other, 460)

    def test_type3_member_roundtrip(self):
        arc = F1 / "Season02/Tracks/Australia/Australia.mas"
        if not arc.exists():
            self.skipTest("F12002 corpus not present")
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
