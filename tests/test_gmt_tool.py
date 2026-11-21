import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_tool  # noqa: E402


class GmtToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_gmt(self, name, v0=1, flags=0x04000000, magic=gmt_tool.GMT_MAGIC_GTR_GTL, tail=b"\x00" * 16):
        p = self.dir / name
        import struct
        p.write_bytes(struct.pack("<II16s", v0, flags, magic) + tail)
        return p

    def test_read_header_known_magic(self):
        p = self._write_gmt("a.gmt", v0=123, flags=0x04000020)
        h = gmt_tool.read_header(p)
        self.assertEqual(h.v0, 123)
        self.assertEqual(h.flags, 0x04000020)
        self.assertTrue(h.known_magic)

    def test_unknown_magic(self):
        p = self._write_gmt("b.gmt", magic=b"X" * 16)
        h = gmt_tool.read_header(p)
        self.assertFalse(h.known_magic)

    def test_scan_and_diff(self):
        left = self.dir / "left"; right = self.dir / "right"
        left.mkdir(); right.mkdir()
        (left / "same.gmt").write_bytes((self.dir / "a.gmt").write_bytes(b"") or b"")
        # recreate properly
        import struct
        (left / "same.gmt").write_bytes(struct.pack("<II16s", 1, 0, gmt_tool.GMT_MAGIC_GTR_GTL) + b"abc")
        (right / "same.gmt").write_bytes(struct.pack("<II16s", 1, 0, gmt_tool.GMT_MAGIC_GTR_GTL) + b"abc")
        (left / "diff.gmt").write_bytes(struct.pack("<II16s", 1, 0, gmt_tool.GMT_MAGIC_GTR_GTL) + b"left")
        (right / "diff.gmt").write_bytes(struct.pack("<II16s", 1, 0x20, gmt_tool.GMT_MAGIC_GTR_GTL) + b"right")
        (left / "only.gmt").write_bytes(struct.pack("<II16s", 1, 0, gmt_tool.GMT_MAGIC_GTR_GTL))
        rc = gmt_tool.main(["diff", str(left), str(right)])
        self.assertEqual(rc, 0)

    def test_real_gmt_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Teams/M-FPDriver.gmt"
        if not p.exists():
            self.skipTest("GTR2Steam GMT not present")
        h = gmt_tool.read_header(p)
        self.assertTrue(h.known_magic)
        self.assertGreater(h.size, 24)


if __name__ == "__main__":
    unittest.main()
