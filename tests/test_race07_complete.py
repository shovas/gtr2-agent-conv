"""Observations for the Race07Complete corpus (Race 07 + DLC content)."""
import glob
import os
import random
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jca_crypt  # noqa: E402
import mas_tool  # noqa: E402

R07C = ROOT.parent / "Race07Complete"
NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")
RACE_GMT = b"RaceGMT\0"


def _files(ext):
    return [p for p in (Path(x) for x in glob.glob(str(R07C / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext.lower()]


class Race07CompleteTest(unittest.TestCase):
    def test_dlc_markers(self):
        gd = R07C / "GameData"
        if not gd.is_dir():
            self.skipTest("Race07Complete corpus not present")
        names = {p.name.lower() for p in gd.iterdir()}
        for expected in ("gtr_evo.gdb", "stcc.gdb", "sim_official.gdb"):
            self.assertIn(expected, names)

    def test_archives_are_type0(self):
        arcs = _files(".gtr")
        if not arcs:
            self.skipTest("Race07Complete corpus not present")
        self.assertEqual(len(arcs), 2)
        for a in arcs:
            self.assertEqual(mas_tool.read_signature(a), mas_tool.MAS_TYPE0, a)
            mtype, entries = mas_tool.read_archive(a)
            self.assertEqual(mtype, 0)

    def test_gmt_categories_sampled(self):
        gmts = _files(".gmt")
        if not gmts:
            self.skipTest("Race07Complete corpus not present")
        self.assertGreater(len(gmts), 60000)
        random.seed(7)
        sample = random.sample(gmts, 1000)
        counts = Counter()
        for p in sample:
            d = p.read_bytes()[:24]
            if d[:4] == b"\x0f\xb1\xff\xff":
                counts["jca"] += 1
            elif d[8:24] == NEW_MAGIC:
                counts["new"] += 1
            elif d[:8] == RACE_GMT:
                counts["racegmt"] += 1
            else:
                counts["other"] += 1
        self.assertGreater(counts["jca"], 600)
        self.assertGreater(counts["new"], 200)
        self.assertGreater(counts["racegmt"], 0)

    def test_racegmt_header(self):
        found = 0
        for p in _files(".gmt"):
            d = p.read_bytes()
            if d[:8] != RACE_GMT:
                continue
            n = struct.unpack_from("<I", d, 8)[0]
            self.assertGreater(n, 0)
            self.assertLess(n, 256)
            try:
                d[12:12 + n].decode("ascii")
            except UnicodeDecodeError:
                self.fail(f"non-ascii RaceGMT name in {p}")
            found += 1
            if found >= 20:
                break
        if found == 0:
            self.skipTest("no RaceGMT files present")
        self.assertGreater(found, 0)

    def test_jca_sample_decrypts_to_new_layout(self):
        for p in _files(".gmt"):
            raw = p.read_bytes()
            if raw[:4] != b"\x0f\xb1\xff\xff":
                continue
            dec = jca_crypt.decrypt_bytes(raw)
            self.assertEqual(dec[8:24], NEW_MAGIC)
            return
        self.skipTest("no JCA GMT sample present")


if __name__ == "__main__":
    unittest.main()
