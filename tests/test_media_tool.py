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

    def test_wav_mp3_format_lossless_roundtrip(self):
        p = ROOT.parent / "GTR2Steam/GameData/Sounds/PIT/bleep.wav"
        if not p.exists():
            self.skipTest("MP3-WAV not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "wav")
        self.assertEqual(info.details.get("audio_format"), 85)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.wav"
            info2 = media_tool.wav_roundtrip(p, out)
            self.assertEqual(info2.format, "wav")
            self.assertEqual(info2.details.get("audio_format"), 85)
            self.assertEqual(p.read_bytes(), Path(out).read_bytes())

    def test_identify_dds_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Objects/FANFEMALE1.DDS"
        if not p.exists():
            self.skipTest("DDS not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "dds")
        self.assertEqual(info.details.get("header_size"), 124)
        self.assertGreater(info.details.get("width", 0), 0)
        self.assertIn("pf_fourcc", info.details)

    def test_identify_dds_mipmaps_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Objects/MARSHAL1.dds"
        if not p.exists():
            self.skipTest("DDS not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "dds")
        self.assertGreater(info.details.get("mipmaps", 0), 1)

    def test_identify_bik_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Barcelona/Barcelona.bik"
        if not p.exists():
            self.skipTest("BIK not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "bik")
        self.assertGreater(info.details.get("frames", 0), 0)

    def test_dds_pixel_formats_observed_in_mas(self):
        # Observed in scanned MAS DDS headers: DXT1/DXT3/DXT5 and uncompressed RGB(A) (pf 0x41/0x40, fourcc 0).
        import glob, os, struct, importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:5]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:2]
        if not archives:
            self.skipTest("no archives")
        allowed = {(0x4, b'DXT1'), (0x4, b'DXT3'), (0x4, b'DXT5'), (0x41, b'\x00\x00\x00\x00'), (0x40, b'\x00\x00\x00\x00')}
        checked = 0
        for arc in archives:
            for name, d in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.dds') or len(d) < 128 or not d.startswith(b'DDS '):
                    continue
                pf_flags, cc = struct.unpack_from('<II', d, 80)
                cc_b = struct.pack('<I', cc)
                self.assertIn((pf_flags, cc_b), allowed)
                checked += 1
        self.assertGreater(checked, 0)

    def test_wav_formats_observed(self):
        # Observed in GTR2/GTL: WAV audio formats are PCM (1) or MP3 (0x55).
        import glob, os, struct
        paths = glob.glob(str(ROOT.parent / 'GTR2Steam/**/*.wav'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTLSteam/**/*.wav'), recursive=True)
        if not paths:
            self.skipTest("no WAV files")
        fmts = set()
        for pth in paths:
            with open(pth, 'rb') as f: b = f.read(64)
            if len(b) < 20 or b[:4] != b'RIFF' or b[8:12] != b'WAVE':
                continue
            off = 12
            while off + 8 <= len(b):
                cid = b[off:off+4]; sz = struct.unpack_from('<I', b, off+4)[0]
                if cid == b'fmt ' and sz >= 2:
                    fmts.add(struct.unpack_from('<H', b, off+8)[0])
                    break
                off += 8 + sz
                if sz == 0: break
        self.assertEqual(fmts, {1, 0x55})

    def test_identify_jpg_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3And_LOD.jpg"
        if not p.exists():
            self.skipTest("JPG not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "jpg")
        self.assertGreater(info.details.get("width", 0), 0)
        self.assertGreater(info.details.get("height", 0), 0)

    def test_identify_mp3_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Sounds/DrivingSchool/Failed.mp3"
        if not p.exists():
            self.skipTest("MP3 not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "mp3")
        self.assertIn("bitrate_index", info.details)

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

    def test_bmp_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.bmp"
            dst = Path(td) / "b.bmp"
            img = media_tool.BmpImage(width=2, height=2, bpp=24, compression=0,
                                      pixels_bgra=bytes(range(12)))
            src.write_bytes(img.to_bytes())
            info = media_tool.bmp_roundtrip(src, dst)
            self.assertEqual(info.format, "bmp")
            a = media_tool.read_bmp(src)
            b = media_tool.read_bmp(dst)
            self.assertEqual((a.width,a.height,a.bpp,a.pixels_bgra), (b.width,b.height,b.bpp,b.pixels_bgra))

    def test_dds_dxt1_synthetic_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 4,4
            rgba = bytes([255,0,0,255] * (w*h))
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='DXT1',rgba=rgba,header=b'\x00'*128)
            src.write_bytes(img.to_bytes())
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual((a.width,a.height,a.fourcc), (w,h,'DXT1'))
            for i in range(0,len(a.rgba),4):
                self.assertGreaterEqual(a.rgba[i], 200)
                self.assertLessEqual(a.rgba[i+1], 20)
                self.assertLessEqual(a.rgba[i+2], 20)

    def test_dds_dxt5_synthetic_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 4,4
            # semi-transparent green
            rgba = bytes([0,255,0,128] * (w*h))
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='DXT5',rgba=rgba,header=b'\x00'*128)
            src.write_bytes(img.to_bytes())
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual((a.width,a.height,a.fourcc), (w,h,'DXT5'))
            for i in range(0,len(a.rgba),4):
                self.assertLessEqual(a.rgba[i], 20)
                self.assertGreaterEqual(a.rgba[i+1], 200)
                self.assertLessEqual(a.rgba[i+2], 20)
                self.assertTrue(80 <= a.rgba[i+3] <= 180)

    def test_dds_dxt3_synthetic_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 4,4
            rgba = bytes([0,0,255,64] * (w*h))
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='DXT3',rgba=rgba,header=b'\x00'*128)
            src.write_bytes(img.to_bytes())
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual((a.width,a.height,a.fourcc), (w,h,'DXT3'))
            for i in range(0,len(a.rgba),4):
                self.assertLessEqual(a.rgba[i], 20)
                self.assertLessEqual(a.rgba[i+1], 20)
                self.assertGreaterEqual(a.rgba[i+2], 200)
                self.assertTrue(50 <= a.rgba[i+3] <= 80)

    def test_dds_uncompressed_synthetic_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 2,2
            rgba = bytes([10,20,30,255, 40,50,60,128, 70,80,90,0, 100,110,120,255])
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='UNCOMPRESSED',rgba=rgba,header=b'\x00'*128)
            src.write_bytes(img.to_bytes())
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual((a.width,a.height,a.fourcc), (w,h,'UNCOMPRESSED'))
            self.assertEqual(a.rgba, rgba)

    def test_dds_uncompressed_x8r8g8b8_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 2,1
            rgba = bytes([1,2,3,255, 4,5,6,255])
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='UNCOMPRESSED',rgba=rgba,header=b'\x00'*128)
            b = bytearray(img.to_bytes())
            struct.pack_into('<I', b, 80, 0x40)
            struct.pack_into('<5I', b, 88, 32, 0x00ff0000, 0x0000ff00, 0x000000ff, 0x00000000)
            src.write_bytes(bytes(b))
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual(a.fourcc, 'UNCOMPRESSED')
            self.assertEqual(a.rgba, rgba)

    def test_dds_uncompressed_r8g8b8_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 1,1
            rgba = bytes([10,20,30,255])
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='UNCOMPRESSED',rgba=rgba,header=b'\x00'*128)
            b = bytearray(img.to_bytes())
            struct.pack_into('<I', b, 80, 0x40)
            struct.pack_into('<5I', b, 88, 24, 0xff0000, 0x00ff00, 0x0000ff, 0x000000)
            b = b[:128] + bytes([30,20,10])
            struct.pack_into('<I', b, 20, 3)
            src.write_bytes(bytes(b))
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual(a.rgba[:3], bytes([10,20,30]))

    def test_dds_uncompressed_r5g6b5_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.dds"
            dst = Path(td) / "b.dds"
            w,h = 1,1
            rgba = bytes([255,0,0,255])
            img = media_tool.DdsImage(width=w,height=h,mipmaps=1,fourcc='UNCOMPRESSED',rgba=rgba,header=b'\x00'*128)
            b = bytearray(img.to_bytes())
            struct.pack_into('<I', b, 80, 0x40)
            struct.pack_into('<5I', b, 88, 16, 0xF800, 0x07E0, 0x001F, 0x0000)
            b = b[:128] + struct.pack('<H', 0xF800)
            struct.pack_into('<I', b, 20, 2)
            src.write_bytes(bytes(b))
            info = media_tool.dds_roundtrip(src, dst)
            self.assertEqual(info.format, "dds")
            a = media_tool.read_dds(src)
            self.assertEqual(a.rgba[0], 255)
            self.assertEqual(a.rgba[3], 255)


if __name__ == "__main__":
    unittest.main()
