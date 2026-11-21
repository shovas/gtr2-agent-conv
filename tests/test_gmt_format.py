import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402


class GmtFormatTest(unittest.TestCase):
    def test_parse_write_roundtrip_real(self):
        p = ROOT.parent / "GTR2Steam/GameData/Teams/M-FPDriver.gmt"
        if not p.exists():
            self.skipTest("GTR2 GMT not present")
        g = gmt_format.parse_gmt(p)
        out = gmt_format.write_gmt(g)
        self.assertEqual(out, p.read_bytes())
        self.assertTrue(g.mesh_count >= 1)
        self.assertEqual(g.magic, gmt_format.GMT_MAGIC)

    def test_parse_write_roundtrip_gtl(self):
        p = ROOT.parent / "GTLSteam/GameData/Teams/M-FPDriver.gmt"
        if not p.exists():
            self.skipTest("GTL GMT not present")
        g = gmt_format.parse_gmt(p)
        out = gmt_format.write_gmt(g)
        self.assertEqual(out, p.read_bytes())

    def test_mesh_material_index_in_range(self):
        p = ROOT.parent / "GTR2Steam/GameData/Teams/M-FPDriver.gmt"
        if not p.exists():
            self.skipTest("GTR2 GMT not present")
        g = gmt_format.parse_gmt(p)
        # tail header has u32 count at +4
        if len(g.tail) >= 8:
            import struct
            mat_count = struct.unpack_from('<I', g.tail, 4)[0]
            for m in g.meshes:
                self.assertLess(m.record.material_index, mat_count)

    def test_roundtrip_from_archive_sample(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr"
        if not mas_p.exists():
            self.skipTest("archive not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name.lower().endswith('.gmt'):
                g = gmt_format.parse_gmt(name, data=data)
                out = gmt_format.write_gmt(g)
                self.assertEqual(out, data)
                break

    def test_vertex_stride_and_material_index(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr"
        if not mas_p.exists():
            self.skipTest("archive not present")
        import importlib.util, struct
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name.lower().endswith('.gmt'):
                g = gmt_format.parse_gmt(name, data=data)
                self.assertIn(g.meshes[0].record.vertex_stride, (32, 48))
                if len(g.tail) >= 8:
                    mat_count = struct.unpack_from('<I', g.tail, 4)[0]
                    for m in g.meshes:
                        self.assertLess(m.record.material_index, mat_count)
                break


if __name__ == "__main__":
    unittest.main()
