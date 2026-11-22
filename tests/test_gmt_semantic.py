"""Tests for the layout-independent GMT submesh decoder."""
import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_semantic  # noqa: E402
import mas_tool  # noqa: E402

OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")
NEW = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")


def _member(corpus, exts, magic, name):
    for archive in glob.glob(str(ROOT.parent / corpus / "**" / "*"), recursive=True):
        if not Path(archive).is_file() or Path(archive).suffix.lower() not in exts:
            continue
        try:
            _, entries = mas_tool.read_archive(archive)
        except Exception:
            continue
        for entry in entries:
            data = entry.data or b""
            if entry.name.lower() != name:
                continue
            if magic == data[0x1d4:0x1e4] or magic == data[0x08:0x18]:
                return data
    return None


class GmtSemanticTest(unittest.TestCase):
    def test_schemas(self):
        self.assertEqual(gmt_semantic.SCHEMAS["rf1"]["v_count"], 0x18)
        self.assertEqual(gmt_semantic.SCHEMAS["gtr2"]["v_count"], 0x08)
        self.assertEqual(gmt_semantic.VERTEX_STRIDE, 32)

    def test_old_layout_submesh(self):
        data = _member("RF1Vanilla", (".mas",), OLD, "startbox.gmt")
        if data is None:
            self.skipTest("rF1 STARTBOX.GMT not present")
        g = gmt_semantic.read_gmt(data)
        self.assertEqual(len(g["submeshes"]), 1)
        sub = g["submeshes"][0]
        self.assertEqual(sub["schema"], "rf1")
        self.assertEqual(len(sub["positions"]), 39)
        self.assertEqual(len(sub["uvs"]), 39)
        self.assertEqual(len(sub["faces"]), 48)
        self.assertEqual(sub["faces"][0], (0, 1, 2))
        self.assertAlmostEqual(sub["positions"][0][0], 1.2258, places=3)

    def test_gtr1_vertex_stride_and_normals(self):
        magic = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")
        checked = unit = 0
        for archive in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                data = entry.data or b""
                if data[4:20] != magic:
                    continue
                descs = gmt_semantic.read_gtr1_descriptors(data)
                if not descs:
                    continue
                verts = gmt_semantic.read_gtr1_vertices(data, descs[0])
                for v in verts:
                    nx, ny, nz = v["normal"]
                    norm = (nx * nx + ny * ny + nz * nz) ** 0.5
                    unit += 0.9 < norm < 1.1
                    checked += 1
            if checked >= 2000:
                break
        if not checked:
            self.skipTest("GTR1 GMT corpus not present")
        self.assertGreater(unit / checked, 0.95)
        self.assertEqual(verts[0]["color"], 0xFFFFFFFF)

    def test_gtr1_descriptor_grid(self):
        magic = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                data = entry.data or b""
                if data[4:20] != magic:
                    continue
                descs = gmt_semantic.read_gtr1_descriptors(data)
                if not descs:
                    continue
                self.assertGreater(descs[0]["v_count"], 0)
                self.assertLess(descs[0]["v_off"], len(data))
                self.assertLess(descs[0]["i_off"], len(data))
                checked += 1
            if checked >= 10:
                break
        if not checked:
            self.skipTest("GTR1 GMT corpus not present")
        self.assertGreaterEqual(checked, 1)

    def test_new_layout_submesh(self):
        data = _member("GTR2Steam", (".gtr", ".mas"), NEW, "addondirtedge.gmt")
        if data is None:
            self.skipTest("GTR2 ADDONDIRTEDGE.GMT not present")
        g = gmt_semantic.read_gmt(data)
        self.assertTrue(g["submeshes"])
        sub = g["submeshes"][0]
        self.assertEqual(sub["schema"], "gtr2")
        self.assertEqual(len(sub["positions"]), 276)
        self.assertEqual(len(sub["uvs"]), 276)
        self.assertTrue(sub["faces"])
        self.assertAlmostEqual(sub["positions"][0][0], -73.44, places=1)


if __name__ == "__main__":
    unittest.main()
