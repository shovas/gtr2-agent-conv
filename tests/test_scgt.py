"""Observations from the Sports Car GT (1999, Image Space Incorporated) corpus.

Sports Car GT predates the GTR2/GTL ISIMotor games. Its `.mas` archives use the
signature-less MAS type-2 layout documented in quickbms_scripts/mas.bms. These
tests record verified structural evidence only.
"""
import glob
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

SCGT = ROOT.parent / "SportsCarGtUsa"


def _archives():
    if not SCGT.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(SCGT / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class SportsCarGTTest(unittest.TestCase):
    def test_type2_archives_read(self):
        # Observed: all 61 .mas files use the signature-less type-2 layout:
        # 8-byte header (count, data_size) + 32-byte records (name[16], offset,
        # size, zsize, dummy); 16,070 members total.
        arcs = _archives()
        if not arcs:
            self.skipTest("SportsCarGtUsa corpus not present")
        self.assertEqual(len(arcs), 61)
        counts = {0: 0, 1: 0, 2: 0}
        total = 0
        for arc in arcs:
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 2, arc)
            self.assertGreater(len(entries), 0, arc)
            total += len(entries)
            for e in entries:
                self.assertIn(e.type, counts)
                counts[e.type] += 1
        self.assertEqual(total, 16070)
        self.assertEqual(counts, {0: 13621, 1: 2427, 2: 22})

    def test_type2_hdr16_zlib_texture_decoding(self):
        # Observed: 2,427 compressed entries store a 16-byte texture header
        # (width, height, flags, 0) followed by a zlib stream of raw pixels.
        arc = SCGT / "Mas/ATLNMAP.MAS"
        if not arc.exists():
            self.skipTest("SportsCarGtUsa corpus not present")
        entries = mas_tool.read_archive(arc)[1]
        target = next(e for e in entries if e.name == "AMBA.BMP")
        self.assertEqual(target.type, 1)
        self.assertEqual(target.size, 24576)
        self.assertEqual(struct.unpack_from("<IIII", target.data, 0), (128, 64, 1, 0))
        self.assertEqual(len(target.data), 16 + target.size)
        self.assertEqual(len(zlib.compress(target.data[16:])), target.zsize - 16)

    def test_type2_member_roundtrip(self):
        # Lossless member-level read/write of a real type-2 archive.
        arc = SCGT / "Mas/ATLNMAP.MAS"
        if not arc.exists():
            self.skipTest("SportsCarGtUsa corpus not present")
        mtype, entries = mas_tool.read_archive(arc)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mas"
            mas_tool.write_archive(out, entries, mas_type=mtype)
            m2, e2 = mas_tool.read_archive(out)
        self.assertEqual(m2, mtype)
        self.assertEqual([e.name for e in e2], [e.name for e in entries])
        for a, b in zip(entries, e2):
            self.assertEqual((a.type, a.size, a.data), (b.type, b.size, b.data), a.name)

    def test_type2_raw_vrl_roundtrip(self):
        # Raw (size == zsize) type-2 members, e.g. .vrl track meshes, are copied verbatim.
        arc = SCGT / "Mas/DONI.MAS"
        if not arc.exists():
            self.skipTest("SportsCarGtUsa corpus not present")
        mtype, entries = mas_tool.read_archive(arc)
        self.assertTrue(all(e.type in (0, 2) for e in entries))
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mas"
            mas_tool.write_archive(out, entries, mas_type=mtype)
            _, e2 = mas_tool.read_archive(out)
        for a, b in zip(entries, e2):
            self.assertEqual((a.name, a.data), (b.name, b.data))


    def test_ambc_raw_texture_decoding(self):
        """The 2 undecoded AMBC.BMP members are 16-byte header + raw 32x8 RGB."""
        found = 0
        for arc in _archives():
            if arc.name.lower() not in ("hckamap.mas", "octamap.mas"):
                continue
            entries = mas_tool.read_archive(arc)[1]
            target = next((e for e in entries if e.name == "AMBC.BMP"), None)
            if target is None:
                continue
            full = mas_tool.reconstruct_type2_member(arc, target)
            self.assertEqual(len(full), target.size)
            self.assertEqual(struct.unpack_from("<IIII", full, 0), (32, 8, 0, 0))
            bmp = mas_tool.scgt_raw_texture_to_bmp(full)
            self.assertIsNotNone(bmp)
            self.assertEqual(bmp[:2], b"BM")
            self.assertEqual(len(bmp), 54 + 768)
            self.assertEqual(struct.unpack_from("<ii", bmp, 18), (32, 8))
            # Coherence: adjacent pixels differ far less than random RGB noise.
            px = full[16:]
            triples = [px[i:i+3] for i in range(0, 768, 3)]
            diffs = [sum(abs(a-b) for a, b in zip(triples[i], triples[i+1]))
                     for i in range(len(triples)-1)]
            self.assertLess(sum(diffs) / len(diffs), 100)
            found += 1
        self.assertEqual(found, 2)


if __name__ == "__main__":
    unittest.main()
