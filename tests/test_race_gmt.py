"""Tests for the partial RaceGMT header parser."""
import glob
import sys
import unittest
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
