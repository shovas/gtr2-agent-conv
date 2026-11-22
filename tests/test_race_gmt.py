"""Tests for the partial RaceGMT header parser."""
import glob
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import race_gmt  # noqa: E402


class RaceGmtTest(unittest.TestCase):
    def test_real_headers(self):
        files = [p for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"), recursive=True)
                 if Path(p).is_file() and Path(p).read_bytes()[:8] == race_gmt.MAGIC]
        if not files:
            self.skipTest("RaceGMT files not present")
        self.assertGreater(len(files), 600)
        for p in files[:20]:
            h = race_gmt.parse_header(Path(p).read_bytes())
            self.assertTrue(h.name)
            self.assertEqual(h.flags, race_gmt.FLAGS)
            self.assertEqual(len(h.floats), 12)

    def test_record_strides_from_same_size_pair(self):
        a = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        b = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_02.gmt"
        if not (a.is_file() and b.is_file()):
            self.skipTest("PEOPLE_STAND pair not present")
        report = race_gmt.diff_strides(a.read_bytes(), b.read_bytes())
        distances = report["distances"]
        self.assertGreater(distances.get(36, 0), 10)
        self.assertGreater(distances.get(64, 0), 10)

    def test_position_records(self):
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND sample not present")
        tris = race_gmt.read_positions(p.read_bytes())
        self.assertEqual(len(tris), 552)
        self.assertTrue(all(len(t) == 3 for t in tris))
        self.assertAlmostEqual(tris[0][0][0], 25.1521, places=3)

    def test_materials_cli(self):
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND_01 not present")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = race_gmt.main(["--materials", str(p)])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("RaceGmtHeader(", out)
        self.assertIn("material@", out)
        self.assertIn("L0DIFFUSET0(type=1,ch=1)", out)
        self.assertIn("L2DIFFUSET0(type=0,ch=0)", out)

    def test_stage_channel_groups(self):
        groups = 0
        l2_nonzero = 0
        for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*.gmt"), recursive=True):
            data = Path(p).read_bytes()
            if data[:8] != race_gmt.MAGIC:
                continue
            for group in race_gmt.decode_stage_channels(
                    race_gmt.read_material_blocks(data)):
                groups += 1
                for stage in group["stages"]:
                    if stage["name"].startswith("L2"):
                        l2_nonzero += stage["channel"] != 0
                    elif stage["name"].startswith(("L0", "L1")):
                        self.assertIn(stage["channel"], (0, 1, 3, 4, 5, 6))
        if not groups:
            self.skipTest("RaceGMT stage blocks not present")
        self.assertGreater(groups, 1000)
        self.assertEqual(l2_nonzero, 0)

    def test_stage_type_map_is_deterministic(self):
        blocks = []
        files = []
        for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*.gmt"), recursive=True):
            data = Path(p).read_bytes()
            if data[:8] == race_gmt.MAGIC:
                files.append(data)
        for data in files:
            blocks.extend(race_gmt.read_material_blocks(data))
        if not blocks:
            self.skipTest("RaceGMT stage blocks not present")
        tmap = race_gmt.build_stage_type_map(blocks)
        expected = {
            "L0DIFFUSET0": 1, "L1DIFFUSET0": 2, "L2DIFFUSET0": 0,
            "L0CMAPT0": 3, "L1BUMPSPECMAPT0": 5, "L1CMAPT0": 7,
        }
        for name, typ in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, tmap)
                self.assertEqual(tmap[name][0], typ)
        well_sampled = {n: v for n, v in tmap.items() if v[2] >= 20}
        self.assertGreater(len(well_sampled), 0)
        for name, (typ, count, total) in well_sampled.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(count / total, 0.8)

    def test_stage_numeric_tail_correlates_with_prefix(self):
        files = [p for p in ROOT.parent.joinpath("Race07Complete").rglob("*.gmt")
                 if p.read_bytes()[:8] == race_gmt.MAGIC]
        if not files:
            self.skipTest("RaceGMT files not present")
        seen = {}
        for p in files[:10]:
            for b in race_gmt.read_material_blocks(p.read_bytes()):
                seen.setdefault(b["name"][:2], b["tail"])
        self.assertEqual(seen.get("L0"), (1, 1))
        self.assertEqual(seen.get("L2"), (0, 0))
        self.assertIn(seen.get("L1"), ((2, 1), (2, 4)))

    def test_material_stage_groups(self):
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND sample not present")
        ss = race_gmt.read_material_strings(p.read_bytes())
        self.assertEqual(len(ss) % 4, 0)
        groups = [ss[i:i + 4] for i in range(0, len(ss), 4)]
        self.assertEqual(len(groups), 5)
        for g in groups:
            self.assertTrue(g[0].rstrip("\0"))
            self.assertTrue(all(s.startswith("L") for s in g[1:]))

    def test_material_strings_present_in_payload(self):
        import re
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND sample not present")
        text = p.read_bytes().decode("latin-1")
        self.assertIn("L0DIFFUSET0", text)
        self.assertIn("PESSOAS_E", text)

    def test_triangles_share_vertices(self):
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND sample not present")
        tris = race_gmt.read_positions(p.read_bytes())
        verts = [tuple(round(c, 4) for c in v) for t in tris for v in t]
        self.assertLess(len(set(verts)), len(verts))  # shared vertices -> triangle soup

    def test_rejects_other_gmt(self):
        with self.assertRaises(ValueError):
            race_gmt.parse_header(b"NOPE" + b"\0" * 64)


if __name__ == "__main__":
    unittest.main()
