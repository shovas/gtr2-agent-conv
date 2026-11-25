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


if __name__ == "__main__":
    unittest.main()
