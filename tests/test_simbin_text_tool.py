"""Tests for the standalone AIW/SCN semantic reader."""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simbin_text_tool as stt  # noqa: E402


def _files(root: str, ext: str):
    base = ROOT.parent / root
    return [p for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext]


class SimbinTextToolTest(unittest.TestCase):
    def test_aiw_parse_from_reference_corpus(self):
        aiws = _files("GTR2Steam", ".aiw") + _files("GTLSteam", ".aiw")
        if not aiws:
            self.skipTest("GTR2/GTL corpora not present")
        self.assertEqual(len(aiws), 59)
        parsed = 0
        for p in aiws:
            aiw = stt.parse_aiw(stt.read_text(p))
            if aiw.waypoints:
                parsed += 1
                self.assertTrue(all(w.pos and len(w.pos) == 3 for w in aiw.waypoints))
        self.assertGreater(parsed, 0)

    def test_aiw_features_and_waypoints(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3Anderstorp.AIW"
        if not p.exists():
            self.skipTest("sample AIW not present")
        aiw = stt.parse_aiw(stt.read_text(p))
        self.assertEqual(aiw.features["pitlanes"], "1")
        self.assertEqual(aiw.features["startinggrid"], "104")
        self.assertEqual(len(aiw.waypoints), 1114)
        self.assertIn(0, aiw.branches())

    def test_scn_trk_parse(self):
        trk = ROOT.parent / "GTR2Steam/GameData/Locations/Anderstorp/3ANDERSTORP.trk"
        if not trk.exists():
            self.skipTest("sample TRK not present")
        info = stt.parse_scn(stt.read_text(trk))
        self.assertIn("GAMEDATA\\LOCATIONS\\Shared", info.search_path)
        self.assertIn("Anderstorp.gtr", info.mas_files)
        self.assertTrue(info.has_skyboxi)

    def test_scn_parse_across_corpora(self):
        files = _files("GTR2Steam", ".trk") + _files("GTR2Steam", ".scn") + \
                _files("GTLSteam", ".trk") + _files("GTLSteam", ".scn")
        if not files:
            self.skipTest("GTR2/GTL corpora not present")
        parsed = 0
        for p in files:
            raw = stt.read_text(p)
            if raw.startswith("CUBEASF"):
                info = stt.parse_scn(raw)
                parsed += 1
                self.assertIsInstance(info.mas_files, list)
        self.assertGreater(parsed, 0)


    def test_veh_parser_corpus(self):
        """.veh descriptors: 57 keys, Graphics universal, 6 near-universal."""
        import glob
        counts = {}
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.veh"), recursive=True):
            d = stt.parse_veh(Path(p).read_bytes())
            if not d:
                continue
            n += 1
            for k in d:
                counts[k] = counts.get(k, 0) + 1
        self.assertGreater(n, 2000)
        self.assertEqual(len(counts), 57)
        self.assertEqual(counts["graphics"], n)
        for k in ("classes", "driver", "number", "team", "sounds", "hdvehicle"):
            self.assertGreaterEqual(counts[k], n - 2)

    def test_svm_key_subset_corpus(self):
        """rF1 .svm keys are a strict subset of the GTR2 setup vocabulary."""
        import glob
        rf_keys = set()
        gtr_keys = set()
        n_rf = n_gtr = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.svm"), recursive=True):
            info = stt.parse_svm(Path(p).read_bytes())
            if info.variant == "encrypted":
                continue
            if info.variant == "rf1":
                rf_keys |= info.keys
                n_rf += 1
            else:
                gtr_keys |= info.keys
                n_gtr += 1
        self.assertGreater(n_rf, 400)
        self.assertGreater(n_gtr, 10000)
        self.assertEqual(len(rf_keys), 77)
        self.assertEqual(rf_keys - gtr_keys, set())


if __name__ == "__main__":
    unittest.main()
