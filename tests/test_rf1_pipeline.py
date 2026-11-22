"""End-to-end rF1 -> GTR2 archive pipeline test (decrypt, convert, repack)."""
import sys
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

        import tempfile
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


if __name__ == "__main__":
    unittest.main()
