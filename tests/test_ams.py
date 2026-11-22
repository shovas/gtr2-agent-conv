"""Observations from the Automobilista (Reiza, 2016) reference corpus (../Automobilista).

Automobilista is a late rFactor-1-lineage ISIMotor title: MAS type-1 archives,
Game Stock Car signature (enctype 1) encryption, and the old GMT layout.
These tests record verified evidence only.
"""
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

import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402

AMS = ROOT.parent / "Automobilista"
MAS1_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c9caddd8bebba6bf90")
GSC_SIGN = 0x4B1DCA9F960524E8
GMT_MAGIC_OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


def _archives():
    if not AMS.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(AMS / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == ".mas"]


class AutomobilistaCorpusTest(unittest.TestCase):
    def test_all_mas_archives_are_type1(self):
        # Header-only scan: all 470 archives use the standard MAS type-1 signature.
        arcs = _archives()
        if not arcs:
            self.skipTest("Automobilista corpus not present")
        self.assertEqual(len(arcs), 470)
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), MAS1_MAGIC, arc)

    def test_gsc_encrypted_gmt_decrypts_and_matches_reference(self):
        arc = AMS / "GameData/Locations/Adelaide/AdelaideMesh.MAS"
        if not arc.exists():
            self.skipTest("Automobilista corpus not present")
        member = next((e for e in mas_tool.read_archive(arc)[1]
                       if e.name.upper() == "ADVERTISEMENT001.GMT"), None)
        self.assertIsNotNone(member)
        sign, key = struct.unpack_from("<QQ", member.data, 0)
        self.assertEqual((sign ^ key) & 0xFFFFFFFFFFFFFFFF, GSC_SIGN)
        dec = isi_crypt.decrypt_bytes(member.data, skip=4)
        self.assertEqual(dec[0x1D4:0x1E4], GMT_MAGIC_OLD)

        rfactordec = Path("/tmp/opencode/rfactordec")
        if rfactordec.exists():
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                enc_path, dec_path = td / "enc.gmt", td / "dec.gmt"
                enc_path.write_bytes(member.data)
                subprocess.run([str(rfactordec), "-o", "-y", str(enc_path), str(dec_path)],
                               capture_output=True)
                self.assertEqual(dec_path.read_bytes(), dec)

    def test_gmt_old_layout_sampled(self):
        # Sampled across the first 20 archives: all GMTs are GSC-encrypted and
        # carry the old-style (0x1D4 / 0xA8) magic after decryption.
        arcs = sorted(_archives())[:20]
        if not arcs:
            self.skipTest("Automobilista corpus not present")
        counted = 0
        for arc in arcs:
            for e in mas_tool.read_archive(arc)[1]:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                sign, key = struct.unpack_from("<QQ", e.data, 0)
                encrypted = ((sign ^ key) & 0xFFFFFFFFFFFFFFFF) in isi_crypt.GAMES
                if encrypted:
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
