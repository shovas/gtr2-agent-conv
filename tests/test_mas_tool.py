import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402


def make_entries():
    return [
        mas_tool.Entry(name="a.txt", offset=0, size=0, zsize=0, data=b"hello"),
        mas_tool.Entry(name="b.bin", offset=0, size=0, zsize=0, data=b"\x00\x01\x02\x03" * 50),
        mas_tool.Entry(name="c.bmp", offset=0, size=0, zsize=0, data=b"BM" + b"Z" * 200),
    ]


class MasToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/tmp"))
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_type0(self):
        arc = self.dir / "t.gtr"
        mas_tool.write_archive(arc, make_entries(), mas_type=0)
        mtype, entries = mas_tool.read_archive(arc)
        self.assertEqual(mtype, 0)
        self.assertEqual([e.name for e in entries], ["a.txt", "b.bin", "c.bmp"])
        self.assertEqual(entries[0].data, b"hello")
        self.assertEqual(entries[1].data, b"\x00\x01\x02\x03" * 50)

    def test_create_list_extract_cli(self):
        src = self.dir / "src"
        src.mkdir()
        (src / "one.txt").write_bytes(b"one")
        (src / "two.bin").write_bytes(b"two")
        arc = self.dir / "arc.gtr"
        self.assertEqual(mas_tool.main(["create", str(arc), str(src / "one.txt"), str(src / "two.bin")]), 0)
        mtype, entries = mas_tool.read_archive(arc)
        self.assertEqual(mtype, 0)
        self.assertEqual([e.name for e in entries], ["one.txt", "two.bin"])
        out = self.dir / "out"
        self.assertEqual(mas_tool.main(["extract", str(arc), "-o", str(out)]), 0)
        self.assertEqual((out / "one.txt").read_bytes(), b"one")
        self.assertEqual((out / "two.bin").read_bytes(), b"two")

    def test_add_update_delete(self):
        src = self.dir / "src"
        src.mkdir()
        (src / "a.txt").write_bytes(b"a1")
        (src / "b.txt").write_bytes(b"b1")
        (src / "a2.txt").write_text("ignored", encoding="utf-8")
        arc = self.dir / "arc.gtr"
        mas_tool.write_archive(arc, [mas_tool.Entry(name="a.txt", offset=0, size=0, zsize=0, data=b"old")], mas_type=0)

        self.assertEqual(mas_tool.main(["add", str(arc), str(src / "b.txt")]), 0)
        _, entries = mas_tool.read_archive(arc)
        self.assertEqual([e.name for e in entries], ["a.txt", "b.txt"])

        (src / "a.txt").write_bytes(b"new")
        self.assertEqual(mas_tool.main(["update", str(arc), str(src / "a.txt")]), 0)
        _, entries = mas_tool.read_archive(arc)
        self.assertEqual(entries[0].data, b"new")

        self.assertEqual(mas_tool.main(["delete", str(arc), "b.txt"]), 0)
        _, entries = mas_tool.read_archive(arc)
        self.assertEqual([e.name for e in entries], ["a.txt"])

    def test_add_rejects_duplicate_update_requires_existing(self):
        arc = self.dir / "arc.gtr"
        f = self.dir / "x.txt"
        f.write_bytes(b"x")
        mas_tool.write_archive(arc, [mas_tool.Entry(name="x.txt", offset=0, size=0, zsize=0, data=b"1")], mas_type=0)
        with self.assertRaises(ValueError):
            mas_tool.main(["add", str(arc), str(f)])
        f2 = self.dir / "y.txt"
        f2.write_bytes(b"y")
        with self.assertRaises(ValueError):
            mas_tool.main(["update", str(arc), str(f2)])

    def test_delete_missing_returns_nonzero(self):
        arc = self.dir / "arc.gtr"
        mas_tool.write_archive(arc, make_entries(), mas_type=0)
        rc = mas_tool.main(["delete", str(arc), "nope.bin"])
        self.assertEqual(rc, 1)

    def test_real_gtr_gtl_roundtrip_if_present(self):
        candidates = [
            ROOT.parent / "GTR2Steam/GameData/Teams/24H/BMW M3GTR Teams/BMW_M3GTR_CPIT.gtr",
            ROOT.parent / "GTLSteam/GameData/Locations/Anderstorp/Anderstorp.gtl",
        ]
        present = [p for p in candidates if p.exists()]
        if not present:
            self.skipTest("GTR2Steam/GTLSteam sample files not present")
        for src in present:
            mtype, entries = mas_tool.read_archive(src)
            out = self.dir / src.name
            mas_tool.write_archive(out, entries, mas_type=mtype)
            m2, e2 = mas_tool.read_archive(out)
            self.assertEqual(mtype, m2)
            self.assertEqual(len(entries), len(e2))
            for a, b in zip(entries, e2):
                self.assertEqual(a.name, b.name)
                self.assertEqual(a.data, b.data)


if __name__ == "__main__":
    unittest.main()
