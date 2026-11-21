import gzip
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gzip_simbin_tool  # noqa: E402
import fxm_tool  # noqa: E402


class SimbinToolsTest(unittest.TestCase):
    def test_gzip_roundtrip_content(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.dsi"
            payload = b"//[[gMb1.000f (c)2004    ]] [[\x00\x00\x00\x00]]\nhello\n"
            p.write_bytes(gzip_simbin_tool.compress_bytes(payload))
            dec = gzip_simbin_tool.decompress(p)
            self.assertEqual(dec, payload)

    def test_real_hat_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/HAT_Dedicated/3ANDERSTORP.hat"
        if not p.exists():
            self.skipTest("HAT not present")
        dec = gzip_simbin_tool.decompress(p)
        self.assertTrue(dec.startswith(b"//[[gMb1.000f"))

    def test_fxm_header(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.fxm"
            # minimal fake header
            import struct
            p.write_bytes(struct.pack("<4sHHIIII", b"FXM ", 257, 16, 1, 2, 3, 4) + b"\x00" * 32)
            h = fxm_tool.read_header(p)
            self.assertTrue(h.known_magic)
            self.assertEqual(h.v1, 257)

    def test_real_fxa_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Pit/FH.FXA"
        if not p.exists():
            self.skipTest("FXA not present")
        h = fxm_tool.read_header(p)
        self.assertTrue(h.known_magic)
        self.assertEqual(h.magic, b"FXA ")

    def test_real_lma_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Driver/ExtDriver_A.LMA"
        if not p.exists():
            self.skipTest("LMA not present")
        h = fxm_tool.read_header(p)
        self.assertTrue(h.known_magic)
        self.assertEqual(h.magic, b"LMA ")
        # Observed: BE-interpreted 24-byte header; last u32 may overlap following string data.
        self.assertEqual(h.be_fields[:5], (257, 256, 184, 1, 66))
        b = p.read_bytes()
        self.assertIn(b'Bip01 Spine', b)
        self.assertIn(b'Bip01 R Clavicle', b)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "x.lma"
            fxm_tool.main(["roundtrip", str(p), str(out)])
            self.assertEqual(out.read_bytes(), b)


if __name__ == "__main__":
    unittest.main()
