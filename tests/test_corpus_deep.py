"""Deep corpus checks: full-tier only (slow, multi-game archive scans)."""
import glob
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collections
import re
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

    def test_skn_parser_corpus(self):
        """.skn skins: 262 files, 788 layers, 786 words, 0 validation problems."""
        import glob
        n = tl = tw = ts = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.skn"), recursive=True):
            info = stt.parse_skn(Path(p).read_bytes())
            self.assertEqual(stt.validate_skn(info), [], p)
            tl += len(info.layers)
            tw += len(info.words)
            ts += len(info.stamps)
            n += 1
        self.assertEqual(n, 262)
        self.assertEqual((tl, tw, ts), (788, 786, 262))

    def test_svm_key_subset_corpus(self):
        """rF1 .svm keys are a strict subset of the GTR2 setup vocabulary."""
        import glob
        rf_keys = set()
        gtr_keys = set()
        rf_sections = set()
        gtr_sections = set()
        n_rf = n_gtr = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.svm"), recursive=True):
            info = stt.parse_svm(Path(p).read_bytes())
            if info.variant == "encrypted":
                continue
            if info.variant == "rf1":
                rf_keys |= info.keys
                rf_sections |= info.sections
                n_rf += 1
            else:
                gtr_keys |= info.keys
                gtr_sections |= info.sections
                n_gtr += 1
        self.assertGreater(n_rf, 400)
        self.assertGreater(n_gtr, 10000)
        self.assertEqual(len(rf_keys), 77)
        self.assertEqual(rf_keys - gtr_keys, set())
        # Section names are identical across rF1 and GTR2 setups.
        self.assertEqual(rf_sections, gtr_sections)
        self.assertEqual(len(rf_sections), 15)

    def test_aud_sound_map_corpus(self):
        """All .aud files (plain + JCA) have no mixed path/numeric keys."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.aud"), recursive=True):
            info = stt.parse_aud(
                media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertEqual(stt.validate_aud_map(info), [], p)
            n += 1
        self.assertEqual(n, 364)

    def test_gdb_car_corpus(self):
        """Generic .gdb/.car parsing: 1,287 + 3,385 files all valid."""
        import glob
        import media_tool
        n = keys = 0
        for ext in (".gdb", ".car"):
            for p in glob.glob(str(ROOT.parent / "**" / ("*" + ext)), recursive=True):
                info = (stt.parse_gdb if ext == ".gdb" else stt.parse_car)(
                    media_tool.decrypt_jca_text(Path(p).read_bytes()))
                self.assertEqual(stt.validate_config(info), [], p)
                keys += len(info.keys)
                n += 1
        self.assertEqual(n, 4672)
        self.assertGreater(keys, 150000)

    def test_cin_scr_corpus(self):
        """All .cin (409) and .scr (123) scripts validate."""
        import glob
        ne = na = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.cin"), recursive=True):
            info = stt.parse_cin(Path(p).read_bytes())
            self.assertEqual(stt.validate_cin(info), [], p)
            ne += len(info.events)
        for p in glob.glob(str(ROOT.parent / "**" / "*.scr"), recursive=True):
            info = stt.parse_scr(Path(p).read_bytes())
            self.assertEqual(stt.validate_scr(info), [], p)
            na += len(info.actors)
        self.assertEqual(ne, 5798)
        self.assertEqual(na, 1998)

    def test_hdc_uses_hdv_parser(self):
        """.hdc handling files share the .hdv section/key structure."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.hdc"), recursive=True):
            info = stt.parse_hdv(media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertIn("mass", info.keys)
            self.assertIn("general", info.sections)
            self.assertIn("frontleft", info.sections)
            n += 1
        self.assertEqual(n, 472)

    def test_eng_parser_corpus(self):
        """All 333 .eng files validate with rising RPMTorque curves."""
        import glob
        import media_tool
        n = pts = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.eng"), recursive=True):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            info = stt.parse_eng(text)
            self.assertEqual(stt.validate_eng(info), [], p)
            rpms = [q[0] for q in info.torque_curve]
            self.assertTrue(all(a < b for a, b in zip(rpms, rpms[1:])), p)
            pts += len(info.torque_curve)
            n += 1
        self.assertEqual(n, 333)
        self.assertEqual(pts, 12771)

    def test_grb_parser_corpus(self):
        """All 248 .grb files (incl. 77 JCA) validate with b/a ratio semantics."""
        import glob
        import media_tool
        n = gears = 0
        commented = matched = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.grb"), recursive=True):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            info = stt.parse_grb(text)
            self.assertEqual(stt.validate_grb(info), [], p)
            gears += len(info.gear_ratios)
            n += 1
            for line in text.splitlines():
                m = re.match(r"^\s*ratio\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", line, re.I)
                c = re.search(r"//.*?\(([-\d.]+)\)", line)
                if m and c and int(m.group(1)) != 0:
                    commented += 1
                    if abs(int(m.group(2)) / int(m.group(1)) - float(c.group(1))) < 0.02:
                        matched += 1
        self.assertEqual(n, 248)
        self.assertEqual(gears, 6929)
        self.assertEqual(matched, commented)  # 214+ commented ratios all b/a

    def test_rcd_parser_corpus(self):
        """All 5,047 .rcd configs classify and validate."""
        import glob
        fam = collections.Counter()
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.rcd"), recursive=True):
            info = stt.parse_rcd(Path(p).read_bytes())
            self.assertEqual(stt.validate_rcd(info), [], p)
            fam[info.family] += 1
            n += 1
        self.assertEqual(n, 5047)
        self.assertEqual(fam["driver"], 3038)
        self.assertEqual(fam["event"], 1830)
        self.assertEqual(fam["nascar"], 178)

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
