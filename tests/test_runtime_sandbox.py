"""Tests for the safe read-only-game sandbox builder."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runtime_sandbox as rs  # noqa: E402


class RuntimeSandboxTest(unittest.TestCase):
    def test_substituted_paths_are_real_and_stock_untouched(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            base = Path(td)
            game = base / "game"
            (game / "GameData/Locations/Hockenheim").mkdir(parents=True)
            (game / "UserData").mkdir()
            (game / "GTR2Dedicated.exe").write_bytes(b"EXE")
            (game / "GameData/Locations/Hockenheim/stock.trk").write_bytes(b"STOCK")
            (game / "GameData/Locations/Hockenheim/sibling.gdb").write_bytes(b"GDB")
            (game / "UserData/existing.txt").write_bytes(b"LOG")

            dest = rs.build_sandbox(game, base / "sandbox", {
                "GameData/Locations/Hockenheim/stock.trk": b"REPLACED",
            })
            replaced = dest / "GameData/Locations/Hockenheim/stock.trk"
            self.assertTrue(replaced.is_file())
            self.assertFalse(replaced.is_symlink())
            self.assertEqual(replaced.read_bytes(), b"REPLACED")
            for rel in ("GameData", "GameData/Locations",
                        "GameData/Locations/Hockenheim"):
                self.assertFalse((dest / rel).is_symlink(), rel)
            self.assertTrue((dest / "GameData/Locations/Hockenheim/sibling.gdb").is_symlink())
            self.assertTrue((dest / "GTR2Dedicated.exe").is_symlink())
            self.assertFalse((dest / "UserData").is_symlink())
            ini = dest / "UserData/DedicatedServer.ini"
            self.assertTrue(ini.is_file())
            text = ini.read_text("ascii")
            self.assertIn("[SETTINGS]", text)
            self.assertIn("GameDatabase=", text)
            self.assertIn("[TRACKS]", text)
            self.assertEqual(rs.assert_no_mutable_symlinks(
                dest, ["GameData/Locations/Hockenheim/stock.trk"]), [])
            self.assertEqual(
                (game / "GameData/Locations/Hockenheim/stock.trk").read_bytes(), b"STOCK")

    def test_ini_settings_override(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            path = Path(td) / "DedicatedServer.ini"
            rs.write_ini(path, {"RaceName": '"Override"'})
            text = path.read_text("ascii")
            self.assertIn('RaceName="Override"', text)
            self.assertNotIn('RaceName="Probe"', text)
            self.assertTrue(path.read_bytes().endswith(b"[TRACKS]\r\n"))


if __name__ == "__main__":
    unittest.main()
