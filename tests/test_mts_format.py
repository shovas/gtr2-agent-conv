"""Tests for the partial CUBE MTS header parser."""
import glob
import os
import struct
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


    def test_48_byte_records_are_not_simple_position_triples(self):
        """Negative result: 48-byte grid does not decode as 3 float triples."""
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] == b"CUBE_MTS_4.20":
                    groups.setdefault((e.name.lower(), len(d)), []).append(d)
            if any(len(v) >= 2 for v in groups.values()):
                break
        sample = next((v[0] for v in groups.values() if len(v) >= 2), None)
        if sample is None:
            self.skipTest("no same-size CUBE MTS 4.20 sample present")
        import struct
        outliers = 0
        for off in range(0, len(sample) - 48, 48):
            vals = struct.unpack_from("<12f", sample, off)
            outliers += sum(1 for v in vals if abs(v) > 1e5)
        self.assertGreater(outliers, 0)  # incompatible with plain coordinates

    def test_48_byte_alignment_is_weak_on_largest_pair(self):
        groups = {}
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] == b"CUBE_MTS_4.20":
                    groups.setdefault((e.name.lower(), len(d)), []).append(d)
        pair = max((v for v in groups.values() if len(v) >= 2 and v[0] != v[1]),
                   key=lambda v: sum(x != y for x, y in zip(v[0], v[1])))
        if not pair:
            self.skipTest("no same-size CUBE MTS 4.20 pair present")
        diff = [i for i in range(len(pair[0])) if pair[0][i] != pair[1][i]]
        best = max(sum(1 for s in diff if s % 48 in (36, 44)) / len(diff) for _ in (0,))
        self.assertLess(best, 0.3)  # 48-byte grid does not explain most differing bytes

    def test_candidate_float_run_is_not_a_normal_array(self):
        import math
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "TLRA.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("TLRA.MTS sample not present")
        off = 0xD388
        mags = []
        while off + 12 <= len(sample):
            v = struct.unpack_from("<3f", sample, off)
            mags.append(math.sqrt(sum(x * x for x in v)))
            off += 12
        self.assertLess(sum(0.9 < m < 1.1 for m in mags) / len(mags), 0.5)

    def test_descriptor_packed_field_pattern(self):
        flags = lows = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] != b"CUBE_MTS_4.20":
                    continue
                for off, _ in mf.submesh_descriptors(d):
                    hi, lo = mf.descriptor_fields(d, off)
                    total += 1
                    flags += hi in (mf.DESCRIPTOR_FLAG_32, mf.DESCRIPTOR_FLAG_ALT)
                    lows += lo in (0, 2, 32, 96, 2048, 2080)
            if total >= 1000:
                break
        if total == 0:
            self.skipTest("CUBE MTS descriptors not present")
        self.assertGreater(flags / total, 0.95)
        self.assertGreater(lows / total, 0.9)

    def test_submesh_descriptor_grid(self):
        sample = None
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if p.is_file() and p.suffix.lower() == ".mas":
                for e in mas_tool.read_archive(p)[1]:
                    if e.name == "LIGHTBOX02.MTS" and (e.data or b"")[:13] == b"CUBE_MTS_4.20":
                        sample = e.data
                        break
            if sample:
                break
        if sample is None:
            self.skipTest("LIGHTBOX02.MTS sample not present")
        desc = mf.submesh_descriptors(sample)
        self.assertEqual([off for off, _ in desc], [216, 412, 608, 804])
        self.assertEqual([n for _, n in desc], ["LIGHTBOX2B", "LIGHTBOXC", "LIGHTBOX2", "GSTAND2"])

    def test_object_count_vs_submesh_names(self):
        hits = total = 0
        for a in glob.glob(str(ROOT.parent / "NascarSimRacing" / "**" / "*"), recursive=True):
            p = Path(a)
            if not p.is_file() or p.suffix.lower() != ".mas":
                continue
            for e in mas_tool.read_archive(p)[1]:
                d = e.data or b""
                if d[:13] not in (b"CUBE_MTS_4.10", b"CUBE_MTS_4.20"):
                    continue
                h = mf.parse_header(d)
                total += 1
                hits += (h.object_count - len(mf.submesh_names(d)) == 1)
            if total >= 400:
                break
        if total == 0:
            self.skipTest("CUBE MTS 4.20 corpus not present")
        self.assertGreater(hits / total, 0.5)

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
