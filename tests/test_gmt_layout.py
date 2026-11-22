"""Tests for the prototype old->new GMT layout bridge (structural only)."""
import glob
import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import gmt_layout  # noqa: E402
import gmt_semantic  # noqa: E402
import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402


def _old_gmts(limit=6):
    out = []
    for a in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*"), recursive=True):
        if not os.path.isfile(a) or not a.lower().endswith(".mas"):
            continue
        for e in mas_tool.read_archive(a)[1]:
            if not e.name.lower().endswith(".gmt") or not e.data:
                continue
            sign, key = struct.unpack_from("<QQ", e.data, 0)
            if (sign ^ key) & 0xFFFFFFFFFFFFFFFF not in isi_crypt.GAMES:
                continue
            out.append((a, e.name, isi_crypt.decrypt_bytes(e.data, skip=4)))
            if len(out) >= limit:
                return out
    return out


class GmtLayoutTest(unittest.TestCase):
    def test_semantic_bridge_preserves_geometry(self):
        import gmt_semantic as gs
        ok = 0
        for _, name, data in _old_gmts(limit=20):
            if not gmt_layout.is_old(data):
                continue
            original = gs.read_gmt(data)
            if not original["submeshes"]:
                continue
            converted = gmt_layout.old_to_new_semantic(data)
            parsed = gmt_format.parse_gmt(name, converted)
            decoded = gs.read_gmt(converted)
            self.assertEqual(parsed.mesh_count, len(original["submeshes"]))
            self.assertEqual(decoded["vertex_count"], original["vertex_count"])
            self.assertEqual(decoded["face_count"], original["face_count"])
            self.assertEqual(gmt_format.write_gmt(parsed), converted)
            ok += 1
        if not ok:
            self.skipTest("no decodable old GMTs")
        self.assertGreaterEqual(ok, 1)

    def test_semantic_bridge_material_tail(self):
        import gmt_semantic as gs
        for _, name, data in _old_gmts(limit=10):
            if not gmt_layout.is_old(data) or not gs.read_gmt(data)["submeshes"]:
                continue
            converted = gmt_layout.old_to_new_semantic(data)
            parsed = gmt_format.parse_gmt(name, converted)
            self.assertTrue(parsed.materials)
            self.assertTrue(any("L0" in s for m in parsed.materials for s in m.strings))
            return
        self.skipTest("no decodable old GMTs with materials")

    def test_magic_constants(self):
        self.assertEqual(gmt_layout.OLD_MAGIC[13], 0xA8)
        self.assertEqual(gmt_layout.NEW_MAGIC[13], 0xA7)
        self.assertEqual(gmt_layout.OLD_MAGIC[:13], gmt_layout.NEW_MAGIC[:13])
        self.assertEqual(gmt_layout.OLD_MAGIC[14:], gmt_layout.NEW_MAGIC[14:])

    def test_old_gmts_convert_to_parseable_new_layout(self):
        samples = _old_gmts()
        if not samples:
            self.skipTest("RF1Vanilla corpus not present")
        for path, name, old in samples:
            with self.subTest(path=os.path.basename(path), name=name):
                self.assertTrue(gmt_layout.is_old(old))
                new = gmt_layout.old_to_new(old)
                self.assertTrue(gmt_layout.is_new(new))
                self.assertEqual(len(new), len(old))
                self.assertEqual(new[0x194:0x1D4], old[0x194:0x1D4])  # name preserved
                obj_count = struct.unpack_from("<I", old, 0x174)[0]
                g = gmt_format.parse_gmt(name, new)
                self.assertEqual(len(g.meshes), obj_count)
                self.assertTrue(any(len(m.base_vertices) > 0 for m in g.meshes))
                self.assertEqual(gmt_format.write_gmt(g), new)

    def test_rejects_new_layout_input(self):
        sample = next(((a, e) for a in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True)
                       if os.path.isfile(a) and a.lower().endswith(".gtr")
                       for e in mas_tool.read_archive(a)[1] if e.name.lower().endswith(".gmt")), None)
        if sample is None:
            self.skipTest("GTR2 corpus not present")
        with self.assertRaises(ValueError):
            gmt_layout.old_to_new(sample[1].data)


if __name__ == "__main__":
    unittest.main()
