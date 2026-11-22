"""Tests for the partial CUBE MTS header parser."""
import glob
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402
import mts_format as mf  # noqa: E402
import race_gmt  # noqa: E402


class MtsFormatTest(unittest.TestCase):
    def test_magic_constants(self):
        self.assertEqual(mf.MAGIC_410[:11], b"CUBE_MTS_4.")
        self.assertIn(b"4.20", mf.MAGIC_420)

    def test_real_headers_both_variants(self):
        counts = Counter()
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                if not e.name.lower().endswith(".mts"):
                    continue
                h = mf.parse_header(e.data)
                counts[h.variant] += 1
                self.assertGreater(h.object_count, 0)
                self.assertTrue(h.name)
            if sum(counts.values()) >= 500:
                break
        if not counts:
            self.skipTest("CUBE MTS corpus not present")
        self.assertIn("4.10", counts)
        self.assertIn("4.20", counts)


    def test_varying_fields_align_to_48_byte_grid(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                groups.setdefault((e.name.lower(), len(d)), []).append(d)
        best = 0
        for v in groups.values():
            if len(v) < 2:
                continue
            diff = [i for i in range(len(v[0])) if v[0][i] != v[1][i]]
            if not diff:
                continue
            runs = []
            start = prev = diff[0]
            for i in diff[1:]:
                if i - prev > 4:
                    runs.append(start)
                    start = i
                prev = i
            runs.append(start)
            aligned = sum(1 for s in runs if s % 48 in (36, 44))
            best = max(best, aligned / len(runs))
        if best == 0:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        self.assertGreater(best, 0.5)

    def test_48_byte_vertex_stride_from_same_size_pair(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:14] != mf.MAGIC_420[:14]:
                    continue
                groups.setdefault((e.name.lower(), len(d)), []).append(d)
            if any(len(v) >= 2 for v in groups.values()):
                break
        pairs = [v for v in groups.values() if len(v) >= 2]
        if not pairs:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        best = max(race_gmt.diff_strides(v[0], v[1])["distances"].get(48, 0) for v in pairs)
        self.assertGreater(best, 10)


if __name__ == "__main__":
    unittest.main()
