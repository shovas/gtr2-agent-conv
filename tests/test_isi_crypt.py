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


    def test_optimized_stream_matches_isy_crypt2(self):
        """The precomputed stream matches the per-byte reference cipher."""
        import random
        random.seed(121)
        for enctype in (0, 1):
            for size in (1, 7, 64, 65, 129, 200):
                data = bytes(random.randrange(256) for _ in range(size))
                key = random.randrange(2 ** 64)
                for skip in (0, 4):
                    reference = bytearray(data)
                    position = skip
                    for index in range(len(reference) - skip):
                        reference[position] = (isi_crypt.isi_crypt2(
                            enctype, position - skip, key) ^ reference[position]) & 0xFF
                        position += 1
                    # Single-block comparison: no key feedback between blocks.
                    if size <= 64 and enctype == 0:
                        self.assertEqual(isi_crypt.isi_crypt(enctype, data, key,
                                                             skip=skip)[:max(0, size - skip)],
                                         bytes(reference)[:max(0, size - skip)])


if __name__ == "__main__":
    unittest.main()
