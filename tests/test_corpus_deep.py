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
    def test_gsc_geometry_invariants(self):
        """GSC geometry: UV count == vertex count, face indices in range."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        subs = faces = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:3]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    if not gmt_semantic.is_gsc_decodable(d):
                        continue
                    g = gmt_semantic.read_gsc_geometry(d)
                    for sub in g["submeshes"]:
                        vc = len(sub["positions"])
                        self.assertEqual(len(sub["uvs"]), vc, e.name)
                        if sub["faces"]:
                            self.assertTrue(all(0 <= i < vc for f in sub["faces"] for i in f),
                                            e.name)
                            faces += 1
                        subs += 1
        self.assertGreater(subs, 15)
        self.assertGreater(faces, 10)

    def test_scgt_vrl_corpus(self):
        """SCGT .vrl members: 60-byte zero header and valid first offset."""
        import glob
        import mas_tool
        import simbin_text_tool as stt_local
        n = 0
        for arc in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                             recursive=True):
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".vrl") or not e.data:
                    continue
                self.assertEqual(stt_local.validate_vrl(e.data), [], f"{arc}/{e.name}")
                n += 1
            if n >= 1200:
                break
        self.assertGreater(n, 1000)

    def test_gsc_geometry_decoder(self):
        """read_gsc_geometry decodes real geometry with quality flags."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        n = good = flagged = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:3]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    if not gmt_semantic.is_gsc_decodable(d):
                        continue
                    g = gmt_semantic.read_gsc_geometry(d)
                    self.assertIsNotNone(g)
                    self.assertIn("quality", g)
                    if g["vertex_count"] == 0:
                        continue  # near-magic present but no decodable submeshes
                    if g["quality"]["plausible_positions"]:
                        good += 1
                    else:
                        flagged += 1
                    n += 1
                    if n >= 30:
                        break
                if n >= 30:
                    break
            if n >= 30:
                break
        self.assertGreater(n, 10)
        self.assertGreater(good, 0)
        self.assertGreater(flagged, 0)  # degenerate files are flagged

    def test_gtr1_descriptor_invariants(self):
        """GTR1 third-magic GMT descriptors have plausible counts/offsets."""
        import glob
        import mas_tool
        import gmt_semantic
        files = descs = 0
        for arc in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"), recursive=True)[:12]:
            try:
                _, entries = mas_tool.read_archive(arc)
            except Exception:
                continue
            for e in entries:
                if not e.name.lower().endswith(".gmt") or not e.data:
                    continue
                ds = gmt_semantic.read_gtr1_descriptors(e.data)
                if not ds:
                    continue
                files += 1
                for desc in ds:
                    self.assertGreater(desc["v_count"], 0)
                    self.assertLess(desc["v_count"], 200000)
                    self.assertGreater(desc["i_count"], 0)
                    self.assertLess(desc["i_count"], 600000)
                    self.assertGreater(desc["v_off"], 0)
                    self.assertLessEqual(desc["v_off"] + 4 + desc["v_count"] * 48,
                                         len(e.data))
                    descs += 1
                if files >= 50:
                    break
            if files >= 50:
                break
        self.assertGreater(files, 30)
        self.assertGreater(descs, 100)

    def test_gsc_gmt_prefilter(self):
        """0x1D4 near-magic predicts GSC GMT decodability (recall 1.0)."""
        import glob
        import isi_crypt
        import mas_tool
        import gmt_semantic
        n = tp = fp = fn = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for arc in glob.glob(str(ROOT.parent / root / "**" / "*.mas"), recursive=True)[:15]:
                try:
                    _, entries = mas_tool.read_archive(arc)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".gmt") or not e.data:
                        continue
                    try:
                        d = isi_crypt.decrypt_bytes(e.data)
                    except Exception:
                        continue
                    pred = gmt_semantic.is_gsc_decodable(d)
                    dec = bool(gmt_semantic.read_gmt(d)["submeshes"])
                    tp += pred and dec; fp += pred and not dec; fn += not pred and dec
                    n += 1
                    if n >= 150:
                        break
                if n >= 150:
                    break
            if n >= 150:
                break
        self.assertGreater(n, 100)
        self.assertEqual(fn, 0)  # no decodable file missed by the pre-filter
        self.assertGreater(tp, 0)
        self.assertGreater(tp, fp)

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

    def test_dmg_parser_corpus(self):
        """All 200 .dmg files carry the 43 universal damage keys."""
        import glob
        import media_tool
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.dmg"), recursive=True):
            info = stt.parse_dmg(
                media_tool.decrypt_jca_text(Path(p).read_bytes()))
            self.assertEqual(stt.validate_dmg(info), [], p)
            n += 1
        self.assertGreaterEqual(n, 200)
        self.assertEqual(len(stt.DMG_UNIVERSAL_KEYS), 43)

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
        self.assertGreaterEqual(n, 364)

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
        self.assertGreaterEqual(n, 4672)
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
        self.assertGreaterEqual(ne, 5798)
        self.assertGreaterEqual(na, 1998)

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
        self.assertGreaterEqual(n, 472)


if __name__ == "__main__":
    unittest.main()
