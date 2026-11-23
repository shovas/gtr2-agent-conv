"""Tests for structured FXM node/keyframe records."""
import glob
import io
import collections
import math
import os
import struct
import sys
import unittest
from contextlib import redirect_stdout
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

    def test_nul_name_wiper_variant(self):
        paths = glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "BMW_MINI_CPITWIPER.FXA"),
                          recursive=True)
        if not paths:
            self.skipTest("wiper FXM sample not present")
        data = Path(paths[0]).read_bytes()
        nodes = fxm_tool.parse_nul_name_nodes(data)
        self.assertGreaterEqual(len(nodes), 2)
        self.assertTrue(all(0.9 < n["quat_norm"] < 1.1 for n in nodes))
        self.assertTrue(all(n["keyframe_offset"] - n["offset"] in (40, 80, 44, 76)
                            for n in nodes))

    def test_nul_name_fxm_variant(self):
        p = ROOT.parent / "Race07Complete/GameData/Animations/Driver/FPDRIVER_Vectra-SteerL_01.FXM"
        if not p.is_file():
            self.skipTest("NUL-name FXM sample not present")
        data = p.read_bytes()
        self.assertEqual(data[:4], b"LMA ")
        nodes = fxm_tool.parse_nul_name_nodes(data)
        self.assertGreater(len(nodes), 50)
        self.assertAlmostEqual(nodes[0]["quat_norm"], 1.0, places=2)
        self.assertEqual(nodes[0]["name"], "Bip01")
        self.assertTrue(all(0.9 < n["quat_norm"] < 1.1 for n in nodes))

    def test_key_count_is_not_a_key_count(self):
        import math
        import struct
        checked = 0
        for corpus in ("GTR2Steam", "GTLSteam", "Race07Complete", "VolvoTheGame"):
            for p in ROOT.parent.joinpath(corpus).rglob("*"):
                if not p.is_file():
                    continue
                data = p.read_bytes()
                for node in fxm_tool.parse_node_records(data):
                    f = struct.unpack_from("<21f", data, node["keyframe_offset"])
                    # key_count==3 would suggest 3 x 28-byte keys with pos+quat;
                    # that yields unit quaternions in 0/148 nodes.
                    three = all(0.9 < math.sqrt(sum(x * x for x in f[k * 7 + 3:k * 7 + 7])) < 1.1
                                for k in range(3))
                    self.assertFalse(three)
                    # The decoded 2 x 40-byte TRS layout is correct.
                    two = all(0.9 < math.sqrt(sum(x * x for x in f[k * 10 + 3:k * 10 + 7])) < 1.1
                              for k in range(2))
                    self.assertTrue(two)
                    checked += 1
        if not checked:
            self.skipTest("FXM corpora not present")
        self.assertGreater(checked, 10)

    def test_node_id_is_name_stable_across_corpus(self):
        nodes = []
        checked = 0
        for corpus in ("GTR2Steam", "GTLSteam", "VolvoTheGame", "Race07Vanilla",
                       "Race07Complete", "BMWM3Challenge"):
            for p in ROOT.parent.joinpath(corpus).rglob("*"):
                if not p.is_file() or p.suffix.lower() not in (".fxm", ".fxa", ".lma"):
                    continue
                data = p.read_bytes()
                found = fxm_tool.parse_node_records(data)
                if not found:
                    continue
                for node in found:
                    self.assertEqual(node["key_count"], 3)
                    self.assertEqual(fxm_tool.decode_node_keys(data, node)["trailer"],
                                     node["size_hint"] - 84)
                nodes.extend(found)
                checked += 1
        if not nodes:
            self.skipTest("FXM corpora not present")
        idmap = fxm_tool.build_node_id_map(nodes)
        self.assertGreater(len(idmap), 10)
        self.assertGreater(checked, 10)
        self.assertEqual(idmap["Bip01"], 12)
        self.assertEqual(idmap["Bip01 Pelvis"], 11)
        self.assertEqual(idmap["Bip01 Head"], 13)

    def test_keys_cli(self):
        if not SAMPLE.exists():
            self.skipTest("FXM sample not present")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = fxm_tool.main(["keys", str(SAMPLE)])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("Bip01\t", out)
        self.assertIn("id=12", out)
        self.assertIn("key0\tpos=", out)
        self.assertIn("norm=1.0000", out)

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


    def test_size_hint_not_a_variable_record_length(self):
        """Nodes with differing size_hint still have fixed 84-byte keyframes."""
        files = []
        for root in ("GTR2Steam", "Race07Complete", "Race07Vanilla",
                     "VolvoTheGame", "BMWM3Challenge"):
            files.extend(glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True))
        target = None
        for p in files:
            if not Path(p).is_file():
                continue
            try:
                data = Path(p).read_bytes()
                nodes = fxm_tool.parse_node_records(data)
            except Exception:
                continue
            if len(nodes) >= 4 and len({n["size_hint"] for n in nodes}) > 1:
                target = (p, nodes)
                break
        if target is None:
            self.skipTest("no mixed-size_hint FXM file present")
        _, nodes = target
        for a, b in zip(nodes, nodes[1:]):
            self.assertEqual(b["offset"] - (a["keyframe_offset"] + 84), 0)


    def test_semantic_decoder(self):
        std = next((p for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"),
                                         recursive=True)
                    if p.lower().endswith(".fxm") and fxm_tool.parse_node_records(
                        Path(p).read_bytes())), None)
        if std is None:
            self.skipTest("standard FXM sample not present")
        doc = fxm_tool.decode_fxm_semantic(Path(std).read_bytes())
        self.assertEqual(doc["variant"], "standard")
        self.assertGreaterEqual(doc["stats"]["nodes"], 1)
        self.assertEqual(doc["stats"]["flagged"], 0)
        for n in doc["nodes"]:
            self.assertEqual(n["key_count"], 2)
            self.assertEqual(n["issues"], [])
        # Standard nodes are static: both TRS keys are identical (148/148 corpus).
        keys = fxm_tool.decode_node_keys(Path(std).read_bytes(),
                                         fxm_tool.parse_node_records(Path(std).read_bytes())[0])["keys"]
        for f in ("position", "quaternion", "scale"):
            self.assertEqual(keys[0][f], keys[1][f])

        nul = next((p for p in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*"),
                                         recursive=True)
                    if p.lower().endswith(".lma") and fxm_tool.parse_nul_name_nodes(
                        Path(p).read_bytes())), None)
        if nul is not None:
            d2 = fxm_tool.decode_fxm_semantic(Path(nul).read_bytes())
            self.assertEqual(d2["variant"], "nul")
            self.assertTrue(all(n["key_count"] == 1 for n in d2["nodes"]))

    def test_nul_parser_rejects_false_name_matches(self):
        """All NUL-variant nodes from the corpus have +/-1 scale components."""
        nodes = 0
        for root in ("GTR2Steam", "Race07Complete"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith((".lma", ".fxm", ".fxa")):
                    continue
                try:
                    data = Path(p).read_bytes()
                    found = fxm_tool.parse_nul_name_nodes(data)
                except Exception:
                    continue
                for n in found:
                    self.assertTrue(all(abs(abs(s) - 1.0) < 0.02 for s in n["scale"]),
                                    f"{p}:{n['name']}")
                    nodes += 1
        self.assertGreater(nodes, 1000)

    def test_node_keyframe_invariants_across_corpus(self):
        """148/148 standard nodes: 84-byte keys, unit quats, +/-1 scale, trailer link."""
        checked = 0
        for root in ("GTR2Steam", "Race07Complete", "Race07Vanilla",
                     "VolvoTheGame", "BMWM3Challenge"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith((".fxm", ".fxa", ".lma")):
                    continue
                try:
                    data = Path(p).read_bytes()
                    nodes = fxm_tool.parse_node_records(data)
                except Exception:
                    continue
                for node in nodes:
                    self.assertEqual(fxm_tool.check_node_consistency(data, node), [],
                                     f"{p}:{node['name']}")
                    checked += 1
        self.assertGreaterEqual(checked, 100)


    def test_length_prefixed_fxm_variant(self):
        """SimBin pit-animation FXM files use length-prefixed bone names."""
        p = ROOT.parent / ("GTR2Steam/GameData/Animations/Pit/"
                           "WT01_dropgun01-l.fxm")
        if not p.is_file():
            self.skipTest("length-prefixed FXM sample not present")
        data = p.read_bytes()
        self.assertEqual(fxm_tool.parse_node_records(data), [])
        nodes = fxm_tool.parse_length_prefixed_nodes(data)
        self.assertGreaterEqual(len(nodes), 1)
        self.assertTrue(any(n["name"] == "Bip01 Pelvis" for n in nodes))
        for node in nodes:
            dec = fxm_tool.decode_node_keys(data, node)
            self.assertEqual(len(dec["keys"]), 2)
            for key in dec["keys"]:
                self.assertAlmostEqual(key["quat_norm"], 1.0, delta=0.02)
        semantic = fxm_tool.decode_fxm_semantic(data)
        self.assertEqual(semantic["variant"], "length-prefixed")


    def test_marker2_rotation_track_variant(self):
        """marker=2 length-prefixed nodes are (time, quaternion) tracks."""
        p = ROOT.parent / ("GTR2Steam/GameData/Animations/Pit/"
                           "WT01_dropgun01-l.fxm")
        if not p.is_file():
            self.skipTest("rotation-track FXM sample not present")
        data = p.read_bytes()
        tracks = fxm_tool.parse_rotation_track_nodes(data)
        self.assertGreaterEqual(len(tracks), 10)
        for track in tracks:
            self.assertEqual(track["size_hint"], 8 + 20 * track["frames"])
            self.assertEqual(len(track["times"]), track["frames"])
            self.assertEqual(len(track["quaternions"]), track["frames"])
            for t, q in zip(track["times"], track["quaternions"]):
                self.assertTrue(math.isfinite(t))
                self.assertAlmostEqual(math.sqrt(sum(x*x for x in q)), 1.0, delta=0.02)
        semantic = fxm_tool.decode_fxm_semantic(data)
        self.assertGreater(semantic["stats"]["rotation_tracks"], 0)
        rot = [n for n in semantic["nodes"] if n.get("kind") == "rotation"]
        self.assertEqual(len(rot), len(tracks))


    def test_trailing_name_fxm_variant(self):
        """Cockpit-wiper FXM files place the node name after the keyframes."""
        p = ROOT.parent / ("Race07Complete/GameData/Teams/Camaro/"
                           "Chevrolet_CPITWIPER.FXM")
        if not p.is_file():
            self.skipTest("trailing-name FXM sample not present")
        data = p.read_bytes()
        nodes = fxm_tool.parse_trailing_name_nodes(data)
        self.assertGreaterEqual(len(nodes), 1)
        self.assertTrue(any("CPITWIPER" in n["name"].upper() for n in nodes))
        for node in nodes:
            dec = fxm_tool.decode_node_keys(data, node)
            self.assertEqual(len(dec["keys"]), 2)
            for key in dec["keys"]:
                self.assertAlmostEqual(key["quat_norm"], 1.0, delta=0.02)
        self.assertEqual(fxm_tool.decode_fxm_semantic(data)["variant"],
                         "trailing-name")


    def test_single_key_fxa_variant(self):
        """FXA wipers use marker=0 with one key and a 28-byte tail."""
        p = ROOT.parent / ("Race07Complete/GameData/Teams/BMW_CSL/"
                           "Bmw_CPITWIPER.FXA")
        if not p.is_file():
            self.skipTest("single-key FXA sample not present")
        data = p.read_bytes()
        nodes = fxm_tool.parse_single_key_nodes(data)
        self.assertGreaterEqual(len(nodes), 1)
        for node in nodes:
            self.assertEqual(node["marker"], 0)
            self.assertEqual(len(node["tail"]), 28)
            self.assertAlmostEqual(math.sqrt(sum(x*x for x in node["quaternion"])),
                                   1.0, delta=0.02)
        self.assertEqual(fxm_tool.decode_fxm_semantic(data)["variant"],
                         "single-key")


    def test_file_key_count_encodes_node_kind_corpus(self):
        """file key_count=3 for TRS nodes, 1 for rotation tracks (56,838 nodes)."""
        import glob
        counts = collections.Counter()
        for corpus in ("GTR2Steam", "GTLSteam", "BMWM3Challenge", "Race07Complete",
                       "Race07Vanilla", "VolvoTheGame"):
            for p in glob.glob(str(ROOT.parent / corpus / "**" / "*"), recursive=True):
                if not Path(p).is_file() or not p.lower().endswith((".fxm", ".fxa", ".lma")):
                    continue
                try:
                    data = Path(p).read_bytes()
                except OSError:
                    continue
                for parser in (fxm_tool.parse_node_records,
                               fxm_tool.parse_length_prefixed_nodes,
                               fxm_tool.parse_rotation_track_nodes,
                               fxm_tool.parse_trailing_name_nodes,
                               fxm_tool.parse_single_key_nodes):
                    try:
                        nodes = parser(data)
                    except Exception:
                        continue
                    for node in nodes:
                        fkc = node.get("key_count")
                        if "frames" in node:  # rotation track: file key_count=1
                            self.assertEqual(fkc, 1, p)
                            counts[1] += 1
                        else:
                            self.assertEqual(fkc, 3, p)
                            counts[3] += 1
        self.assertGreater(counts[3], 40000)
        self.assertGreater(counts[1], 10000)


if __name__ == "__main__":
    unittest.main()
