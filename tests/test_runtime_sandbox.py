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

    def test_session_result_parsing_and_acceptance(self):
        """Session result files reveal which track the engine actually used."""
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            results_dir = Path(td) / "Results"
            results_dir.mkdir()
            payload = (
                '//[[gMa1.000f (c)2004    ]] [[\x00\x00]]\r\n'
                '[Header]\r\nGame=GTR2\r\n\r\n[Race]\r\nRaceMode=5\r\n'
                'Scene=GAMEDATA\\LOCATIONS\\Hockenheim\\NTHockenheim.TRK\r\n'
                'AIDB=GAMEDATA\\LOCATIONS\\Hockenheim\\NTHockenheim.AIW\r\n'
                'Track Length=656.6953\r\n'
            ).encode("latin-1")
            (results_dir / "Probe_Practice1.txt").write_bytes(payload)
            parsed = rs.parse_session_results(results_dir)
            self.assertEqual(len(parsed), 1)
            self.assertAlmostEqual(parsed[0]["track_length"], 656.6953)
            report = rs.acceptance_report(parsed, "NTHockenheim.TRK", 656.7)
            self.assertTrue(report["accepted"])
            self.assertEqual(report["scene_matches"], 1)
            bad = rs.acceptance_report(parsed, "3ANDERSTORP.TRK", 4018.0)
            self.assertFalse(bad["accepted"])

    def test_client_config_patch_preserves_other_keys(self):
        cfg = (b"//[[gMa1.000f]]\r\nVIDEOMODE=12\r\nVIDEORAM=-52\r\n"
               b"SHADERLEVEL=0\r\nRaceName=Probe\r\n")
        patched = rs.patch_client_config(cfg)
        self.assertIn(b"VIDEOMODE=0\r\n", patched)
        self.assertIn(b"VIDEORAM=256\r\n", patched)
        self.assertIn(b"SHADERLEVEL=0\r\n", patched)
        self.assertIn(b"RaceName=Probe\r\n", patched)
        self.assertEqual(patched.count(b"VIDEOMODE="), 1)

    def test_status_cli_runtime_report(self):
        """The dashboard CLI summarises runtime acceptance results."""
        import contextlib
        import io

        import conversion_status

        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
            result = Path(td) / "A_Practice1.txt"
            result.write_bytes(
                b"//[[gMa1.000f]]\r\n[Race]\r\n"
                b"Scene=GAMEDATA\\LOCATIONS\\Hockenheim\\NTHockenheim.TRK\r\n"
                b"Track Length=656.6953\r\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(conversion_status.main(
                    ["--runtime-results", td, "--expect-scene",
                     "NTHockenheim.TRK", "--expect-length", "656.7"]), 0)
            self.assertIn("Accepted: yes", out.getvalue())
            with contextlib.redirect_stdout(out):
                self.assertEqual(conversion_status.main(
                    ["--runtime-results", td, "--expect-scene", "WRONG.TRK"]), 0)
            self.assertIn("Accepted: no", out.getvalue())

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
