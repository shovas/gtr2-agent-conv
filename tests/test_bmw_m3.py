"""Observations from the BMW M3 Challenge reference corpus (../BMW M3 Challenge).

BMW M3 Challenge is an older ISIMotor-lineage title. Its on-disk formats match the
GTR2/GTL families already supported here; these tests record cross-game evidence,
not new semantics. All findings are structural observations only.
"""
import glob
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fxm_tool  # noqa: E402
import mas_tool  # noqa: E402

BMW = ROOT.parent / "BMW M3 Challenge"

NORMAL_GMT_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")
MAS_MAGIC = b"GMOTORMAS10\x00\x00\x00\x00\x00"


def _files(ext):
    if not BMW.is_dir():
        return []
    pat = str(BMW / "**" / "*")
    return [Path(p) for p in glob.glob(pat, recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == "." + ext.lower()]


class BmwM3CorpusTest(unittest.TestCase):
    def test_bmw_archives_are_gmotor_mas10(self):
        # Observed: 17 .bmw files are GMOTORMAS10 type-0 archives, same as GTR2 .gtr / GTL .gtl.
        arcs = _files("bmw")
        if not arcs:
            self.skipTest("BMW M3 Challenge corpus not present")
        self.assertEqual(len(arcs), 17)
        for arc in arcs:
            self.assertEqual(arc.read_bytes()[:16], MAS_MAGIC, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 0, arc)
            self.assertGreater(len(entries), 0, arc)

    def test_bmw_archive_member_roundtrip(self):
        # Lossless read/write of a real .bmw archive at member level (smallest corpus archive).
        arcs = _files("bmw")
        if not arcs:
            self.skipTest("BMW M3 Challenge corpus not present")
        arc = min(arcs, key=lambda p: p.stat().st_size)
        mtype, entries = mas_tool.read_archive(arc)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.bmw"
            mas_tool.write_archive(out, entries, mas_type=mtype)
            m2, e2 = mas_tool.read_archive(out)
        self.assertEqual(m2, mtype)
        self.assertEqual([e.name for e in e2], [e.name for e in entries])
        for a, b in zip(entries, e2):
            self.assertEqual(a.data, b.data, a.name)

    def test_gmt_magic_in_bmw_corpus_observed(self):
        # Observed: 976 GMTs (26 loose + 950 inside .bmw archives) all have normal GMT magic.
        loose = _files("gmt")
        if not loose:
            self.skipTest("BMW M3 Challenge corpus not present")
        total = 0
        for p in loose:
            self.assertEqual(p.read_bytes()[8:24], NORMAL_GMT_MAGIC, p)
            total += 1
        for arc in _files("bmw"):
            for e in mas_tool.read_archive(arc)[1]:
                if e.name.lower().endswith(".gmt"):
                    self.assertEqual(e.data[8:24], NORMAL_GMT_MAGIC, (arc, e.name))
                    total += 1
        self.assertEqual(total, 976)

    def test_fxm_family_magic_and_extension_in_bmw_corpus(self):
        # Observed: 75 FXM-family files, all with known magic; 5 have extension != magic.
        files = []
        for ext in ("fxm", "fxa", "lma"):
            files.extend(_files(ext))
        if not files:
            self.skipTest("BMW M3 Challenge corpus not present")
        self.assertEqual(len(files), 75)
        mismatches = []
        for p in files:
            magic = p.read_bytes()[:4]
            self.assertIn(magic, fxm_tool.MAGICS, p)
            ext = p.suffix.lower().lstrip(".").upper()
            if magic.decode("ascii").strip() != ext:
                mismatches.append((p.name, magic.decode("ascii")))
        self.assertEqual(len(mismatches), 5)
        self.assertIn(("TE_wait-l.FXM", "LMA "), mismatches)
        self.assertIn(("FPDriverRHD_M02.LMA", "FXM "), mismatches)


if __name__ == "__main__":
    unittest.main()
