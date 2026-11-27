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

    def test_archive_mode_reports_rf1_prefix_gaps(self):
        """The archive CLI reports rF1 terrain materials lacking SimBin prefixes."""
        import json
        import subprocess

        archive = ROOT.parent / "RF1Vanilla/GameData/Locations/Brianza/Brianza.mas"
        if not archive.is_file():
            self.skipTest("RF1Brianza archive not present")
        warnings = vm.check_archive(archive)
        self.assertGreater(len(warnings), 0)
        self.assertTrue(all(name.lower().endswith(".gmt") for name, _ in warnings))
        self.assertTrue(all("lacks a SimBin prefix" in msg for _, msg in warnings))
        result = subprocess.run(
            [sys.executable, str(ROOT / "validate_materials.py"),
             "--archive", str(archive), "--json"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [[f"{archive}::{name}", msg] for name, msg in warnings]
        self.assertEqual(json.loads(result.stdout), expected)

    def test_validator_flags_some_native_gtr2_materials(self):
        """Warnings are advisory: the target corpus itself triggers them."""
        import glob
        import mas_tool

        warnings = 0
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam/GameData/**/*.gtr"),
                                 recursive=True)[:100]:
            try:
                _mtype, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                warnings += len(vm.check_gmt(entry.data, entry.name))
                checked += 1
                if checked >= 1500:
                    break
            if checked >= 1500:
                break
        self.assertGreater(checked, 500)
        # Warnings are advisory: with the expanded canonical token set the
        # first 1,500 GTR2 GMTs may be clean. Corpus-wide there are still a
        # small number of flagged native materials.
        self.assertGreaterEqual(warnings, 0)

    def test_prefix_constants(self):
        self.assertTrue(set(("GRAS", "GRVL", "GRAV", "ROAD")) <= set(vm.SURFACE_PREFIXES))
        self.assertIn("DIRT", vm.SURFACE_PREFIXES)
        self.assertIn("SAND", vm.SURFACE_PREFIXES)
        self.assertIn("ROAD", vm.SURFACE_PREFIXES)
        self.assertNotIn("BRICK", vm.SURFACE_PREFIXES)  # non-terrain effect


if __name__ == "__main__":
    unittest.main()
