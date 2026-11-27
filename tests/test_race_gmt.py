"""Tests for the partial RaceGMT header parser."""
import glob
import io
import struct
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

    def test_triangle_record_framing(self):
        """PEOPLE_STAND's 36-byte records carry indices, group, ordinal, 5 f32."""
        p = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models/PEOPLE_STAND_01.gmt"
        if not p.is_file():
            self.skipTest("PEOPLE_STAND sample not present")
        recs = race_gmt.read_triangle_records(p.read_bytes())
        self.assertEqual(len(recs), 48)
        from collections import Counter
        self.assertEqual(dict(sorted(Counter(r["group"] for r in recs).items())),
                         {0: 8, 1: 12, 2: 8, 3: 14, 4: 6})
        self.assertTrue(all(r["ordinal"] == i for i, r in enumerate(recs)))
        # Indices restart at (0,1,2) at each group boundary and advance by 3.
        group_indices = {}
        for rec in recs:
            group_indices.setdefault(rec["group"], []).append(rec["indices"])
        for indices in group_indices.values():
            self.assertEqual(indices[0], (0, 1, 2))
            for offset, triple in enumerate(indices):
                self.assertEqual(triple, (3 * offset, 3 * offset + 1, 3 * offset + 2))
        self.assertTrue(all(len(rec["floats"]) == 5 for rec in recs))
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, str(ROOT / "race_gmt.py"), "--triangles", str(p)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("triangles=48", result.stdout)
        self.assertIn("groups=[0, 1, 2, 3, 4]", result.stdout)

    def test_racegmt_converts_to_gtr2_gmt(self):
        """A decoded RaceGMT mesh builds a parseable GTR2 GMT."""
        import subprocess
        import tempfile
        import gmt_format as gf
        import mas_tool

        source = ROOT.parent / ("Race07Complete/GameData/Locations/Marrakech/"
                                "Models/PEOPLE_STAND_01.gmt")
        archive = next((p for p in (ROOT.parent / "GTR2Steam/GameData").rglob("*.gtr")
                        if p.is_file()), None)
        if not source.is_file() or archive is None:
            self.skipTest("RaceGMT/GTR2 template corpora not present")
        _mtype, entries = mas_tool.read_archive(archive)
        template = next((e.data for e in entries
                         if e.name.lower().endswith(".gmt") and e.data), None)
        if template is None:
            self.skipTest("no GTR2 GMT template")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            tpl = Path(td) / "template.gmt"
            tpl.write_bytes(template)
            out = Path(td) / "out.gmt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "race_gmt.py"), str(source),
                 "--to-gtr2", str(out), "--template", str(tpl)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = gf.parse_gmt("out.gmt", out.read_bytes())
            self.assertEqual(len(parsed.meshes), 1)
            self.assertEqual(parsed.meshes[0].record.vertex_count, 144)
            self.assertEqual(parsed.meshes[0].record.index_count, 144)

    def test_variant_submeshes_decode_zolder09_plots(self):
        """The 0x2000403d variant uses 88-byte vertices and decodes fully."""
        base = (ROOT.parent / "Race07Complete/GameData/Locations/Zolder09"
                / "MODELS")
        for name, nv, ni in (("plots01.gmt", 37, 51), ("plots02.gmt", 32, 36)):
            path = base / name
            if not path.is_file():
                self.skipTest("Race07Complete plots corpus not present")
            data = path.read_bytes()
            subs = race_gmt.read_variant_submeshes(data)
            self.assertEqual(len(subs), 1, name)
            self.assertEqual(len(subs[0]["vertices"]), nv, name)
            self.assertEqual(len(subs[0]["indices"]), ni, name)
            self.assertEqual(max(subs[0]["indices"]), nv - 1, name)
            # Position word order is [y,z,x]; the exported tuple is (x,y,z).
            raw_y, raw_z, raw_x = struct.unpack_from("<3f", data,
                                                      data.find(b"\x3d\x40\x00\x20") + 12)
            pos = subs[0]["vertices"][0]["position"]
            self.assertAlmostEqual(pos[0], raw_x, places=4, msg=name)
            self.assertAlmostEqual(pos[1], raw_y, places=4, msg=name)
            self.assertAlmostEqual(pos[2], raw_z, places=4, msg=name)
            self.assertEqual(len(subs[0]["vertices"][0]["uv_sets"]), 4, name)

    def test_submeshes_resolve_triangle_indices(self):
        """The 5 submesh vertex arrays resolve every triangle's u16 indices."""
        base = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models"
        files = [base / f"PEOPLE_STAND_0{i}.gmt" for i in range(1, 6)]
        if not all(p.is_file() for p in files):
            self.skipTest("PEOPLE_STAND variants not present")
        for path in files:
            data = path.read_bytes()
            submeshes = race_gmt.read_racegmt_submeshes(data)
            records = race_gmt.read_triangle_records(data)
            self.assertEqual(len(submeshes), 5, path.name)
            for group, submesh in enumerate(submeshes):
                expected = 3 * sum(1 for r in records if r["group"] == group)
                self.assertEqual(len(submesh["vertices"]), expected, path.name)
                self.assertEqual(list(submesh["indices"]),
                                 list(range(expected)), path.name)
            for record in records:
                submesh = submeshes[record["group"]]
                self.assertTrue(all(idx < len(submesh["vertices"])
                                    for idx in record["indices"]), path.name)

    def test_vertex_table_has_real_uvs(self):
        """The table after the axes holds 5 world positions and UV corners."""
        from math import isfinite

        base = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models"
        files = [base / f"PEOPLE_STAND_0{i}.gmt" for i in range(1, 6)]
        if not all(p.is_file() for p in files):
            self.skipTest("PEOPLE_STAND variants not present")
        for path in files:
            vertices = race_gmt.read_racegmt_vertices(path.read_bytes())
            self.assertEqual(len(vertices), 24, path.name)
            indices = race_gmt.read_racegmt_indices(path.read_bytes())
            self.assertEqual(indices, list(range(24)), path.name)
            for vertex in vertices:
                self.assertTrue(all(isfinite(v) for v in vertex["position"]))
                self.assertGreater(abs(vertex["axis"][0]), 0.05)
                self.assertLess(abs(vertex["axis"][1]), 1.0)
                self.assertEqual(len(vertex["uv_sets"]), 4)
                self.assertEqual(vertex["uv"], vertex["uv_sets"][0])
            self.assertAlmostEqual(vertices[0]["uv"][0], 0.73711, places=4)
            self.assertAlmostEqual(vertices[0]["uv"][1], -0.00631, places=4)
            self.assertAlmostEqual(vertices[1]["uv"][1], -0.99574, places=4)

    def test_texture_axes_decode_f0(self):
        """Each triangle's texture axis (cos,sin) reproduces its column 0."""
        base = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models"
        files = [base / f"PEOPLE_STAND_0{i}.gmt" for i in range(1, 6)]
        if not all(p.is_file() for p in files):
            self.skipTest("PEOPLE_STAND variants not present")
        for path in files:
            data = path.read_bytes()
            axes = race_gmt.read_texture_axes(data)
            records = race_gmt.read_triangle_records(data)
            self.assertEqual(len(axes), len(records), path.name)
            self.assertEqual(len(axes), 48, path.name)
            for rec, (cos, sin) in zip(records, axes):
                x, y = rec["floats"][3], rec["floats"][1]
                self.assertAlmostEqual(rec["floats"][0], sin * x + cos * y,
                                       delta=0.00001, msg=f"{path.name} {rec['ordinal']}")

    def test_f0_is_fixed_horizontal_projection(self):
        """Column 0 is a unit-length projection of (x, y) at a constant angle."""
        import math

        base = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models"
        files = [base / f"PEOPLE_STAND_0{i}.gmt" for i in range(1, 6)]
        if not all(p.is_file() for p in files):
            self.skipTest("PEOPLE_STAND variants not present")
        cx, cy, intercept = 0.18051934549, 0.98357292081, 0.00024729259
        self.assertAlmostEqual(math.hypot(cx, cy), 1.0, places=4)
        for path in files:
            for rec in race_gmt.read_triangle_records(path.read_bytes()):
                x, y = rec["floats"][3], rec["floats"][1]
                predicted = cx * x + cy * y + intercept
                self.assertAlmostEqual(rec["floats"][0], predicted,
                                       delta=0.001, msg=f"{path.name} {rec['ordinal']}")

    def test_f32_columns_track_header_translation(self):
        """Two per-triangle f32 columns shift exactly with the header bbox."""
        import statistics

        base = ROOT.parent / "Race07Complete/GameData/Locations/Marrakech/Models"
        files = [base / f"PEOPLE_STAND_0{i}.gmt" for i in range(1, 6)]
        if not all(p.is_file() for p in files):
            self.skipTest("PEOPLE_STAND variants not present")
        records = [race_gmt.read_triangle_records(p.read_bytes()) for p in files]
        headers = [race_gmt.parse_header(p.read_bytes()).floats for p in files]
        for index in range(1, 5):
            for column, header_index in ((1, 1), (2, 2), (3, 3)):
                observed = statistics.mean(
                    b["floats"][column] - a["floats"][column]
                    for a, b in zip(records[0], records[index]))
                expected = headers[index][header_index] - headers[0][header_index]
                self.assertAlmostEqual(observed, expected, places=4,
                                       msg=f"file {index} column {column}")
        # (f3, f1, f2) is a world-space position inside each file's header bbox.
        for recs, head in zip(records, headers):
            x_min, x_max = head[3], head[0]
            for rec in recs:
                x, y, z = rec["floats"][3], rec["floats"][1], rec["floats"][2]
                self.assertLessEqual(x_min, x)
                self.assertLessEqual(x, x_max)
                self.assertAlmostEqual(y, head[1], delta=10.0)
                self.assertAlmostEqual(z, head[2], delta=3.0)

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
