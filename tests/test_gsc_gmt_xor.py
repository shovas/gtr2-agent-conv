"""Quick-tier detector tests for XOR-masked opaque GSC GMT headers."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_semantic  # noqa: E402
import isi_crypt  # noqa: E402
import mas_tool  # noqa: E402


class GscGmtXorTest(unittest.TestCase):
    def test_purchased_gmt_masked_header(self):
        archive = ROOT.parent / "CopaPetrobrasdeMarcas" / "Gamedata" / \
            "Vehicles" / "showroom.mas"
        if not archive.is_file():
            self.skipTest("showroom.mas not present")
        _, entries = mas_tool.read_archive(str(archive))
        entry = next((e for e in entries if e.name.lower() == "purchased.gmt"), None)
        if entry is None:
            self.skipTest("PURCHASED.GMT not present")
        data = isi_crypt.decrypt_bytes(entry.data, 1)
        self.assertIsNotNone(gmt_semantic.opaque_gsc_flags(data))
        self.assertEqual(gmt_semantic.read_gmt(data).get("submeshes"), [])
        self.assertEqual(gmt_semantic.gsc_xor_magic_key(data), 0x0B)
        self.assertEqual(gmt_semantic.gsc_masked_submeshes(data),
                         [(740, 0xFB, 0x20004011)])
        # Region-specific masks restore known old-layout fields.
        mask_table = bytes((i ^ 0x0C) for i in range(256))
        mask_body = bytes((i ^ 0x0B) for i in range(256))
        head = data[:0x194].translate(mask_table) + data[0x194:].translate(mask_body)
        self.assertEqual(head[0x194:0x19D], b"purchased")
        self.assertEqual(head[0x1D4:0x1E4], gmt_semantic.OLD_GMT_MAGIC)


    def test_region_masked_file_remains_unsupported(self):
        """PURCHASED.GMT has region keys but no derivable bulk key."""
        archive = ROOT.parent / "CopaPetrobrasdeMarcas" / "Gamedata" / \
            "Vehicles" / "showroom.mas"
        if not archive.is_file():
            self.skipTest("showroom.mas not present")
        _, entries = mas_tool.read_archive(str(archive))
        entry = next((e for e in entries if e.name.lower() == "purchased.gmt"), None)
        if entry is None:
            self.skipTest("PURCHASED.GMT not present")
        data = isi_crypt.decrypt_bytes(entry.data, 1)
        self.assertEqual(gmt_semantic.gsc_xor_magic_key(data), 0x0B)
        self.assertEqual(gmt_semantic.gsc_masked_submeshes(data),
                         [(740, 0xFB, 0x20004011)])
        self.assertIsNone(gmt_semantic.decode_gsc_xor_gmt(data))

    def test_xor_decode_does_not_restore_geometry(self):
        """A structurally decoded GMT usually still has masked bulk vertices."""
        import mas_tool
        for root, name in (("CopaPetrobrasdeMarcas", "TRACKWORKERRIGHT.GMT"),
                           ("Automobilista", "AMBULANCE_LOD001.GMT")):
            base = ROOT.parent / root
            if not base.is_dir():
                continue
            found = False
            for archive in base.glob("**/*.mas"):
                try:
                    _, entries = mas_tool.read_archive(str(archive))
                except Exception:
                    continue
                entry = next((e for e in entries
                              if e.name.lower().endswith(name.lower())), None)
                if entry is None:
                    continue
                data = isi_crypt.decrypt_bytes(entry.data, 1)
                result = gmt_semantic.decode_gsc_xor_gmt(data)
                self.assertIsNotNone(result)
                quality = gmt_semantic.read_gsc_geometry(result[0])
                self.assertFalse(quality.get("plausible_positions"), name)
                found = True
                break
            self.assertTrue(found, f"{root}/{name} not found")

    def test_whole_file_xor_decodes_subset(self):
        """Magic-derived masks restore GMT structure in 4 corpora (not geometry)."""
        cases = (
            ("CopaPetrobrasdeMarcas", "TRACKWORKERRIGHT.GMT"),
            ("GameStockCar", "TR_LF_LVL1.GMT"),
            ("StockCarExtreme", "STARTBOX.GMT"),
            ("Automobilista", "AMBULANCE_LOD001.GMT"),
        )
        for root, name in cases:
            base = ROOT.parent / root
            if not base.is_dir():
                continue
            found = False
            for archive in base.glob("**/*.mas"):
                try:
                    _, entries = mas_tool.read_archive(str(archive))
                except Exception:
                    continue
                entry = next((e for e in entries
                              if e.name.lower().endswith(name.lower())), None)
                if entry is None:
                    continue
                data = isi_crypt.decrypt_bytes(entry.data, 1)
                result = gmt_semantic.decode_gsc_xor_gmt(data)
                self.assertIsNotNone(result, f"{root}/{name}")
                decoded, mask = result
                self.assertNotEqual(mask, 0)
                self.assertTrue(gmt_semantic.read_gmt(decoded).get("submeshes"))
                # Structural decode only: bulk vertices are often still masked.
                self.assertIsInstance(gmt_semantic.read_gsc_geometry(decoded), dict)
                found = True
                break
            self.assertTrue(found, f"{root}/{name} not found")


if __name__ == "__main__":
    unittest.main()
