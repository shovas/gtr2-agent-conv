"""Observations for F1CS2000, GameStockCar and NascarSimRacing."""
import glob
import hashlib
import os
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402

OLD_MTS = b"CUBE_MTS_4.10\x00\x00\x00"
NEW_MTS = b"CUBE_MTS_4.20\x00\x00\x00"
OLD_GMT = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


def _files(root, ext):
    base = ROOT.parent / root
    return [p for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext.lower()]


class ThreeCorporaTest(unittest.TestCase):
    def test_f1cs2000_is_byte_identical_copy_of_f12000(self):
        def hashes(root):
            base = ROOT.parent / root
            return {str(p.relative_to(base)).lower():
                    hashlib.md5(p.read_bytes()).hexdigest()
                    for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
                    if p.is_file()}
        a, b = hashes("F12000"), hashes("F1CS2000")
        if not a or not b:
            self.skipTest("F1 corpora not present")
        self.assertEqual(len(a), 570)
        self.assertEqual(a, b)  # all 570 files identical

    def test_gamestockcar_archives_and_encryption(self):
        arcs = _files("GameStockCar", ".mas")
        if not arcs:
            self.skipTest("GameStockCar corpus not present")
        self.assertEqual(len(arcs), 48)
        total = encrypted = 0
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), mas_tool.MAS_TYPE1, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 1, arc)
            total += len(entries)
            for e in entries:
                d = e.data or b""
                if len(d) < 16:
                    continue
                sign, key = struct.unpack_from("<QQ", d, 0)
                if (sign ^ key) & 0xFFFFFFFFFFFFFFFF in isi_crypt.GAMES:
                    encrypted += 1
        self.assertEqual(total, 19995)
        self.assertEqual(encrypted, 19987)

    def test_gamestockcar_gmts_use_old_layout(self):
        arcs = _files("GameStockCar", ".mas")
        if not arcs:
            self.skipTest("GameStockCar corpus not present")
        counted = 0
        for arc in arcs[:8]:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                d = e.data
                rem = (len(d) - 20) % 128
                dec = isi_crypt.decrypt_bytes(d[:20 + rem + 128 * 8], skip=4)
                self.assertEqual(dec[0x1D4:0x1E4], OLD_GMT, (arc, e.name))
                counted += 1
        self.assertGreater(counted, 0)

    def test_nascar_simracing_mts_versions(self):
        arcs = _files("NascarSimRacing", ".mas")
        if not arcs:
            self.skipTest("NascarSimRacing corpus not present")
        self.assertEqual(len(arcs), 311)
        versions = Counter()
        total = 0
        for arc in arcs:
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 3, arc)
            total += len(entries)
            for e in entries:
                if e.name.lower().endswith(".mts"):
                    versions[(e.data or b"")[:16]] += 1
        self.assertEqual(total, 36716)
        self.assertEqual(versions, {NEW_MTS: 25689, OLD_MTS: 784})


if __name__ == "__main__":
    unittest.main()
