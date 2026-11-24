"""Tests for the standalone AIW/SCN semantic reader."""
import collections
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simbin_text_tool as stt  # noqa: E402


def _files(root: str, ext: str):
    base = ROOT.parent / root
    return [p for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext]


class SimbinTextToolTest(unittest.TestCase):
    def test_aiw_parse_from_reference_corpus(self):
        aiws = _files("GTR2Steam", ".aiw") + _files("GTLSteam", ".aiw")
        if not aiws:
            self.skipTest("GTR2/GTL corpora not present")
        self.assertEqual(len(aiws), 59)
        parsed = 0
        for p in aiws:
            aiw = stt.parse_aiw(stt.read_text(p))
            if aiw.waypoints:
                parsed += 1
                self.assertTrue(all(w.pos and len(w.pos) == 3 for w in aiw.waypoints))
        self.assertGreater(parsed, 0)

    def test_aiw_features_and_waypoints(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3Anderstorp.AIW"
        if not p.exists():
            self.skipTest("sample AIW not present")
        aiw = stt.parse_aiw(stt.read_text(p))
        self.assertEqual(aiw.features["pitlanes"], "1")
        self.assertEqual(aiw.features["startinggrid"], "104")
        self.assertEqual(len(aiw.waypoints), 1114)
        self.assertIn(0, aiw.branches())

    def test_scn_trk_parse(self):
        trk = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3ANDERSTORP.trk"
        if not trk.exists():
            self.skipTest("sample TRK not present")
        info = stt.parse_scn(stt.read_text(trk))
        self.assertIn("GAMEDATA\\LOCATIONS\\Shared", info.search_path)
        self.assertIn("Anderstorp.gtr", info.mas_files)
        self.assertTrue(info.has_skyboxi)

    def test_scn_parse_across_corpora(self):
        files = _files("GTR2Steam", ".trk") + _files("GTR2Steam", ".scn") + \
                _files("GTLSteam", ".trk") + _files("GTLSteam", ".scn")
        if not files:
            self.skipTest("GTR2/GTL corpora not present")
        parsed = 0
        for p in files:
            raw = stt.read_text(p)
            if raw.startswith("CUBEASF"):
                info = stt.parse_scn(raw)
                parsed += 1
                self.assertIsInstance(info.mas_files, list)
        self.assertGreater(parsed, 0)


    def test_sp_parser_corpus(self):
        """.sp suspension geometry: field presence and body refs hold."""
        import glob
        n = totals = 0
        tb = tbar = tj = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.sp"), recursive=True):
            if Path(p).read_bytes()[:4] == b"\x0f\xb1\xff\xff":
                continue
            info = stt.parse_sp(Path(p).read_bytes())
            self.assertEqual(stt.validate_sp(info), [], p)
            tb += len(info.bodies)
            tbar += len(info.bars)
            tj += len(info.joints)
            n += 1
        self.assertEqual(n, 172)
        self.assertEqual((tb, tbar, tj), (1872, 3320, 688))

    def test_sp_parser_reference_validation(self):
        """A dangling posbody reference is flagged."""
        good = ("[BODY]\nname=body mass=(0.0) inertia=(0,0,0) pos=(0,0,0)\n"
                "[BAR]\nposbody=body negbody=body pos=(1,0,0) neg=(2,0,0)\n")
        self.assertEqual(stt.validate_sp(stt.parse_sp(good)), [])
        bad = good.replace("negbody=body", "negbody=missing")
        self.assertTrue(stt.validate_sp(stt.parse_sp(bad)))
        info = stt.parse_sp(good)
        self.assertEqual(info.bars[0].pos, (1.0, 0.0, 0.0))
        self.assertEqual(info.bars[0].neg, (2.0, 0.0, 0.0))

    def test_set_parser_corpus(self):
        """.set files: 22 CUBEASF camera/scene descriptors parse fully."""
        import glob
        n = with_inst = with_search = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.set"), recursive=True):
            if Path(p).read_bytes()[:7] != b"CUBEASF":
                continue  # 3 unrelated tool settings files
            info = stt.parse_set(Path(p).read_bytes())
            self.assertEqual(len(info.views), 1, p)
            self.assertEqual(len(info.lights), 1, p)
            self.assertIsNotNone(info.ambient_color, p)
            view = info.views[0]
            self.assertEqual(view.name, "mainview")
            self.assertIn(view.clear, ("False", "false"))
            self.assertEqual(len(view.color), 3)
            self.assertEqual(len(view.size), 2)
            self.assertEqual(len(view.center), 2)
            self.assertEqual(len(view.fov), 2)
            self.assertEqual(len(view.clip_planes), 2)
            light = info.lights[0]
            self.assertEqual(light.name, "FDirect01")
            self.assertEqual(light.kind, "Directional")
            self.assertEqual(len(light.direction), 3)
            self.assertEqual(len(light.color), 3)
            with_inst += bool(info.instances)
            with_search += bool(info.search_paths)
            n += 1
        self.assertEqual(n, 22)
        self.assertEqual(with_inst, 5)
        self.assertEqual(with_search, 5)

    def test_set_multi_kv_per_line(self):
        """Lines can pack several key=value pairs; filenames with '.' are safe."""
        info = stt.parse_set(
            "CUBEASF\nView=mainview\n{\nSize=(.5, 0.5) Center=(0.5, 0.5)\n"
            "ClipPlanes=(0.10, 20.00)\n}\nAmbientColor=(95,104,121)\n"
            "Instance=Test\n{\nMeshFile=SpinnerAlphaFloor.gmt CollTarget=False "
            "LODOut=(30.0)\n}\nSearchPath=UiData\\\n")
        v = info.views[0]
        self.assertEqual(v.size, (0.5, 0.5))
        self.assertEqual(v.center, (0.5, 0.5))
        self.assertEqual(v.clip_planes, (0.1, 20.0))
        self.assertEqual(info.ambient_color, (95.0, 104.0, 121.0))
        inst = info.instances[0]
        self.assertEqual(inst.mesh_files, ["SpinnerAlphaFloor.gmt"])
        self.assertEqual(inst.coll_target, "False")
        self.assertEqual(inst.lod_out, (30.0,))
        self.assertEqual(info.search_paths, ["UiData\\"])

    def test_hdv_parser_corpus(self):
        """.hdv physics: 9 universal sections, 81 universal keys over 156 files."""
        import glob
        sec = collections.Counter()
        key = collections.Counter()
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.hdv"), recursive=True):
            info = stt.parse_hdv(Path(p).read_bytes())
            self.assertGreater(len(info.keys), 100, p)
            n += 1
            for s in info.sections:
                sec[s] += 1
            for k in info.keys:
                key[k] += 1
        self.assertEqual(n, 156)
        self.assertEqual(len(sec), 17)
        self.assertEqual(len(key), 496)
        universal_sec = {s for s, v in sec.items() if v == n}
        self.assertEqual(universal_sec,
                         {"general", "bodyaero", "suspension", "controls",
                          "engine", "frontleft", "frontright", "rearleft", "rearright"})
        self.assertGreaterEqual(sum(1 for v in key.values() if v == n), 80)
        self.assertIn("mass", key)
        self.assertIn("inertia", key)

    def test_hdv_value_comments_and_quotes(self):
        info = stt.parse_hdv(
            "[GENERAL]\r\nMass=603.0  // kg\r\nNotes=\"a // b\"\r\nInertia=(1,2,3)\r\n")
        self.assertEqual(info.values["mass"], "603.0")
        self.assertEqual(info.values["notes"], "a // b")
        self.assertEqual(info.values["inertia"], "(1,2,3)")
        self.assertEqual(info.sections, {"general"})

    def test_veh_parser_corpus(self):
        """.veh descriptors: 57 keys, Graphics universal, 6 near-universal."""
        import glob
        counts = {}
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.veh"), recursive=True):
            d = stt.parse_veh(Path(p).read_bytes())
            if not d:
                continue
            n += 1
            for k in d:
                counts[k] = counts.get(k, 0) + 1
        self.assertGreater(n, 2000)
        self.assertEqual(len(counts), 57)
        self.assertEqual(counts["graphics"], n)
        for k in ("classes", "driver", "number", "team", "sounds", "hdvehicle"):
            self.assertGreaterEqual(counts[k], n - 2)

    def test_svm_key_subset_corpus(self):
        """rF1 .svm keys are a strict subset of the GTR2 setup vocabulary."""
        import glob
        rf_keys = set()
        gtr_keys = set()
        rf_sections = set()
        gtr_sections = set()
        n_rf = n_gtr = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.svm"), recursive=True):
            info = stt.parse_svm(Path(p).read_bytes())
            if info.variant == "encrypted":
                continue
            if info.variant == "rf1":
                rf_keys |= info.keys
                rf_sections |= info.sections
                n_rf += 1
            else:
                gtr_keys |= info.keys
                gtr_sections |= info.sections
                n_gtr += 1
        self.assertGreater(n_rf, 400)
        self.assertGreater(n_gtr, 10000)
        self.assertEqual(len(rf_keys), 77)
        self.assertEqual(rf_keys - gtr_keys, set())
        # Section names are identical across rF1 and GTR2 setups.
        self.assertEqual(rf_sections, gtr_sections)
        self.assertEqual(len(rf_sections), 15)


if __name__ == "__main__":
    unittest.main()
