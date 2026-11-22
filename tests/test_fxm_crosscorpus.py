"""Cross-corpus FXM/FXA/LMA magic-vs-extension observations (567 files)."""
import glob
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CORPORA = ("GTR2Steam", "GTLSteam", "BMWM3Challenge", "Race07Vanilla", "VolvoTheGame")


def _counts():
    out = Counter()
    for corpus in CORPORA:
        base = ROOT.parent / corpus
        for p in glob.glob(str(base / "**" / "*"), recursive=True):
            if os.path.isfile(p):
                ext = Path(p).suffix.lower()
                if ext in (".fxm", ".fxa", ".lma"):
                    out[(corpus, ext, Path(p).read_bytes()[:4])] += 1
    return out


class FxmCrossCorpusTest(unittest.TestCase):
    def test_total_and_known_magics(self):
        counts = _counts()
        if not counts:
            self.skipTest("no FXM corpora present")
        self.assertEqual(sum(counts.values()), 567)
        self.assertEqual({k[2] for k in counts}, {b"FXM ", b"FXA ", b"LMA "})

    def test_extension_magic_mismatches(self):
        counts = _counts()
        if not counts:
            self.skipTest("no FXM corpora present")
        mismatch = sum(v for (c, ext, magic), v in counts.items()
                       if magic.decode("ascii").strip() != ext[1:].upper())
        self.assertEqual(mismatch, 54)
        # Concrete observed cases
        self.assertEqual(counts[("Race07Vanilla", ".fxa", b"LMA ")], 22)
        self.assertEqual(counts[("GTR2Steam", ".lma", b"FXM ")], 4)
        self.assertEqual(counts[("VolvoTheGame", ".fxa", b"LMA ")], 0)


if __name__ == "__main__":
    unittest.main()
