"""Observations from the Race 07 (SimBin, 2007) reference corpus (../Race07Vanilla).

Race 07 is a sibling of GT Legends/GTR2, but most of its loose GMTs use an
opaque high-entropy representation rather than the standard new-layout GMT.
These tests record verified evidence only.
"""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import mas_tool  # noqa: E402

R07 = ROOT.parent / "Race07Vanilla"
OPAQUE_PREFIX = bytes.fromhex("0fb1ffff03000000")
NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")
OLD_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


def _files(ext):
    if not R07.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(R07 / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == "." + ext]


class Race07Test(unittest.TestCase):
    def test_two_gtr_archives_are_type0(self):
        arcs = _files("gtr")
        if not arcs:
            self.skipTest("Race07Vanilla corpus not present")
        self.assertEqual(len(arcs), 2)
        for arc in arcs:
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 0, arc)
            self.assertGreater(len(entries), 0, arc)

    def test_crew_archive_gmts_use_standard_layout(self):
        arc = R07 / "GameData/Scripts/crew.gtr"
        if not arc.exists():
            self.skipTest("Race07Vanilla corpus not present")
        gmts = [e for e in mas_tool.read_archive(arc)[1] if e.name.lower().endswith(".gmt")]
        self.assertEqual(len(gmts), 5)
        for e in gmts:
            self.assertEqual(e.data[8:24], NEW_MAGIC, e.name)
            g = gmt_format.parse_gmt(e.name, e.data)
            self.assertEqual(gmt_format.write_gmt(g), e.data)

    def test_loose_gmts_use_opaque_representation(self):
        # Observed: all 21,687 loose GMTs start with 0fb1ffff03000000 and match
        # neither the standard 0x08 nor old 0x1D4 magic. Not ISI-16 encrypted,
        # not a standard compression stream; format undecoded.
        gmts = _files("gmt")
        if not gmts:
            self.skipTest("Race07Vanilla corpus not present")
        self.assertEqual(len(gmts), 21687)
        for p in gmts:
            d = p.read_bytes()
            self.assertGreaterEqual(len(d), 8)
            self.assertEqual(d[:8], OPAQUE_PREFIX, p)
            self.assertNotEqual(d[8:24], NEW_MAGIC, p)
            if len(d) >= 0x1E4:
                self.assertNotEqual(d[0x1D4:0x1E4], OLD_MAGIC, p)

    def test_opaque_gmt_header_matches_jca_layout(self):
        # Observed JCA header: magic 0xffffb10f, u32 file_version, u32 data_size,
        # u32 compressed_size, then Blowfish-encrypted payload at 0x10.
        gmts = _files("gmt")
        if not gmts:
            self.skipTest("Race07Vanilla corpus not present")
        import struct
        for p in gmts[:50]:
            d = p.read_bytes()
            magic, version, data_size, zlen = struct.unpack_from("<IIII", d, 0)
            self.assertEqual(magic, 0xFFFFB10F, p)
            self.assertIn(version, (0, 1, 2, 3, 4, 5, 6, 7), p)
            self.assertGreater(data_size, 0, p)
            self.assertLessEqual(zlen + 16, len(d) + 8, p)

    def test_jca_decryption_with_external_wtcced_if_present(self):
        # Optional verification: wtcced (GPLv2, Luigi Auriemma) decrypts these
        # files to standard GTR2-layout GMTs. Not vendored in this repo.
        tool = Path("/tmp/opencode/wtcced")
        src = R07 / "GameData/Locations/Macau_2007/MODELS/CONE01.GMT"
        if not tool.exists() or not src.exists():
            self.skipTest("wtcced binary or sample not present")
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            enc, dec = td / "enc.gmt", td / "dec.gmt"
            enc.write_bytes(src.read_bytes())
            # wtcced exits non-zero even on success in this build; compare output.
            subprocess.run([str(tool), "-o", str(enc), str(dec)], capture_output=True)
            self.assertEqual(dec.read_bytes()[8:24], NEW_MAGIC)
            g = gmt_format.parse_gmt(dec.name, dec.read_bytes())
            self.assertEqual(gmt_format.write_gmt(g), dec.read_bytes())

    def test_fxm_family_extension_magic_mismatches(self):
        # Observed: 195 animation files; extension does not always match magic.
        counts = {}
        for ext in ("fxm", "fxa", "lma"):
            for p in _files(ext):
                magic = p.read_bytes()[:4]
                counts[(ext, magic)] = counts.get((ext, magic), 0) + 1
        self.assertEqual(sum(counts.values()), 195)
        self.assertEqual(counts[("fxm", b"FXM ")], 77)
        self.assertEqual(counts[("lma", b"LMA ")], 62)
        self.assertEqual(counts[("fxm", b"LMA ")], 22)
        self.assertEqual(counts[("fxa", b"LMA ")], 22)
        self.assertEqual(counts[("fxa", b"FXA ")], 12)


if __name__ == "__main__":
    unittest.main()
