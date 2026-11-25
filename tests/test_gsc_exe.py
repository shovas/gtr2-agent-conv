"""Quick-tier tests for the GSC-family EXE embedded-resource reader."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gsc_exe_tool as gsc  # noqa: E402


class GscExeTest(unittest.TestCase):

    def test_marcas_resources_decode(self):
        exe = ROOT.parent / "CopaPetrobrasdeMarcas" / "Marcas.exe"
        if not exe.is_file():
            self.skipTest("Marcas.exe not present")
        container = gsc.read_container(exe)
        self.assertEqual(container.version, 2)
        self.assertEqual(len(container.resources), 45)
        self.assertEqual(len(container.key_list()), 32)

        scn = container.get("Gamedata\\Locations\\Brasilia\\Brasilia\\Brasilia.scn")
        data, ok = gsc.decode_resource(scn, container.key_list()[1])
        self.assertTrue(ok)
        self.assertEqual(len(data), 161671)
        self.assertTrue(data.startswith(b"CUBEASF\r\n"))

    def test_marcas_embedded_scn_references(self):
        """All six embedded .scn resolve their MAS refs via EXE resources."""
        import simbin_text_tool as stt
        exe = ROOT.parent / "CopaPetrobrasdeMarcas" / "Marcas.exe"
        if not exe.is_file():
            self.skipTest("Marcas.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        key_index = 0
        scripts = []
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                key = keys[min(key_index, len(keys) - 1)]
                key_index += 1
            if res.name.lower().endswith(".scn"):
                data, ok = gsc.decode_resource(res, key)
                self.assertTrue(ok, res.name)
                scripts.append(stt.parse_scn(data.decode("latin-1")))
        self.assertEqual(len(scripts), 6)
        refs = [value for info in scripts for value in info.mas_files]
        self.assertEqual(len(refs), 45)
        embedded = {res.name.replace("\\", "/").rsplit("/", 1)[-1].lower()
                    for res in container.resources}
        adpack = {v.lower() for v in refs if "adpackstockcar" in v.lower()}
        self.assertEqual(adpack, {"adpackstockcar.mas"})
        self.assertIn("adpackstockcar.mas", embedded)

    def test_unsupported_family_is_raw(self):
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        res = container.get("GameData\\Locations\\Brasilia\\Brasilia\\Brasilia.scn")
        data, ok = gsc.decode_resource(res, container.key_list()[1])
        self.assertFalse(ok)
        self.assertEqual(data, res.data)

    def test_ams_decrypts_without_decompression(self):
        exe = ROOT.parent / "Automobilista" / "AMS.exe"
        if not exe.is_file():
            self.skipTest("AMS.exe not present")
        container = gsc.read_container(exe)
        res = container.get("GameData\\Locations\\Adelaide\\Adelaide\\Adelaide.AIW")
        data, ok = gsc.decode_resource(res, container.key_list()[0], "AMS.exe")
        self.assertTrue(ok)
        self.assertEqual(len(data), 59955)
        self.assertFalse(data.startswith(b"\x01\x00\x00\x00"))


if __name__ == "__main__":
    unittest.main()
