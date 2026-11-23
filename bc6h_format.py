#!/usr/bin/env python3
"""BC6H unsigned-float (UF16) block decoder: modes 10 and 11.

Format data (partition/anchor tables, per-mode bit runs, unquantization,
interpolation) is transcribed from the Khronos Data Format Specification 1.3.1
BPTC tables and Microsoft's BC6H documentation. The MIT/Apache-2.0
``patodois/bcn-decode`` project was consulted as a format reference only; no
code was copied. Numeric tables were generated mechanically from its
spec-generated ``tables.rs`` to avoid transcription errors.

Only the two *non-transformed* UF16 modes are implemented (stored mode code
30: two subsets, 6-bit endpoints; stored code 3: one subset, 10-bit endpoints).
The other 12 BC6H modes are reported as unsupported rather than guessed. BC6H defines no
8-bit form: output here clamps to [0, 1] and truncates to 8 bits per channel
(the HDR half-float range is intentionally lost).
"""
from __future__ import annotations

# Khronos Table 114, partitions 0..31 (BC6H uses a 5-bit partition number).
PARTITION2 = [
    [0,0,1,1,0,0,1,1,0,0,1,1,0,0,1,1],
    [0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1],
    [0,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1],
    [0,0,0,1,0,0,1,1,0,0,1,1,0,1,1,1],
    [0,0,0,0,0,0,0,1,0,0,0,1,0,0,1,1],
    [0,0,1,1,0,1,1,1,0,1,1,1,1,1,1,1],
    [0,0,0,1,0,0,1,1,0,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,1,0,0,1,1,0,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1],
    [0,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,1,0,1,1,1],
    [0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1],
    [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
    [0,0,0,0,1,0,0,0,1,1,1,0,1,1,1,1],
    [0,1,1,1,0,0,0,1,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,1,0,0,0,1,1,1,0],
    [0,1,1,1,0,0,1,1,0,0,0,1,0,0,0,0],
    [0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0],
    [0,0,0,0,1,0,0,0,1,1,0,0,1,1,1,0],
    [0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0],
    [0,1,1,1,0,0,1,1,0,0,1,1,0,0,0,1],
    [0,0,1,1,0,0,0,1,0,0,0,1,0,0,0,0],
    [0,0,0,0,1,0,0,0,1,0,0,0,1,1,0,0],
    [0,1,1,0,0,1,1,0,0,1,1,0,0,1,1,0],
    [0,0,1,1,0,1,1,0,0,1,1,0,1,1,0,0],
    [0,0,0,1,0,1,1,1,1,1,1,0,1,0,0,0],
    [0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,1,1,1,0,0,0,1,1,0,0,0,1,1,1,0],
    [0,0,1,1,1,0,0,1,1,0,0,1,1,1,0,0],
]
# Khronos Table 118 anchor texel of subset 1, partitions 0..31.
ANCHOR2 = [15]*16 + [15,2,8,2,2,8,8,15,2,8,2,2,8,8,2,2]
WEIGHTS3 = [0, 9, 18, 27, 37, 46, 55, 64]
WEIGHTS4 = [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64]

# (src bit, length, endpoint slot = channel*4 + endpoint, dst bit),
# generated from Khronos Tables 122-124.
RUNS = {
    30: [  # stored code 30: two subsets, 6-bit endpoints, no delta transform
        (5,6,0,0),(11,1,7,4),(12,2,11,0),(14,1,10,4),
        (15,6,4,0),(21,1,6,5),(22,1,10,5),(23,1,11,2),(24,1,6,4),
        (25,6,8,0),(31,1,7,5),(32,1,11,3),(33,1,11,5),(34,1,11,4),
        (35,6,1,0),(41,4,6,0),(45,6,5,0),(51,4,7,0),(55,6,9,0),
        (61,4,10,0),(65,6,2,0),(71,6,3,0),
    ],
    3: [  # stored code 3: one subset, 10-bit endpoints
        (5,10,0,0),(15,10,4,0),(25,10,8,0),
        (35,10,1,0),(45,10,5,0),(55,10,9,0),
    ],
}
# stored code -> (endpoint bits, partition / two subsets)
MODE_INFO = {30: (6, True), 3: (10, False)}


def _bits(v: int, src: int, length: int) -> int:
    if src >= 128:
        return 0
    return (v >> src) & ((1 << length) - 1)


def _unquantize(x: int, bits: int) -> int:
    if bits >= 15:
        return x
    if x == 0:
        return 0
    if x == (1 << bits) - 1:
        return 0xFFFF
    return ((x << 15) + 0x4000) >> (bits - 1)


def _finish(i: int) -> int:
    return ((i * 31) >> 6) & 0xFFFF


def _half_to_unorm8(h: int) -> int:
    """Half-float bit pattern -> 8-bit UNORM, clamped to [0, 1], truncated."""
    if h >= 0x7C00:
        return 255 if h == 0x7C00 else 0
    if h >= 0x3C00:
        return 255
    exp, man = h >> 10, h & 0x3FF
    if exp == 0:
        return (man * 255) >> 24
    return ((1024 + man) * 255) >> (25 - exp)


def decode_block(block: bytes) -> list[tuple[int, int, int, int]] | None:
    """Decode one 16-byte UF16 block to 16 RGBA8 pixels (raster order).

    Returns ``None`` if the block uses an unsupported mode.
    """
    if len(block) < 16:
        return None
    v = int.from_bytes(block[:16], "little")
    low2 = v & 3
    mode = low2 if low2 < 2 else (v & 31)
    if mode not in MODE_INFO:
        return None
    prec, two = MODE_INFO[mode]

    raw = [0] * 12
    for src, length, slot, dst in RUNS[mode]:
        raw[slot] |= _bits(v, src, length) << dst
    n_ep = 4 if two else 2
    unq = [[_unquantize(raw[c * 4 + k], prec) for k in range(n_ep)]
           for c in range(3)]

    if two:
        part = (v >> 77) & 31
        partition, anchor = PARTITION2[part], ANCHOR2[part]
        index_bits, index_pos, weights = 3, 82, WEIGHTS3
    else:
        partition, anchor = [0] * 16, -1
        index_bits, index_pos, weights = 4, 65, WEIGHTS4

    out = []
    pos = index_pos
    for i in range(16):
        n = index_bits - 1 if (i == 0 or i == anchor) else index_bits
        idx = _bits(v, pos, n)
        pos += n
        subset = partition[i] if two else 0
        w = weights[idx]
        pixel = tuple(
            _half_to_unorm8(_finish(
                (unq[c][subset * 2] * (64 - w) + unq[c][subset * 2 + 1] * w + 32) >> 6))
            for c in range(3))
        out.append((*pixel, 255))
    return out


def decode_bc6h(data: bytes, width: int, height: int) -> bytes | None:
    """Decode a BC6H UF16 image to RGBA8, or None if any block is unsupported."""
    bw, bh = max(1, (width + 3) // 4), max(1, (height + 3) // 4)
    if len(data) < bw * bh * 16:
        return None
    out = bytearray()
    for by in range(bh):
        row = [decode_block(data[(by * bw + bx) * 16:(by * bw + bx + 1) * 16])
               for bx in range(bw)]
        if any(b is None for b in row):
            return None
        for y in range(4):
            for bx in range(bw):
                for x in range(4):
                    if by * 4 + y < height and bx * 4 + x < width:
                        out.extend(row[bx][y * 4 + x])
    return bytes(out)
