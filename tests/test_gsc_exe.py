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

    def test_marcas_embedded_vehicle_configs(self):
        """Embedded vehicle physics configs decode to rF1-era key vocabularies."""
        import re
        exe = ROOT.parent / "CopaPetrobrasdeMarcas" / "Marcas.exe"
        if not exe.is_file():
            self.skipTest("Marcas.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        key_index = 0
        by_ext: dict[str, list[set[str]]] = {}
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                key = keys[min(key_index, len(keys) - 1)]
                key_index += 1
            ext = res.name.lower().rsplit(".", 1)[-1]
            if ext not in ("hdv", "gen", "tbc", "pm", "sfx"):
                continue
            data, ok = gsc.decode_resource(res, key)
            self.assertTrue(ok, res.name)
            by_ext.setdefault(ext, []).append({
                match.group(1).lower() for match in re.finditer(
                    r"(?m)^\s*([A-Za-z_]\w*)\s*=", data.decode("latin-1"))})
        self.assertEqual({ext: len(items) for ext, items in by_ext.items()},
                         {"gen": 6, "hdv": 5, "pm": 2, "tbc": 2, "sfx": 2})
        for ext, expected in (("hdv", 288), ("gen", 6), ("tbc", 38),
                              ("pm", 3), ("sfx", 116)):
            universal = set.intersection(*by_ext[ext])
            self.assertEqual(len(universal), expected, ext)

    def test_marcas_embedded_config_validators(self):
        """Embedded vehicle configs satisfy their own corpus-derived bounds."""
        import simbin_text_tool as stt
        exe = ROOT.parent / "CopaPetrobrasdeMarcas" / "Marcas.exe"
        if not exe.is_file():
            self.skipTest("Marcas.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        key_index = 0
        checked = 0
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                key = keys[min(key_index, len(keys) - 1)]
                key_index += 1
            ext = res.name.lower().rsplit(".", 1)[-1]
            if ext not in stt.EMBEDDED_MARCAS_NUMERIC_BOUNDS:
                continue
            data, ok = gsc.decode_resource(res, key)
            self.assertTrue(ok, res.name)
            self.assertEqual(stt.validate_embedded_marcas_config(data, ext), [], res.name)
            checked += 1
        self.assertEqual(checked, 17)
        self.assertTrue(stt.validate_embedded_marcas_config(b"bumptravel=1", "hdv")[0].startswith(
            "hdv: bumptravel=1.0 outside"))
        self.assertEqual(stt.validate_embedded_marcas_config(b"x=1", "car"),
                         ["unsupported embedded config extension car"])

    def test_unsupported_family_is_raw(self):
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        res = container.get("GameData\\Locations\\Brasilia\\Brasilia\\Brasilia.scn")
        data, ok = gsc.decode_resource(res, container.key_list()[1])
        self.assertFalse(ok)
        self.assertEqual(data, res.data)

    def test_sce_resources_decode(self):
        """StockCarExtreme resources use the SCE key schedule (+11)."""
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        scn = container.get("GameData\\Locations\\BolognaHistoric\\"
                            "BolognaHistoric\\bolognahistoric.scn")
        data, ok = gsc.decode_resource(scn, keys[11])
        self.assertTrue(ok)
        self.assertTrue(data.startswith(b"CUBEASF\r\n"))
        self.assertGreater(len(data), 100_000)

    def test_sce_scn_references(self):
        """All MASFile refs in 70 SCE embedded .scn resolve in-locale."""
        import os
        import simbin_text_tool as stt
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        index = 0
        refs = []
        parsed = 0
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                if res.kind == 1:
                    key = keys[index + 11]
                    index += 1
            if not res.name.lower().endswith(".scn"):
                continue
            data, ok = gsc.decode_resource(res, key)
            self.assertTrue(ok, res.name)
            refs.extend(stt.parse_scn(data.decode("latin-1")).mas_files)
            parsed += 1
        self.assertEqual(parsed, 70)
        self.assertEqual(len(refs), 543)
        loose = {os.path.basename(p).lower() for p in
                 (ROOT.parent / "StockCarExtreme").glob("**/*") if p.is_file()}
        embedded = {res.name.replace("\\", "/").rsplit("/", 1)[-1].lower()
                    for res in container.resources}
        basenames = {os.path.basename(v.replace("\\", "/")).lower() for v in refs}
        self.assertEqual(basenames, basenames & (loose | embedded))
        self.assertEqual(len({v for v in refs if
                              os.path.basename(v.replace("\\", "/")).lower()
                              not in loose}), 2)

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
