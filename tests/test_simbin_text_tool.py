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


    def test_skn_nested_fields(self):
        info = stt.parse_skn(
            'Skin="Ritual"\n{\nModel="Ford"\nStyle="Ritual"\n'
            'Layer="Base.tga"\n{\nColor=(0, 0, 255)\n}\n'
            'Word="101"\n{\nFont="Standard"\nColor=(255, 255, 255)\n'
            'Pos=(0.5, 0.2)\nOri=(180.0)\nSize=(0.15, 0.15)\n}\n'
            'Stamp="Detail.tga"\nDecal="Small"\n}\n')
        self.assertEqual(info.name, "Ritual")
        self.assertEqual(info.model, "Ford")
        self.assertEqual(info.layers[0].color, (0.0, 0.0, 255.0))
        self.assertEqual(info.words[0].font, "Standard")
        self.assertEqual(info.words[0].pos, (0.5, 0.2))
        self.assertEqual(info.stamps, ["Detail.tga"])
        self.assertEqual(info.decals, ["Small"])

    def test_aud_sound_map_fixture(self):
        """.aud keys are consistently path- or numeric-valued."""
        sample = ("VS_INSIDE_COAST_ENGINE_1=GTR\\engine.wav\n"
                  "MinimumRPM=1000\n"
                  "VS_OUTSIDE_SHIFT_1=1.20,Mini\\shift_1\n")
        info = stt.parse_aud(sample)
        self.assertEqual(info.path_keys,
                         {"vs_inside_coast_engine_1", "vs_outside_shift_1"})
        self.assertEqual(info.numeric_keys, {"minimumrpm"})
        self.assertEqual(stt.validate_aud_map(info), [])
        mixed = sample + "MinimumRPM=GTR\\x.wav\n"
        self.assertTrue(stt.validate_aud_map(stt.parse_aud(mixed)))

    def test_cin_script_fixture(self):
        """.cin events parse with Probability/Iterations invariants."""
        sample = ("PreRacePresentation\n{\nCinematicEvent\n{\n"
                  "Type = CAMERA_SELECT\nProbability = 1.00\n"
                  "Time = +0.0\nIterations = 1\nWait = YES\n"
                  "Camera = STATIC001\n}\n}\n")
        info = stt.parse_cin(sample)
        self.assertEqual(info.sections, ["PreRacePresentation"])
        self.assertEqual(len(info.events), 1)
        self.assertEqual(info.events[0].type, "CAMERA_SELECT")
        self.assertEqual(info.events[0].camera, "STATIC001")
        self.assertEqual(stt.validate_cin(info), [])
        bad = sample.replace("Probability = 1.00", "Probability = 0.50")
        self.assertTrue(stt.validate_cin(stt.parse_cin(bad)))

    def test_scr_script_fixture(self):
        """.scr Actor blocks parse Detail/Position/Mesh."""
        sample = ('Actor "Pit box"\n{\nDetail 0\nPosition 1.0 2.0 3.0\n'
                  'Mesh "Startbox.gmt"\nMove PATH\n}\n')
        info = stt.parse_scr(sample)
        self.assertEqual(info.actors[0].name, "Pit box")
        self.assertEqual(info.actors[0].position, (1.0, 2.0, 3.0))
        self.assertEqual(info.actors[0].mesh, "Startbox.gmt")
        self.assertEqual(info.actors[0].move, "PATH")
        self.assertEqual(stt.validate_scr(info), [])

    def test_eng_torque_curve(self):
        """.eng RPMTorque points are (rpm, friction, torque) with rising RPM."""
        sample = ("RPMTorque=(0, -58.40, -58.00)\n"
                  "RPMTorque=(250, -33.00, -9.00)\n"
                  "EngineInertia=(0.15)\n")
        # minimal fixture: validator will flag missing universals but parser must work
        info = stt.parse_eng(sample)
        self.assertEqual(info.torque_curve, [(0.0, -58.4, -58.0), (250.0, -33.0, -9.0)])
        self.assertEqual(info.values["engineinertia"], "(0.15)")
        self.assertIn("rpmtorque", info.keys)
        bad = stt.parse_eng("RPMTorque=(500, 0, 10)\nRPMTorque=(250, 0, 20)\n")
        self.assertIn("RPMTorque RPM values not strictly increasing",
                      stt.validate_eng(bad))

    def test_grb_ratio_semantics(self):
        """.grb gear ratio is b/a (driven/driving teeth), not a/b."""
        sample = ("[GEAR_RATIOS]\nratio=(10,40) // 4.00\n"
                  "Ratio=( 16 , 38 ) // 2.38\n"
                  "[FINAL_DRIVE]\nbevel=(1, 1) // 1.0\n"
                  "ratio=(12,44) // 3.67\n")
        info = stt.parse_grb(sample)
        self.assertEqual(info.gear_ratios, [(10, 40), (16, 38)])
        self.assertEqual(info.final_ratio, (12, 44))
        self.assertEqual(info.bevel, (1, 1))
        self.assertEqual(stt.validate_grb(info), [])
        self.assertAlmostEqual(info.gear_ratios[0][1] / info.gear_ratios[0][0], 4.0, places=1)

    def test_rcd_parser_families(self):
        """.rcd classification and validation on small fixtures."""
        event = ("CJames\r\n{\r\nNationality=German\r\nStartsDry=10\r\n"
                 "StartsWet=5\r\nStartStalls=2\r\nCrash=6.5\r\nPassing=70\r\n"
                 "QualifyingAbility=80\r\nRaceAbility=75\r\nRainAbility=60\r\n"
                 "Recovery=68\r\n}\r\n")
        info = stt.parse_rcd(event)
        self.assertEqual(info.family, "event")
        self.assertEqual(info.name, "CJames")
        self.assertEqual(info.values["nationality"], "German")
        self.assertEqual(stt.validate_rcd(info), [])
        nascar = ("Bill\n{\nSpeed=92\nConcentration=80\nFitness=70\n"
                  "Intimidation=50\nAggression=86\nStatus=1\nCourtesy=74\n"
                  "Script=0\n}\n")
        info = stt.parse_rcd(nascar)
        self.assertEqual(info.family, "nascar")
        self.assertEqual(stt.validate_rcd(info), [])

    def test_hed_parser_corpus(self):
        """.hed: 88 files, 5 springs in fixed order, all invariants hold."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.hed"), recursive=True):
            plain = media_tool.decrypt_jca_text(Path(p).read_bytes())
            info = stt.parse_hed(plain)
            self.assertEqual(stt.validate_hed(info), [], p)
            self.assertEqual(tuple(s.kind for s in info.springs),
                             stt.HED_SPRING_TYPES, p)
            self.assertEqual(len(info.springs), 5)
            n += 1
        self.assertGreaterEqual(n, 88)

    def test_hed_plain_fields(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Vehicles/headphysics.hed"
        if not p.is_file():
            import glob
            cand = glob.glob(str(ROOT.parent / "**" / "headphysics.hed"), recursive=True)
            if not cand:
                self.skipTest("no plain headphysics.hed")
            p = Path(cand[0])
        info = stt.parse_hed(p.read_bytes())
        self.assertEqual(info.head_mass, 6.0)
        self.assertEqual(info.head_inertia, (0.032, 0.028, 0.029))
        self.assertEqual(info.springs[0].direction, (0.0, 1.0, 0.0))
        self.assertEqual(info.springs[0].params, (1000.0, 225.0))

    def test_cli_decrypts_jca_wrapped_scn(self):
        """The scn CLI reports search paths from JCA-wrapped Race07 configs."""
        import glob
        import subprocess
        import sys

        candidates = [p for p in glob.glob(
            str(ROOT.parent / "Race07Complete" / "**" / "*.scn"),
            recursive=True)
            if Path(p).read_bytes()[:4] == b"\x0f\xb1\xff\xff"]
        if not candidates:
            self.skipTest("JCA-wrapped SCN corpus not present")
        result = subprocess.run(
            [sys.executable, str(ROOT / "simbin_text_tool.py"),
             "scn", candidates[0]], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SEARCH_PATH:", result.stdout.upper())
        self.assertIn("GAMEDATA\\LOCATIONS", result.stdout.upper())

    def test_cas_uses_scn_parser(self):
        """.cas car graphics descriptors share the .scn key family."""
        import glob
        n = with_mas = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.cas"), recursive=True):
            if Path(p).read_bytes()[:4] == b"\x0f\xb1\xff\xff":
                continue
            info = stt.parse_scn(stt.read_text(p))
            self.assertIsInstance(info.mas_files, list)
            with_mas += bool(info.mas_files)
            n += 1
        self.assertEqual(n, 417)
        self.assertGreater(with_mas, 300)

    def test_inccar_uses_veh_parser(self):
        """.inccar configs share the .veh key=value syntax (96 keys)."""
        import collections
        import glob
        c = collections.Counter()
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.inccar"), recursive=True):
            d = stt.parse_veh(Path(p).read_bytes())
            if not d:
                continue
            n += 1
            for k in d:
                c[k] += 1
        self.assertGreaterEqual(n, 39)
        self.assertGreaterEqual(len(c), 100)
        core = {"hdvehicle", "sounds", "engine", "classes", "description",
                "manufacturer", "model", "modelid", "horsepower", "weight",
                "transmission", "torque", "valves"}
        self.assertTrue(all(c[k] >= 39 for k in core))

    def test_sp_parser_reference_validation(self):
        """A dangling posbody reference is flagged."""
        bodies = "".join(f"[BODY]\nname={n} mass=(0.0) inertia=(0,0,0) pos=(0,0,0)\n"
                         for n in stt.SP_UNIVERSAL_BODIES)
        bars = "".join(f"[BAR]\nname={n} posbody=body negbody=body "
                       "pos=(1,0,0) neg=(2,0,0)\n" for n in stt.SP_UNIVERSAL_BARS)
        good = bodies + bars + ("[BAR]\nposbody=body negbody=body "
                                "pos=(1,0,0) neg=(2,0,0)\n")
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
        self.assertGreaterEqual(n, 22)
        self.assertGreaterEqual(with_inst, 5)
        self.assertGreaterEqual(with_search, 5)

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
        import isi_crypt
        import media_tool
        for p in glob.glob(str(ROOT.parent / "**" / "*.hdv"), recursive=True):
            raw = Path(p).read_bytes()
            if raw[:4] == b"\x0f\xb1\xff\xff":
                raw = media_tool.decrypt_jca_text(raw)
            elif len(raw) >= 16:
                try:
                    import isi_crypt as ic
                    s, _ = ic.crypt_info(raw)
                    if s in ic.GAMES:
                        raw = ic.decrypt_bytes(raw)
                except Exception:
                    pass
            info = stt.parse_hdv(raw)
            if not info.keys:
                continue  # opaque encrypted variant (e.g. TR2009 ISI)
            self.assertGreater(len(info.keys), 0, p)
            n += 1
            for s in info.sections:
                sec[s] += 1
            for k in info.keys:
                key[k] += 1
        self.assertGreaterEqual(n, 156)
        self.assertGreaterEqual(len(sec), 17)
        self.assertGreaterEqual(len(key), 496)
        universal_sec = {s for s, v in sec.items() if v == max(sec.values())}
        self.assertTrue(universal_sec.issuperset(
                         {"general", "bodyaero", "suspension", "controls",
                          "engine", "frontleft", "frontright", "rearleft", "rearright"}))
        self.assertGreaterEqual(sum(1 for v in key.values() if v == max(key.values())), 80)
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



if __name__ == "__main__":
    unittest.main()
