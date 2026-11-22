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

    def test_real_gtt_if_present(self):
        p = ROOT.parent / "GTR2Steam/TimeTrial/Anderstorp/Henrik Roos - 0_45_297_AndS_550.GTT"
        if not p.exists():
            self.skipTest("GTT not present")
        dec = gzip_simbin_tool.decompress(p)
        self.assertTrue(dec.startswith(b"//[[gMb1.000f"))
        self.assertIn(b"GTTF", dec[:80])

    def test_real_vcr_if_present(self):
        p = ROOT.parent / "GTR2Steam/ReplayData/Anderstorp HOT LAP.Vcr"
        if not p.exists():
            self.skipTest("VCR not present")
        dec = gzip_simbin_tool.decompress(p)
        self.assertTrue(dec.startswith(b"//[[gMb1.000f"))
        self.assertIn(b"IRSR", dec[:80])

    def test_gtt_vcr_header_fields_observed(self):
        # Observed: GTTF/VCR payloads have magic + f32 version + u32 len + TRK + u32 len + AIW.
        import gzip, struct
        cases = [
            (ROOT.parent / "GTR2Steam/TimeTrial/Anderstorp/Henrik Roos - 0_45_297_AndS_550.GTT", b'GTTF', 1.0),
            (ROOT.parent / "GTR2Steam/ReplayData/Anderstorp HOT LAP.Vcr", b'IRSR', 1.0499999523162842),
        ]
        for pth, magic, ver in cases:
            if not pth.exists():
                self.skipTest(f"{pth.name} not present")
            dec = gzip.decompress(pth.read_bytes())
            i = dec.find(magic)
            self.assertGreaterEqual(i, 0)
            off = i + 4
            f = struct.unpack_from('<f', dec, off)[0]; off += 4
            self.assertAlmostEqual(f, ver, places=3)
            ln = struct.unpack_from('<I', dec, off)[0]; off += 4
            trk = dec[off:off+ln]; off += ln
            ln2 = struct.unpack_from('<I', dec, off)[0]; off += 4
            aiw = dec[off:off+ln2]
            self.assertTrue(trk.upper().endswith(b'.TRK'))
            self.assertTrue(aiw.upper().endswith(b'.AIW'))

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

    def test_lma_node_name_extraction(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Driver/ExtDriver_A.LMA"
        if not p.exists():
            self.skipTest("LMA not present")
        b = p.read_bytes()
        nodes = fxm_tool.extract_strings(b)
        names = [s for _, s in nodes]
        self.assertIn('Bip01 Spine', names)
        self.assertIn('Bip01 R Clavicle', names)
        self.assertIn('Bip01 R UpperArm', names)

    def test_fxm_layout_family_observed(self):
        # Observed: LMA driver files often have first string at 19; FXA/FXM pit files at 30.
        cases = [
            (ROOT.parent / "GTR2Steam/GameData/Animations/Driver/ExtDriver_A.LMA", 19),
            (ROOT.parent / "GTR2Steam/GameData/Animations/Pit/FH.FXA", 30),
        ]
        for p, expected in cases:
            if not p.exists():
                self.skipTest(f"{p.name} not present")
            b = p.read_bytes()
            self.assertEqual(fxm_tool._first_string_offset(b), expected)

    def test_lma_node_prefix_observed(self):
        # Observed in sampled GTR2 LMAs: many Bip01 node names are preceded by a 12-byte
        # record prefix LE(u32,u32,u32) where third==1 and second matches BE header u32 at offset 8.
        # Semantics unconfirmed; this is a structural correlation test.
        import struct, glob, os, re
        paths = glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/Animations/Driver/*.LMA'))
        if not paths:
            self.skipTest('no LMA files')
        checked = 0
        for p in paths:
            b = Path(p).read_bytes()
            be8 = struct.unpack_from('>I', b, 8)[0]
            for m in re.finditer(b'Bip01[^\x00]{0,40}\x00', b):
                off = m.start()
                if off < 12:
                    continue
                a, c, d = struct.unpack_from('<III', b, off - 12)
                # only assert on the common pattern family
                if d == 1 and c == be8 and a in (0, 1):
                    checked += 1
        self.assertGreater(checked, 0)


    def test_fxm_offset30_family_signature(self):
        # Observed: offset-30 FXA/FXM/LMA files have BE u16[1]==257, BE u32[2]==4096, BE u32[4]==256, BE u32[5]==528, and source string contains "3D Studio Max".
        import struct, glob, os, re
        paths=[]
        for root in [ROOT.parent / 'GTR2Steam', ROOT.parent / 'GTLSteam']:
            paths += glob.glob(str(root / '**/*.*'), recursive=True)
        checked=0
        for pth in paths:
            if os.path.splitext(pth)[1].lower() not in ('.fxa','.fxm','.lma'): continue
            b = Path(pth).read_bytes()
            m = re.search(br'[\x20-\x7e]{4,}\x00', b)
            if not m or m.start()!=30: continue
            be = struct.unpack_from('>4sHHIIII', b, 0)
            self.assertEqual(be[1], 257)
            self.assertEqual(be[2], 4096)
            self.assertEqual(be[4], 256)
            self.assertEqual(be[5], 528)
            s = m.group()[:-1].decode('latin1','replace')
            self.assertIn('3D Studio Max', s)
            checked += 1
        self.assertGreater(checked, 0)

    def test_fxm_offset30_contains_source_path(self):
        # Observed: most offset-30 files contain a source path string (contains ":" or ":/") within 300 bytes after first string.
        import glob, os, re
        paths=[]
        for root in [ROOT.parent / 'GTR2Steam', ROOT.parent / 'GTLSteam']:
            paths += glob.glob(str(root / '**/*.*'), recursive=True)
        off30=haspath=0
        for pth in paths:
            if os.path.splitext(pth)[1].lower() not in ('.fxa','.fxm','.lma'): continue
            b = Path(pth).read_bytes()
            m = re.search(br'[\x20-\x7e]{4,}\x00', b)
            if not m or m.start()!=30: continue
            off30 += 1
            chunk = b[m.end():m.end()+300]
            if b':\\' in chunk or b':/' in chunk:
                haspath += 1
        self.assertGreaterEqual(off30, 100)
        self.assertGreaterEqual(haspath, off30 - 10)


    def test_fxm_offset19_header_observations(self):
        # Observed: offset-19 FXA/FXM/LMA files have BE u16[1]==257; BE u32[2] in {1,256}; BE u32[3] in {80,184}; BE u32[4]==1; BE u32[5] in {65,66,67,77}.
        import struct, glob, os, re
        paths=[]
        for root in [ROOT.parent / 'GTR2Steam', ROOT.parent / 'GTLSteam']:
            paths += glob.glob(str(root / '**/*.*'), recursive=True)
        checked=0
        for pth in paths:
            if os.path.splitext(pth)[1].lower() not in ('.fxa','.fxm','.lma'): continue
            b = Path(pth).read_bytes()
            m = re.search(br'[\x20-\x7e]{4,}\x00', b)
            if not m or m.start()!=19: continue
            be = struct.unpack_from('>4sHHIIII', b, 0)
            self.assertEqual(be[1], 257)
            self.assertIn(be[2], (1, 256))
            self.assertIn(be[3], (80, 184))
            self.assertEqual(be[4], 1)
            self.assertIn(be[5], (65, 66, 67, 77))
            checked += 1
        self.assertGreater(checked, 0)

    def test_phs_files_not_isi_16byte(self):
        # Observed: 5 .phs files in GTL MAS archives have unknown signatures, not ISI 16-byte-header.
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        arc = ROOT.parent / "GTLSteam/Physics2.gtl"
        if not arc.exists():
            self.skipTest("Physics2.gtl not present")
        found = 0
        for name, data in mas.mas_unpack_to_data(str(arc)):
            if name.lower().endswith('.phs'):
                found += 1
                import isi_crypt
                # crypt_info may parse, but decrypt with known scheme should fail on unknown signature
                with self.assertRaises(Exception):
                    isi_crypt.decrypt_bytes(data, skip=0)
        self.assertGreater(found, 0)

    def test_aiw_header_observed(self):
        # Observed: GTR2/GTL .AIW files are uncompressed and start with //[[gMa1.000...
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3Anderstorp.AIW"
        if not p.exists():
            self.skipTest("AIW not present")
        b = p.read_bytes()
        self.assertTrue(b.startswith(b'//[[gMa1.000'))
        self.assertIn(b'[Features]', b[:4096])


if __name__ == "__main__":
    unittest.main()
