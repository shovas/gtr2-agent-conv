"""Tests for the rFactor->SimBin AIW text conversion rules."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simbin_text_tool as stt  # noqa: E402

SAMPLE = """//[[gMa1.000f (c)2004    ]] [[            ]]
[Waypoint]
wp_pos=(-1.5474,3.7705,419.8781)
wp_normal=(-0.0471,0.9989,-0.0089)
wp_vect=(-0.0075,-0.0469,-5.2486)
wp_galpha=(1.0000)
wp_cheat=(72.4523)
wp_test_speed=(72.452301)
wp_pathabstraction=(0,-1)
wp_branchID=(0)
wp_bitfields=(0)
WP_PTRS=(10,12,-1,0)
"""


class AiwConvertTest(unittest.TestCase):
    def test_rules_from_gtr2_tools(self):
        out = stt.aiw_for_simbin(SAMPLE)
        self.assertIn("wp_galpha=(0.4500)", out)
        self.assertIn("wp_event=(1.000,0,0)", out)
        for tag in ("wp_normal", "wp_vect", "wp_cheat", "wp_test_speed", "wp_pathabstraction"):
            self.assertNotIn(tag, out)
        self.assertIn("wp_pos=(-1.5474,3.7705,419.8781)", out)
        self.assertIn("WP_PTRS=(10,12,-1,0)", out)

    def test_preserves_other_lines(self):
        out = stt.aiw_for_simbin(SAMPLE)
        self.assertIn("//[[gMa1.000f", out)
        self.assertIn("[Waypoint]", out)
        self.assertIn("wp_branchID=(0)", out)

    def test_simbin_input_is_idempotent(self):
        once = stt.aiw_for_simbin(SAMPLE)
        self.assertEqual(stt.aiw_for_simbin(once), once)


    def test_waypoint_ptrs_class_corpus(self):
        """WP_PTRS[3] buckets and branchID equality hold corpus-wide."""
        import glob
        files = []
        for corpus in ("GTLSteam", "GTR2Steam", "Race07Complete", "BMWM3Challenge",
                       "F12002", "GTR1Vanilla"):
            files += glob.glob(str(ROOT.parent / corpus / "**" / "*.aiw"), recursive=True)
        if not files:
            self.skipTest("no AIW corpus present")
        checked = 0
        kinds = set()
        for path in files:
            with self.subTest(path=path):
                aiw = stt.parse_aiw(stt.read_text(path))
                self.assertGreater(len(aiw.waypoints), 0)
                self.assertEqual(stt.validate_aiw_waypoints(aiw), [])
                for wp in aiw.waypoints:
                    self.assertEqual(len(wp.ptrs), 4)
                    k = wp.kind()
                    self.assertIn(k, ("track", "pit", "grid", "pitbox"))
                    kinds.add(k)
                    checked += 1
        self.assertGreaterEqual(checked, 30000)
        self.assertEqual(kinds, {"track", "pit", "grid", "pitbox"})

    def test_waypoint_ptrs_parse_and_validation(self):
        sample = """[Waypoint]
wp_pos=(1.0,2.0,3.0)
WP_PTRS=(10,2,-1,0)
wp_branchID=(0)
wp_pos=(4.0,5.0,6.0)
WP_PTRS=(0,3,-1,1)
wp_branchID=(1)
"""
        aiw = stt.parse_aiw(sample)
        self.assertEqual(aiw.waypoints[0].ptrs, (10, 2, -1, 0))
        self.assertEqual(aiw.waypoints[0].kind(), "track")
        self.assertEqual(aiw.waypoints[1].kind(), "pit")
        self.assertEqual(stt.validate_aiw_waypoints(aiw), [])
        aiw.waypoints[1].branch_id = 7
        self.assertEqual(len(stt.validate_aiw_waypoints(aiw)), 1)


    def test_cam_parse_and_negated_position(self):
        p = ROOT.parent / "GTLSteam/GameData/Locations/Spa/Spa.cam"
        if not p.is_file():
            self.skipTest("CAM sample not present")
        info = stt.parse_cam(stt.read_text(p))
        self.assertEqual(len(info.cameras), 35)
        first = info.cameras[0]
        self.assertEqual(first.kind, "StaticCam")
        self.assertEqual(first.fov, (60.0, 45.0))
        self.assertEqual(first.clip_planes, (3.0, 1750.0))
        self.assertEqual(first.aiw_position(),
                         (-first.position[0], first.position[1], -first.position[2]))

    def test_cam_negation_corpus(self):
        """Negating CAM X/Z brings cameras measurably closer to AIW waypoints."""
        import glob
        import math
        import os
        import re
        vec = r"\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)"
        pairs = 0
        for corpus in ("GTLSteam", "GTR2Steam", "BMWM3Challenge", "Race07Complete"):
            for aiw in glob.glob(str(ROOT.parent / corpus / "**" / "*.aiw"), recursive=True):
                cams = glob.glob(os.path.join(os.path.dirname(aiw), "*.cam"))
                if not cams:
                    continue
                text = stt.read_text(aiw)
                wps = [tuple(float(x) for x in m.groups())
                       for m in re.finditer(r"wp_pos\s*=" + vec, text)]
                if len(wps) < 20:
                    continue
                positions = []
                for cam in cams:
                    for c in stt.parse_cam(stt.read_text(cam)).cameras:
                        if c.position:
                            positions.append(c.position)
                if not positions:
                    continue
                def mean_dist(negate):
                    total = 0.0
                    for px, py, pz in positions:
                        x, z = (-px, -pz) if negate else (px, pz)
                        total += min(math.sqrt((x-wx)**2 + (py-wy)**2 + (z-wz)**2)
                                     for wx, wy, wz in wps)
                    return total / len(positions)
                self.assertLess(mean_dist(True), mean_dist(False), aiw)
                pairs += 1
        self.assertGreaterEqual(pairs, 8)


if __name__ == "__main__":
    unittest.main()
