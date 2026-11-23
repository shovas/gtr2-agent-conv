"""Corpus-independent BC6H decoder tests (spec-derived synthetic fixtures).

No BC6H samples exist in the local install corpus; these fixtures are built
from the published Khronos BPTC bit layout and verify the decoder against
analytically known endpoint/partition outcomes.
"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bc6h_format as bc  # noqa: E402
import media_tool  # noqa: E402


def encode_block(mode, endpoints, partition, indices):
    """Build a 16-byte block with known endpoints/indices (inverse bit packing)."""
    v = mode
    for src, length, slot, dst in bc.RUNS[mode]:
        v |= ((endpoints[slot] >> dst) & ((1 << length) - 1)) << src
    if partition is not None:
        v |= partition << 77
    pos = 82 if partition is not None else 65
    anchor = bc.ANCHOR2[partition] if partition is not None else -1
    ib = 3 if partition is not None else 4
    for i, idx in enumerate(indices):
        n = ib - 1 if (i == 0 or i == anchor) else ib
        v |= (idx & ((1 << n) - 1)) << pos
        pos += n
    return v.to_bytes(16, "little")


class TestBc6hFormat(unittest.TestCase):
    def test_spec_tables(self):
        # Spot-check Khronos Table 114/118 entries used by the decoder.
        self.assertEqual(bc.PARTITION2[0], [0, 0, 1, 1] * 4)
        self.assertEqual(bc.PARTITION2[18][-1], 0)
        self.assertEqual(bc.PARTITION2[21][-1], 0)
        self.assertEqual(bc.ANCHOR2[16], 15)
        self.assertEqual(bc.ANCHOR2[17], 2)
        self.assertEqual(bc.WEIGHTS3[7], 64)
        self.assertEqual(bc.WEIGHTS4[15], 64)

    def test_mode3_all_black(self):
        px = bc.decode_block(encode_block(3, [0] * 12, None, [15] * 16))
        self.assertEqual(px, [(0, 0, 0, 255)] * 16)

    def test_mode3_bright_endpoints(self):
        ep = [0] * 12
        for slot in (1, 5, 9):
            ep[slot] = 1023
        px = bc.decode_block(encode_block(3, ep, None, [15] * 16))
        # Texel 0 is the subset anchor: only 3 index bits are stored, so its
        # weight is 30 (not 64) and it cannot reach endpoint E1.
        self.assertEqual(px[0], (195, 195, 195, 255))
        self.assertEqual(px[1:], [(255, 255, 255, 255)] * 15)

    def test_mode10_partition_assignment(self):
        ep = [0] * 12
        for slot in (2, 3, 6, 7, 10, 11):  # subset 1 endpoints E2/E3
            ep[slot] = 63
        px = bc.decode_block(encode_block(30, ep, 0, [0] * 16))
        part = bc.PARTITION2[0]
        self.assertTrue(all(px[i] == (0, 0, 0, 255)
                            for i in range(16) if part[i] == 0))
        self.assertTrue(all(px[i] == (255, 255, 255, 255)
                            for i in range(16) if part[i] == 1))

    def test_mode10_anchor_second_subset(self):
        # Partition 17 uses anchor texel 2 for subset 1; that texel carries a
        # 2-bit index and therefore interpolates differently from its peers.
        ep = [0] * 12
        for slot in (2, 3, 6, 7, 10, 11):
            ep[slot] = 63
        px = bc.decode_block(encode_block(30, ep, 17, [0] * 16))
        self.assertEqual(len(set(px)), 2)

    def test_sf16_signed_endpoints(self):
        # 10-bit two's complement 0x3FF == -1; negative endpoints clamp to 0
        # after interpolation, while the unsigned reading would be bright.
        ep = [0] * 12
        for slot in (0, 1, 4, 5, 8, 9):
            ep[slot] = 1023
        blk = encode_block(3, ep, None, [0] * 16)
        self.assertEqual(bc.decode_block(blk, signed=True), [(0, 0, 0, 255)] * 16)
        self.assertNotEqual(bc.decode_block(blk, signed=False),
                            bc.decode_block(blk, signed=True))

    def test_sf16_positive_endpoints(self):
        ep = [0] * 12
        for slot in (1, 5, 9):
            ep[slot] = 511  # +511 in 10-bit two's complement
        px = bc.decode_block(encode_block(3, ep, None, [15] * 16), signed=True)
        self.assertGreater(px[1][0], 200)

    def test_all_modes_zero_block_black(self):
        for code in bc.MODE_INFO:
            with self.subTest(mode=code):
                blk = bytes([code]) + bytes(15)
                self.assertEqual(bc.decode_block(blk), [(0, 0, 0, 255)] * 16)
                self.assertEqual(bc.decode_block(blk, signed=True),
                                 [(0, 0, 0, 255)] * 16)

    def test_delta_mode_endpoint(self):
        # Mode 0 is transformed: R0 occupies bits 5..14 (10-bit endpoints).
        # With zero deltas and zero indices, a max R0 makes every pixel red.
        blk = (1023 << 5).to_bytes(16, "little")
        px = bc.decode_block(blk)
        self.assertTrue(all(p[0] > 200 and p[1] == 0 and p[2] == 0 for p in px))

    def test_reserved_modes(self):
        # All 14 valid BC6H modes are supported; only codes 19/23/27/31 are
        # reserved and must be reported as unsupported rather than guessed.
        self.assertEqual(len(bc.MODE_INFO), 14)
        for code in (19, 23, 27, 31):
            blk = bytearray(16)
            blk[0] = code
            self.assertIsNone(bc.decode_block(bytes(blk)))
        self.assertIsNotNone(bc.decode_block(bytes(16)))  # mode 0, delta-coded

    def test_decode_bc6h_image(self):
        ep = [0] * 12
        for slot in (1, 5, 9):
            ep[slot] = 1023
        block = encode_block(3, ep, None, [15] * 16)
        rgba = bc.decode_bc6h(block * 4, 8, 8)
        self.assertEqual(len(rgba), 8 * 8 * 4)
        self.assertEqual(rgba[-4:], b"\xff\xff\xff\xff")
        self.assertIsNone(bc.decode_bc6h(b"\x00" * 16, 8, 8))

    def test_dx10_dds_read(self):
        ep = [0] * 12
        for slot in (1, 5, 9):
            ep[slot] = 1023
        block = encode_block(3, ep, None, [15] * 16)
        hdr = bytearray(148)
        struct.pack_into("<I", hdr, 0, 0x20534444)
        struct.pack_into("<I", hdr, 4, 124)
        struct.pack_into("<I", hdr, 12, 4)
        struct.pack_into("<I", hdr, 16, 4)
        struct.pack_into("<I", hdr, 80, 32)
        struct.pack_into("<I", hdr, 84, 0x30315844)  # 'DX10'
        struct.pack_into("<5I", hdr, 128, 95, 3, 0, 1, 0)  # BC6H_UF16, TEXTURE2D
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dds", delete=False) as fh:
            fh.write(bytes(hdr) + block)
            path = fh.name
        try:
            dds = media_tool.read_dds(path)
            self.assertEqual(dds.fourcc, "BC6H_UF16")
            self.assertEqual(dds.width, 4)
            self.assertEqual(dds.rgba[-4:], b"\xff\xff\xff\xff")
            with self.assertRaises(ValueError):
                dds.to_bytes()  # write-back is intentionally unsupported
        finally:
            os.unlink(path)

    def test_dx10_sf16_dds_read(self):
        ep = [0] * 12
        for slot in (1, 5, 9):
            ep[slot] = 511
        block = encode_block(3, ep, None, [15] * 16)
        hdr = bytearray(148)
        struct.pack_into("<I", hdr, 0, 0x20534444)
        struct.pack_into("<I", hdr, 4, 124)
        struct.pack_into("<I", hdr, 12, 4)
        struct.pack_into("<I", hdr, 16, 4)
        struct.pack_into("<I", hdr, 80, 32)
        struct.pack_into("<I", hdr, 84, 0x30315844)
        struct.pack_into("<5I", hdr, 128, 96, 3, 0, 1, 0)  # BC6H_SF16
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dds", delete=False) as fh:
            fh.write(bytes(hdr) + block)
            path = fh.name
        try:
            dds = media_tool.read_dds(path)
            self.assertEqual(dds.fourcc, "BC6H_SF16")
            self.assertGreater(dds.rgba[-4], 200)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
