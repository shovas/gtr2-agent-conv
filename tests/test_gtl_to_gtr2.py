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
    def test_tree_conversion_preserves_ani_references(self):
        """Converting a GTL track tree does not lose ANI asset bindings."""
        import shutil

        import simbin_text_tool as stt

        source = ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp"
        if not source.is_dir():
            self.skipTest("GTL corpus not present")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            out = Path(td) / "converted"
            g.convert_tree(source, out)
            before = stt.validate_ani_assets(source)
            after = stt.validate_ani_assets(out)
            self.assertEqual(before["references"], after["references"])
            self.assertGreater(before["references"], 100)
            self.assertEqual(set(before["missing"]), set(after["missing"]))
            self.assertEqual(before["missing"], after["missing"])

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
               b"MASFile=skies_north.gtl\r\n\r\nView=mainview\r\n"
               b"Instance=TRACK01\r\n{\r\n"
               b"  MeshFile=track01.gmt CollTarget=True HATTarget=True\r\n}\r\n")
        out, changes = g.convert_trk_bytes(src)
        self.assertIn(b"MASFile=teammaps2.gtr\r\n", out)
        self.assertIn(b"MASFile=skies_north.gtr\r\n", out)
        self.assertIn(b"MASFile=Misc.gtr\r\n", out)
        self.assertEqual(changes["teammaps2"], 1)
        self.assertEqual(g.validate_trk(out), [])

    def test_hdc_clutch_constant_rewrite(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".hdc")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("HDC corpora not present")
        self.assertTrue(all(not g.validate_hdc_clutch(p.read_bytes()) for p in gtr))
        changed = 0
        for p in gtl:
            data = p.read_bytes()
            out, n = g.rewrite_hdc_clutch(data)
            self.assertEqual(g.validate_hdc_clutch(out), [])
            if n:
                changed += 1
                # Only the numeric literal changes.
                reverted = __import__('re').compile(rb"(?im)^([ \t]*clutchengagerate[ \t]*=[ \t]*)0\.8\b").subn(
                    rb"\g<1>0.6", out)[0]
                self.assertEqual(reverted, data)
        self.assertGreater(changed, 30)

    def test_aud_sound_path_rewrite(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".aud")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("audio corpora not present")
        self.assertTrue(all(g.validate_aud_paths(p.read_bytes()) for p in gtl))
        self.assertTrue(all(not g.validate_aud_paths(p.read_bytes()) for p in gtr))
        changed = 0
        for p in gtl:
            data = p.read_bytes()
            out, n = g.rewrite_aud_sound_paths(data)
            self.assertGreater(n, 0, p.name)
            self.assertEqual(g.validate_aud_paths(out), [])
            # Nothing except the prefix changes: revert and compare.
            import re
            reverted, _ = re.compile(rb"GTR\\").subn(lambda _m: b"Cars\\", out)
            self.assertEqual(reverted, data)
            changed += 1
        self.assertGreater(changed, 0)
        for p in gtr:
            out, n = g.rewrite_aud_sound_paths(p.read_bytes())
            self.assertEqual(n, 0)

    def test_ani_motion_blocks(self):
        def idx(root):
            return {Path(p).name.lower(): Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".ani")}
        gtl, gtr = idx("GTLSteam"), idx("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("animation corpora not present")
        self.assertTrue(all(not g.validate_ani(p.read_bytes()) for p in gtr.values()))
        flagged = [p for p in gtl.values() if g.validate_ani(p.read_bytes())]
        self.assertEqual(len(flagged), 2)  # special variant/pitcrew files
        tmpl = next((p for p in gtr.values() if p.name.lower() == "3anderstorp.ani"), None)
        if tmpl is not None:
            src = gtl.get("nanderstorp.ani")
            if src is not None:
                out, rep = g.adapt_ani_from_template(src.read_bytes(), tmpl.read_bytes())
                self.assertEqual(g.validate_ani(out), [])
                self.assertEqual(rep["blocks_added"], 7)
                self.assertTrue(out.startswith(src.read_bytes().rstrip(b"\r\n")))
        for p in gtr.values():
            out, rep = g.adapt_ani_from_template(p.read_bytes(), tmpl.read_bytes() if tmpl else p.read_bytes())
            self.assertEqual(rep["blocks_added"], 0)

    def test_dmg_universal_constants(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".dmg")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("damage-model corpora not present")
        self.assertTrue(all(g.validate_dmg_constants(p.read_bytes()) for p in gtl))
        self.assertTrue(all(not g.validate_dmg_constants(p.read_bytes()) for p in gtr))
        for p in gtl:
            data = p.read_bytes()
            out, n = g.rewrite_dmg_constants(data)
            self.assertEqual(n, len(g.GTR2_DMG_CONSTANTS), p.name)
            self.assertEqual(g.validate_dmg_constants(out), [])
            # GTR2's own values are never re-touched.
            out2, n2 = g.rewrite_dmg_constants(out)
            self.assertEqual(n2, 0)
            self.assertEqual(out2, out)

    def test_jca_encrypted_aud_decrypt_and_rewrite(self):
        """Race07/Volvo .aud files are JCA-wrapped; rules must see plain text."""
        enc = [Path(p) for p in glob.glob(
            str(ROOT.parent / "Race07Complete" / "**" / "*.aud"), recursive=True)]
        if not enc:
            self.skipTest("Race07 audio corpus not present")
        checked = 0
        for p in enc:
            data = p.read_bytes()
            if data[:4] != b"\x0f\xb1\xff\xff":
                continue
            plain = g.aud_plain(data)
            self.assertNotEqual(plain[:4], b"\x0f\xb1\xff\xff", p.name)
            self.assertIn(b"=", plain[:4096], p.name)
            out, n = g.rewrite_aud_sound_paths(data)
            self.assertEqual(g.validate_aud_paths(out), [], p.name)
            if n:
                self.assertNotEqual(out[:4], b"\x0f\xb1\xff\xff", p.name)
            checked += 1
        self.assertGreater(checked, 50)

    def test_aud_roadnoise_rewrite(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".aud")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("audio corpora not present")
        self.assertTrue(all(not g.validate_aud_roadnoise(p.read_bytes()) for p in gtr))
        changed = 0
        for p in gtl:
            data = p.read_bytes()
            out, n = g.rewrite_aud_roadnoise(data)
            self.assertEqual(g.validate_aud_roadnoise(out), [])
            if n:
                changed += 1
                reverted = __import__('re').compile(
                    rb"(?im)^([ \t]*vs_inside_roadnoise_dry[ \t]*=[ \t]*)road_roll_int\.wav\b").subn(
                        rb"\g<1>gtc_road_roll_int.wav", out)[0]
                self.assertEqual(reverted, data)
        self.assertGreater(changed, 25)
        for p in gtr:
            out, n = g.rewrite_aud_roadnoise(p.read_bytes())
            self.assertEqual(n, 0)

    def test_rcd_key_rule_and_template(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".rcd")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("race-config corpora not present")
        self.assertTrue(all(g.validate_rcd(p.read_bytes()) for p in gtl))
        self.assertTrue(all(not g.validate_rcd(p.read_bytes()) for p in gtr))
        src = next((p for p in gtl if p.name.lower() == "cunningham.rcd"), None)
        tmpl = next((p for p in gtr if p.name.lower() == "cunningham.rcd"), None)
        if src and tmpl:
            out, rep = g.adapt_rcd_from_template(src.read_bytes(), tmpl.read_bytes())
            self.assertEqual(g.validate_rcd(out), [])
            self.assertEqual(rep["keys_applied"], 4)
            # Constants are universal in GTR2: verify against every GTR2 file.
            for p in gtr[:20]:
                vals = g.gdb_key_values(p.read_bytes())
                for k, v in g.GTR2_RCD_CONSTANTS.items():
                    self.assertEqual(vals.get(k), v)
            out2, rep2 = g.add_rcd_gtr2_constants(src.read_bytes())
            self.assertEqual(rep2["constants_added"], 2)
            self.assertEqual(len(g.validate_rcd(out2)), 2)

    def test_aud_key_rule_and_template(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".aud")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("audio corpora not present")
        self.assertTrue(all(not g.validate_aud(p.read_bytes()) for p in gtr))
        flagged = [p for p in gtl if g.validate_aud(p.read_bytes())]
        self.assertGreater(len(flagged), 0)
        tmpl = next((p for p in gtr if p.name.lower() == "default.aud"), None)
        if tmpl is not None:
            for p in flagged[:5]:
                with self.subTest(name=p.name):
                    out, rep = g.adapt_aud_from_template(p.read_bytes(),
                                                         tmpl.read_bytes())
                    self.assertEqual(g.validate_aud(out), [])
                    self.assertEqual(rep["keys_applied"], 17)

    def test_hdc_key_rule_and_template(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".hdc")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("HDC corpora not present")
        self.assertTrue(all(not g.validate_hdc(p.read_bytes()) for p in gtr))
        # 34/42 GTL files are flagged; the rest already carry the keys.
        flagged = [p for p in gtl if g.validate_hdc(p.read_bytes())]
        self.assertGreater(len(flagged), 0)
        tmpl = next((p for p in gtr if p.name.lower() == "safetycar.hdc"), None)
        if tmpl is not None:
            for p in flagged[:5]:
                with self.subTest(name=p.name):
                    out, rep = g.adapt_hdc_from_template(p.read_bytes(),
                                                         tmpl.read_bytes())
                    self.assertEqual(g.validate_hdc(out), [])
                    self.assertEqual(rep["keys_applied"], 30)

    def test_aiw_key_rule_and_template(self):
        def idx(root):
            return {Path(p).name.lower(): Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".aiw")}
        gtl, gtr = idx("GTLSteam"), idx("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("AIW corpora not present")
        self.assertTrue(all(g.validate_aiw(p.read_bytes()) for p in gtl.values()))
        self.assertTrue(all(not g.validate_aiw(p.read_bytes()) for p in gtr.values()))
        common = sorted(set(gtl) & set(gtr))
        self.assertGreaterEqual(len(common), 5)
        for name in common:
            with self.subTest(name=name):
                src = gtl[name].read_bytes()
                template = gtr[name].read_bytes()
                out, _ = g.adapt_aiw_from_template(src, template)
                self.assertEqual(g.validate_aiw(out), [])
                tv, ov = g.gdb_key_values(template), g.gdb_key_values(out)
                for key in g.GTR2_AIW_ONLY_KEYS:
                    self.assertEqual(ov.get(key), tv[key])

    def test_tyr_wetweather_rule(self):
        def files(root):
            return [Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".tyr")]
        gtl, gtr = files("GTLSteam"), files("GTR2Steam")
        if not gtl or not gtr:
            self.skipTest("tire corpora not present")
        self.assertTrue(all(not g.validate_tyr(p.read_bytes()) for p in gtr))
        fixed = 0
        for p in gtl:
            out, _ = g.add_tyr_gtr2_defaults(p.read_bytes())
            self.assertEqual(g.validate_tyr(out), [], p.name)
            self.assertEqual(g.gdb_key_values(out).get("wetweather"), "1")
            fixed += 1
        self.assertGreater(fixed, 0)

    def test_car_adapt_from_template(self):
        def index(root):
            return {Path(p).name.lower(): Path(p) for p in glob.glob(
                str(ROOT.parent / root / "**" / "*"), recursive=True)
                if p.lower().endswith(".car")}
        gtl, gtr = index("GTLSteam"), index("GTR2Steam")
        common = sorted(set(gtl) & set(gtr))
        if not common:
            self.skipTest("no same-name GTL/GTR2 .car pair present")
        for name in common:
            with self.subTest(name=name):
                src = gtl[name].read_bytes()
                template = gtr[name].read_bytes()
                out, report = g.adapt_car_from_template(src, template)
                self.assertEqual(g.validate_car(out), [])
                self.assertEqual(report["keys_applied"], 4)
                tv, ov = g.gdb_key_values(template), g.gdb_key_values(out)
                for key in g.GTR2_CAR_ONLY_KEYS:
                    self.assertEqual(ov.get(key), tv[key])
                strip = lambda d: [ln for ln in d.split(b"\n")
                                   if not any(ln.lower().lstrip().startswith(k.encode())
                                              for k in g.GTR2_CAR_ONLY_KEYS)]
                self.assertEqual(strip(src), strip(out))

    def test_car_adapt_generic_template(self):
        gtl = [Path(p) for p in glob.glob(
            str(ROOT.parent / "GTLSteam" / "**" / "*"), recursive=True)
            if p.lower().endswith(".car")]
        tmpl = next((p for p in glob.glob(
            str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
            if p.lower().endswith("safetycar.car")), None)
        if not gtl or tmpl is None:
            self.skipTest("car corpora not present")
        template = Path(tmpl).read_bytes()
        for src in gtl[:10]:
            with self.subTest(name=src.name):
                data = src.read_bytes()
                out, _ = g.adapt_car_from_template(data, template)
                self.assertEqual(g.validate_car(out), [])
                ov, tv = g.gdb_key_values(out), g.gdb_key_values(template)
                for key in g.GTR2_CAR_ONLY_KEYS:
                    self.assertEqual(ov.get(key), tv[key])

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

    def test_gdb_racetime_invariant(self):
        gdbs = [Path(p) for p in glob.glob(
            str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
            if p.lower().endswith(".gdb")]
        if not gdbs:
            self.skipTest("GTR2 GDB corpus not present")
        self.assertTrue(all(not g.validate_gdb_times(p.read_bytes()) for p in gdbs))
        # A deliberately mismatched copy must be flagged.
        data = gdbs[0].read_bytes()
        broken = data.replace(b"racetime=180", b"racetime=999", 1)
        if broken != data:
            self.assertTrue(g.validate_gdb_times(broken))

    def test_tree_validator_decrypts_jca_configs(self):
        """validate_gtr2_tree must see inside JCA-wrapped config files."""
        import media_tool
        samples = [Path(p) for p in glob.glob(
            str(ROOT.parent / "Race07Complete" / "**" / "*.dmg"), recursive=True)
            if open(p, "rb").read(4) == b"\x0f\xb1\xff\xff"]
        if not samples:
            self.skipTest("encrypted DMG corpus not present")
        detected = 0
        for path in samples:
            raw = path.read_bytes()
            plain = media_tool.decrypt_jca_text(raw)
            # Raw encrypted bytes cannot be validated; decrypted values can.
            self.assertEqual(g.validate_dmg_constants(raw), [])
            problems = g.validate_dmg_constants(plain)
            if problems:
                detected += 1
        self.assertGreater(detected, 5)

    def test_gdb_racetime_invariant_jca(self):
        """The session racetime invariant also holds on decrypted JCA GDBs."""
        import media_tool
        checked = 0
        for root in ("Race07Complete", "VolvoTheGame"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.gdb"), recursive=True):
                data = Path(path).read_bytes()
                if data[:4] != b"\x0f\xb1\xff\xff":
                    continue
                plain = media_tool.decrypt_jca_text(data)
                self.assertEqual(g.validate_gdb_times(plain), [], path)
                checked += 1
        self.assertGreaterEqual(checked, 80)

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

    def test_hat_files_are_omitted_from_converted_tree(self):
        """Engine-generated GTL HAT caches are not copied into GTR2 trees."""
        src = ROOT.parent / "GTLSteam/UserData/LOG"
        if not src.is_dir() or not list(src.rglob("*.hat")):
            self.skipTest("GTL HAT corpus not present")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            out = Path(td) / "out"
            report = g.convert_tree(src, out, include_others=True)
            self.assertGreaterEqual(report.get("hat_skipped", 0), 1)
            self.assertEqual(list(out.rglob("*.hat")), [])

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
            self.assertTrue(all(any(k in p for k in ("missing session key", "unresolved MASFile",
                                                      "missing aiw key", "missing tyr key",
                                                      "missing ani block", "missing car key"))
                                for p in probs))
            # Same-name templates close the GDB and AIW gaps for SAnderstorp.
            for name, adapt, check in (("sanderstorp.gdb", g.adapt_gdb_from_template,
                                        g.validate_gdb),
                                       ("sanderstorp.aiw", g.adapt_aiw_from_template,
                                        g.validate_aiw)):
                tgt = Path(td) / name
                template = gtr_dir / name
                if tgt.is_file() and template.is_file():
                    out, _ = adapt(tgt.read_bytes(), template.read_bytes())
                    self.assertEqual(check(out), [])

    def test_convert_config_bytes_all_rewrites(self):
        def sample(ext):
            return next((Path(p) for p in glob.glob(
                str(ROOT.parent / "GTLSteam" / "**" / "*"), recursive=True)
                if p.lower().endswith(ext)), None)
        checks = ((".aud", "aud_paths"), (".hdc", "hdc_clutch"),
                  (".dmg", "dmg_constants"), (".tyr", "tyr_defaults"))
        for ext, key in checks:
            p = sample(ext)
            if p is None:
                continue
            with self.subTest(ext=ext):
                out, changes = g.convert_config_bytes(p.name, p.read_bytes())
                self.assertGreater(changes.get(key, 0), 0, ext)

    def test_convert_tree_end_to_end(self):
        src = ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp"
        gtr = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp"
        if not src.is_dir() or not gtr.is_dir():
            self.skipTest("Anderstorp folders not present")
        tpl = {Path(p).name.lower(): p for p in glob.glob(str(gtr / "*"))
               if Path(p).is_file() and Path(p).suffix.lower() in
               (".gdb", ".car", ".aiw", ".rcd", ".hdc", ".aud", ".ani")}
        for p in glob.glob(str(src / "*")):
            n = Path(p).name.lower()
            if n in tpl:
                continue
            for ext, substitute in ((".aiw", "3Anderstorp.AIW"),
                                    (".gdb", "3Anderstorp.gdb"),
                                    (".ani", "3Anderstorp.ani")):
                if n.endswith(ext) and (gtr / substitute).is_file():
                    tpl[n] = gtr / substitute
        known = {Path(p).name.lower() for p in glob.glob(
            str(ROOT.parent / "GTR2Steam/GameData/**/*"), recursive=True)
            if p.lower().endswith(".gtr")}
        with tempfile.TemporaryDirectory() as td:
            report = g.convert_tree(src, td, include_others=False, templates=tpl)
            self.assertGreater(report["trk"], 0)
            self.assertGreater(report["config"], 0)
            self.assertGreater(report["archives"], 0)
            local = {Path(p).name.lower() for p in glob.glob(td + "/**/*", recursive=True)
                     if p.lower().endswith(".gtr")}
            self.assertEqual(g.validate_gtr2_tree(td, known | local), [])

    def test_multiple_track_subtrees_convert_cleanly(self):
        base_g = ROOT.parent / "GTLSteam/GameData/Locations"
        base_h = ROOT.parent / "GTR2Steam/GameData/Locations"
        if not base_g.is_dir() or not base_h.is_dir():
            self.skipTest("GTL/GTR2 Locations not present")
        known = {Path(p).name.lower() for p in glob.glob(
            str(ROOT.parent / "GTR2Steam/GameData/**/*"), recursive=True)
            if p.lower().endswith(".gtr")}
        exts = (".gdb", ".car", ".aiw", ".rcd", ".hdc", ".aud", ".ani")
        checked = 0
        for src in sorted(p for p in base_g.iterdir() if p.is_dir()):
            tgt = base_h / src.name
            if not tgt.is_dir():
                continue
            tpl = {p.name.lower(): p for p in tgt.iterdir()
                   if p.is_file() and p.suffix.lower() in exts}
            for p in src.iterdir():
                n = p.name.lower()
                if n in tpl or not p.is_file():
                    continue
                cand = next((q for q in tpl.values() if q.suffix.lower() == p.suffix.lower()), None)
                if cand:
                    tpl[n] = cand
            with tempfile.TemporaryDirectory() as td:
                g.convert_tree(src, td, include_others=False, templates=tpl)
                local = {Path(q).name.lower() for q in glob.glob(td + "/**/*", recursive=True)
                         if q.lower().endswith(".gtr")}
                self.assertEqual(g.validate_gtr2_tree(td, known | local), [], src.name)
                checked += 1
                if checked >= 4:  # representative subset keeps Normal within budget
                    break
        self.assertGreaterEqual(checked, 4)

    def test_shared_folder_teammaps_rename(self):
        src = ROOT.parent / "GTLSteam/GameData/Locations/shared"
        if not src.is_dir():
            self.skipTest("GTL shared folder not present")
        with tempfile.TemporaryDirectory() as td:
            report = g.convert_tree(src, td, include_others=False)
            self.assertEqual(report["archives"], 7)
            names = {p.name.lower() for p in Path(td).iterdir()}
            self.assertIn("teammaps2.gtr", names)
            self.assertNotIn("teammaps.gtr", names)
            self.assertEqual(g.validate_gtr2_tree(td), [])

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
        tpl = {Path(p).name.lower(): p for p in glob.glob(str(target / "*"))
               if Path(p).is_file() and Path(p).suffix.lower() in
               (".gdb", ".car", ".aiw", ".rcd", ".hdc", ".aud", ".ani")}
        for p in glob.glob(str(src / "*")):
            n = Path(p).name.lower()
            if n in tpl:
                continue
            for ext, substitute in ((".aiw", "3Anderstorp.AIW"),
                                    (".gdb", "3Anderstorp.gdb"),
                                    (".ani", "3Anderstorp.ani")):
                if n.endswith(ext) and (target / substitute).is_file():
                    tpl[n] = target / substitute
        with tempfile.TemporaryDirectory() as td:
            g.convert_tree(src, td, include_others=False, templates=tpl)
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


    def test_rf1_svm_detector(self):
        """rF1-style .svm setups are detected; vanilla GTR2 has 10."""
        self.assertIn("rF1-style", " ".join(g.validate_svm_setup(
            b"//[[gMa1.000f (c)2004    ]]\n[DRIVELINE]\nFinalDriveSetting=1\n")))
        self.assertEqual(g.validate_svm_setup(
            b"[GENERAL]\r\nNotes=\"\"\r\nSymmetric=1\r\n"), [])
        paths = g.rf1_svm_paths(ROOT.parent / "GTR2Steam")
        self.assertEqual(len(paths), 10)


if __name__ == "__main__":
    unittest.main()
