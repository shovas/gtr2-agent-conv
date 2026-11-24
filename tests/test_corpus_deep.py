"""Deep corpus checks: full-tier only (slow, multi-game archive scans)."""
import glob
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import anm_format  # noqa: E402
import simbin_text_tool as stt  # noqa: E402
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


class CorpusDeepTest(unittest.TestCase):
    def test_sp_parser_corpus(self):
        """.sp suspension geometry: field presence and body refs hold."""
        import glob
        n = totals = 0
        tb = tbar = tj = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.sp"), recursive=True):
            if Path(p).read_bytes()[:4] == b"\x0f\xb1\xff\xff":
                continue
            info = stt.parse_sp(Path(p).read_bytes())
            self.assertEqual(stt.validate_sp(info), [], p)
            tb += len(info.bodies)
            tbar += len(info.bars)
            tj += len(info.joints)
            n += 1
        self.assertEqual(n, 172)
        self.assertEqual((tb, tbar, tj), (1872, 3320, 688))
        self.assertEqual(len(stt.SP_UNIVERSAL_BODIES), 9)
        self.assertEqual(len(stt.SP_UNIVERSAL_BARS), 6)

    def test_corpus_decode_rate(self):
        """Archived ANM members decode across every ANM-bearing corpus.

        The full 2,436-member survey (F1C/F12001/F12002/NT2003/NT2004/
        NascarSimRacing/GTR1) yields 2,435 decodes; the sole exception is a
        degenerate quaternion in F12001 CATSTEER.ANM. Sample a bounded number
        per corpus here to keep the test fast.
        """
        corpora = ("F1C", "F12001", "F12002", "NT2003", "NT2004",
                   "NascarSimRacing", "GTR1Vanilla")
        per_corpus = {}
        for root in corpora:
            ok = bad = 0
            for name, data in _anm_samples(root, 120):
                try:
                    anm_format.read_anm(data)
                    ok += 1
                except ValueError as ex:
                    # Only degenerate quaternions are acceptable failures.
                    self.assertIn("quaternion norm", str(ex), f"{root}/{name}")
                    bad += 1
            per_corpus[root] = (ok, bad)
            self.assertGreater(ok, 0, root)
        # At least 7 corpora and >400 sampled decodes overall.
        self.assertEqual(len(per_corpus), 7)
        self.assertGreater(sum(o for o, _ in per_corpus.values()), 400)



if __name__ == "__main__":
    unittest.main()
