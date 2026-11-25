"""Deep corpus checks: full-tier only (slow, multi-game archive scans)."""
import glob
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collections
import re
import anm_format  # noqa: E402
import simbin_text_tool as stt  # noqa: E402
import mas_tool  # noqa: E402
import validate_materials  # noqa: E402


def _anm_samples(root, limit=None):
    for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
        if not p.lower().endswith((".mas", ".exe", ".gtr", ".gtl", ".bmw")):
            continue
        try:
            _, entries = mas_tool.read_archive(p)
        except Exception:
            continue
        for e in entries:
            if e.name.lower().endswith(".anm") and e.data:
                yield e.name, e.data
                if limit is not None:
                    limit -= 1
                    if limit <= 0:
                        return


class CorpusDeepTest(unittest.TestCase):
    def test_opaque_gsc_flags(self):
        """Opaque GSC GMTs carry one of three flags words at +4."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        import time
        n = known = 0
        started = time.time()
        arcs = []
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            arcs += glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                              recursive=True)
        arcs.sort(key=lambda p: (ROOT.parent / p).stat().st_size)
        for arc in arcs:
            try:
                _, entries = mas_tool.read_archive(arc, read_data=False)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt"):
                    continue
                try:
                    d = isi_crypt.decrypt_bytes(mas_tool.read_member(arc, e))
                except Exception:
                    continue
                if gmt_semantic.is_gsc_decodable(d):
                    continue
                flags = gmt_semantic.opaque_gsc_flags(d)
                n += 1
                known += flags in gmt_semantic.GSC_OPAQUE_FLAGS
                if n >= 400:
                    break
            if n >= 400 or time.time() - started > 240:
                break
        self.assertGreater(n, 300)
        self.assertGreaterEqual(known / n, 0.95)

    def test_gsc_geometry_invariants(self):
        """GSC geometry: UV count == vertex count, face indices in range."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        subs = faces = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:3]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    if not gmt_semantic.is_gsc_decodable(d):
                        continue
                    g = gmt_semantic.read_gsc_geometry(d)
                    for sub in g["submeshes"]:
                        vc = len(sub["positions"])
                        self.assertEqual(len(sub["uvs"]), vc, e.name)
                        if sub["faces"]:
                            self.assertTrue(all(0 <= i < vc for f in sub["faces"] for i in f),
                                            e.name)
                            faces += 1
                        subs += 1
        self.assertGreater(subs, 15)
        self.assertGreater(faces, 10)

    def test_gdb_terrain_data_references(self):
        """GDB TerrainDataFile refs resolve; only rF1Vanilla uses them."""
        import glob
        import mas_tool
        import simbin_text_tool as stt_local
        refs = resolved = 0
        for root in ("RF1Vanilla", "F1C", "F12002", "NT2003"):
            base = ROOT.parent / root
            names: set[str] = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if Path(p).is_file() and p.lower().endswith(".tdf"):
                    names.add(Path(p).name.lower())
                if p.lower().endswith((".mas", ".MAS")):
                    try:
                        _, entries = mas_tool.read_archive(p, read_data=False)
                    except Exception:
                        continue
                    for e in entries:
                        if e.name.lower().endswith(".tdf"):
                            names.add(Path(e.name).name.lower())
            for p in glob.glob(str(base / "**" / "*.gdb"), recursive=True):
                if not Path(p).is_file():
                    continue
                for ref in stt_local.parse_gdb_terrain_refs(stt_local.read_text(p)):
                    refs += 1
                    resolved += ref in names
        self.assertEqual(refs, 26)
        self.assertEqual(resolved, refs)

    def test_scr_move_parent_references(self):
        """SCR Move/Parent actor references resolve locally."""
        import glob
        import os
        import simbin_text_tool as stt_local
        actors_ok = parents_ok = actors = parents = anims = 0
        for root in ("NT2003", "NascarSimRacing", "F12002", "RF1Vanilla"):
            base = ROOT.parent / root
            members: set[str] = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if p.lower().endswith((".mas", ".MAS")):
                    try:
                        _, entries = mas_tool.read_archive(p, read_data=False)
                    except Exception:
                        continue
                    for e in entries:
                        members.add(Path(e.name).stem.lower())
            for p in glob.glob(str(base / "**" / "*.scr"), recursive=True):
                if not Path(p).is_file():
                    continue
                scene = stt_local.parse_scr(stt_local.read_text(p))
                names = {a.name.lower() for a in scene.actors}
                for a in scene.actors:
                    if a.parent:
                        parents += 1
                        parents_ok += (a.parent.lower() in names
                                       or a.parent.lower() in ("world", "none"))
                    if a.move:
                        actor, anim = stt_local.parse_scr_move(a.move)
                        if actor:
                            actors += 1
                            actors_ok += actor.lower() in names or actor.lower() in members
                        anims += anim is not None
        self.assertGreater(actors, 1100)
        self.assertEqual(actors_ok, actors)
        self.assertGreater(parents, 1100)
        self.assertEqual(parents_ok, parents)
        self.assertGreater(anims, 1100)

    def test_rf1_gdb_filter_format_differs(self):
        """rF1-era GDBs use Filter Properties, not SimBin class filters."""
        import glob
        import re
        import simbin_text_tool as stt_local
        gdbs = tokens = resolved = 0
        for root in ("RF1Vanilla", "F1C", "F12002", "NT2003"):
            base = ROOT.parent / root
            car_tags: set[str] = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if Path(p).is_file() and p.lower().endswith((".veh", ".hdv")):
                    car_tags.update(stt_local.car_class_tags(stt_local.read_text(p)))
            for p in glob.glob(str(base / "**" / "*.gdb"), recursive=True):
                if not Path(p).is_file():
                    continue
                text = stt_local.read_text(p)
                self.assertNotIn("SpecialClasses", text, p)
                self.assertNotIn("Game Filter", text, p)
                gdbs += 1
                for m in re.finditer(r"(?mi)^[ \t]*Filter Properties[ \t]*=[ \t]*(.*)$", text):
                    for tag in m.group(1).split():
                        tokens += 1
                        resolved += tag.strip().lower() in car_tags
        self.assertGreater(gdbs, 70)
        self.assertGreater(tokens, 100)
        self.assertLess(resolved / tokens, 0.01)  # documented negative

    def test_anm_bone_names_not_mesh_names(self):
        """ANM bone names are internal nodes, not mesh member names."""
        import glob
        import anm_format
        import mas_tool
        bones = resolved = anms = 0
        for root in ("SportsCarGtUsa", "RF1Vanilla", "F1C", "F12002", "NT2003"):
            meshes: set[str] = set()
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not p.lower().endswith((".mas", ".gtr", ".gtl")):
                    continue
                try:
                    _, entries = mas_tool.read_archive(p)
                except Exception:
                    continue
                for e in entries:
                    stem = Path(e.name).stem.lower()
                    if e.name.lower().endswith((".gmt", ".vrl", ".mts")):
                        meshes.add(stem)
                    if e.name.lower().endswith(".anm") and e.data:
                        anms += 1
                        try:
                            anim = anm_format.read_anm(e.data)
                        except Exception:
                            continue
                        for bone in anim.bones:
                            if not bone.name:
                                continue
                            bones += 1
                            resolved += bone.name.lower() in meshes
        self.assertGreater(anms, 800)
        self.assertGreater(bones, 12000)
        self.assertLess(resolved, 10)

    def test_gdb_special_class_resolution(self):
        """GDB SpecialClasses keys resolve against local .car class tags."""
        import glob
        import media_tool
        import simbin_text_tool as stt_local
        checked = resolved = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            tags: set[str] = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith(".car"):
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                tags.update(stt_local.car_class_tags(text))
            for p in glob.glob(str(base / "**" / "*.gdb"), recursive=True):
                if not Path(p).is_file():
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                for key in stt_local.parse_gdb_class_blocks(text).get("SpecialClasses", []):
                    checked += 1
                    resolved += key in tags
        self.assertGreater(checked, 110)
        self.assertGreater(resolved / checked, 0.95)

    def test_trk_cam_names_are_separate_namespaces(self):
        """TRK View/Instance names never match .cam camera names."""
        import glob
        import media_tool
        import simbin_text_tool as stt_local
        views = instances = matches = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            for p in glob.glob(str(base / "**" / "*.trk"), recursive=True):
                if not Path(p).is_file():
                    continue
                cam = Path(p).with_suffix(".cam")
                if not cam.is_file():
                    continue
                names = {c.name.lower() for c in stt_local.parse_cam(
                    media_tool.decrypt_jca_text(cam.read_bytes()).decode("latin-1")).cameras}
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                for key in ("View", "Instance"):
                    for m in re.finditer(r"(?mi)^[ \t]*" + key + r"[ \t]*=\s*([^\r\n]+)", text):
                        value = m.group(1).strip().strip('"').lower()
                        if not value:
                            continue
                        if key == "View":
                            views += 1
                        else:
                            instances += 1
                        matches += value in names
        self.assertGreater(views, 250)
        self.assertGreater(instances, 100000)
        self.assertEqual(matches, 0)

    def test_gdb_filter_class_resolution(self):
        """GDB filter class tags resolve against local .car declarations."""
        import glob
        import media_tool
        import simbin_text_tool as stt_local
        checked = resolved = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            tags: set[str] = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith(".car"):
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                tags.update(stt_local.car_class_tags(text))
            for p in glob.glob(str(base / "**" / "*.gdb"), recursive=True):
                if not Path(p).is_file():
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                for tag in stt_local.parse_gdb_filter_tags(text):
                    checked += 1
                    resolved += tag in tags
        self.assertGreater(checked, 160)
        self.assertGreater(resolved / checked, 0.97)

    def test_trk_reference_resolution(self):
        """TRK MASFile/MeshFile references resolve to local content."""
        import glob
        import media_tool
        import mas_tool
        import simbin_text_tool as stt_local
        mas_refs = mas_ok = mesh_refs = mesh_ok = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            available = set()
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if not Path(p).is_file():
                    continue
                available.add(Path(p).name.lower())
                if p.lower().endswith((".gtr", ".gtl", ".mas")):
                    try:
                        _, entries = mas_tool.read_archive(p, read_data=False)
                    except Exception:
                        continue
                    for e in entries:
                        available.add(Path(e.name).name.lower())
            for p in glob.glob(str(base / "**" / "*.trk"), recursive=True):
                if not Path(p).is_file():
                    continue
                refs = stt_local.parse_trk_refs(media_tool.decrypt_jca_text(Path(p).read_bytes()))
                for name in refs["mas"]:
                    mas_refs += 1
                    mas_ok += name in available
                for name in refs["mesh"]:
                    mesh_refs += 1
                    mesh_ok += name in available
        self.assertGreater(mas_refs, 250)
        self.assertEqual(mas_ok, mas_refs)
        self.assertGreater(mesh_refs, 100000)
        self.assertGreater(mesh_ok / mesh_refs, 0.999)

    def test_scgt_text_ani_corpus(self):
        """The SCGT text .ani member parses into valid animation rules."""
        import glob
        import simbin_text_tool as stt_local
        n = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True):
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".ani") or not e.data:
                    continue
                rules = stt_local.parse_ani_text(e.data)
                self.assertEqual(stt_local.validate_ani_text(rules), [], e.name)
                self.assertEqual(len(rules), 12)
                n += 1
        self.assertEqual(n, 1)

    def test_scgt_prt_corpus(self):
        """All SCGT .prt members are well-formed CRLF text scenes."""
        import glob
        import mas_tool
        import simbin_text_tool as stt_local
        n = objects = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True):
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".prt") or not e.data:
                    continue
                self.assertEqual(stt_local.validate_prt(e.data), [], e.name)
                objects += len(re.findall(r"(?mi)^\s*ObjFile\s*=",
                                          e.data.decode("latin-1")))
                n += 1
        self.assertEqual(n, 5)
        self.assertGreater(objects, 900)

    def test_scgt_vrl_corpus(self):
        """SCGT .vrl members: 60-byte zero header and valid first offset."""
        import glob
        import mas_tool
        import simbin_text_tool as stt_local
        n = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True):
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".vrl") or not e.data:
                    continue
                self.assertEqual(stt_local.validate_vrl(e.data), [], f"{arc}/{e.name}")
                v = stt_local.read_vrl(e.data)
                self.assertIsNotNone(v, f"{arc}/{e.name}")
                self.assertEqual(len(v["vertices"]), v["vertex_count"])
                self.assertTrue(all(all(abs(c) < 1e6 for c in pos[:3])
                                    for pos in v["vertices"]))
                self.assertEqual(len(v["indices"]), v["index_count"])
                self.assertTrue(all(i < v["vertex_count"] for i in v["indices"]))
                self.assertEqual(len(v["coords"]), v["index_count"])
                self.assertEqual(len(v["vertex_map"]), v["vertex_count"])
                self.assertEqual(v["vertex_map"][0], 0)
                self.assertLess(max(v["vertex_map"]), v["index_count"])
                self.assertLess(max(v["group_ids"]), 256)
                self.assertEqual(v["constant_flag"], 15)
                n += 1
            if n >= 1200:
                break
        self.assertGreater(n, 1000)

    def test_gmt_f0_is_first_vertex_marker(self):
        """A nonzero f0 occurs only on vertex 0 of a mesh."""
        import glob
        import gmt_format
        import mas_tool
        meshes = marked = 0
        for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                           recursive=True) + \
                glob.glob(str(ROOT.parent / "GTLSteam" / "**" / "*.gtl"),
                          recursive=True):
            try:
                _, entries = mas_tool.read_archive(p)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                try:
                    g = gmt_format.parse_gmt(e.name, data=e.data)
                except Exception:
                    continue
                for m in g.meshes:
                    if not m.base_vertices:
                        continue
                    meshes += 1
                    nonzero = [i for i, v in enumerate(m.base_vertices) if v.f0]
                    if nonzero:
                        marked += 1
                        self.assertEqual(nonzero, [0], e.name)
                        self.assertEqual(gmt_format.mesh_marker(m),
                                         m.base_vertices[0].f0, e.name)
                if meshes >= 12000:
                    break
            if meshes >= 12000:
                break
        self.assertGreater(marked, 1000)

    def test_gmt_vertex_f7_is_packed_color(self):
        """Base-vertex f7 holds packed grayscale colors, not packed UVs."""
        import glob
        import gmt_format
        import mas_tool
        meshes = colors = 0
        for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                           recursive=True) + \
                glob.glob(str(ROOT.parent / "GTLSteam" / "**" / "*.gtl"),
                          recursive=True):
            try:
                _, entries = mas_tool.read_archive(p)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                try:
                    g = gmt_format.parse_gmt(e.name, data=e.data)
                except Exception:
                    continue
                for m in g.meshes:
                    vs = m.base_vertices
                    if len(vs) < 100 or len({v.f7 for v in vs}) <= 10:
                        continue
                    meshes += 1
                    for v in vs:
                        r, g0, b, a = gmt_format.unpack_vertex_color(v.f7)
                        self.assertEqual(a, 255, e.name)
                        self.assertEqual((r, g0, b), (r, r, r), e.name)
                        colors += 1
                if meshes >= 40:
                    break
            if meshes >= 40:
                break
        self.assertGreater(meshes, 30)
        self.assertGreater(colors, 10000)

    def test_batch_convert_archives(self):
        """Batch conversion writes only reparseable, material-clean GMTs."""
        import glob
        import tempfile
        import batch_convert
        import gmt_format
        import validate_materials
        template_path = None
        for q in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gmt"),
                           recursive=True)[:500]:
            try:
                if gmt_format.parse_gmt(q).meshes:
                    template_path = Path(q)
                    break
            except Exception:
                continue
        self.assertIsNotNone(template_path)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            report = batch_convert.batch_convert(template_path.read_bytes(), out, limit=8)
            self.assertEqual(report["vrl_scanned"], 8)
            self.assertEqual(report["gtr1_scanned"], 8)
            files = list(out.rglob("*.gmt"))
            self.assertGreaterEqual(len(files), 8)
            for f in files:
                data = f.read_bytes()
                self.assertGreater(len(gmt_format.parse_gmt(f).meshes), 0, f.name)
                self.assertEqual(validate_materials.check_gmt(data, f.name), [], f.name)

    def test_gtr1_descriptorless_fallback(self):
        """Descriptor-less GTR1 shadow meshes convert via object-mesh streams."""
        import glob
        import gmt_format
        import gtr1_to_gmt
        import mas_tool
        import vrl_to_gmt
        template = None
        for q in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gmt"),
                           recursive=True)[:500]:
            try:
                if gmt_format.parse_gmt(q).meshes:
                    template = Path(q).read_bytes()
                    break
            except Exception:
                continue
        self.assertIsNotNone(template)
        found = 0
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                             recursive=True)[:6]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if e.name != "ARMCOSHAD01.GMT" or not e.data:
                    continue
                geometry = gtr1_to_gmt.geometry_from_gtr1(e.data)
                self.assertIsNotNone(geometry)
                positions, normals, triangles = geometry
                self.assertGreater(len(positions), 20)
                self.assertGreater(len(triangles), 20)
                data = gtr1_to_gmt.gtr1_to_gmt(e.data, template)
                self.assertEqual(vrl_to_gmt.verify_gmt_geometry(
                    data, positions, triangles, normals), [], e.name)
                found += 1
        self.assertEqual(found, 1)

    def test_gtr1_to_gtr2_gmt_roundtrip(self):
        """Converted GTR1 third-magic GMTs reparse as valid GTR2 GMTs."""
        import glob
        import gmt_format
        import gtr1_to_gmt
        import mas_tool
        import vrl_to_gmt
        template = None
        for q in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gmt"),
                           recursive=True)[:500]:
            try:
                if gmt_format.parse_gmt(q).meshes:
                    template = Path(q).read_bytes()
                    break
            except Exception:
                continue
        self.assertIsNotNone(template)
        n = 0
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                             recursive=True)[:12]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                geometry = gtr1_to_gmt.geometry_from_gtr1(e.data)
                if not geometry:
                    continue
                positions, normals, triangles = geometry
                data = gtr1_to_gmt.gtr1_to_gmt(e.data, template)
                self.assertEqual(vrl_to_gmt.verify_gmt_geometry(
                    data, positions, triangles, normals), [], e.name)
                self.assertEqual(validate_materials.check_gmt(data, e.name), [], e.name)
                n += 1
                if n >= 25:
                    break
            if n >= 25:
                break
        self.assertGreater(n, 20)

    def test_vrl_to_gtr2_gmt_roundtrip(self):
        """Converted VRL meshes reparse as valid GTR2 GMTs."""
        import glob
        import gmt_format
        import mas_tool
        import simbin_text_tool as stt
        import vrl_to_gmt
        template = None
        for q in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gmt"),
                           recursive=True)[:500]:
            try:
                if gmt_format.parse_gmt(q).meshes:
                    template = Path(q).read_bytes()
                    break
            except Exception:
                continue
        self.assertIsNotNone(template)
        n = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True)[:10]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".vrl") or not e.data:
                    continue
                vrl = stt.read_vrl(e.data)
                if not vrl or vrl["vertex_count"] == 0:
                    continue
                data = vrl_to_gmt.vrl_to_gmt(vrl, template)
                self.assertEqual(vrl_to_gmt.verify_gmt(data, vrl), [], e.name)
                self.assertEqual(validate_materials.check_gmt(data, e.name), [], e.name)
                n += 1
                if n >= 25:
                    break
            if n >= 25:
                break
        self.assertGreater(n, 20)

    def test_scgt_vrl_uv_quad_score(self):
        """VRL coordinates show quad-corner UV reuse above random baseline."""
        import glob
        import random
        import simbin_text_tool as stt_local
        random.seed(7)
        scores = baseline = 0
        n = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True):
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".vrl") or not e.data:
                    continue
                v = stt_local.read_vrl(e.data)
                if not v:
                    continue
                s = stt_local.vrl_uv_quad_score(v)
                if s is None:
                    continue
                scores += s
                uv = list(v["coords"])
                random.shuffle(uv)
                shuffled = dict(v, coords=uv)
                baseline += stt_local.vrl_uv_quad_score(shuffled)
                n += 1
            if n >= 500:
                break
        self.assertGreater(n, 300)
        self.assertGreater(scores / n, 0.6)
        self.assertGreater(scores / n - baseline / n, 0.2)

    def test_gtr1_triangle_coherence(self):
        """GTR1 fields 1-3 are more spatially coherent than fields 9-11."""
        import glob
        import statistics
        import gmt_semantic
        import mas_tool
        a = []
        b = []
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                             recursive=True)[:15]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                geom = gmt_semantic.read_gtr1_geometry(e.data)
                if not geom:
                    continue
                for item in geom:
                    x = gmt_semantic.gtr1_triangle_coherence(item, (1, 2, 3))
                    y = gmt_semantic.gtr1_triangle_coherence(item, (9, 10, 11))
                    if x is not None and y is not None:
                        a.append(x)
                        b.append(y)
                if len(a) >= 300:
                    break
            if len(a) >= 300:
                break
        self.assertGreater(len(a), 250)
        self.assertLess(statistics.median(a), 0.6)
        self.assertLess(statistics.median(a), statistics.median(b) - 0.2)

    def test_gtr1_descriptor_geometry(self):
        """GTR1 third-magic descriptor vertices/indices decode cleanly."""
        import glob
        import gmt_semantic
        import mas_tool
        files = descs = 0
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                             recursive=True)[:12]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                geom = gmt_semantic.read_gtr1_geometry(e.data)
                if not geom:
                    continue
                files += 1
                for item in geom:
                    self.assertEqual(gmt_semantic.validate_gtr1_geometry(item), [], e.name)
                    self.assertEqual(len(item["vertices"]), item["v_count"])
                    self.assertEqual(len(item["indices"]), item["i_count"])
                    self.assertEqual(len(item["normals"]), item["v_count"])
                    descs += 1
                if files >= 50:
                    break
            if files >= 50:
                break
        self.assertGreater(files, 30)
        self.assertGreater(descs, 80)

    def test_gsc_geometry_decoder(self):
        """read_gsc_geometry decodes real geometry with quality flags."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        n = good = flagged = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:3]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    if not gmt_semantic.is_gsc_decodable(d):
                        continue
                    g = gmt_semantic.read_gsc_geometry(d)
                    self.assertIsNotNone(g)
                    self.assertIn("quality", g)
                    if g["vertex_count"] == 0:
                        continue  # near-magic present but no decodable submeshes
                    if g["quality"]["plausible_positions"]:
                        good += 1
                    else:
                        flagged += 1
                    n += 1
                    if n >= 30:
                        break
                if n >= 30:
                    break
            if n >= 30:
                break
        self.assertGreater(n, 10)
        self.assertGreater(good, 0)
        self.assertGreater(flagged, 0)  # degenerate files are flagged

    def test_gtr1_descriptor_invariants(self):
        """GTR1 third-magic GMT descriptors have plausible counts/offsets."""
        import glob
        import mas_tool
        import gmt_semantic
        files = descs = 0
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"), recursive=True)[:12]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                ds = gmt_semantic.read_gtr1_descriptors(e.data)
                if not ds:
                    continue
                files += 1
                for desc in ds:
                    self.assertGreater(desc["v_count"], 0)
                    self.assertLess(desc["v_count"], 200000)
                    self.assertGreater(desc["i_count"], 0)
                    self.assertLess(desc["i_count"], 600000)
                    self.assertGreater(desc["v_off"], 0)
                    self.assertLessEqual(desc["v_off"] + 4 + desc["v_count"] * 48,
                                         len(e.data))
                    descs += 1
                if files >= 50:
                    break
            if files >= 50:
                break
        self.assertGreater(files, 30)
        self.assertGreater(descs, 100)

    def test_gsc_gmt_prefilter(self):
        """0x1D4 near-magic predicts GSC GMT decodability (recall 1.0)."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        n = tp = fp = fn = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:15]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    pred = gmt_semantic.is_gsc_decodable(d)
                    dec = bool(gmt_semantic.read_gmt(d)["submeshes"])
                    tp += pred and dec; fp += pred and not dec; fn += not pred and dec
                    n += 1
                    if n >= 150:
                        break
                if n >= 150:
                    break
            if n >= 150:
                break
        self.assertGreater(n, 100)
        self.assertEqual(fn, 0)  # no decodable file missed by the pre-filter
        self.assertGreater(tp, 0)
        self.assertGreater(tp, fp)

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
        self.assertEqual(len(stt.SP_UNIVERSAL_BODIES), 9)
        self.assertEqual(len(stt.SP_UNIVERSAL_BARS), 6)

    def test_skn_parser_corpus(self):
        """.skn skins: 262 files, 788 layers, 786 words, 0 validation problems."""
        import glob
        n = tl = tw = ts = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.skn"), recursive=True):
            info = stt.parse_skn(Path(p).read_bytes())
            self.assertEqual(stt.validate_skn(info), [], p)
            tl += len(info.layers)
            tw += len(info.words)
            ts += len(info.stamps)
            n += 1
        self.assertEqual(n, 262)
        self.assertEqual((tl, tw, ts), (788, 786, 262))

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

    def test_dmg_parser_corpus(self):
        """All 200 .dmg files carry the 43 universal damage keys."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.dmg"), recursive=True):
            info = stt.parse_dmg(
                media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertEqual(stt.validate_dmg(info), [], p)
            n += 1
        self.assertGreaterEqual(n, 200)
        self.assertEqual(len(stt.DMG_UNIVERSAL_KEYS), 43)

    def test_aud_sound_map_corpus(self):
        """All .aud files (plain + JCA) have no mixed path/numeric keys."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.aud"), recursive=True):
            info = stt.parse_aud(
                media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertEqual(stt.validate_aud_map(info), [], p)
            n += 1
        self.assertGreaterEqual(n, 364)

    def test_gdb_car_corpus(self):
        """Generic .gdb/.car parsing: 1,287 + 3,385 files all valid."""
        import glob
        import media_tool
        n = keys = 0
        for ext in (".gdb", ".car"):
            for p in glob.glob(str(ROOT.parent / "**" / ("*" + ext)), recursive=True):
                info = (stt.parse_gdb if ext == ".gdb" else stt.parse_car)(
                    media_tool.decrypt_jca_text(Path(p).read_bytes()))
                self.assertEqual(stt.validate_config(info), [], p)
                keys += len(info.keys)
                n += 1
        self.assertGreaterEqual(n, 4672)
        self.assertGreater(keys, 150000)

    def test_cin_scr_corpus(self):
        """All .cin (409) and .scr (123) scripts validate."""
        import glob
        ne = na = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.cin"), recursive=True):
            info = stt.parse_cin(Path(p).read_bytes())
            self.assertEqual(stt.validate_cin(info), [], p)
            ne += len(info.events)
        for p in glob.glob(str(ROOT.parent / "**" / "*.scr"), recursive=True):
            info = stt.parse_scr(Path(p).read_bytes())
            self.assertEqual(stt.validate_scr(info), [], p)
            na += len(info.actors)
        self.assertGreaterEqual(ne, 5798)
        self.assertGreaterEqual(na, 1998)

    def test_hdc_uses_hdv_parser(self):
        """.hdc handling files share the .hdv section/key structure."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.hdc"), recursive=True):
            info = stt.parse_hdv(media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertIn("mass", info.keys)
            self.assertIn("general", info.sections)
            self.assertIn("frontleft", info.sections)
            n += 1
        self.assertGreaterEqual(n, 472)


if __name__ == "__main__":
    unittest.main()
