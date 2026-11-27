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
        self.assertIn("MASFile=COMMONMAPS.gtr", out)
        self.assertIn("MASFile=JOESVILLE_SPEEDWAY_MAP.gtr", out)
        self.assertNotIn("SearchPath=.", out)

    def test_gtl_trk_extensions(self):
        src = "MASFile=Anderstorp.gtl\nMASFile=skies_north.gtl\nSearchPath=GameData\\Locations\n"
        out = tc.trk_extensions_to_gtr2(src)
        self.assertIn("MASFile=Anderstorp.gtr", out)
        self.assertIn("MASFile=skies_north.gtr", out)
        self.assertNotIn(".gtl", out)
        self.assertIn("SearchPath=GameData\\Locations", out)

    def test_scn_masfile_unquoted_matches_corpus(self):
        """Converted MASFile lines are bare, as in all 293 GTR2/GTL TRKs."""
        import gtl_to_gtr2 as g2g
        out = tc.scn_to_trk(SCN, "JOESVILLE_SPEEDWAY")
        values = g2g.masfile_values(out.encode("latin-1"))
        self.assertTrue(values)
        self.assertTrue(all(not value.startswith('"') for value in values))
        self.assertTrue(all(value.lower().endswith(".gtr") for value in values))

    def test_crlf_preserved_by_rewrites(self):
        """Rewritten lines keep CRLF endings and inline comments."""
        scn = ("CUBEASF\r\n"
               "SearchPath=.\r\n"
               "MASFile=COMMONMAPS.MAS\r\n")
        out = tc.scn_to_trk(scn, "JOESVILLE")
        self.assertEqual(out.count("\n"), 5)
        self.assertEqual(out.count("\r\n"), 5)
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


    def test_tree_conversion_trk_conventions(self):
        """An end-to-end converted tree has corpus-conforming TRK references."""
        import tempfile
        import gtl_to_gtr2 as g2g
        source = ROOT.parent / "RF1Vanilla/GameData/Locations/Joesville"
        if not source.is_dir():
            self.skipTest("RF1Vanilla sample track not present")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tree"
            tc.convert_tree(source, target)
            tracks = list(target.rglob("*.trk"))
            self.assertTrue(tracks)
            for path in tracks:
                data = path.read_bytes()
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), path)
                values = g2g.masfile_values(data)
                self.assertTrue(values)
                self.assertTrue(all(v.lower().endswith(".gtr") for v in values), path)
                self.assertTrue(any(v.lower() == "misc.gtr" for v in values), path)
            problems = g2g.validate_gtr2_tree(target)
            self.assertFalse([p for p in problems if "non-.gtr MASFile" in p])
            self.assertFalse([p for p in problems if "missing Misc.gtr" in p])

    def test_tdf_track_vars_transfer_to_gdb(self):
        """rF1 per-track .tdf surface variables move into the GTR2 GDB."""
        tdf = (ROOT.parent / "RF1Vanilla/GameData/Locations/Joesville"
               / "Joesville_Speedway.tdf")
        if not tdf.is_file():
            self.skipTest("rF1 Joesville TDF not present")
        variables = tc.tdf_track_vars(tdf.read_bytes())
        self.assertEqual(len(variables), 12)
        self.assertEqual(variables["roaddrygrip"], "1.00")
        gdb = b"[GENERAL]\r\nSomeKey=1\r\n"
        updated, added = tc.add_tdf_vars_to_gdb(gdb, variables)
        self.assertEqual(added, 10)  # two rF1-only grip keys skipped
        self.assertIn(b"RoadWetGrip=0.80\r\n", updated)
        self.assertNotIn(b"RoadMetalGrip", updated)
        self.assertIn(b"SomeKey=1\r\n", updated)

    def test_unified_rf1_tree_converts_and_validates(self):
        """A whole rF1 track converts to a GTR2-valid tree with templates."""
        import tempfile
        import gtl_to_gtr2 as gtl

        src = ROOT.parent / "RF1Vanilla/GameData/Locations/Joesville"
        template_dir = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp"
        shared = (ROOT.parent / "RF1Vanilla/GameData/Locations/commonmaps.mas",)
        if not src.is_dir() or not template_dir.is_dir() or not shared[0].is_file():
            self.skipTest("rF1/GTR2 Anderstorp corpora not present")
        templates = {p.name.lower(): p for p in template_dir.iterdir()
                     if p.is_file() and p.suffix.lower() in (".gdb", ".aiw")}
        self.assertTrue(templates)
        gtr_shared = {p.name.lower() for p in (ROOT.parent / "GTR2Steam/GameData").rglob("*")
                      if p.is_file() and p.suffix.lower() == ".gtr"}
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            out = Path(td) / "converted"
            report = tc.convert_tree(src, out, templates=templates,
                                     shared_archives=shared)
            self.assertEqual(report["archives"], 3)
            self.assertEqual(report["adapted"], 2)
            self.assertTrue((out / "commonmaps.gtr").is_file())
            local = {p.name.lower() for p in out.rglob("*")
                     if p.is_file() and p.suffix.lower() == ".gtr"}
            self.assertEqual(gtl.validate_gtr2_tree(out, gtr_shared | local), [])

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
