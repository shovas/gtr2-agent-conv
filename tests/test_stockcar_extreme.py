"""Observations from the Stock Car Extreme (Reiza, GSC-based) corpus (../StockCarExtreme).

Stock Car Extreme is a late rFactor-1-lineage ISIMotor title using the same
MAS type-1 / GSC-signature / old-GMT-layout family as Automobilista and Copa.
These tests record verified evidence only.
"""
import glob
import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402

SCE = ROOT.parent / "StockCarExtreme"
MAS1_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c9caddd8bebba6bf90")
GSC_SIGN = 0x4B1DCA9F960524E8
GMT_MAGIC_OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


def _archives():
    if not SCE.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(SCE / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class StockCarExtremeTest(unittest.TestCase):
    def test_all_mas_archives_are_type1(self):
        arcs = _archives()
        if not arcs:
            self.skipTest("StockCarExtreme corpus not present")
        self.assertEqual(len(arcs), 196)
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), MAS1_MAGIC, arc)

    def test_gsc_encrypted_gmt_decrypts(self):
        arc = SCE / "GameData/Locations/BolognaHistoric/BolognaMesh.MAS"
        if not arc.exists():
            self.skipTest("StockCarExtreme corpus not present")
        member = next((e for e in mas_tool.read_archive(arc)[1]
                       if e.name.upper() == "ADVERTISEMENT01.GMT"), None)
        self.assertIsNotNone(member)
        sign, key = struct.unpack_from("<QQ", member.data, 0)
        self.assertEqual((sign ^ key) & 0xFFFFFFFFFFFFFFFF, GSC_SIGN)
        dec = isi_crypt.decrypt_bytes(member.data, skip=4)
        self.assertEqual(dec[0x1D4:0x1E4], GMT_MAGIC_OLD)

    def test_gmt_old_layout_sampled(self):
        arcs = sorted(_archives())[:20]
        if not arcs:
            self.skipTest("StockCarExtreme corpus not present")
        counted = 0
        for arc in arcs:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                sign, key = struct.unpack_from("<QQ", e.data, 0)
                if ((sign ^ key) & 0xFFFFFFFFFFFFFFFF) in isi_crypt.GAMES:
                    rem = (len(e.data) - 20) % 128
                    n = min(len(e.data), 20 + rem + 128 * 8)
                    data = isi_crypt.decrypt_bytes(e.data[:n], skip=4)
                else:
                    data = e.data
                self.assertEqual(data[0x1D4:0x1E4], GMT_MAGIC_OLD, (arc, e.name))
                counted += 1
        self.assertGreater(counted, 0)


if __name__ == "__main__":
    unittest.main()
