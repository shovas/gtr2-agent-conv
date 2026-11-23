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


if __name__ == "__main__":
    unittest.main()
