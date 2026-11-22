"""Observations from the F1 2000 (ISI, 2000) corpus (../F12000).

F1 2000 uses a new MAS variant (`CUBEMAS2.50`, type 5 in mas_tool) with
256-byte file records. These tests record verified structural evidence.
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

F1 = ROOT.parent / "F12000"


def _archives():
    if not F1.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(F1 / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class F12000Test(unittest.TestCase):
    def test_type25_archives_read(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("F12000 corpus not present")
        self.assertEqual(len(arcs), 118)
        counts = {0: 0, 1: 0, 2: 0}
        total = 0
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc)[:12], mas_tool.MAS_TYPE25, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 5, arc)
            total += len(entries)
            for e in entries:
                self.assertIn(e.type, counts)
                counts[e.type] += 1
        self.assertEqual(total, 30909)
        self.assertEqual(counts, {0: 25392, 1: 5198, 2: 319})

    def test_type25_member_roundtrip(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("F12000 corpus not present")
        arc = sorted(arcs)[0]
        mtype, entries = mas_tool.read_archive(arc)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mas"
            mas_tool.write_archive(out, entries, mas_type=mtype)
            m2, e2 = mas_tool.read_archive(out)
        self.assertEqual(m2, mtype)
        self.assertEqual([e.name for e in e2], [e.name for e in entries])
        for a, b in zip(entries, e2):
            self.assertEqual((a.type, a.size, a.data), (b.type, b.size, b.data), a.name)

    def test_other_formats_observed(self):
        if not F1.is_dir():
            self.skipTest("F12000 corpus not present")
        # .scn scene files use the CUBEASF header, as seen in F1 2002/F1C.
        scn = [Path(p) for p in glob.glob(str(F1 / "**" / "*"), recursive=True)
               if os.path.isfile(p) and p.lower().endswith(".scn")]
        self.assertEqual(len(scn), 71)
        self.assertTrue(any(p.read_bytes().startswith(b"CUBEASF") for p in scn))
        # .tgq animation textures start with SCHl.
        tgq = [Path(p) for p in glob.glob(str(F1 / "**" / "*"), recursive=True)
               if os.path.isfile(p) and p.lower().endswith(".tgq")]
        self.assertEqual(len(tgq), 22)
        self.assertTrue(all(p.read_bytes().startswith(b"SCHl") for p in tgq))


if __name__ == "__main__":
    unittest.main()
