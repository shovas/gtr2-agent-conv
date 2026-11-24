import os
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import media_tool  # noqa: E402


class MediaToolTest(unittest.TestCase):
    def test_tgq_identify_and_decode(self):
        import shutil
        src = ROOT.parent / "F12000/ANIM/A1RA.TGQ"
        if not src.is_file():
            self.skipTest("TGQ sample not present")
        info = media_tool.identify(src)
        self.assertEqual(info.format, "tgq")
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")
        with tempfile.TemporaryDirectory() as td:
            frames = media_tool.tgq_decode(src, td, frames=2)
            self.assertEqual(len(frames), 2)
            self.assertTrue(all(f.stat().st_size > 100 for f in frames))

    def test_bink_encode_via_libbink(self):
        import os
        import shutil
        exe = os.environ.get("BINKBUILD") or shutil.which("bink_build")
        if exe is None:
            self.skipTest("bink_build not available")
        src = ROOT.parent / "GTR2Steam/GameData/Locations/Barcelona/Barcelona.bik"
        if not src.is_file():
            self.skipTest("BIK sample not present")
        with tempfile.TemporaryDirectory() as td:
            frames = media_tool.bink_decode(src, td, frames=2)
            self.assertEqual(len(frames), 2)
            out = media_tool.bink_encode(Path(td), Path(td) / "out.bik",
                                         fps=15, exe=exe)
            self.assertIsNotNone(out)
            self.assertEqual(out.read_bytes()[:4], b"BIKi")
            # ffmpeg can decode the encoder's output.
            self.assertTrue(shutil.which("ffmpeg"))
            import subprocess
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(out),
                            "-frames:v", "1", "-f", "null", "-"], check=True)

    def test_bink_decode_via_ffmpeg(self):
        import shutil
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")
        src = ROOT.parent / "GTR2Steam/GameData/Locations/Barcelona/Barcelona.bik"
        if not src.is_file():
            self.skipTest("BIK sample not present")
        with tempfile.TemporaryDirectory() as td:
            frames = media_tool.bink_decode(src, td, frames=2)
            self.assertEqual(len(frames), 2)
            self.assertTrue(all(f.stat().st_size > 100 for f in frames))

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

    def test_jca_key_autodetection(self):
        import glob
        for root, expected in (("Race07Complete", "default"), ("VolvoTheGame", "volvo")):
            sample = next((p for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True)
                           if Path(p).is_file() and p.lower().endswith((".dds", ".tga", ".wav"))
                           and open(p, "rb").read(4) == b"\x0f\xb1\xff\xff"), None)
            if sample is None:
                continue
            with self.subTest(root=root):
                self.assertEqual(media_tool.detect_jca_key(Path(sample).read_bytes()), expected)
                self.assertEqual(media_tool.identify(sample).details["jca_key"], expected)

    def test_jca_encrypted_textures(self):
        import glob
        for ext, magic in ((".dds", b"DDS "), (".tga", None)):
            sample = next((p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"),
                                                recursive=True)
                           if p.lower().endswith(ext) and Path(p).is_file()
                           and open(p, "rb").read(4) == b"\x0f\xb1\xff\xff"), None)
            if sample is None:
                continue
            with self.subTest(ext=ext):
                info = media_tool.identify(sample)
                self.assertEqual(info.format, ext[1:] + "-jca")
                self.assertGreater(info.details["decrypted_size"], 0)
                plain = media_tool.decrypt_jca_bytes(Path(sample).read_bytes())
                if magic:
                    self.assertEqual(plain[:4], magic)
                else:
                    self.assertEqual(plain[1], 0)

    def test_compressed_wav_decode_via_ffmpeg(self):
        import glob
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not present")
        samples = []
        for root, tag in (("RF1Vanilla", 17), ("GTR2Steam", 85)):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith(".wav"):
                    continue
                with open(p, "rb") as f:
                    head = f.read(64)
                if head[:4] != b"RIFF" or len(head) < 22:
                    continue
                if struct.unpack_from("<H", head, 20)[0] == tag:
                    samples.append(p)
                    break
        self.assertEqual(len(samples), 2, "ADPCM and MP3-in-WAV samples expected")
        for src in samples:
            with self.subTest(src=src):
                with tempfile.TemporaryDirectory() as td:
                    dst = Path(td) / "pcm.wav"
                    self.assertTrue(media_tool.wav_decode(src, dst))
                    with wave.open(str(dst), "rb") as w:
                        self.assertEqual(w.getcomptype(), "NONE")
                        self.assertGreater(w.getnframes(), 0)

    def test_dxt4_corpus_decode(self):
        import glob
        import shutil
        import subprocess
        sample = next((p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"), recursive=True)
                       if p.lower().endswith(".dds") and Path(p).is_file()
                       and open(p, "rb").read(96)[84:88] == b"DXT4"), None)
        if sample is None:
            self.skipTest("DXT4 sample not present")
        img = media_tool.read_dds(sample)
        self.assertEqual(img.fourcc, "DXT4")
        self.assertEqual(len(img.rgba), img.width * img.height * 4)
        if shutil.which("ffmpeg"):
            with tempfile.TemporaryDirectory() as td:
                raw = Path(td) / "ref.rgba"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", sample,
                                "-f", "rawvideo", "-pix_fmt", "rgba", str(raw)],
                               capture_output=True)
                if raw.is_file():
                    ref = raw.read_bytes()
                    self.assertEqual(img.rgba[3::4], ref[3::4])

    def test_palettized_bmp_corpus_roundtrip(self):
        import glob
        sample = next((p for p in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*"),
                                            recursive=True)
                       if p.lower().endswith(".bmp") and Path(p).is_file()
                       and open(p, "rb").read(2) == b"BM"
                       and struct.unpack_from("<H", open(p, "rb").read(64), 28)[0] == 8), None)
        if sample is None:
            self.skipTest("8-bit BMP sample not present")
        img = media_tool.read_bmp(sample)
        self.assertEqual(img.bpp, 8)
        self.assertGreater(len(img.palette), 0)
        self.assertEqual(len(img.indices), img.width * img.height)
        self.assertEqual(img.to_bytes(), Path(sample).read_bytes())

    def test_bc4_bc5_synthetic_decode(self):
        def mkdds(fourcc, w, h, payload):
            hdr = bytearray(128)
            struct.pack_into("<I", hdr, 0, 0x20534444)
            struct.pack_into("<I", hdr, 4, 124)
            struct.pack_into("<I", hdr, 8, 0x1007)
            struct.pack_into("<II", hdr, 12, h, w)
            struct.pack_into("<I", hdr, 20, len(payload))
            struct.pack_into("<I", hdr, 76, 32)
            struct.pack_into("<I", hdr, 80, 0x4)
            hdr[84:88] = fourcc
            struct.pack_into("<I", hdr, 108, 0x1000)
            return bytes(hdr) + payload

        # endpoints 255,0 -> exact 8-level palette; indices 0..7 then reverse
        blk = bytes([255, 0]) + bytes([0b00011011, 0b11100100, 0, 0, 0, 0])
        self.assertEqual(media_tool._bc4_interpolate(255, 0),
                         [255, 219, 182, 146, 109, 73, 36, 0])
        with tempfile.TemporaryDirectory() as td:
            for fourcc, payload, expect in (
                    (b"BC4U", blk, (146, 146, 146)),
                    (b"ATI1", blk, (146, 146, 146)),
                    (b"BC5U", blk + blk, (146, 146, 0)),
                    (b"ATI2", blk + blk, (146, 146, 0))):
                with self.subTest(fourcc=fourcc):
                    f = Path(td) / (fourcc.decode() + ".dds")
                    f.write_bytes(mkdds(fourcc, 4, 4, payload))
                    img = media_tool.read_dds(f)
                    self.assertEqual((img.width, img.height), (4, 4))
                    self.assertEqual(tuple(img.rgba[:3]), expect)
                    self.assertEqual(img.rgba[3], 255)

    def test_mipmapped_dds_roundtrip_preserves_chain(self):
        import glob
        import struct
        samples = [p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"),
                                        recursive=True)
                   if p.lower().endswith(".dds") and Path(p).is_file()
                   and open(p, "rb").read(4) == b"DDS "
                   and struct.unpack_from("<I", open(p, "rb").read(128), 28)[0] >= 2]
        if not samples:
            self.skipTest("mipmapped DDS not present")
        checked = 0
        for src in samples[:2]:
            with self.subTest(src=Path(src).name):
                img = media_tool.read_dds(src)
                self.assertGreater(img.mipmaps, 1)
                self.assertGreater(len(img.mip_payload), 0)
                out = img.to_bytes()
                self.assertEqual(out, Path(src).read_bytes())
                checked += 1
        self.assertGreater(checked, 0)

    def test_dds_zero_pitch_field_preserved(self):
        p = (ROOT.parent / "Race07Complete/GameData/Locations/Jyllandsringen/"
             "Textures/GENERAL_S.DDS")
        if not p.exists():
            self.skipTest("DDS with zero pitch field not present")
        self.assertEqual(struct.unpack_from("<I", p.read_bytes(), 20)[0], 0)
        self.assertEqual(media_tool.read_dds(p).to_bytes(), p.read_bytes())

    def test_bmp_nonzero_row_padding_preserved(self):
        p = ROOT.parent / "Race07Complete/GameData/Teams/Motec_Type2/FNTCMOTS.BMP"
        if not p.exists():
            self.skipTest("BMP with non-zero row padding not present")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "out.bmp"
            media_tool.bmp_roundtrip(p, dst)
            self.assertEqual(dst.read_bytes(), p.read_bytes())

    def test_cubemap_dds_roundtrip_preserves_six_faces(self):
        import glob
        samples = [p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"),
                                        recursive=True)
                   if p.lower().endswith(".dds") and Path(p).is_file()
                   and open(p, "rb").read(4) == b"DDS "
                   and struct.unpack_from("<I", open(p, "rb").read(128), 112)[0] & 0xFE00]
        if not samples:
            self.skipTest("cube-map DDS not present")
        checked = 0
        for src in samples:
            with self.subTest(src=Path(src).name):
                img = media_tool.read_dds(src)
                self.assertEqual(len(img.cube_face_rgba), 6)
                self.assertEqual(len({f for f in img.cube_face_rgba}), 6)
                self.assertEqual(img.to_bytes(), Path(src).read_bytes())
                checked += 1
        self.assertEqual(checked, len(samples))

    def test_jca_encrypted_dxt5_cubemap(self):
        import jca_crypt
        src = (ROOT.parent / "Race07Complete/GameData/Locations/Brands_Hatch_2007/"
               "TEXTURES/EMAP_GLASS.DDS")
        if not src.is_file():
            self.skipTest("encrypted cube-map sample not present")
        plain = jca_crypt.decrypt_bytes(src.read_bytes())
        with tempfile.TemporaryDirectory() as td:
            q = Path(td) / "emap.dds"
            q.write_bytes(plain)
            img = media_tool.read_dds(q)
            self.assertEqual(img.fourcc, "DXT5")
            self.assertEqual(len(img.cube_face_rgba), 6)
            self.assertEqual(len({f for f in img.cube_face_rgba}), 6)
            self.assertEqual(img.to_bytes(), plain)

    def test_jpg_semantic_roundtrip(self):
        import glob
        sample = next((p for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
                       if p.lower().endswith(".jpg") and Path(p).is_file()
                       and open(p, "rb").read(3) == b"\xff\xd8\xff"), None)
        if sample is None:
            self.skipTest("JPG sample not present")
        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "decoded.png"
            size = media_tool.jpg_decode(sample, png)
            self.assertIsNotNone(size)
            self.assertGreater(size[0], 0)
            reenc = Path(td) / "reenc.jpg"
            self.assertTrue(media_tool.jpg_encode(png, reenc))
            info = media_tool.identify(reenc)
            self.assertEqual(info.format, "jpg")
            self.assertEqual((info.details["width"], info.details["height"]), size)

    def test_mp3_semantic_roundtrip(self):
        import glob
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not present")
        sample = next((p for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
                       if p.lower().endswith(".mp3") and Path(p).is_file()), None)
        if sample is None:
            self.skipTest("MP3 sample not present")
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "decoded.wav"
            self.assertTrue(media_tool.mp3_decode(sample, wav))
            reenc = Path(td) / "reenc.mp3"
            self.assertTrue(media_tool.mp3_encode(wav, reenc))
            self.assertEqual(media_tool.identify(reenc).format, "mp3")

    def test_compressed_wav_encode_roundtrip(self):
        import glob
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not present")
        sample = next((p for p in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*"), recursive=True)
                       if Path(p).is_file() and p.lower().endswith(".wav")
                       and open(p, "rb").read(4) == b"RIFF"), None)
        self.assertIsNotNone(sample)
        with tempfile.TemporaryDirectory() as td:
            pcm = Path(td) / "pcm.wav"
            self.assertTrue(media_tool.wav_decode(sample, pcm))
            for codec in ("adpcm_ima_wav", "libmp3lame"):
                with self.subTest(codec=codec):
                    enc = Path(td) / (codec + ".wav")
                    self.assertTrue(media_tool.wav_encode_compressed(pcm, enc, codec))
                    info = media_tool.identify(enc)
                    self.assertEqual(info.format, "wav")
                    dec = Path(td) / (codec + "_dec.wav")
                    self.assertTrue(media_tool.wav_decode(enc, dec))
                    with wave.open(str(dec), "rb") as w:
                        self.assertGreater(w.getnframes(), 0)

    def test_jca_encrypted_wav_decrypt(self):
        import glob
        def jca_wav(p):
            if not Path(p).is_file():
                return False
            with open(p, "rb") as f:
                return p.lower().endswith(".wav") and f.read(4) == b"\x0f\xb1\xff\xff"
        sample = next((p for p in glob.glob(str(ROOT.parent / "Race07Vanilla" / "**" / "*"), recursive=True)
                       if jca_wav(p)), None)
        if sample is None:
            self.skipTest("JCA-encrypted WAV sample not present")
        info = media_tool.identify(sample)
        self.assertEqual(info.format, "wav-jca")
        self.assertTrue(info.details["jca_encrypted"])
        self.assertIn("audio_format", info.details)
        plain = media_tool.decrypt_jca_wav(Path(sample).read_bytes())
        self.assertEqual(plain[:4], b"RIFF")
        self.assertEqual(plain[8:12], b"WAVE")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "plain.wav"
            dst.write_bytes(plain)
            self.assertEqual(media_tool.identify(dst).format, "wav")
            with wave.open(str(dst), "rb") as w:
                self.assertGreater(w.getnframes(), 0)

    def test_archived_cubemap_roundtrip(self):
        import mas_tool
        p = ROOT.parent / "RF1Vanilla/GameData/Vehicles/showroom.mas"
        if not p.is_file():
            self.skipTest("MAS cube-map sample not present")
        _mtype, entries = mas_tool.read_archive(p)
        members = [e for e in entries if e.name.lower() == "car_cube.dds" and e.data]
        self.assertEqual(len(members), 1)
        with tempfile.TemporaryDirectory() as td:
            q = Path(td) / "cube.dds"
            q.write_bytes(members[0].data)
            img = media_tool.read_dds(q)
            self.assertEqual(img.fourcc, "DXT5")
            self.assertEqual(len(img.cube_face_rgba), 6)
            self.assertEqual(img.to_bytes(), members[0].data)

    def test_jca_mipmapped_cubemap(self):
        import jca_crypt
        src = (ROOT.parent / "Race07Vanilla/GameData/Locations/Vara/TEXTURES/Cube_map.dds")
        if not src.is_file():
            self.skipTest("mipmapped encrypted cube map not present")
        plain = jca_crypt.decrypt_bytes(src.read_bytes())
        with tempfile.TemporaryDirectory() as td:
            q = Path(td) / "cube.dds"
            q.write_bytes(plain)
            img = media_tool.read_dds(q)
            self.assertEqual(len(img.cube_face_rgba), 6)
            self.assertEqual(len(img.cube_face_mips), 6)
            self.assertTrue(all(img.cube_face_mips))
            self.assertEqual(img.to_bytes(), plain)

    def test_wav_extra_riff_chunks_preserved(self):
        p = ROOT.parent / "GTR2Steam/GameData/Sounds/GTR/GT3RSRex_onhigh.wav"
        if not p.exists():
            self.skipTest("WAV with extra chunks not present")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "out.wav"
            media_tool.wav_roundtrip(p, dst)
            self.assertEqual(dst.read_bytes(), p.read_bytes())

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

    def test_identify_jca_text_configs(self):
        """JCA-wrapped text configs are identified as text-jca, not generic jca."""
        import glob
        checked = 0
        for corpus in ("Race07Complete", "VolvoTheGame"):
            for ext in (".car", ".gdb", ".cam", ".scn", ".aud"):
                for p in glob.glob(str(ROOT.parent / corpus / "**" / ("*" + ext)),
                                   recursive=True):
                    if open(p, "rb").read(4) != b"\x0f\xb1\xff\xff":
                        continue
                    info = media_tool.identify(p)
                    self.assertEqual(info.format, "text-jca", p)
                    self.assertTrue(info.details["jca_text"])
                    self.assertGreater(info.details["lines"], 0)
                    checked += 1
                    if checked >= 20:
                        break
                if checked >= 20:
                    break
            if checked >= 20:
                break
        self.assertGreaterEqual(checked, 20)

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

    def test_tga_types_observed(self):
        # Observed in GTR2/GTL files/MAS: TGA image types 2 (uncompressed true-color) and 10 (RLE true-color).
        import glob, os, struct, importlib.util
        types = set()
        for root in [ROOT.parent / 'GTR2Steam', ROOT.parent / 'GTLSteam']:
            for pth in glob.glob(str(root / '**/*.*'), recursive=True):
                if os.path.splitext(pth)[1].lower() != '.tga': continue
                with open(pth, 'rb') as f: b = f.read(18)
                if len(b) >= 18: types.add(b[2])
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:4]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:2]
        for arc in archives:
            for name, d in mas.mas_unpack_to_data(arc):
                if name.lower().endswith('.tga') and len(d) >= 18:
                    types.add(d[2])
        self.assertTrue(types)
        self.assertTrue(types.issubset({2, 10}))

    def test_bmp_formats_observed(self):
        # Observed in GTR2/GTL files/MAS: BMP BI_RGB (comp 0) with bpp 8/24/32 in scanned samples.
        import glob, os, struct, importlib.util
        seen = set()
        for root in [ROOT.parent / 'GTR2Steam', ROOT.parent / 'GTLSteam']:
            for pth in glob.glob(str(root / '**/*.*'), recursive=True):
                if os.path.splitext(pth)[1].lower() != '.bmp': continue
                with open(pth, 'rb') as f: b = f.read(54)
                if len(b) < 54 or b[:2] != b'BM': continue
                dib = struct.unpack_from('<I', b, 14)[0]
                if dib >= 40:
                    seen.add((struct.unpack_from('<H', b, 28)[0], struct.unpack_from('<I', b, 30)[0]))
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:4]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:2]
        for arc in archives:
            for name, d in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.bmp') or len(d) < 54 or d[:2] != b'BM': continue
                dib = struct.unpack_from('<I', d, 14)[0]
                if dib >= 40:
                    seen.add((struct.unpack_from('<H', d, 28)[0], struct.unpack_from('<I', d, 30)[0]))
        self.assertTrue(seen)
        self.assertTrue(seen.issubset({(8, 0), (24, 0), (32, 0)}))

    def test_bik_magic_observed(self):
        # Observed: all 137 GTR2/GTL .bik files start with BIKi.
        import glob, os
        paths = glob.glob(str(ROOT.parent / 'GTR2Steam/**/*.bik'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTLSteam/**/*.bik'), recursive=True)
        if not paths:
            self.skipTest("no BIK files")
        for pth in paths:
            with open(pth, 'rb') as f: magic = f.read(4)
            self.assertEqual(magic, b'BIKi')

    def test_jpg_sof_observed(self):
        # Observed: GTR2/GTL JPGs are baseline SOF0, 8-bit, 3 components.
        import glob, os, struct
        paths = glob.glob(str(ROOT.parent / 'GTR2Steam/**/*.jpg'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTR2Steam/**/*.jpeg'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTLSteam/**/*.jpg'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTLSteam/**/*.jpeg'), recursive=True)
        if not paths:
            self.skipTest("no JPG files")
        for pth in paths:
            with open(pth, 'rb') as f: b = f.read()
            self.assertTrue(b.startswith(b'\xff\xd8'))
            i=2; found=None
            while i < len(b)-1:
                if b[i]!=0xff: i+=1; continue
                while i < len(b) and b[i]==0xff: i+=1
                if i>=len(b): break
                m=b[i]; i+=1
                if m==0xD9 or m==0xDA: break
                if i+2>len(b): break
                ln=struct.unpack_from('>H',b,i)[0]
                if m in (0xC0,0xC1,0xC2) and ln>=7:
                    prec,comp=b[i+2],b[i+7]
                    found=(m,prec,comp)
                i+=ln
            self.assertEqual(found, (0xC0, 8, 3))

    def test_mp3_headers_observed(self):
        # Observed: most GTR2/GTL MP3s start with ID3 or MPEG frame sync; one known null-padded file exists.
        import glob, os
        paths = glob.glob(str(ROOT.parent / 'GTR2Steam/**/*.mp3'), recursive=True)
        paths += glob.glob(str(ROOT.parent / 'GTLSteam/**/*.mp3'), recursive=True)
        if not paths:
            self.skipTest("no MP3 files")
        ok = 0
        for pth in paths:
            with open(pth, 'rb') as f: b = f.read(4)
            if b.startswith(b'ID3') or (len(b)>=2 and b[0]==0xff and (b[1]&0xe0)==0xe0):
                ok += 1
        self.assertGreaterEqual(ok, len(paths)-1)

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

    def test_tga_rle_corpus_roundtrip(self):
        import glob
        sample = next((p for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
                       if p.lower().endswith(".tga") and Path(p).is_file()
                       and open(p, "rb").read(18)[2] == 10), None)
        if sample is None:
            self.skipTest("RLE TGA sample not present")
        img = media_tool.read_tga(sample)
        self.assertEqual(img.image_type, 10)
        out = media_tool.write_tga(img)
        self.assertLess(len(out), os.path.getsize(sample) * 2)
        # decoded pixels are identical after re-encode
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "rle.tga"
            dst.write_bytes(out)
            self.assertEqual(media_tool.read_tga(dst).pixels, img.pixels)

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

    def test_tga_v2_footer_preserved(self):
        p = (ROOT.parent / "GTR2Steam/GameData/Championships/Custom/"
             "001_Pan Euro RS 2003 Rookie Cup_Icon.tga")
        if not p.exists():
            self.skipTest("footer-bearing TGA not present")
        img = media_tool.read_tga(p)
        self.assertEqual(len(img.footer), 26)
        self.assertEqual(img.footer[-18:-1], b"TRUEVISION-XFILE.")
        self.assertEqual(media_tool.write_tga(img), p.read_bytes())

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

    def test_bmp_32bit_trailing_bytes_preserved(self):
        p = (ROOT.parent / "GTR2Steam/GameData/Teams/NGT/Ferrari 360 Teams/GPC Giesse/"
             "04064_NGT_FERRARI_360Graph.bmp")
        if not p.exists():
            self.skipTest("trailing-byte BMP sample not present")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "out.bmp"
            media_tool.bmp_roundtrip(p, dst)
            self.assertEqual(dst.read_bytes(), p.read_bytes())

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

    def test_dds_bc_synthetic_roundtrip(self):
        """BC4/BC5/BC6H/BC7 blocks round-trip byte-exactly when unedited."""
        import struct

        def make(fourcc, dxgi, payload):
            hdr = bytearray(128)
            struct.pack_into("<I", hdr, 0, 0x20534444)
            struct.pack_into("<I", hdr, 4, 124)
            struct.pack_into("<II", hdr, 12, 4, 4)
            struct.pack_into("<I", hdr, 80, 32)
            hdr[84:88] = fourcc.encode() if dxgi is None else b"DX10"
            dx = struct.pack("<5I", dxgi, 3, 0, 1, 0) if dxgi else b""
            return bytes(hdr) + dx + payload

        cases = [("BC4U", None, bytes(8)), ("ATI1", None, bytes(8)),
                 ("BC5U", None, bytes(16)), ("ATI2", None, bytes(16)),
                 ("BC6H_UF16", 95, bytes(16)), ("BC6H_SF16", 96, bytes(16)),
                 ("BC7_UNORM", 98, bytes(16))]
        for fourcc, dxgi, payload in cases:
            with self.subTest(fourcc=fourcc):
                data = make(fourcc, dxgi, payload)
                with tempfile.TemporaryDirectory() as td:
                    p = Path(td) / "x.dds"
                    p.write_bytes(data)
                    img = media_tool.read_dds(p)
                    self.assertEqual(img.fourcc, fourcc)
                    self.assertEqual(img.to_bytes(), data)
                    if dxgi is not None:
                        self.assertEqual(len(img.dx10_header), 20)

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


    def test_png_and_veh_identification(self):
        """PNG and .veh descriptors are identified corpus-wide."""
        import glob
        import simbin_text_tool as stt
        pngs = glob.glob(str(ROOT.parent / "**" / "*.png"), recursive=True)
        self.assertGreater(len(pngs), 1000)
        for p in pngs:
            i = media_tool.identify(p)
            self.assertEqual(i.format, "png", p)
            self.assertGreater(i.details["width"], 0)
            self.assertIn(i.details["color_type"], (0, 2, 3, 4, 6))
        vehs = glob.glob(str(ROOT.parent / "**" / "*.veh"), recursive=True)
        self.assertGreater(len(vehs), 2000)
        for p in vehs:
            self.assertEqual(media_tool.identify(p).format, "rfactor-veh", p)
            self.assertIn("graphics", stt.parse_veh(Path(p).read_bytes()))

    def test_rfactor_scene_scripts_identification(self):
        """.scr and .cin scene scripts are identified."""
        import glob
        for ext, fmt in ((".scr", "rfactor-scr"), (".cin", "rfactor-cin")):
            n = 0
            for p in glob.glob(str(ROOT.parent / "**" / ("*" + ext)), recursive=True):
                self.assertEqual(media_tool.identify(p).format, fmt, p)
                n += 1
            self.assertGreater(n, 100)

    def test_rfactor_gen_identification(self):
        """All .gen vehicle-graphics descriptors are identified."""
        import glob
        import simbin_text_tool as stt
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.gen"), recursive=True):
            self.assertEqual(media_tool.identify(p).format, "rfactor-gen", p)
            stt.parse_scn(stt.read_text(p))  # same key family as .scn
            n += 1
        self.assertGreater(n, 250)

    def test_cubeasf_family_identification(self):
        """Plain CUBEASF scene files (.scn/.clf/.set/.trk) are identified."""
        import glob
        n = 0
        for ext in (".scn", ".clf", ".set"):
            for p in glob.glob(str(ROOT.parent / "**" / ("*" + ext)), recursive=True):
                if open(p, "rb").read(7) != b"CUBEASF":
                    continue
                info = media_tool.identify(p)
                self.assertEqual(info.format, "cubeasf", p)
                self.assertEqual(info.details["extension"], ext)
                n += 1
        self.assertGreater(n, 150)  # ~203 plain .scn/.clf/.set (others are JCA)

    def test_svm_identification_corpus(self):
        """All .svm car setups are identified by variant."""
        import glob
        c = {}
        for p in glob.glob(str(ROOT.parent / "**" / "*.svm"), recursive=True):
            fmt = media_tool.identify(p).format
            c[fmt] = c.get(fmt, 0) + 1
        self.assertGreater(c.get("svm-gtr2", 0), 20000)
        self.assertGreater(c.get("svm-rf1", 0), 500)
        self.assertGreater(c.get("svm-encrypted", 0), 0)
        # All 10 encrypted setups share one 8-byte payload magic.
        magics = set()
        for p in glob.glob(str(ROOT.parent / "**" / "*.svm"), recursive=True):
            i = media_tool.identify(p)
            if i.format == "svm-encrypted":
                magics.add(i.details["payload_magic"])
        self.assertEqual(magics, {"5b 79 6d 98 7f 80 a9 e0"})
        self.assertEqual(sum(v for k, v in c.items() if k.startswith("svm-")),
                         sum(c.values()))

    def test_hat_gzip_corpus(self):
        """All local .hat files are gzip track data with a classified header."""
        import glob
        checked = 0
        variants = set()
        for p in glob.glob(str(ROOT.parent / "**" / "*.hat"), recursive=True):
            result = media_tool.hat_decompress(p)
            self.assertIsNotNone(result, p)
            data, info = result
            self.assertGreater(len(data), 1000, p)
            self.assertIn(info["variant"], ("gMb1.000f", "gMb1.002f", "ver008"), p)
            self.assertEqual(info["decompressed_size"], len(data))
            self.assertEqual(media_tool.identify(p).format, "hat-gzip")
            variants.add(info["variant"])
            checked += 1
        self.assertGreaterEqual(checked, 180)
        self.assertIn("gMb1.000f", variants)
        self.assertIn("ver008", variants)

    def test_hdr_dat_audio_pairs(self):
        """NASCAR-era .hdr/.dat pairs are MP3 streams with a block index."""
        import glob
        checked = exact = 0
        for root in ("NT2003", "NascarSimRacing"):
            for hdr in glob.glob(str(ROOT.parent / root / "**" / "*.hdr"),
                                 recursive=True):
                pair = media_tool.hdr_dat_mp3(hdr)
                if pair is None:
                    continue
                payload, info = pair
                self.assertEqual(payload[0], 0xFF)
                self.assertEqual(payload[1] & 0xE0, 0xE0)
                self.assertEqual(info["dat_size"] % 256, 0)
                self.assertGreater(info["block_count"], 0)
                self.assertEqual(media_tool.identify(hdr).format, "hdr-dat")
                if info["block_count"] == info["dat_blocks"]:
                    exact += 1
                checked += 1
                if checked >= 60:
                    break
            if checked >= 60:
                break
        self.assertGreaterEqual(checked, 60)
        self.assertGreater(exact, 0)  # NT2003 headers match exactly

    def test_hdr_dat_decode_to_wav(self):
        """A real pair decodes to a valid PCM WAV via ffmpeg."""
        import shutil
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg unavailable")
        hdr = ROOT.parent / "NT2003/Sounds/Commentary/Blank.hdr"
        if not hdr.is_file():
            self.skipTest("audio pair not present")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "out.wav"
            self.assertTrue(media_tool._cmd_hdr_dat_decode(hdr, dst))
            with wave.open(str(dst), "rb") as w:
                self.assertGreater(w.getnframes(), 1000)
                self.assertIn(w.getnchannels(), (1, 2))


if __name__ == "__main__":
    unittest.main()
