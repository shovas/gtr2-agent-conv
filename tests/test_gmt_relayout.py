"""Self-consistency tests for GMT relayout (rebuilt offsets after data grows)."""
import glob
import io
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format as gf  # noqa: E402
import mas_tool  # noqa: E402


def _samples():
    """One real GMT per structural variant, found in the GTR2 archives."""
    wanted = {
        "GOALPOST.GMT": "single mesh",
        "AMBULANCE00.GMT": "four meshes",
        "ANNOUNCERSOUND01.GMT": "streams 2+3",
        "FUELHOSE.GMT": "extra vertex block",
    }
    found = {}
    for arc in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"), recursive=True):
        try:
            _, entries = mas_tool.read_archive(arc)
        except Exception:
            continue
        for e in entries:
            name = e.name.upper()
            if name in wanted and name not in found and gf.GMT_MAGIC in (e.data or b"")[:32]:
                found[name] = (e.data, wanted[name])
        if len(found) == len(wanted):
            break
    return found


class GmtRelayoutTest(unittest.TestCase):
    def test_relayout_real_variants_roundtrip(self):
        samples = _samples()
        if not samples:
            self.skipTest("GTR2 GMT archives not present")
        for name, (data, variant) in samples.items():
            with self.subTest(name=name, variant=variant):
                g = gf.parse_gmt(name, data)
                out = gf.relayout_gmt(g)
                g2 = gf.parse_gmt(name, out)
                self.assertEqual(g2.mesh_count, g.mesh_count)
                self.assertEqual(g2.obj_list_offset, struct.unpack_from("<I", out, 0)[0])
                self.assertEqual(g2.tail, g.tail)
                self.assertEqual([m.name for m in g2.materials],
                                 [m.name for m in g.materials])
                for a, b in zip(g.meshes, g2.meshes):
                    self.assertEqual(b.vertex_data, a.vertex_data)
                    self.assertEqual(b.index_data, a.index_data)
                    self.assertEqual(b.extra_vertex_data, a.extra_vertex_data)
                    self.assertEqual(b.stream2_data, a.stream2_data)
                    self.assertEqual(b.stream3_data, a.stream3_data)
                    self.assertEqual(b.record.vertex_count, a.record.vertex_count)
                    self.assertEqual(b.record.index_count, a.record.index_count)
                    self.assertEqual(b.base_vertices, a.base_vertices)
                # write_gmt on the relayouted parse must be a fixed point.
                self.assertEqual(gf.write_gmt(g2), out)

    def test_relayout_after_vertex_and_index_growth(self):
        samples = _samples()
        if "GOALPOST.GMT" not in samples:
            self.skipTest("GOALPOST.GMT sample not present")
        data, _ = samples["GOALPOST.GMT"]
        g = gf.parse_gmt("GOALPOST.GMT", data)
        m = g.meshes[0]
        old_vc, old_ic = m.record.vertex_count, m.record.index_count
        # Append one 32-byte vertex and one u16 index, keeping the invariant
        # len(index_data) == 4 + index_count * 2.
        m.vertex_data += m.vertex_data[:32]
        m.index_data += struct.pack("<H", 0)
        m.record.raw[3] = old_vc + 1
        m.record.raw[10] = old_ic + 1

        baseline = len(gf.relayout_gmt(gf.parse_gmt("GOALPOST.GMT", data)))
        out = gf.relayout_gmt(g)
        g2 = gf.parse_gmt("GOALPOST.GMT", out)
        # The extra 2 index bytes may be absorbed by the tail's alignment pad.
        self.assertGreaterEqual(len(out), baseline + 32)
        self.assertEqual(g2.meshes[0].record.vertex_count, old_vc + 1)
        self.assertEqual(g2.meshes[0].record.index_count, old_ic + 1)
        self.assertEqual(g2.meshes[0].vertex_data, m.vertex_data)
        self.assertEqual(g2.meshes[0].index_data, m.index_data)
        self.assertEqual(len(g2.meshes[0].base_vertices), old_vc + 1)
        self.assertEqual(g2.tail, g.tail)
        self.assertEqual(gf.write_gmt(g2), out)

    def test_relayout_streams_force_nonzero_vertex_end(self):
        samples = _samples()
        if "GOALPOST.GMT" not in samples:
            self.skipTest("GOALPOST.GMT sample not present")
        data, _ = samples["GOALPOST.GMT"]
        g = gf.parse_gmt("GOALPOST.GMT", data)
        g.meshes[0].record.raw[6] = 0
        g.meshes[0].stream2_data = b"\xab" * 16
        out = gf.relayout_gmt(g)
        g2 = gf.parse_gmt("GOALPOST.GMT", out)
        self.assertEqual(g2.meshes[0].stream2_data, b"\xab" * 16)
        self.assertNotEqual(g2.meshes[0].record.raw[6], 0)

    def test_relayout_cli(self):
        samples = _samples()
        if "GOALPOST.GMT" not in samples:
            self.skipTest("GOALPOST.GMT sample not present")
        import gmt_tool
        data, _ = samples["GOALPOST.GMT"]
        with tempfile.TemporaryDirectory() as td:
            src, dst = Path(td) / "in.gmt", Path(td) / "out.gmt"
            src.write_bytes(data)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = gmt_tool.main(["relayout", str(src), str(dst)])
            self.assertEqual(rc, 0)
            self.assertIn("relayout:", buf.getvalue())
            out = dst.read_bytes()
        g = gf.parse_gmt("out.gmt", out)
        self.assertEqual(g.mesh_count, 1)
        self.assertEqual(g.tail, gf.parse_gmt("in.gmt", data).tail)

    def test_relayout_rejects_inconsistent_blobs(self):
        samples = _samples()
        if "GOALPOST.GMT" not in samples:
            self.skipTest("GOALPOST.GMT sample not present")
        data, _ = samples["GOALPOST.GMT"]
        g = gf.parse_gmt("GOALPOST.GMT", data)
        # Undersized blobs are rejected; oversized legacy blobs are preserved.
        g.meshes[0].vertex_data = g.meshes[0].vertex_data[:-8]
        with self.assertRaises(ValueError):
            gf.relayout_gmt(g)
        g2 = gf.parse_gmt("GOALPOST.GMT", data)
        g2.meshes[0].vertex_data += b"\x00" * 8
        out = gf.relayout_gmt(g2)
        self.assertGreater(len(out), 0)


if __name__ == "__main__":
    unittest.main()
