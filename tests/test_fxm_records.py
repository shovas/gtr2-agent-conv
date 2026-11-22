"""Tests for structured FXM node/keyframe records."""
import glob
import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fxm_tool  # noqa: E402

SAMPLE = ROOT.parent / "GTR2Steam/GameData/Animations/Pit/FU_PreIdle4-R.FXM"


class FxmRecordTest(unittest.TestCase):
    def test_node_records_resolve(self):
        if not SAMPLE.exists():
            self.skipTest("FXM sample not present")
        nodes = fxm_tool.parse_node_records(SAMPLE.read_bytes())
        bip = [n for n in nodes if n["name"].startswith("Bip")]
        self.assertGreaterEqual(len(bip), 20)
        self.assertTrue(all(n["key_count"] == 3 for n in nodes))
        self.assertTrue(all(n["keyframe_bytes"] == 84 for n in nodes))
        # Anchored walk must not pick up 3ds Max metadata as node records.
        self.assertTrue(all(n["name"].startswith("Bip") or n["name"] == "FU_Cap_LOCK"
                            for n in nodes))
        self.assertEqual(nodes[0]["name"], "Bip01")
        self.assertEqual(nodes[1]["name"], "Bip01 Pelvis")
        # Records are contiguous: stride is name length + 12-byte header + 84-byte keys.
        for a, bnode in zip(nodes, nodes[1:]):
            self.assertEqual(bnode["offset"] - a["offset"], len(a["name"]) + 96)

    def test_keyframe_trs_decode(self):
        if not SAMPLE.exists():
            self.skipTest("FXM sample not present")
        data = SAMPLE.read_bytes()
        nodes = fxm_tool.parse_node_records(data)
        qok = sok = 0
        for node in nodes:
            dec = fxm_tool.decode_node_keys(data, node)
            self.assertEqual(len(dec["keys"]), 2)
            for key in dec["keys"]:
                self.assertEqual(len(key["position"]), 3)
                self.assertEqual(len(key["quaternion"]), 4)
                self.assertEqual(len(key["scale"]), 3)
                qok += abs(key["quat_norm"] - 1.0) < 0.05
                sok += all(abs(x - 1.0) < 0.05 for x in key["scale"])
        self.assertGreater(qok, 0.9 * len(nodes) * 2)
        self.assertGreater(sok, 0.9 * len(nodes) * 2)

    def test_corpus_consistency(self):
        files = [p for p in ROOT.parent.joinpath("GTR2Steam").rglob("*")
                 if p.is_file() and p.suffix.lower() in (".fxm", ".fxa", ".lma")]
        if not files:
            self.skipTest("FXM corpus not present")
        parsed = 0
        for p in files[:20]:
            nodes = fxm_tool.parse_node_records(p.read_bytes())
            parsed += bool([n for n in nodes if n["name"].startswith("Bip")])
        self.assertGreater(parsed, 0)


if __name__ == "__main__":
    unittest.main()
