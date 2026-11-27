"""Smoke test: every documented CLI entrypoint imports and responds to --help."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOOLS = (
    "anm_format.py", "batch_convert.py", "corpus_diff.py", "fxm_tool.py",
    "gmt_format.py", "gmt_layout.py", "gmt_semantic.py", "gmt_tool.py",
    "gsc_exe_tool.py", "gtl_to_gtr2.py", "gzip_simbin_tool.py",
    "isi_crypt.py", "isi_gm_crypt.py", "jca_crypt.py", "mas_tool.py",
    "media_tool.py", "mts_format.py", "phs_tool.py", "race_gmt.py",
    "rf1_to_gtr2.py", "simbin_events_tool.py", "simbin_text_tool.py",
    "text_convert.py", "validate_conversion.py", "validate_materials.py",
    "vrl_to_gmt.py", "gtr1_to_gmt.py", "ghost_align.py",
)


class CliSmokeTest(unittest.TestCase):
    def test_text_convert_cli_check_and_write(self):
        """text_convert.py --check writes nothing; normal mode matches the API."""
        import contextlib
        import io

        sys.path.insert(0, str(ROOT))
        import text_convert as tc

        source = ROOT.parent / "RF1Vanilla/GameData/Locations/Joesville"
        if not source.is_dir():
            self.skipTest("RF1Vanilla Joesville not present")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            check_target = Path(td) / "check"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tc.main([str(source), str(check_target), "--check"]), 0)
            self.assertIn("archives", out.getvalue())
            self.assertFalse(check_target.exists())
            cli_target = Path(td) / "cli"
            api_target = Path(td) / "api"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tc.main([str(source), str(cli_target)]), 0)
            tc.convert_tree(source, api_target)
            cli_files = {p.relative_to(cli_target): p.read_bytes()
                         for p in cli_target.rglob("*") if p.is_file()}
            api_files = {p.relative_to(api_target): p.read_bytes()
                         for p in api_target.rglob("*") if p.is_file()}
            self.assertTrue(cli_files)
            self.assertEqual(cli_files, api_files)

    def test_batch_convert_cli_bounded(self):
        """batch_convert.py --limit 1 writes one member per family."""
        import contextlib
        import io

        sys.path.insert(0, str(ROOT))
        import batch_convert as bc

        template = next((p for p in (ROOT.parent / "GTR2Steam/GameData").rglob("*.gmt")
                         if p.is_file()), None)
        if template is None:
            self.skipTest("GTR2 GMT template not present")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(bc.main(
                    ["--template", str(template), "--out", td, "--limit", "1"]), 0)
            printed = out.getvalue()
            for family in ("vrl", "gtr1", "gsc", "racegmt"):
                self.assertIn(f"{family}_scanned=1", printed)
                self.assertIn(f"{family}_written=1", printed)

    def test_all_tools_respond_to_help(self):
        for name in TOOLS:
            with self.subTest(tool=name):
                path = ROOT / name
                if not path.is_file():
                    continue
                result = subprocess.run(
                    [sys.executable, str(path), "--help"],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr[:400])


if __name__ == "__main__":
    unittest.main()
