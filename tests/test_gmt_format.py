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

    def test_material_l0_heuristic_bumper_a(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr"
        if not mas_p.exists():
            self.skipTest("archive not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name == 'BMW_M3GTR_BUMPER_A.GMT':
                g = gmt_format.parse_gmt(name, data=data)
                self.assertEqual([m.name for m in g.materials], ['WC_TEAM_BODY1_PA', 'WC_TEAM_BODY2_FL'])
                self.assertTrue(g.materials[0].strings[1].startswith('L0'))
                self.assertEqual(g.materials[0].stages[0].name, 'L0CMAPT0')
                self.assertEqual(g.materials[1].stages[0].name, 'L0DIFFUSET0')
                break

    def test_48byte_vertex_blocks(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Scripts/crew.gtr"
        if not mas_p.exists():
            self.skipTest("crew.gtr not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name == 'FUELHOSE.GMT':
                g = gmt_format.parse_gmt(name, data=data)
                m = g.meshes[0].record
                self.assertEqual(m.vertex_stride, 48)
                self.assertTrue(m.has_extra_vertex_block)
                self.assertEqual(m.vertex_block2_offset, m.vertex_offset + m.vertex_count * 32)
                self.assertEqual(m.vertex_end, m.vertex_offset + m.vertex_count * 48)
                break

    def test_extra_vertex_stream_offsets(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/Anderstorp.gtr"
        if not mas_p.exists():
            self.skipTest("Anderstorp.gtr not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name == 'ANNOUNCERSOUND01.GMT':
                g = gmt_format.parse_gmt(name, data=data)
                r = g.meshes[0].record
                self.assertEqual((r.vertex_count, r.vertex_offset, r.raw[6], r.stream2_end, r.stream3_end), (20, 1164, 1804, 2444, 3084))
                m = g.meshes[0]
                self.assertEqual(len(m.stream2_data), 20 * 32)
                self.assertEqual(len(m.stream3_data), 20 * 32)
                self.assertEqual(gmt_format.write_gmt(g), data)
                break

    def test_decoded_base_vertices_roundtrip(self):
        mas_p = ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr"
        if not mas_p.exists():
            self.skipTest("archive not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name == 'BMW_M3GTR_BUMPER_A.GMT':
                g = gmt_format.parse_gmt(name, data=data)
                self.assertEqual(gmt_format.write_gmt(g), data)
                v = g.meshes[0].base_vertices[0]
                self.assertAlmostEqual(v.x, 0.6859208345413208, places=4)
                self.assertAlmostEqual(v.nx, 0.23175576329231262, places=4)
                self.assertEqual(v.f7, 0xFFFFFFFF)
                break

    def test_48byte_extra_block_and_driver_style(self):
        import struct, math, importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)

        crew = ROOT.parent / "GTR2Steam/GameData/Scripts/crew.gtr"
        if crew.exists():
            for name, data in mas.mas_unpack_to_data(str(crew)):
                if name == 'FUELHOSE.GMT':
                    g = gmt_format.parse_gmt(name, data=data)
                    self.assertEqual(gmt_format.write_gmt(g), data)
                    m = g.meshes[0]
                    self.assertTrue(m.record.has_extra_vertex_block)
                    self.assertEqual(len(m.extra_vertex_data), m.record.vertex_count * 16)
                    self.assertEqual(len(m.extra_vertices), m.record.vertex_count)
                    vals = struct.unpack_from('<4f', m.extra_vertex_data, 0)
                    self.assertEqual(vals[0], 0.0)
                    self.assertTrue(math.isnan(vals[1]))
                    self.assertEqual(vals[2], 0.0)
                    self.assertEqual(vals[3], 0.0)
                    self.assertEqual(m.extra_vertices[0].raw_u32[0], 0)
                    self.assertEqual(m.extra_vertices[0].raw_u32[2], 0)
                    break

        talent = ROOT.parent / "GTR2Steam/GameData/Teams/TALENT.GTR"
        if talent.exists():
            for name, data in mas.mas_unpack_to_data(str(talent)):
                if name == 'EXT_DRIVER_STYLE01.GMT':
                    g = gmt_format.parse_gmt(name, data=data)
                    self.assertEqual(gmt_format.write_gmt(g), data)
                    m = g.meshes[0]
                    self.assertTrue(m.record.has_extra_vertex_block)
                    self.assertEqual(m.record.vertex_stride, 48)
                    self.assertEqual(len(m.extra_vertex_data), m.record.vertex_count * 16)
                    break

    def test_material_stage_strings(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)

        samples = [
            (ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr", 'BMW_M3GTR_BUMPER_A.GMT',
             lambda g: ('BMW_M3GTR_BODY1.TGA' in g.materials[0].strings and 'EMAP_PAINT.DDS' in g.materials[0].strings and 'L0CMAPT0' in g.materials[0].stages[0].strings)),
            (ROOT.parent / "GTR2Steam/GameData/Scripts/crew.gtr", 'FUELHOSE.GMT',
             lambda g: ('FUELHOSE.DDS' in g.materials[0].strings and g.materials[0].stages[0].name == 'L0DIFFUSET0')),
            (ROOT.parent / "GTR2Steam/GameData/Teams/TALENT.GTR", 'EXT_DRIVER_STYLE01.GMT',
             lambda g: ('BODY_BLACKWHITE.DDS' in g.materials[0].strings)),
            (ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/Anderstorp.gtr", 'ANNOUNCERSOUND01.GMT',
             lambda g: ('ROAD_S.TGA' in g.materials[0].strings and 'ROAD_B.TGA' in g.materials[0].strings)),
        ]
        for mas_p, gmt_name, check in samples:
            if not mas_p.exists():
                continue
            for name, data in mas.mas_unpack_to_data(str(mas_p)):
                if name == gmt_name:
                    g = gmt_format.parse_gmt(name, data=data)
                    self.assertEqual(gmt_format.write_gmt(g), data)
                    self.assertTrue(check(g), gmt_name)
                    break


if __name__ == "__main__":
    unittest.main()
