import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_format  # noqa: E402
import gmt_tool  # noqa: E402
import mas_tool  # noqa: E402


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


    def test_split_f0_and_info_output(self):
        """f0 halves are exposed by the helper and the info CLI."""
        import subprocess
        import sys
        import gmt_format
        low, high, delta = gmt_format.split_f0(0x0067006F)
        self.assertEqual((low, high, delta), (0x6F, 0x67, 8))
        sample = None
        for path in Path(__file__).resolve().parents[1].parent.glob("GTR2Steam/**/*.gtr"):
            try:
                _, entries = mas_tool.read_archive(str(path))
            except Exception:
                continue
            sample = next((e.data for e in entries
                           if e.name.lower().endswith(".gmt") and e.data), None)
            if sample:
                break
        if sample is None:
            self.skipTest("no GTR2 GMT sample")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.gmt"
            target.write_bytes(sample)
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "gmt_tool.py"),
                 "info", "--meshes", str(target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("f0=0x", result.stdout)
        self.assertIn("halves=", result.stdout)


    def test_f0_command(self):
        """The f0 subcommand reports marker halves and summary counts."""
        import subprocess
        import sys
        sample = None
        for path in Path(__file__).resolve().parents[1].parent.glob("GTR2Steam/**/*.gtr"):
            try:
                _, entries = mas_tool.read_archive(str(path))
            except Exception:
                continue
            sample = next((e.data for e in entries
                           if e.name.lower().endswith(".gmt") and e.data), None)
            if sample:
                break
        if sample is None:
            self.skipTest("no GTR2 GMT sample")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.gmt"
            target.write_bytes(sample)
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "gmt_tool.py"),
                 "f0", str(target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("halves=", result.stdout)
        self.assertIn("near_equal<=1=", result.stdout)


    def test_f0_command_warns_on_mesh0(self):
        """The f0 command flags an unexpected near-equal mesh-0 marker."""
        import struct
        import subprocess
        import sys
        sample = None
        for path in Path(__file__).resolve().parents[1].parent.glob("GTR2Steam/**/*.gtr"):
            try:
                _, entries = mas_tool.read_archive(str(path))
            except Exception:
                continue
            sample = next((e.data for e in entries
                           if e.name.lower().endswith(".gmt") and e.data), None)
            if sample:
                break
        if sample is None:
            self.skipTest("no GTR2 GMT sample")
        import tempfile
        data = bytearray(sample)
        # Locate mesh records via gmt_format, then patch the first vertex f0.
        parsed = gmt_format.parse_gmt("sample.gmt", bytes(data))
        self.assertTrue(parsed.meshes)
        first_vertex = parsed.meshes[0].record.vertex_offset
        struct.pack_into("<I", data, first_vertex, 0x00AA00A9)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "patched.gmt"
            target.write_bytes(data)
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "gmt_tool.py"),
                 "f0", str(target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mesh0_normally_has_large_delta", result.stdout)


if __name__ == "__main__":
    unittest.main()
