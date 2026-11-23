"""Tests for the GTL -> GTR2 container/.trk conversion building block."""
import glob
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gtl_to_gtr2 as g  # noqa: E402
import mas_tool  # noqa: E402


def _trks(root: str) -> list[Path]:
    base = ROOT.parent / root
    return [Path(p) for p in glob.glob(str(base / "**" / "*"), recursive=True)
            if p.lower().endswith(".trk")]


class GtlToGtr2Test(unittest.TestCase):
    def test_corpus_masfile_rules(self):
        gtl, gtr2 = _trks("GTLSteam"), _trks("GTR2Steam")
        if not gtl or not gtr2:
            self.skipTest("GTL/GTR2 corpora not present")
        gtl_vals = [v for p in gtl for v in g.masfile_values(p.read_bytes())]
        gtr_vals = [v for p in gtr2 for v in g.masfile_values(p.read_bytes())]
        self.assertGreater(len(gtl_vals), 100)
        self.assertGreater(len(gtr_vals), 150)
        self.assertTrue(all(v.lower().endswith(".gtl") for v in gtl_vals))
        self.assertTrue(all(v.lower().endswith(".gtr") for v in gtr_vals))
        self.assertTrue(any(v.lower() == "teammaps.gtl" for v in gtl_vals))
        self.assertTrue(any(v.lower() == "teammaps2.gtr" for v in gtr_vals))
        # Every real GTR2 .trk already satisfies our validator.
        self.assertTrue(all(not g.validate_trk(p.read_bytes()) for p in gtr2))

    def test_trk_conversion_and_non_masfile_preservation(self):
        trks = _trks("GTLSteam")
        if not trks:
            self.skipTest("GTL corpus not present")
        converted = 0
        for p in trks:
            data = p.read_bytes()
            self.assertTrue(g.validate_trk(data), p.name)
            out, changes = g.convert_trk_bytes(data)
            self.assertEqual(g.validate_trk(out), [], p.name)
            self.assertGreater(changes["gtl_ext"], 0)
            self.assertTrue(changes["misc_added"])
            # All non-MASFile lines are byte-identical.
            a = [l for l in data.split(b"\n") if b"MASFile=" not in l]
            b = [l for l in out.split(b"\n") if b"MASFile=" not in l]
            self.assertEqual(a, b, p.name)
            converted += 1
        self.assertGreater(converted, 0)

    def test_gtr2_trk_conversion_is_idempotent(self):
        trks = _trks("GTR2Steam")
        if not trks:
            self.skipTest("GTR2 corpus not present")
        for p in trks:
            data = p.read_bytes()
            out, changes = g.convert_trk_bytes(data)
            self.assertEqual(out, data, p.name)
            self.assertEqual(changes["gtl_ext"], 0)
            self.assertFalse(changes["misc_added"])

    def test_teammaps2_rewrite(self):
        src = (b"SearchPath=GAMEDATA\\TRACKS\r\n"
               b"MASFile=teammaps.gtl\r\n"
               b"MASFile=skies_north.gtl\r\n\r\nView=mainview\r\n")
        out, changes = g.convert_trk_bytes(src)
        self.assertIn(b"MASFile=teammaps2.gtr\r\n", out)
        self.assertIn(b"MASFile=skies_north.gtr\r\n", out)
        self.assertIn(b"MASFile=Misc.gtr\r\n", out)
        self.assertEqual(changes["teammaps2"], 1)
        self.assertEqual(g.validate_trk(out), [])

    def test_gdb_session_key_rule(self):
        gtl, gtr = _trks("GTLSteam"), _trks("GTR2Steam")
        gdbs = lambda root: [Path(p) for p in glob.glob(
            str(ROOT.parent / root / "**" / "*"), recursive=True)
            if p.lower().endswith(".gdb")]
        gtl_g, gtr_g = gdbs("GTLSteam"), gdbs("GTR2Steam")
        if not gtl_g or not gtr_g:
            self.skipTest("GTL/GTR2 GDB corpora not present")
        self.assertTrue(all(g.validate_gdb(p.read_bytes()) for p in gtl_g))
        self.assertTrue(all(not g.validate_gdb(p.read_bytes()) for p in gtr_g))

    def test_car_key_rule(self):
        def cars(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".car")]
        gtl, gtr = cars("GTLSteam"), cars("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("GTL/GTR2 car corpora not present")
        self.assertTrue(all(g.validate_car(p.read_bytes()) for p in gtl))
        self.assertTrue(all(not g.validate_car(p.read_bytes()) for p in gtr))

    def test_gdb_adapt_from_same_name_template(self):
        def index(root):
            return {Path(p).name.lower(): Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".gdb")}
        gtl, gtr = index("GTLSteam"), index("GTR2Steam")
        common = sorted(set(gtl) & set(gtr))
        if not common:
            self.skipTest("no same-name GTL/GTR2 GDB pair present")
        for name in common:
            with self.subTest(name=name):
                src = gtl[name].read_bytes()
                template = gtr[name].read_bytes()
                self.assertTrue(g.validate_gdb(src))
                out, report = g.adapt_gdb_from_template(src, template)
                self.assertEqual(g.validate_gdb(out), [])
                self.assertTrue(report["keys_applied"] >= 15)
                tv, ov = g.gdb_key_values(template), g.gdb_key_values(out)
                for key in g.GTR2_SESSION_KEYS:
                    self.assertEqual(ov.get(key), tv[key])
                # Non-session lines are preserved verbatim.
                strip = lambda d: [ln for ln in d.split(b"\n")
                                   if not any(ln.lower().lstrip().startswith(k.encode())
                                              for k in g.GTR2_SESSION_KEYS)]
                self.assertEqual(strip(src), strip(out))

    def test_full_subtree_gap_inventory(self):
        """Converting a single track folder leaves only documented shared/GDB gaps."""
        src = ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp"
        gtr_dir = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp"
        if not src.is_dir() or not gtr_dir.is_dir():
            self.skipTest("Anderstorp folders not present")
        known = {Path(p).name.lower()
                 for p in glob.glob(str(ROOT.parent / "GTR2Steam/GameData/**/*"),
                                    recursive=True)
                 if p.lower().endswith(".gtr")}
        with tempfile.TemporaryDirectory() as td:
            g.convert_tree(src, td, include_others=True)
            local = {Path(p).name.lower() for p in glob.glob(td + "/**/*", recursive=True)
                     if p.lower().endswith(".gtr")}
            probs = g.validate_gtr2_tree(td, known | local)
            self.assertTrue(probs)
            # No stale .gtl, and every problem is a known GDB/shared-archive gap.
            self.assertFalse(any("stale .gtl" in p for p in probs))
            self.assertTrue(all("missing session key" in p or "unresolved MASFile" in p
                                for p in probs))
            # The one same-name GDB template can close its own gap.
            name = "sanderstorp.gdb"
            tgt = Path(td) / name
            template = gtr_dir / name
            if tgt.is_file() and template.is_file():
                out, _ = g.adapt_gdb_from_template(tgt.read_bytes(), template.read_bytes())
                self.assertEqual(g.validate_gdb(out), [])

    def test_validate_tree(self):
        src = ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp"
        target = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp"
        if not src.is_dir() or not target.is_dir():
            self.skipTest("GTL/GTR2 Anderstorp folders not present")
        self.assertTrue(g.validate_gtr2_tree(src))
        known = {Path(p).name.lower()
                 for p in glob.glob(str(ROOT.parent / "GTR2Steam/GameData/**/*"),
                                    recursive=True)
                 if p.lower().endswith(".gtr")}
        self.assertEqual(g.validate_gtr2_tree(target, known), [])
        with tempfile.TemporaryDirectory() as td:
            g.convert_tree(src, td, include_others=False)
            local = {Path(p).name.lower() for p in glob.glob(td + "/**/*", recursive=True)
                     if p.lower().endswith(".gtr")}
            self.assertEqual(g.validate_gtr2_tree(td, known | local), [])

    def test_convert_tree(self):
        src = ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp"
        if not src.is_dir():
            self.skipTest("Anderstorp GTL track not present")
        with tempfile.TemporaryDirectory() as td:
            report = g.convert_tree(src, td, include_others=False)
            self.assertGreater(report["trk"], 0)
            self.assertGreater(report["archives"], 0)
            trks = list(Path(td).rglob("*.trk"))
            self.assertEqual(len(trks), report["trk"])
            for p in trks:
                self.assertEqual(g.validate_trk(p.read_bytes()), [], p.name)
            gtrs = list(Path(td).rglob("*.gtr"))
            self.assertEqual(len(gtrs), report["archives"])
            for p in gtrs:
                self.assertEqual(mas_tool.read_archive(p)[0], 0)


if __name__ == "__main__":
    unittest.main()
