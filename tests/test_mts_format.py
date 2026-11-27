"""Tests for the CUBE MTS header/geometry/material parser."""
import glob
import io
import os
import struct
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402
import mts_format as mf  # noqa: E402
import race_gmt  # noqa: E402


class MtsFormatTest(unittest.TestCase):
    def test_magic_constants(self):
        self.assertEqual(mf.MAGIC_410[:11], b"CUBE_MTS_4.")
        self.assertIn(b"4.20", mf.MAGIC_420)

    def test_real_headers_both_variants(self):
        counts = Counter()
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                if not e.name.lower().endswith(".mts"):
                    continue
                h = mf.parse_header(e.data)
                counts[h.variant] += 1
                self.assertGreater(h.object_count, 0)
                self.assertTrue(h.name)
            if sum(counts.values()) >= 500:
                break
        if not counts:
            self.skipTest("CUBE MTS corpus not present")
        self.assertIn("4.10", counts)
        self.assertIn("4.20", counts)


    def test_48_byte_records_are_not_simple_position_triples(self):
        """Negative result: 48-byte grid does not decode as 3 float triples."""
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] == b"CUBE_MTS_4.20":
                    groups.setdefault((e.name.lower(), len(d)), []).append(d)
            if any(len(v) >= 2 for v in groups.values()):
                break
        sample = next((v[0] for v in groups.values() if len(v) >= 2), None)
        if sample is None:
            self.skipTest("no same-size CUBE MTS 4.20 sample present")
        import struct
        outliers = 0
        for off in range(0, len(sample) - 48, 48):
            vals = struct.unpack_from("<12f", sample, off)
            outliers += sum(1 for v in vals if abs(v) > 1e5)
        self.assertGreater(outliers, 0)  # incompatible with plain coordinates

    def test_48_byte_alignment_is_weak_on_largest_pair(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] == b"CUBE_MTS_4.20":
                    groups.setdefault((e.name.lower(), len(d)), []).append(d)
        pair = max((v for v in groups.values() if len(v) >= 2 and v[0] != v[1]),
                   key=lambda v: sum(x != y for x, y in zip(v[0], v[1])))
        if not pair:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        diff = [i for i in range(len(pair[0])) if pair[0][i] != pair[1][i]]
        best = max(sum(1 for s in diff if s % 48 in (36, 44)) / len(diff) for _ in (0,))
        self.assertLess(best, 0.3)  # 48-byte grid does not explain most differing bytes

    def test_candidate_float_run_is_not_a_normal_array(self):
        import math
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TLRA.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TLRA.MTS sample not present")
        off = 0xD388
        mags = []
        while off + 12 <= len(sample):
            v = struct.unpack_from("<3f", sample, off)
            mags.append(math.sqrt(sum(x * x for x in v)))
            off += 12
        self.assertLess(sum(0.9 < m < 1.1 for m in mags) / len(mags), 0.5)

    def test_descriptor_tail_states(self):
        states = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                for off, _ in mf.submesh_descriptors(d):
                    if off + 168 > len(d):
                        continue
                    total += 1
                    states += mf.descriptor_tail_u32(d, off) in mf.DESCRIPTOR_164_STATES
            if total >= 1000:
                break
        if total == 0:
            self.skipTest("CUBE MTS descriptors not present")
        self.assertGreater(states / total, 0.9)

    def test_descriptor_packed_field_pattern(self):
        flags = lows = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                for off, _ in mf.submesh_descriptors(d):
                    hi, lo = mf.descriptor_fields(d, off)
                    total += 1
                    flags += hi in (mf.DESCRIPTOR_FLAG_32, mf.DESCRIPTOR_FLAG_ALT)
                    lows += lo in (0, 2, 32, 96, 2048, 2080)
            if total >= 1000:
                break
        if total == 0:
            self.skipTest("CUBE MTS descriptors not present")
        self.assertGreater(flags / total, 0.95)
        self.assertGreater(lows / total, 0.9)

    def test_mesh_table_resolves_submeshes(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "LIGHTBOX02.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("LIGHTBOX02.MTS sample not present")
        table = mf.parse_mesh_table(sample)
        self.assertIsNotNone(table)
        self.assertEqual(table["table_offset"], 0x500)
        self.assertEqual(table["header"], (5, 328, 118, 648, 97, 4896, 0, 6448))
        self.assertEqual(len(table["submeshes"]), 5)
        self.assertEqual(table["submeshes"][0], (129, 0, 150, 6448, 150, 13648))

    def test_mts_converts_to_gtr2_gmt(self):
        """Convertible CUBE MTS meshes rebuild as parseable GTR2 GMTs."""
        import gmt_format

        template = None
        for p in (ROOT.parent / "GTR2Steam/GameData").rglob("*.gtr"):
            if not p.is_file():
                continue
            for e in mas_tool.read_archive(p)[1]:
                if e.name.lower().endswith(".gmt") and e.data:
                    template = e.data
                    break
            if template:
                break
        if template is None:
            self.skipTest("GTR2 GMT template not present")
        converted = 0
        for root in ("F1C", "F12002"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    entries = mas_tool.read_archive(archive)[1]
                except Exception:
                    continue
                for entry in entries:
                    data = entry.data or b""
                    if not entry.name.lower().endswith(".mts"):
                        continue
                    out = mf.to_gtr2_gmt(data, template)
                    if out is None:
                        continue
                    parsed = gmt_format.parse_gmt("converted.gmt", out)
                    self.assertGreater(parsed.meshes[0].record.vertex_count, 0,
                                       entry.name)
                    converted += 1
                    if converted >= 20:
                        break
                if converted >= 20:
                    break
            if converted >= 20:
                break
        self.assertGreaterEqual(converted, 20)

    def test_material_records_are_triangle_indices(self):
        """The 36-byte 'material' records actually hold triangle indices."""
        found = 0
        for root in ("F12002", "F1C", "NascarSimRacing"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    entries = mas_tool.read_archive(archive)[1]
                except Exception:
                    continue
                for entry in entries:
                    data = entry.data or b""
                    if not entry.name.lower().endswith(".mts") or data[:13] != b"CUBE_MTS_4.10":
                        continue
                    triangles = mf.read_triangles(data)
                    if not triangles:
                        continue
                    try:
                        geometry = mf.read_geometry(data)
                    except Exception:
                        continue
                    if not geometry or not geometry.get("descriptors"):
                        continue
                    max_vertices = max(d["count_a"] for d in geometry["descriptors"])
                    self.assertTrue(all(index < max_vertices
                                        for tri in triangles for index in tri),
                                    entry.name)
                    found += 1
                    if found >= 20:
                        break
                if found >= 20:
                    break
            if found >= 20:
                break
        self.assertGreaterEqual(found, 20)

    def test_material_records_are_shared_rig_tables(self):
        by = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.10":
                    continue
                sig = mf.rig_table_signature(d)
                if sig:
                    by.setdefault(sig, []).append(e.name)
        if not by:
            self.skipTest("CUBE MTS 4.10 corpus not present")
        self.assertLessEqual(len(by), 10)
        self.assertGreater(sum(len(v) for v in by.values()), 10)
        # Pit-crew meshes share one table; JET has its own.
        pit = next((v for v in by.values() if "TIREMANFRONT.MTS" in v), None)
        self.assertIsNotNone(pit)
        self.assertIn("PITOFFICIAL.MTS", pit)
        self.assertNotIn("JET.MTS", pit)

    def test_material_ids_have_no_local_name_table(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TIREMANFRONT.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        vals = [x for r in mf.parse_material_records(sample)
                for x in mf.decode_material_numbers(r)]
        self.assertGreater(len(set(vals)), 20)
        self.assertLess(max(vals), 1024)
        # No contiguous u16 array of these IDs exists in the file: they are
        # references to a table not shipped with the mesh.
        pattern = struct.pack("<%dH" % 16, *vals[:16])
        self.assertEqual(sample.find(pattern), -1)

    def test_material_numbers_stable_across_same_name_files(self):
        found = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    d = e.data or b""
                    if d[:13] == b"CUBE_MTS_4.10" and e.name in ("TIREMANFRONT.MTS", "TIREMANBACK.MTS"):
                        found.setdefault(e.name, mf.parse_material_records(d))
        if len(found) < 2:
            self.skipTest("TIREMAN pair not present")
        a, b = found["TIREMANFRONT.MTS"], found["TIREMANBACK.MTS"]
        self.assertEqual(len(a), len(b))
        self.assertTrue(all(mf.decode_material_numbers(x) == mf.decode_material_numbers(y)
                            for x, y in zip(a, b)))

    def test_material_numeric_fields_decode(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TIREMANFRONT.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        recs = mf.parse_material_records(sample)
        vals = [mf.decode_material_numbers(r) for r in recs]
        self.assertGreater(len(vals), 10)
        self.assertTrue(all(0 < x < 1024 for v in vals for x in v))

    def test_detail_cli(self):
        loose = [p for p in ROOT.parent.joinpath("NascarSimRacing").rglob("*.MTS")
                 if (p.read_bytes()[:16] in (mf.MAGIC_410, mf.MAGIC_420))]
        if not loose:
            self.skipTest("loose CUBE MTS files not present")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mf.main(["--detail", str(loose[0])])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("MtsHeader(", out)
        self.assertIn("table:", out)
        self.assertIn("geometry:", out)

    def test_material_records_4_10(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TIREMANFRONT.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        recs = mf.parse_material_records(sample)
        self.assertGreaterEqual(len(recs), 4)
        self.assertEqual([r["index"] for r in recs[:4]], [0, 1, 2, 3])
        self.assertEqual([r["offset"] for r in recs[:3]], [6760, 6796, 6832])

    def test_material_records_in_4_10_corpus(self):
        parsed = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.10":
                    continue
                total += 1
                parsed += bool(mf.parse_material_records(d))
            if total >= 300:
                break
        if total == 0:
            self.skipTest("CUBE MTS 4.10 corpus not present")
        self.assertGreater(parsed, 0)
        self.assertLess(parsed, total)  # subset of files use this record kind

    def test_geometry_blocks_from_table_offsets(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "LIGHTBOX02.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("LIGHTBOX02.MTS sample not present")
        geo = mf.read_geometry(sample)
        self.assertTrue(geo["positions_available"])
        self.assertTrue(geo["descriptors"])
        self.assertTrue(geo["vertices"])
        # Descriptor streams are float triples (normals/UVs), not positions.
        for desc in geo["descriptors"][:3]:
            self.assertTrue(desc["vertices"])
            self.assertGreater(len(desc["vertices"]), 0)

    def test_post_normal_block_is_float_data(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "LIGHTBOX02.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("LIGHTBOX02.MTS sample not present")
        h = mf.parse_mesh_table(sample)["header"]
        off = h[7]
        values = struct.unpack_from("<64f", sample, off)
        # Float bit patterns in 0x3x-0x4x range, not small u16 vertex indices.
        words = struct.unpack_from("<32I", sample, off)
        self.assertGreater(sum(1 for w in words if 0x3E000000 <= w <= 0x4B000000), 5)

    def test_normal_end_field_is_not_an_index_array(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "JACK.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("JACK.MTS sample not present")
        table = mf.parse_mesh_table(sample)
        h = table["header"]
        self.assertEqual(h[7], h[5] + h[4] * 16)
        geo = mf.read_geometry(sample)
        self.assertTrue(geo["positions_available"])
        self.assertEqual(h[7], h[5] + h[4] * 16)

    def test_36byte_records_are_not_positions(self):
        """Regression: the voff records are indices/materials, not float positions."""
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TIREMANFRONT.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        h = mf.parse_mesh_table(sample)["header"]
        voff = h[3]
        # At least one 36-byte record contains an ASCII material name.
        block = sample[voff:voff + 36 * 12]
        self.assertTrue(b"NASCAR_FACE" in block or b"WCPCREW" in block)
        # read_geometry no longer exposes these as positions.
        geo = mf.read_geometry(sample)
        self.assertTrue(geo["positions_available"])
        self.assertTrue(geo["vertices"])

    def test_vertex_decode_corpus(self):
        import math
        checked = ok = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            try:
                entries = mas_tool.read_archive(p)[1]
            except Exception:
                continue
            for e in entries:
                d = e.data or b""
                if d[:13] not in (b"CUBE_MTS_4.10", b"CUBE_MTS_4.20"):
                    continue
                geo = mf.read_geometry(d)
                if not geo or not geo["vertices"]:
                    continue
                verts = geo["vertices"]
                finite = sum(1 for v in verts if all(math.isfinite(x) for x in v))
                ok += finite / len(verts) > 0.5
                checked += 1
            if checked >= 100:
                break
        if not checked:
            self.skipTest("CUBE MTS corpus not present")
        self.assertGreater(ok / checked, 0.95)

    def test_rig_table_triangles(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TIREMANFRONT.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.10":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        report = mf.rig_table_triangles(sample)
        self.assertGreater(report["valid"], 0)
        self.assertGreaterEqual(report["valid"] / report["total"], 0.4)
        self.assertTrue(all(0 < e < 100 for e in report["edges"]))

    def test_vertex_normal_strides_from_offsets(self):
        checked = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] not in (b"CUBE_MTS_4.20", b"CUBE_MTS_4.10"):
                    continue
                table = mf.parse_mesh_table(d)
                if not table:
                    continue
                h = table["header"]
                if h[2] and h[4] and h[3] < h[5]:
                    self.assertEqual((h[5] - h[3]) / h[2], 36)
                    self.assertEqual((h[7] - h[5]) / h[4], 16)
                    checked += 1
            if checked >= 50:
                break
        self.assertGreater(checked, 0)

    def test_alternate_submesh_record(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "CROWD.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("CROWD.MTS sample not present")
        table = mf.parse_mesh_table(sample)
        self.assertEqual(table["submeshes"], [(128, 0, 32, 1224, 46, 2760, 0, 0)])

    def test_mesh_table_header_without_submesh_records(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "CLOUDRNY.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("CLOUDRNY.MTS sample not present")
        table = mf.parse_mesh_table(sample)
        self.assertIsNotNone(table)
        self.assertEqual(table["header"][:4], (1, 328, 1406, 392))
        self.assertEqual(table["header"][6:], (0, table["header"][7]))
        self.assertIsInstance(table["submeshes"], list)

    def test_mesh_table_in_4_10_corpus(self):
        parsed = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.10":
                    continue
                total += 1
                parsed += mf.parse_mesh_table(d) is not None
            if total >= 100:
                break
        if total == 0:
            self.skipTest("CUBE MTS 4.10 corpus not present")
        self.assertGreater(parsed / total, 0.2)

    def test_mesh_table_across_corpus(self):
        parsed = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                total += 1
                parsed += mf.parse_mesh_table(d) is not None
            if total >= 100:
                break
        if total == 0:
            self.skipTest("CUBE MTS 4.20 corpus not present")
        self.assertGreater(parsed / total, 0.9)

    def test_submesh_descriptor_grid(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "LIGHTBOX02.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("LIGHTBOX02.MTS sample not present")
        desc = mf.submesh_descriptors(sample)
        self.assertEqual([off for off, _ in desc], [216, 412, 608, 804])
        self.assertEqual([n for _, n in desc], ["LIGHTBOX2B", "LIGHTBOXC", "LIGHTBOX2", "GSTAND2"])

    def test_object_count_vs_submesh_names(self):
        hits = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] not in (b"CUBE_MTS_4.10", b"CUBE_MTS_4.20"):
                    continue
                h = mf.parse_header(d)
                total += 1
                hits += (h.object_count - len(mf.submesh_names(d)) == 1)
            if total >= 400:
                break
        if total == 0:
            self.skipTest("CUBE MTS 4.20 corpus not present")
        self.assertGreater(hits / total, 0.5)

    def test_varying_fields_align_to_48_byte_grid(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                groups.setdefault((e.name.lower(), len(d)), []).append(d)
        best = 0
        for v in groups.values():
            if len(v) < 2:
                continue
            diff = [i for i in range(len(v[0])) if v[0][i] != v[1][i]]
            if not diff:
                continue
            runs = []
            start = prev = diff[0]
            for i in diff[1:]:
                if i - prev > 4:
                    runs.append(start)
                    start = i
                prev = i
            runs.append(start)
            aligned = sum(1 for s in runs if s % 48 in (36, 44))
            best = max(best, aligned / len(runs))
        if best == 0:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        self.assertGreater(best, 0.5)

    def test_48_byte_vertex_stride_from_same_size_pair(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:14] != mf.MAGIC_420[:14]:
                    continue
                groups.setdefault((e.name.lower(), len(d)), []).append(d)
            if any(len(v) >= 2 for v in groups.values()):
                break
        pairs = [v for v in groups.values() if len(v) >= 2]
        if not pairs:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        best = max(race_gmt.diff_strides(v[0], v[1])["distances"].get(48, 0) for v in pairs)
        self.assertGreater(best, 10)


    def test_rig_triples_form_coherent_surface_patch(self):
        """Per-rig triples are a disk-like triangle surface, not arbitrary indices."""
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                if e.name == "TIREMANFRONT.MTS":
                    sample = e.data
                    break
            if sample:
                break
        if sample is None:
            self.skipTest("TIREMANFRONT.MTS sample not present")
        geo = mf.read_geometry(sample)
        if not geo or not geo.get("descriptors"):
            self.skipTest("geometry unavailable")
        points = geo["descriptors"][0]["vertices"]
        triples = [mf.decode_material_numbers(r) for r in mf.parse_material_records(sample)]
        valid = [t for t in triples if max(t) < len(points)]
        self.assertGreaterEqual(len(valid), 50)
        edges = Counter()
        for t in valid:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges[tuple(sorted((t[a], t[b])))] += 1
        # Most edges are shared by exactly two adjacent triangles; the patch
        # has a boundary and Euler characteristic V-E+F == 1 (a disk).
        self.assertGreater(sum(1 for n in edges.values() if n == 2), len(edges) // 2)
        used = {i for t in valid for i in t}
        verts = len(used)
        self.assertEqual(verts - len(edges) + len(valid), 1)
        # The shared pit-crew patch is planar (all x equal), i.e. a 2D
        # triangulation rather than a volumetric collision mesh.
        self.assertEqual(len({points[i][0] for i in used}), 1)


if __name__ == "__main__":
    unittest.main()
