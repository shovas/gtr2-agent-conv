"""Corpus-independent BC7 decoder tests.

The block decoder was verified against an independent Python transcription of
the spec-derived `patodois/bcn-decode` reference on 8,000 random blocks (all
8 modes). These tests guard the aligned tables and the DDS integration. No BC7
samples exist in the local corpus.
"""
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bc7_format as bc7  # noqa: E402
import media_tool  # noqa: E402


class TestBc7Format(unittest.TestCase):
    def test_spec_tables(self):
        self.assertEqual(len(bc7.MODES), 8)
        self.assertEqual(bc7.PARTITION2[0][:4], [0, 0, 1, 1])
        self.assertEqual(len(bc7.PARTITION3), 64)
        self.assertEqual(bc7.ANCHOR3_1[0], 3)
        self.assertEqual(bc7.ANCHOR3_2[0], 15)

    def test_all_modes_zero_block(self):
        for mode in range(8):
            with self.subTest(mode=mode):
                blk = bytes([1 << mode]) + bytes(15)
                # Modes 0-3 have no explicit alpha: it decodes to opaque.
                alpha = 255 if mode < 4 else 0
                self.assertEqual(bc7.decode_block(blk), [(0, 0, 0, alpha)] * 16)

    def test_mode0_max_endpoints_white(self):
        px = bc7.decode_block(bytes([0xFF] * 16))
        self.assertEqual(px, [(255, 255, 255, 255)] * 16)

    def test_mode6_max_endpoints_white(self):
        blk = bytes([0xC0]) + bytes([0xFF] * 15)  # mode 6
        self.assertEqual(bc7.decode_block(blk), [(255, 255, 255, 255)] * 16)

    def test_reserved_block(self):
        self.assertEqual(bc7.decode_block(bytes(16)), [(0, 0, 0, 0)] * 16)

    def test_rotation_uses_spec_swapping(self):
        # Mode 4 has 2 rotation bits (bits 1-2) and a 1-bit index selector
        # (bit 3). Rotation 1 must swap the separate red channel with alpha.
        # Compare rotation 0 and 1 on otherwise identical headers: the decoded
        # red and alpha channels exchange.
        def make(rot):
            # mode 4: mode bit at 4, rotation bits at 5-6, selector at 7,
            # six 5-bit colour endpoints from bit 8, two 6-bit alpha endpoints
            # from bit 38. Colour endpoints 0, alpha endpoints max.
            v = (1 << 4) | (rot << 5) | (0x3F << 38) | (0x3F << 44)
            return v.to_bytes(16, "little")
        plain = bc7.decode_block(make(0))[0]
        rotated = bc7.decode_block(make(1))[0]
        self.assertEqual(plain, (0, 0, 0, 255))
        self.assertEqual(rotated, (255, 0, 0, 0))

    def test_decode_bc7_image(self):
        blk = bytes([0xFF] * 16)
        rgba = bc7.decode_bc7(blk * 4, 8, 8)
        self.assertEqual(len(rgba), 8 * 8 * 4)
        self.assertEqual(rgba[:4], b"\xff\xff\xff\xff")
        self.assertIsNone(bc7.decode_bc7(b"", 8, 8))

    def test_dx10_bc7_dds_read(self):
        hdr = bytearray(148)
        struct.pack_into("<I", hdr, 0, 0x20534444)
        struct.pack_into("<I", hdr, 4, 124)
        struct.pack_into("<I", hdr, 12, 4)
        struct.pack_into("<I", hdr, 16, 4)
        struct.pack_into("<I", hdr, 80, 32)
        struct.pack_into("<I", hdr, 84, 0x30315844)
        struct.pack_into("<5I", hdr, 128, 98, 3, 0, 1, 0)  # BC7_UNORM
        with tempfile.NamedTemporaryFile(suffix=".dds", delete=False) as fh:
            fh.write(bytes(hdr) + bytes([0xFF] * 16))
            path = fh.name
        try:
            dds = media_tool.read_dds(path)
            self.assertEqual(dds.fourcc, "BC7_UNORM")
            self.assertEqual(dds.rgba[:4], b"\xff\xff\xff\xff")
            with self.assertRaises(ValueError):
                dds.to_bytes()  # write-back intentionally unsupported
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
