import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import media_tool  # noqa: E402


class MediaToolTest(unittest.TestCase):
    def test_wav_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.wav"
            dst = Path(td) / "b.wav"
            with wave.open(str(src), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(b"\x00\x01\x02\x03" * 100)
            info = media_tool.wav_roundtrip(src, dst)
            self.assertEqual(info.format, "wav")
            self.assertEqual(info.details["channels"], 1)
            self.assertEqual(info.details["framerate"], 22050)
            with wave.open(str(src), "rb") as a, wave.open(str(dst), "rb") as b:
                self.assertEqual(a.getparams(), b.getparams())
                self.assertEqual(a.readframes(a.getnframes()), b.readframes(b.getnframes()))

    def test_identify_dds_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Objects/FANFEMALE1.DDS"
        if not p.exists():
            self.skipTest("DDS not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "dds")
        self.assertEqual(info.details.get("header_size"), 124)
        self.assertGreater(info.details.get("width", 0), 0)
        self.assertIn("pf_fourcc", info.details)

    def test_identify_bik_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Barcelona/Barcelona.bik"
        if not p.exists():
            self.skipTest("BIK not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "bik")
        self.assertGreater(info.details.get("frames", 0), 0)

    def test_tga_type2_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.tga"
            dst = Path(td) / "b.tga"
            # type 2, 2x2, 24bpp, no id, no cmap
            import struct
            hdr = struct.pack('<BBB5sHHHHBB', 0, 0, 2, b'\x00'*5, 0, 0, 2, 2, 24, 0)
            pixels = bytes(range(12))  # 4 pixels * 3 bytes
            src.write_bytes(hdr + pixels)
            info = media_tool.tga_roundtrip(src, dst)
            self.assertEqual(info.format, "tga")
            self.assertEqual(src.read_bytes(), dst.read_bytes())

    def test_tga_real_type2_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/SpecialEvent/001_Pan Euro RS 2003 Rookie Cup_Icon.tga"
        if not p.exists():
            self.skipTest("TGA not present")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "out.tga"
            info = media_tool.tga_roundtrip(p, dst)
            self.assertEqual(info.format, "tga")
            # type 2 should be byte-identical
            self.assertEqual(p.read_bytes(), dst.read_bytes())

    def test_tga_type10_rle_semantic_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.tga"
            dst = Path(td) / "b.tga"
            # type 10, 2x2, 24bpp
            hdr = struct.pack('<BBB5sHHHHBB', 0, 0, 10, b'\x00'*5, 0, 0, 2, 2, 24, 0)
            pixels = bytes(range(12))
            # encode as raw RLE packet: header 0x03 = raw packet of 4 pixels
            rle = bytes([0x03]) + pixels
            src.write_bytes(hdr + rle)
            media_tool.tga_roundtrip(src, dst)
            a = media_tool.read_tga(src)
            b = media_tool.read_tga(dst)
            self.assertEqual(a.pixels, b.pixels)
            self.assertEqual((a.width,a.height,a.bpp,a.image_type), (2,2,24,10))


if __name__ == "__main__":
    unittest.main()
