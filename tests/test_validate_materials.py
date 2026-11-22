"""Tests for the SimBin material-prefix validator."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_materials as vm  # noqa: E402


class MaterialValidatorTest(unittest.TestCase):
    def test_real_gmt_runs_without_crashing(self):
        base = ROOT.parent / "GTR2Steam"
        sample = None
        for p in base.rglob("*.gtr"):
            import mas_tool
            sample = next((e.data for e in mas_tool.read_archive(p)[1] if e.name.lower().endswith(".gmt")), None)
            if sample:
                break
        if sample is None:
            self.skipTest("GTR2 GMT sample not present")
        self.assertIsInstance(vm.check_gmt(sample), list)

    def test_prefix_constants(self):
        self.assertEqual(vm.SURFACE_PREFIXES, ("GRAS", "GRVL", "GRAV", "ROAD"))


if __name__ == "__main__":
    unittest.main()
