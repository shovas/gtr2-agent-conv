"""Tests for SCN->TRK text conversion and tree-level pipeline."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import text_convert as tc  # noqa: E402

SCN = """CUBEASF

SearchPath=.
SearchPath=JOESVILLE
MASFile=COMMONMAPS.MAS
MASFile=JOESVILLE_SPEEDWAY_MAP.MAS
View=mainview
"""


class TextConvertTest(unittest.TestCase):
    def test_scn_to_trk_rules(self):
        out = tc.scn_to_trk(SCN, "JOESVILLE_SPEEDWAY")
        self.assertIn("SearchPath=GameData\\Locations\\Shared", out)
        self.assertIn("SearchPath=GameData\\Locations\\JOESVILLE_SPEEDWAY", out)
        self.assertIn('MASFile="COMMONMAPS.gtr"', out)
        self.assertIn('MASFile="JOESVILLE_SPEEDWAY_MAP.gtl"', out)
        self.assertNotIn("SearchPath=.", out)

    def test_gtl_trk_extensions(self):
        src = "MASFile=Anderstorp.gtl\nMASFile=skies_north.gtl\nSearchPath=GameData\\Locations\n"
        out = tc.trk_extensions_to_gtr2(src)
        self.assertIn("MASFile=Anderstorp.gtr", out)
        self.assertIn("MASFile=skies_north.gtr", out)
        self.assertNotIn(".gtl", out)
        self.assertIn("SearchPath=GameData\\Locations", out)

    def test_crlf_preserved_by_rewrites(self):
        """Rewritten lines keep CRLF endings and inline comments."""
        scn = ("CUBEASF\r\n"
               "SearchPath=.\r\n"
               "MASFile=COMMONMAPS.MAS\r\n")
        out = tc.scn_to_trk(scn, "JOESVILLE")
        self.assertEqual(out.count("\n"), 4)
        self.assertEqual(out.count("\r\n"), 4)
        self.assertEqual(out.count("\n") - out.count("\r\n"), 0)
        trk = ("  MASFile=Anderstorp.gtl // track map\r\n"
               "SearchPath=GameData\\Locations\r\n")
        out = tc.trk_extensions_to_gtr2(trk)
        self.assertIn("MASFile=Anderstorp.gtr // track map\r\n", out)
        self.assertEqual(out.count("\n") - out.count("\r\n"), 0)

    def test_gtl_trk_corpus_keeps_crlf(self):
        """All GTL TRK rewrites preserve uniform CRLF endings."""
        checked = 0
        for path in (ROOT.parent / "GTLSteam").rglob("*"):
            if path.suffix.lower() != ".trk":
                continue
            with path.open(encoding="latin-1", newline="") as handle:
                source = handle.read()
            output = tc.trk_extensions_to_gtr2(source)
            self.assertEqual(output.count("\n"), output.count("\r\n"), path)
            checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_tree_check_on_real_corpus(self):
        src = ROOT.parent / "RF1Vanilla/GameData/Locations/Joesville"
        if not src.is_dir():
            self.skipTest("RF1Vanilla sample track not present")
        report = tc.convert_tree(src, Path("/tmp/unused"), check=True)
        self.assertGreater(report["archives"], 0)
        self.assertGreater(report["scn"], 0)
        self.assertGreater(report["copy"], 0)


    def test_jca_encrypted_scn_decryption(self):
        """Race07/Volvo .scn files are JCA-wrapped; tree conversion must decrypt."""
        import glob
        import media_tool
        samples = [p for p in glob.glob(
            str(ROOT.parent / "Race07Complete" / "**" / "*.scn"), recursive=True)
            if open(p, "rb").read(4) == b"\x0f\xb1\xff\xff"]
        if not samples:
            self.skipTest("encrypted SCN corpus not present")
        checked = 0
        for path in samples:
            data = Path(path).read_bytes()
            plain = media_tool.decrypt_jca_text(data)
            self.assertNotEqual(plain[:4], b"\x0f\xb1\xff\xff", path)
            text = tc.decode_config_bytes(data)
            self.assertIn("=", text, path)
            converted = tc.scn_to_trk(text, Path(path).name)
            self.assertTrue(converted, path)
            checked += 1
        self.assertGreaterEqual(checked, 5)


if __name__ == "__main__":
    unittest.main()
