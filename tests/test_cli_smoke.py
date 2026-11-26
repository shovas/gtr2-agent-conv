"""Smoke test: every documented CLI entrypoint imports and responds to --help."""
import subprocess
import sys
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
