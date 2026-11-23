"""Full-corpus coverage check for the GTR1 GMT magic variant."""
import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_semantic  # noqa: E402
import mas_tool  # noqa: E402

GTR1_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")


class Gtr1CoverageTest(unittest.TestCase):
    def test_every_gtr1_magic_gmt_decodes(self):
        base = ROOT.parent / "GTR1Vanilla"
        if not base.is_dir():
            self.skipTest("GTR1Vanilla corpus not present")
        archives = glob.glob(str(base / "**" / "*.gtr"), recursive=True)
        if not archives:
            self.skipTest("GTR1Vanilla archives not present")
        total = decoded = 0
        for arc in archives:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for entry in entries:
                data = entry.data or b""
                if data[4:20] != GTR1_MAGIC:
                    continue
                total += 1
                try:
                    if gmt_semantic.read_gtr1_descriptors(data):
                        decoded += 1
                        continue
                    if gmt_semantic.read_gtr1_object_mesh(data):
                        decoded += 1
                except Exception:
                    pass
        self.assertGreater(total, 30000)
        self.assertEqual(decoded, total, f"{total - decoded} GTR1 GMTs undecoded")


if __name__ == "__main__":
    unittest.main()
