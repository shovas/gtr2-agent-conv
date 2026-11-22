"""Observations from the rFactor 1 vanilla reference corpus (../RF1Vanilla).

rFactor 1 is the ISIMotor branch that uses the ISI 16-byte-header cipher and an
older GMT layout. These tests record verifiable cross-corpus evidence; no new
semantic claims are made beyond the observed structural fields.
"""
import glob
import os
import struct
import sys
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402

RF1 = ROOT.parent / "RF1Vanilla"

MAS1_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c9caddd8bebba6bf90")
GMT_MAGIC_OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")  # rF1: at 0x1D4
GMT_MAGIC_NEW = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")  # GTR2/GTL: at 0x08
RFACTOR_SIGN = 0x38AF5637E81BC9A0


def _archives():
    if not RF1.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(RF1 / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


@lru_cache(maxsize=1)
def _gmt_members():
    """Return [(archive_basename, member_name, plaintext_bytes, sign)] (cached)."""
    result = []
    for arc in _archives():
        for e in mas_tool.read_archive(arc)[1]:
            if not e.name.lower().endswith(".gmt") or not e.data:
                continue
            sign, key = struct.unpack_from("<QQ", e.data, 0)
            sign = (sign ^ key) & 0xFFFFFFFFFFFFFFFF
            data = isi_crypt.decrypt_bytes(e.data, skip=4) if sign in isi_crypt.GAMES else e.data
            result.append((arc.name, e.name, data, sign))
    return tuple(result)


class Rf1VanillaCorpusTest(unittest.TestCase):
    def test_rf1_mas_archives_are_mas_type1(self):
        # Observed: all 85 .mas files use the MAS type-1 signature and open with mas_tool.py.
        arcs = _archives()
        if not arcs:
            self.skipTest("RF1Vanilla corpus not present")
        self.assertEqual(len(arcs), 85)
        for arc in arcs:
            self.assertEqual(arc.read_bytes()[:16], MAS1_MAGIC, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 1, arc)
            self.assertGreater(len(entries), 0, arc)

    def test_rf1_gmt_two_layout_variants_observed(self):
        # Observed: 9630 GMTs carry the old rF1 magic at 0x1D4 (0xA8 byte);
        # 32 carry the GTR2/GTL magic at 0x08 (0xA7 byte).
        gmts = list(_gmt_members())
        if not gmts:
            self.skipTest("RF1Vanilla corpus not present")
        self.assertEqual(len(gmts), 9662)
        old = sum(1 for _, _, d, _ in gmts if d[0x1D4:0x1E4] == GMT_MAGIC_OLD)
        new = sum(1 for _, _, d, _ in gmts if d[0x08:0x18] == GMT_MAGIC_NEW)
        self.assertEqual(old, 9630)
        self.assertEqual(new, 32)

    def test_rf1_encrypted_gmts_decrypt_with_known_signature(self):
        # Observed: 120 GMTs use the known rFactor ISI 16-byte-header signature
        # and skip=4 decryption yields 90 old-layout + 30 new-layout GMTs.
        gmts = list(_gmt_members())
        if not gmts:
            self.skipTest("RF1Vanilla corpus not present")
        enc = [(a, n, d) for a, n, d, sign in gmts if sign == RFACTOR_SIGN]
        self.assertEqual(len(enc), 120)
        for arc, name, data in enc:
            self.assertTrue(data[0x1D4:0x1E4] == GMT_MAGIC_OLD or
                            data[0x08:0x18] == GMT_MAGIC_NEW, (arc, name))
        old = sum(1 for _, _, d in enc if d[0x1D4:0x1E4] == GMT_MAGIC_OLD)
        new = sum(1 for _, _, d in enc if d[0x08:0x18] == GMT_MAGIC_NEW)
        self.assertEqual((old, new), (90, 30))

    def test_rf1_new_layout_gmts_parse_with_gmt_format(self):
        # Verified: after decryption where needed, all 32 new-layout rF1 GMTs
        # parse with gmt_format.py and round-trip losslessly.
        gmts = list(_gmt_members())
        if not gmts:
            self.skipTest("RF1Vanilla corpus not present")
        new = [(a, n, d) for a, n, d, _ in gmts if d[0x08:0x18] == GMT_MAGIC_NEW]
        self.assertEqual(len(new), 32)
        for arc, name, data in new:
            with self.subTest(arc=arc, name=name):
                g = gmt_format.parse_gmt(name, data)
                self.assertEqual(gmt_format.write_gmt(g), data)


if __name__ == "__main__":
    unittest.main()
