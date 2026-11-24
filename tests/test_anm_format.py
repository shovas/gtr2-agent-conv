"""Tests for the single-bone ISI ANM decoder."""
import glob
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import anm_format  # noqa: E402
import mas_tool  # noqa: E402


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


class AnmFormatTest(unittest.TestCase):
    def test_single_bone_corpus(self):
        checked = 0
        for name, data in _anm_samples("F1C", 200):
            if struct.unpack_from("<I", data, 28)[0] != 1:
                continue
            with self.subTest(name=name):
                anm = anm_format.read_anm(data)
                self.assertEqual(anm.version, 1)
                self.assertGreater(len(anm.keys), 0)
                times = [k.time for k in anm.keys]
                self.assertEqual(times, sorted(times))
                for k in anm.keys:
                    self.assertAlmostEqual(
                        sum(x * x for x in k.quaternion) ** 0.5, 1.0, places=1)
                checked += 1
                if checked >= 8:
                    break
        self.assertGreater(checked, 0)

    def test_multi_bone_corpus(self):
        checked = 0
        for name, data in _anm_samples("NT2003", 200):
            if struct.unpack_from("<I", data, 28)[0] <= 1:
                continue
            with self.subTest(name=name):
                anm = anm_format.read_anm(data)
                self.assertGreater(len(anm.bones), 1)
                self.assertGreater(sum(len(b.keys) for b in anm.bones), 0)
                for b in anm.bones:
                    self.assertTrue(b.name)
                    self.assertTrue(all(b.keys[i].time < b.keys[i+1].time
                                        for i in range(len(b.keys)-1)))
                checked += 1
                if checked >= 5:
                    break
        self.assertGreater(checked, 0)

    def test_cli(self):
        sample = next(((n, d) for n, d in _anm_samples("F1C", 200)
                       if struct.unpack_from("<I", d, 28)[0] == 1), None)
        if sample is None:
            self.skipTest("single-bone ANM not present")
        import io
        import tempfile
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.ANM"
            p.write_bytes(sample[1])
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = anm_format.main([str(p)])
            self.assertEqual(rc, 0)
            self.assertIn("keys=", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
