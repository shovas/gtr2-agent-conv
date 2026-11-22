"""Tests for GMT-family variant detection across corpora."""
import glob
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_tool  # noqa: E402
import mas_tool  # noqa: E402


def first_gmt(corpus: str, ext: str, decrypt=None):
    for p in glob.glob(str(ROOT.parent / corpus / "**" / "*"), recursive=True):
        path = Path(p)
        if not path.is_file() or path.suffix.lower() != ext:
            continue
        entries = mas_tool.read_archive(p)[1]
        for e in entries:
            if e.name.lower().endswith(".gmt") and e.data:
                return e.data
    return None


class GmtVariantTest(unittest.TestCase):
    def test_known_variant_magics(self):
        self.assertEqual(gmt_tool.detect_variant(b"X" * 8 + gmt_tool.GMT_MAGIC_GTR_GTL + b"\0" * 16), "new-gtr2-gtl")
        self.assertEqual(gmt_tool.detect_variant(b"RaceGMT\0" + b"\0" * 16), "racegmt")
        self.assertEqual(gmt_tool.detect_variant(b"\x0f\xb1\xff\xff" + b"\0" * 16), "jca-encrypted")

    def test_real_corpus_variants(self):
        cases = [("GTR2Steam", ".gtr", {"new-gtr2-gtl"}),
                 ("RF1Vanilla", ".mas", {"jca-encrypted", "old-rfactor1", "new-gtr2-gtl"}),
                 ("GTR1Vanilla", ".gtr", {"old-gtr2004"}),
                 ("Race07Complete", ".gtr", {"racegmt", "new-gtr2-gtl", "jca-encrypted"})]
        for corpus, ext, expected in cases:
            data = first_gmt(corpus, ext)
            if data is None:
                continue
            self.assertIn(gmt_tool.detect_variant(data), expected, corpus)


if __name__ == "__main__":
    unittest.main()
