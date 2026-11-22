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

    def test_detomaso_rainscreen_header_repair_roundtrip(self):
        # Known odd case: not ISI 16-byte-header encrypted; header magic/flags are mangled.
        # Repairing to normal GMT magic+flags yields a structurally parseable/lossless-roundtrip GMT.
        import importlib.util, struct
        mas_p = ROOT.parent / "GTLSteam/GameData/Teams/GTC-TC-76/Detomaso Pantera/DETOMASO_PANTERA_CPIT.gtl"
        if not mas_p.exists():
            self.skipTest("GTL DETOMASO CPIT not present")
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        normal = bytes.fromhex('c8cfd2d8ced8e6c3d6ded8bebba7bf90')
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name.upper() == 'DETOMASO_PANTERA_RAINSCREEN.GMT':
                repaired = bytearray(data)
                repaired[4:8] = struct.pack('<I', 0)
                repaired[8:24] = normal
                repaired = bytes(repaired)
                g = gmt_format.parse_gmt(name, data=repaired)
                self.assertEqual(g.mesh_count, 0)
                self.assertTrue(any('RAIN_ANIM' in s for s in g.materials[0].strings))
                self.assertEqual(gmt_format.write_gmt(g), repaired)
                return
        self.skipTest("DETOMASO_PANTERA_RAINSCREEN.GMT not found")

    def test_material_header_and_stage_trailing_params_observed(self):
        # Observed (semantics unconfirmed) numeric fields in material header and stage tails.
        import importlib.util, struct
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        mas_p = ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_OBJ.gtr"
        if not mas_p.exists():
            self.skipTest("archive not present")
        for name, data in mas.mas_unpack_to_data(str(mas_p)):
            if name == 'BMW_M3GTR_BUMPER_A.GMT':
                g = gmt_format.parse_gmt(name, data=data)
                self.assertEqual(gmt_format.write_gmt(g), data)
                m = g.materials[0]
                self.assertEqual(len(m.header_raw), 152)
                hdr = struct.unpack_from('<38I', m.header_raw)
                self.assertEqual(hdr[32:38], (1065353216, 2, 1, 1109393408, 0, 3))
                self.assertEqual((m.stages[0].tail_u32_64, m.stages[0].tail_u32_65), (3, 4))
                self.assertEqual((m.stages[1].tail_u32_64, m.stages[1].tail_u32_65), (7, 3))
                return
        self.skipTest("sample not found")


    def test_material_header_observed_invariants(self):
        # Observed across large L0-heuristic GMT sample (semantics unconfirmed):
        # hdr_u32[32]==1065353216 (1.0f), hdr_u32[36]==0 always in sample.
        import importlib.util, struct, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:8]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:4]
        if not archives:
            self.skipTest("no archives")
        checked = 0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'):
                    continue
                g = gmt_format.parse_gmt(name, data=data)
                self.assertEqual(gmt_format.write_gmt(g), data)
                for m in g.materials:
                    if len(m.header_raw) < 152:
                        continue
                    # Only assert on L0-heuristic/confident materials
                    if not m.stages or not m.stages[0].name.startswith('L0'):
                        continue
                    hdr = struct.unpack_from('<38I', m.header_raw)
                    self.assertEqual(hdr[32], 1065353216)
                    self.assertEqual(hdr[36], 0)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_material_texture_strings_in_stage3_observed(self):
        # Observed in large L0-heuristic sample: texture filename strings (.DDS/.TGA/.BMP)
        # appear in stage block 3, not stages 0-2, for nearly all materials.
        import importlib.util, struct, glob, os, re
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        tex_re = re.compile(br'\.(DDS|TGA|BMP)', re.I)
        s0=s1=s2=s3=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for m in g.materials:
                    if not m.stages or not m.stages[0].name.startswith('L0'): continue
                    for si, st in enumerate(m.stages[:4]):
                        has = bool(tex_re.search(st.raw))
                        if si==0 and has: s0+=1
                        if si==1 and has: s1+=1
                        if si==2 and has: s2+=1
                        if si==3 and has: s3+=1
        self.assertEqual(s0, 0)
        self.assertEqual(s1, 0)
        self.assertEqual(s2, 0)
        self.assertGreater(s3, 0)

    def test_stage3_texture_offsets_observed(self):
        # Observed: stage-3 texture filename strings commonly appear at offsets 28 and/or 200
        # within the 264-byte stage block. Semantics unconfirmed.
        import importlib.util, struct, glob, os, re
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        tex_re = re.compile(br'[ -~]{4,}\.(DDS|TGA|BMP)\x00', re.I)
        at28=at200=other=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for m in g.materials:
                    if not m.stages or not m.stages[0].name.startswith('L0'): continue
                    if len(m.stages) < 4: continue
                    st3 = m.stages[3].raw
                    for mm in tex_re.finditer(st3):
                        o = mm.start()
                        if o == 28: at28 += 1
                        elif o == 200: at200 += 1
                        else: other += 1
        self.assertGreater(at28, 0)
        self.assertGreater(at200, 0)
        # observed dominant offsets; allow rare others but they should be few
        self.assertGreater(at28 + at200, other * 10)

    def test_stage3_texture_slot_patterns_observed(self):
        # Observed: stage-3 texture slots commonly (28,200) or (28,); semantics unconfirmed.
        import importlib.util, struct, glob, os, re
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        tex_re = re.compile(br'[\x20-\x7e]{4,}\.(DDS|TGA|BMP)\x00', re.I)
        both=one=none=other=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for m in g.materials:
                    if not m.stages or not m.stages[0].name.startswith('L0'): continue
                    if len(m.stages) < 4: continue
                    offs = tuple(mm.start() for mm in tex_re.finditer(m.stages[3].raw))
                    if offs == (28,200): both+=1
                    elif offs == (28,): one+=1
                    elif offs == (): none+=1
                    else: other+=1
        self.assertGreater(both, 0)
        self.assertGreater(one, 0)
        self.assertGreater(both+one, other)


    def test_common_stage_shader_names_observed(self):
        # Observed common stage 0-2 shader names in L0-heuristic materials (semantics unconfirmed).
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        seen = set()
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for m in g.materials:
                    if not m.stages or not m.stages[0].name.startswith('L0'): continue
                    for st in m.stages[:3]:
                        if st.name: seen.add(st.name)
        for expected in ['L0NOLIGHTING','L0DIFFUSET0','L1DIFFUSET0','L1BUMPSPECMAPT0','L2USEVERTEXPIXEL','L2SPECULART0']:
            self.assertIn(expected, seen)

    def test_stage3_observed_param_fields(self):
        # Observed: stage-3 u32 at offset 24 and 92 have common value distributions; semantics unconfirmed.
        import importlib.util, struct, glob, os, collections
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        c24=collections.Counter(); c92=collections.Counter(); total=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for m in g.materials:
                    if not m.stages or not m.stages[0].name.startswith('L0'): continue
                    if len(m.stages)<4: continue
                    st3=m.stages[3].raw
                    c24[struct.unpack_from('<I',st3,24)[0]]+=1
                    c92[struct.unpack_from('<I',st3,92)[0]]+=1
                    total+=1
        self.assertGreater(total, 0)
        self.assertIn(131096, c92)
        self.assertIn(24, c92)
        self.assertTrue(set(c24).issubset(set(range(0,256))) or max(c24) < 1000)

    def test_mesh_stream2_stream3_stride_observed(self):
        # Observed: when present, stream2 (rec[6]..rec[7]) and stream3 (rec[7]..rec[8])
        # are 32 bytes per vertex. Semantics unconfirmed.
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        seen_s2=seen_s3=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    vc = mesh.record.vertex_count
                    if vc <= 0: continue
                    if mesh.stream2_data:
                        self.assertEqual(len(mesh.stream2_data), vc * 32)
                        seen_s2 += 1
                    if mesh.stream3_data:
                        self.assertEqual(len(mesh.stream3_data), vc * 32)
                        seen_s3 += 1
        self.assertGreater(seen_s2, 0)
        self.assertGreater(seen_s3, 0)

    def test_mesh_record_observed_invariants(self):
        # Observed in scanned GTR2/GTL GMTs: rec[0]==0, vertex stride 32 or 48 (or 0 for empty).
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        total=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    r = mesh.record.raw
                    self.assertEqual(r[0], 0)
                    vc = r[3]
                    if vc > 0 and r[6] > r[4] and (r[6]-r[4]) % vc == 0:
                        st = (r[6]-r[4]) // vc
                        self.assertIn(st, (32, 48))
                    total += 1
        self.assertGreater(total, 0)

    def test_mesh_flag_bit0x20_correlates_with_stream23(self):
        # Observed: mesh rec[1] bit 0x20 set iff stream2/3 blocks present (scanned sample).
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        total=s23=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    r = mesh.record.raw
                    vc=r[3]; v6,v7,v8=r[6],r[7],r[8]
                    has_s23 = vc>0 and v7>v6 and v8>v7 and v6>0
                    self.assertEqual(bool(r[1] & 0x20), has_s23)
                    if has_s23: s23+=1
                    total+=1
        self.assertGreater(total, 0)
        self.assertGreater(s23, 0)

    def test_mesh_flag_bits_observed(self):
        # Observed in scanned samples: bit 0 always set, bit 14 always set, bit 1 set iff 48-byte extra vertex block.
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        total=extra=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    r = mesh.record.raw
                    f=r[1]
                    self.assertTrue(f & 0x1)
                    self.assertTrue(f & 0x4000)
                    vc,vo,v5,v6=r[3],r[4],r[5],r[6]
                    has_extra = vc>0 and v5==vo+vc*32 and v6==vo+vc*48
                    self.assertEqual(bool(f & 0x2), has_extra)
                    if has_extra: extra+=1
                    total+=1
        self.assertGreater(total, 0)

    def test_vertex_base_f0_mostly_zero_observed(self):
        # Observed: base vertex f0 (u32 at offset 0 of 32-byte vertex) is 0 in vast majority of samples.
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:4]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:2]
        if not archives:
            self.skipTest("no archives")
        zero=nonzero=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    for v in mesh.base_vertices[:20]:
                        if v.f0 == 0: zero += 1
                        else: nonzero += 1
        self.assertGreater(zero, nonzero * 10)

    def test_header_flags_observed_mask(self):
        # Observed in normal-magic GMTs: file flags at offset 4 use only bits in 0x06000020.
        import importlib.util, glob, os, struct
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:8]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:4]
        if not archives:
            self.skipTest("no archives")
        checked=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt') or len(data) < 24: continue
                if data[8:24] != bytes.fromhex('c8cfd2d8ced8e6c3d6ded8bebba7bf90'): continue
                flags = struct.unpack_from('<I', data, 4)[0]
                self.assertEqual(flags & ~0x06000020, 0)
                checked += 1
        self.assertGreater(checked, 0)

    def test_mesh_table_first_offset_observed(self):
        # Observed in scanned normal-magic GMTs: mesh table first_record is 528 (0x210).
        import importlib.util, glob, os, struct
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:8]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:4]
        if not archives:
            self.skipTest("no archives")
        checked=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt') or len(data) < 0x174: continue
                if data[8:24] != bytes.fromhex('c8cfd2d8ced8e6c3d6ded8bebba7bf90'): continue
                mc, mf = struct.unpack_from('<II', data, 0x16C)
                self.assertEqual(mf, 528)
                self.assertGreater(mc, 0)
                self.assertLessEqual(mf + mc * 108, len(data))
                checked += 1
        self.assertGreater(checked, 0)

    def test_mesh_index_bounds_observed(self):
        # Observed: mesh index values are within vertex_count in scanned samples; index_count not always multiple of 3.
        import importlib.util, glob, os, struct
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        checked=mod3=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                for mesh in g.meshes:
                    r = mesh.record.raw
                    vc,ic = r[3], r[10]
                    idata = mesh.index_data
                    if ic == 0 or len(idata) < 4 + ic*2: continue
                    idx = struct.unpack_from('<'+str(ic)+'H', idata, 4)
                    if vc > 0:
                        self.assertLess(max(idx), vc)
                    if ic % 3 != 0:
                        mod3 += 1
                    checked += 1
        self.assertGreater(checked, 0)

    def test_mesh_record_field_observations(self):
        # Observed in scanned samples: rec[0,9,12-23]==0; rec[24] in {0,0xFFFFFFFF}; material index in bounds.
        # Rare observed rec[24..26] patterns: (0,0xFFFFFFFF,0) and (0xFFFFFFFF,0,1098907648==18.0f).
        import importlib.util, glob, os
        spec = importlib.util.spec_from_file_location('mas', ROOT.parent / 'rfactortools/rfactortools/mas.py')
        mas = importlib.util.module_from_spec(spec); spec.loader.exec_module(mas)
        archives = sorted(glob.glob(str(ROOT.parent / 'GTR2Steam/GameData/**/*.gtr'), recursive=True))[:6]
        archives += sorted(glob.glob(str(ROOT.parent / 'GTLSteam/GameData/**/*.gtl'), recursive=True))[:3]
        if not archives:
            self.skipTest("no archives")
        checked=0
        for arc in archives:
            for name, data in mas.mas_unpack_to_data(arc):
                if not name.lower().endswith('.gmt'): continue
                g = gmt_format.parse_gmt(name, data=data)
                mcount = len(g.materials)
                for mesh in g.meshes:
                    r = mesh.record.raw
                    self.assertEqual(r[0], 0)
                    self.assertEqual(r[9], 0)
                    for i in range(12, 24):
                        self.assertEqual(r[i], 0)
                    self.assertIn(r[24], (0, 0xFFFFFFFF))
                    if mcount:
                        self.assertLess(r[2], mcount)
                    if (r[24], r[25], r[26]) not in ((0xFFFFFFFF, 0, 0), (0, 0xFFFFFFFF, 0), (0xFFFFFFFF, 0, 1098907648)):
                        self.fail(f"unexpected rec[24..26] pattern {r[24],r[25],r[26]} in {name}")
                    checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
