"""Observations from the Volvo (SimBin, ISIMotor) corpus (../VolvoTheGame).

All loose GMTs use JCA encryption with the non-default `volvo` key; with that
key they decrypt to standard GTR2-layout GMTs.
"""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import jca_crypt  # noqa: E402

VOLVO = ROOT.parent / "VolvoTheGame"
NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")


class VolvoTest(unittest.TestCase):
    def test_gmts_are_jca_encrypted(self):
        gmts = [Path(p) for p in glob.glob(str(VOLVO / "**" / "*"), recursive=True)
                if os.path.isfile(p) and p.lower().endswith(".gmt")]
        if not gmts:
            self.skipTest("VolvoTheGame corpus not present")
        self.assertEqual(len(gmts), 2026)
        for p in gmts:
            self.assertEqual(p.read_bytes()[:4], b"\x0f\xb1\xff\xff", p)

    def test_volvo_key_decrypts_to_standard_gmt(self):
        gmts = [Path(p) for p in glob.glob(str(VOLVO / "**" / "*"), recursive=True)
                if os.path.isfile(p) and p.lower().endswith(".gmt")]
        if not gmts:
            self.skipTest("VolvoTheGame corpus not present")
        key = jca_crypt.CUSTOM_KEYS["volvo"]
        for p in sorted(gmts)[:25]:
            with self.subTest(path=p.name):
                dec = jca_crypt.decrypt_bytes(p.read_bytes(), custom_key=key)
                self.assertEqual(dec[8:24], NEW_MAGIC)
                g = gmt_format.parse_gmt(p.name, dec)
                self.assertEqual(gmt_format.write_gmt(g), dec)

    def test_volvo_key_decrypts_text_files(self):
        # Volvo's .gdb/.trk/.scn/.cam files also use JCA with the volvo key.
        key = jca_crypt.CUSTOM_KEYS["volvo"]
        for ext, prefix in ((".gdb", b"ApplicationTitle"), (".trk", b"CUBEASF"),
                            (".cam", b"LocalCam")):
            paths = [Path(p) for p in glob.glob(str(VOLVO / "**" / "*"), recursive=True)
                     if os.path.isfile(p) and p.lower().endswith(ext)
                     and Path(p).read_bytes()[:4] == b"\x0f\xb1\xff\xff"]
            self.assertGreater(len(paths), 0, ext)
            dec = jca_crypt.decrypt_bytes(paths[0].read_bytes(), custom_key=key)
            self.assertTrue(dec.startswith(prefix), (ext, dec[:40]))

    def test_animation_magics(self):
        counts = {}
        for ext in ("fxm", "fxa", "lma"):
            for p in glob.glob(str(VOLVO / "**" / "*"), recursive=True):
                if os.path.isfile(p) and p.lower().endswith("." + ext):
                    counts.setdefault(Path(p).read_bytes()[:4], 0)
                    counts[Path(p).read_bytes()[:4]] += 1
        if not counts:
            self.skipTest("VolvoTheGame corpus not present")
        self.assertEqual(counts, {b"FXM ": 22, b"FXA ": 14, b"LMA ": 6})


if __name__ == "__main__":
    unittest.main()
