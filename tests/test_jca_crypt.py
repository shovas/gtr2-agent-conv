"""Tests for native SimBin JCA decryption (GPLv2-derived, see jca_crypt.py)."""
import glob
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import jca_crypt  # noqa: E402

R07 = ROOT.parent / "Race07Vanilla"
NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")


class JcaCryptTest(unittest.TestCase):
    def test_roundtrip_all_versions(self):
        payload = b"JCA roundtrip " + bytes(range(256)) * 4
        for version in range(8):
            with self.subTest(version=version):
                enc = jca_crypt.encrypt_bytes(payload, version=version)
                self.assertEqual(enc[:4], struct.pack("<I", jca_crypt.MAGIC))
                self.assertEqual(jca_crypt.decrypt_bytes(enc), payload)

    def test_custom_key_roundtrip(self):
        payload = b"raceroom key test " + bytes(range(128))
        for name in jca_crypt.CUSTOM_KEYS:
            with self.subTest(key=name):
                enc = jca_crypt.encrypt_bytes(payload, version=3, custom_key=jca_crypt.CUSTOM_KEYS[name])
                self.assertEqual(jca_crypt.decrypt_bytes(enc, jca_crypt.CUSTOM_KEYS[name]), payload)

    def test_rejects_wrong_magic(self):
        with self.assertRaises(ValueError):
            jca_crypt.decrypt_bytes(b"NOPE" + b"\x00" * 32)

    def test_real_race07_gmts_decrypt_to_standard_layout(self):
        gmts = [Path(p) for p in glob.glob(str(R07 / "**" / "*"), recursive=True)
                if os.path.isfile(p) and p.lower().endswith(".gmt")]
        if not gmts:
            self.skipTest("Race07Vanilla corpus not present")
        for p in sorted(gmts)[:20]:
            with self.subTest(path=p.name):
                raw = p.read_bytes()
                dec = jca_crypt.decrypt_bytes(raw)
                self.assertEqual(dec[8:24], NEW_MAGIC)
                g = gmt_format.parse_gmt(p.name, dec)
                self.assertEqual(gmt_format.write_gmt(g), dec)

    def test_matches_wtcced_if_present(self):
        tool = Path("/tmp/opencode/wtcced")
        src = R07 / "GameData/Locations/Macau_2007/MODELS/CONE01.GMT"
        if not tool.exists() or not src.exists():
            self.skipTest("wtcced binary or sample not present")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            enc, dec = td / "enc.gmt", td / "dec.gmt"
            enc.write_bytes(src.read_bytes())
            subprocess.run([str(tool), "-o", str(enc), str(dec)], capture_output=True)
            self.assertEqual(jca_crypt.decrypt_bytes(enc.read_bytes()), dec.read_bytes())


if __name__ == "__main__":
    unittest.main()
