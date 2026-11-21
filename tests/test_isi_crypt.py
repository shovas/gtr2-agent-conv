import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import isi_crypt  # noqa: E402


class IsiCryptTest(unittest.TestCase):
    def test_roundtrip_gmt_skip4(self):
        raw = b"GMTTEST" + bytes(range(256)) * 20
        enc = isi_crypt.encrypt_bytes(raw, skip=4, sign=0x4b1dca9f960524e8, key=0x0102030405060708)
        dec = isi_crypt.decrypt_bytes(enc, skip=4)
        self.assertEqual(dec, raw)

    def test_roundtrip_no_skip(self):
        raw = b"MASDATA" + bytes(range(256)) * 10
        enc = isi_crypt.encrypt_bytes(raw, skip=0, sign=0x4b1dca9f960524e8, key=0x1112131415161718)
        dec = isi_crypt.decrypt_bytes(enc, skip=0)
        self.assertEqual(dec, raw)

    def test_matches_rfactordec_if_present(self):
        rfactordec = ROOT.parent / "rfactortools" / "rfactordec.c"
        # only run if we have the compiled binary we used earlier
        bin_path = Path("/tmp/opencode/rfactordec")
        if not bin_path.exists() or not rfactordec.exists():
            self.skipTest("rfactordec binary not present")
        raw = b"GMT" + bytes(range(256)) * 8
        enc = isi_crypt.encrypt_bytes(raw, skip=4, sign=0x4b1dca9f960524e8, key=0x0102030405060708)
        tmp = Path("/tmp/opencode")
        (tmp / "py_enc.gmt").write_bytes(enc)
        import subprocess
        r = subprocess.run([str(bin_path), "-o", "-y", str(tmp / "py_enc.gmt"), str(tmp / "dec_ref.gmt")], capture_output=True, text=True)
        self.assertEqual((tmp / "dec_ref.gmt").read_bytes(), raw, f"rfactordec rc={r.returncode} stderr={r.stderr[-200:]}")


if __name__ == "__main__":
    unittest.main()
