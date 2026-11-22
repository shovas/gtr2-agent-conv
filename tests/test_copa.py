"""Observations from the Copa Petrobras de Marcas reference corpus (../CopaPetrobrasdeMarcas).

Copa is a Reiza-era ISIMotor title: MAS type-1X archives and Game Stock Car
signature (enctype 1) ISI encryption. These tests record verified evidence only.
"""
import glob
import os
import struct
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402

COPA = ROOT.parent / "CopaPetrobrasdeMarcas"
GSC_SIGN = 0x4B1DCA9F960524E8
GMT_MAGIC_OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


class CopaCorpusTest(unittest.TestCase):
    def test_gsc_encrypted_member_decrypts_and_matches_reference(self):
        # Verified: ISI signature 0x4b1dca9f960524e8 (Game Stock Car, enctype 1)
        # and skip=4 decryption yields the old-style rF1 GMT magic at 0x1D4.
        arc = COPA / "Gamedata/Locations/commonmaps.MAS"
        if not arc.exists():
            self.skipTest("CopaPetrobrasdeMarcas corpus not present")
        member = None
        for e in mas_tool.read_archive(arc)[1]:
            if e.name.upper() == "STARTBOX.GMT":
                member = e
                break
        self.assertIsNotNone(member)
        sign, key = struct.unpack_from("<QQ", member.data, 0)
        self.assertEqual((sign ^ key) & 0xFFFFFFFFFFFFFFFF, GSC_SIGN)
        dec = isi_crypt.decrypt_bytes(member.data, skip=4)
        self.assertEqual(dec[0x1D4:0x1E4], GMT_MAGIC_OLD)

        rfactordec = Path("/tmp/opencode/rfactordec")
        if rfactordec.exists():
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                enc_path = td / "enc.gmt"
                dec_path = td / "dec.gmt"
                enc_path.write_bytes(member.data)
                # rfactordec exits non-zero even on success in this build; compare output.
                subprocess.run([str(rfactordec), "-o", "-y", str(enc_path), str(dec_path)],
                               capture_output=True)
                self.assertEqual(dec_path.read_bytes(), dec)


    def test_all_gmts_are_encrypted_old_layout(self):
        # Observed: all 12,990 GMT members in Copa are GSC-signature encrypted
        # and use the old rF1-style magic (0xA8 byte) at 0x1D4.
        arcs = [Path(p) for p in glob.glob(str(COPA / "**" / "*"), recursive=True)
                if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]
        if not arcs:
            self.skipTest("CopaPetrobrasdeMarcas corpus not present")
        counted = 0
        for arc in arcs:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                sign, key = struct.unpack_from("<QQ", e.data, 0)
                self.assertEqual((sign ^ key) & 0xFFFFFFFFFFFFFFFF, GSC_SIGN, (arc, e.name))
                # Decrypt a block-aligned prefix sufficient to reach the 0x1D4 magic.
                rem = (len(e.data) - 20) % 128
                n = min(len(e.data), 20 + rem + 128 * 8)
                dec = isi_crypt.decrypt_bytes(e.data[:n], skip=4)
                self.assertEqual(dec[0x1D4:0x1E4], GMT_MAGIC_OLD, (arc, e.name))
                counted += 1
        self.assertEqual(counted, 12990)


if __name__ == "__main__":
    unittest.main()
