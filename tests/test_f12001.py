"""Observations from the F1 2001 (ISI, 2001) corpus (../F12001).

Introduces MAS type 6 (`CUBEMAS4.00`/`CUBEMAS4.01`) with a 256-byte record
layout of (type, offset, size, zsize, crc, name[236]).
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

F1 = ROOT.parent / "F12001"


def _archives():
    if not F1.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(F1 / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class F12001Test(unittest.TestCase):
    def test_type6_archives_read(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("F12001 corpus not present")
        self.assertEqual(len(arcs), 80)
        sigs = {}
        total = 0
        for arc in arcs:
            sig = mas_tool.read_signature(arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 6, arc)
            self.assertIn(sig, (mas_tool.MAS_TYPE400, mas_tool.MAS_TYPE401), arc)
            sigs[sig] = sigs.get(sig, 0) + 1
            total += len(entries)
        self.assertEqual(sigs, {mas_tool.MAS_TYPE401: 56, mas_tool.MAS_TYPE400: 24})
        self.assertEqual(total, 16720)

    def test_type2_raw_textures_decode_to_bmp(self):
        """All F12001 type-2 members are raw 16-byte-header RGB textures."""
        import struct

        if not F1.is_dir():
            self.skipTest("F12001 corpus not present")
        checked = 0
        for path in F1.rglob("*"):
            if not path.is_file() or path.suffix.lower() != ".mas":
                continue
            try:
                _mtype, entries = mas_tool.read_archive(path)
            except Exception:
                continue
            for entry in entries:
                if entry.type != 2:
                    continue
                data = entry.data or b""
                width, height, flags, zero = struct.unpack_from("<4I", data, 0)
                self.assertEqual((flags, zero), (24, 0), entry.name)
                self.assertEqual(16 + width * height * 3, len(data), entry.name)
                bmp = mas_tool.scgt_raw_texture_to_bmp(data)
                self.assertIsNotNone(bmp, entry.name)
                self.assertEqual(bmp[:2], b"BM")
                self.assertEqual(struct.unpack_from("<IiiHH", bmp, 14),
                                 (40, width, height, 1, 24))
                checked += 1
        self.assertEqual(checked, 279)

    def test_type6_member_roundtrip_preserves_signature(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("F12001 corpus not present")
        arc = sorted(arcs)[0]
        mtype, entries = mas_tool.read_archive(arc)
        sig = mas_tool.read_signature(arc)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mas"
            mas_tool.write_archive(out, entries, mas_type=mtype, signature=sig)
            self.assertEqual(mas_tool.read_signature(out), sig)
            m2, e2 = mas_tool.read_archive(out)
        self.assertEqual(m2, mtype)
        self.assertEqual([e.name for e in e2], [e.name for e in entries])
        for a, b in zip(entries, e2):
            self.assertEqual((a.type, a.size, a.flags, a.data),
                             (b.type, b.size, b.flags, b.data), a.name)


if __name__ == "__main__":
    unittest.main()
