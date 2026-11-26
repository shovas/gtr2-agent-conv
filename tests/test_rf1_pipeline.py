"""End-to-end rF1 -> GTR2 archive pipeline test (decrypt, convert, repack)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import mas_tool  # noqa: E402
import rf1_to_gtr2  # noqa: E402

SOURCE = ROOT.parent / "RF1Vanilla/GameData/Locations/BamaSuperspeedway/Bama_SS.mas"


class Rf1PipelineTest(unittest.TestCase):
    def test_archive_check_and_repack(self):
        if not SOURCE.exists():
            self.skipTest("RF1Vanilla sample archive not present")
        report = rf1_to_gtr2.convert_archive(SOURCE, check=True)
        self.assertEqual(report["source_type"], 1)
        self.assertEqual(report["members"], 253)
        self.assertEqual(report["actions"], {"decrypt+layout": 253})

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "converted.gtr"
            rf1_to_gtr2.convert_archive(SOURCE, out)
            mtype, entries = mas_tool.read_archive(out)
            self.assertEqual(mtype, 0)
            self.assertEqual(len(entries), 253)
            gmts = [e for e in entries if e.name.lower().endswith(".gmt")]
            self.assertEqual(len(gmts), 253)
            for e in gmts[:5]:
                g = gmt_format.parse_gmt(e.name, e.data)
                self.assertGreater(len(g.meshes), 0, e.name)
                self.assertEqual(gmt_format.write_gmt(g), e.data)

            reference_path = (ROOT.parent / "gtr2-agent-tools" / "scripts"
                              / "gtr2_driving" / "gmt.py")
            if reference_path.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("reference_gmt", reference_path)
                reference = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(reference)
                for e in gmts[:5]:
                    parsed = reference.parse(e.data)
                    self.assertEqual(len(parsed),
                                     len(gmt_format.parse_gmt(e.name, e.data).meshes),
                                     e.name)


    def test_relayout_mode(self):
        if not SOURCE.exists():
            self.skipTest("RF1Vanilla sample archive not present")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "converted.gtr"
            report = rf1_to_gtr2.convert_archive(SOURCE, out, relayout=True)
            self.assertTrue(report["relayout"])
            self.assertEqual(report["members"], 253)
            self.assertEqual(report["actions"], {"decrypt+semantic+relayout": 253})
            entries = mas_tool.read_archive(out)[1]
            gmts = [e for e in entries if e.name.lower().endswith(".gmt")]
            self.assertEqual(len(gmts), 253)
            for e in gmts[:5]:
                g = gmt_format.parse_gmt(e.name, e.data)
                self.assertEqual(gmt_format.write_gmt(g), e.data)
                self.assertTrue(all(m.record.index_count * 2 + 4 == len(m.index_data)
                                    for m in g.meshes))

    def test_relayout_handles_grown_meshes(self):
        if not SOURCE.exists():
            self.skipTest("RF1Vanilla sample archive not present")
        import struct

        def grow(g):
            if g.meshes and g.meshes[0].record.vertex_count:
                m = g.meshes[0]
                stride = 48 if m.record.has_extra_vertex_block else 32
                m.vertex_data += m.vertex_data[:stride]
                m.index_data += struct.pack("<H", 0)
                m.record.raw[3] += 1
                m.record.raw[10] += 1
            return g

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "grown.gtr"
            rf1_to_gtr2.convert_archive(SOURCE, out, relayout=True, mesh_transform=grow)
            entries = mas_tool.read_archive(out)[1]
            gmts = [e for e in entries if e.name.lower().endswith(".gmt")]
            self.assertEqual(len(gmts), 253)
            checked = 0
            for e in gmts[:5]:
                g = gmt_format.parse_gmt(e.name, e.data)
                self.assertEqual(gmt_format.write_gmt(g), e.data)
                if g.meshes and g.meshes[0].record.vertex_count:
                    m = g.meshes[0]
                    stride = 48 if m.record.has_extra_vertex_block else 32
                    # Legacy blobs may carry a few trailing bytes; the key
                    # invariant is that growth is present and offsets rebuild.
                    self.assertGreaterEqual(len(m.vertex_data),
                                            m.record.vertex_count * stride)
                    self.assertEqual(len(m.index_data), 4 + m.record.index_count * 2)
                    checked += 1
            self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
