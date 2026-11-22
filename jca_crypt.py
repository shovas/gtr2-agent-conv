#!/usr/bin/env python3
"""SimBin JCA (Race 07 / GTR Evolution / Race Room) file decryption/encryption.

Pure-Python port of the algorithm published in wtcced 0.3.5 by Luigi Auriemma
(GPLv2, http://aluigi.altervista.org/papers/wtcced.zip). Constant tables live in
GPLv2-attributed ``jca_tables.py``. This module is therefore GPLv2 as well.

Layout:
    0x00 u32 magic   = 0xffffb10f
    0x04 u32 version = 0..7 (odd versions use zlib compression)
    0x08 u32 data_size
    0x0C u32 zlen    (compressed size; 0 when uncompressed)
    0x10 ..          Blowfish-encrypted payload, padded to a multiple of 8 bytes

Decryption: Blowfish (key/table chosen by version) -> optional zlib inflate ->
XOR every output byte with 0xEB. Encryption is the exact inverse.
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

from jca_tables import P_INIT, S_TABLES

MAGIC = 0xFFFFB10F
XOR_BYTE = 0xEB

# version -> (key, keytable, compressed)
_VERSIONS = {
    0: (bytes.fromhex("4617802d13e42f2f276f1e1923656914412c0105"), 0, False),
    1: (bytes.fromhex("4617802d13e42f2f276f1e1923656914412c0105"), 0, True),
    2: (b"qcB81[O x_@)pobk", 1, False),
    3: (b"qcB81[O x_@)pobk", 1, True),
    4: (bytes.fromhex("45133b810ba109962542f0e57d191153"), 2, False),
    5: (bytes.fromhex("45133b810ba109962542f0e57d191153"), 2, True),
    6: (bytes.fromhex("8ff89d489a2e37623254d7d8ab052c44"), 2, False),
    7: (bytes.fromhex("8ff89d489a2e37623254d7d8ab052c44"), 2, True),
}

CUSTOM_KEYS = {
    "raceroom": bytes.fromhex("5f67b337a2769a3413ac28d0926e3290f755fe4a"),
    "raceroom_plr": bytes.fromhex("f84ac994a30b5d1c0b348cdb6f91335c422d9e49"),
    "volvo": bytes.fromhex("70fba44519284947399893256965b32065"),
    "old_raceroom": bytes.fromhex("0c925edae91742c03c1e17ede13d4206b4b969ea"),
}

_MASK = 0xFFFFFFFF


class Blowfish:
    """Minimal Blowfish with the game's fixed S-box tables (no standard key setup)."""

    def __init__(self, key: bytes, keytable: int = 0):
        if keytable not in (0, 1, 2):
            raise ValueError(f"unsupported keytable {keytable}")
        self.p = list(P_INIT)
        self.s = list(S_TABLES[keytable])
        j = 0
        for i in range(18):
            data = 0
            for _ in range(4):
                data = ((data << 8) | key[j]) & _MASK
                j = (j + 1) % len(key)
            self.p[i] ^= data
        left = right = 0
        for i in range(0, 18, 2):
            left, right = self._encipher(left, right)
            self.p[i], self.p[i + 1] = left, right
        for i in range(4):
            for j in range(0, 256, 2):
                left, right = self._encipher(left, right)
                self.s[i * 256 + j] = left
                self.s[i * 256 + j + 1] = right

    def _f(self, x: int) -> int:
        a = (x >> 24) & 0xFF
        b = (x >> 16) & 0xFF
        c = (x >> 8) & 0xFF
        d = x & 0xFF
        return (((self.s[a] + self.s[256 + b]) & _MASK) ^ self.s[512 + c]) + self.s[768 + d] & _MASK

    def _encipher(self, left: int, right: int) -> tuple[int, int]:
        for i in range(16):
            left ^= self.p[i]
            right ^= self._f(left)
            left, right = right, left
        left, right = right, left
        right ^= self.p[16]
        left ^= self.p[17]
        return left & _MASK, right & _MASK

    def _decipher(self, left: int, right: int) -> tuple[int, int]:
        for i in range(17, 1, -1):
            left ^= self.p[i]
            right ^= self._f(left)
            left, right = right, left
        left, right = right, left
        right ^= self.p[1]
        left ^= self.p[0]
        return left & _MASK, right & _MASK

    def crypt_blocks(self, data: bytearray, decrypt: bool) -> None:
        """Process whole 8-byte blocks in place; leave any trailing bytes alone."""
        for off in range(0, len(data) - 7, 8):
            left, right = struct.unpack_from("<II", data, off)
            left, right = self._decipher(left, right) if decrypt else self._encipher(left, right)
            struct.pack_into("<II", data, off, left, right)


def _key_for(version: int, custom: bytes | None = None):
    if version not in _VERSIONS:
        raise ValueError(f"unsupported JCA version {version}")
    key, keytable, compressed = _VERSIONS[version]
    if custom is not None:
        key = custom
    return key, keytable, compressed


def decrypt_bytes(data: bytes, custom_key: bytes | None = None) -> bytes:
    """Decrypt a JCA file to its original payload."""
    if len(data) < 16:
        raise ValueError("file too short")
    magic, version, data_size, zlen = struct.unpack_from("<IIII", data, 0)
    if magic != MAGIC:
        raise ValueError(f"not a JCA file (magic 0x{magic:08x})")
    key, keytable, compressed = _key_for(version, custom_key)
    if version % 2 == 0:  # even versions ignore the compression field
        compressed = False
        zlen = 0
    payload = bytearray(data[16:])
    backup = bytes(payload[zlen & ~7:zlen]) if zlen and (zlen & 7) else b""
    Blowfish(key, keytable).crypt_blocks(payload, decrypt=True)

    if zlen:
        try:
            out = zlib.decompress(payload[:zlen])
        except zlib.error:
            if not backup:
                raise
            payload[zlen & ~7:zlen] = backup  # wtcced workaround for odd files
            out = zlib.decompress(payload[:zlen])
        if len(out) != data_size:
            raise ValueError(f"size mismatch: {len(out)} != {data_size}")
    else:
        out = bytes(payload[:data_size])
    return bytes(b ^ XOR_BYTE for b in out)


def encrypt_bytes(data: bytes, version: int = 3, custom_key: bytes | None = None) -> bytes:
    """Encrypt a payload into a JCA file (inverse of :func:`decrypt_bytes`)."""
    key, keytable, compressed = _key_for(version, custom_key)
    body = bytes(b ^ XOR_BYTE for b in data)
    if compressed:
        zipped = zlib.compress(body, 9)
        zlen = len(zipped)
    else:
        zipped = body
        zlen = 0
    bflen = (len(zipped) + 7) & ~7
    block = bytearray(zipped) + bytes(bflen - len(zipped))
    Blowfish(key, keytable).crypt_blocks(block, decrypt=False)
    return struct.pack("<IIII", MAGIC, version, len(data), zlen) + bytes(block)


def _main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("decrypt", "encrypt"):
        p = sub.add_parser(cmd)
        p.add_argument("input")
        p.add_argument("output")
        p.add_argument("--version", type=int, default=3, help="encryption version (encrypt only)")
        p.add_argument("--key", choices=sorted(CUSTOM_KEYS), help="non-default game key")
    args = ap.parse_args()
    src = Path(args.input).read_bytes()
    custom = CUSTOM_KEYS.get(args.key) if args.key else None
    out = decrypt_bytes(src, custom) if args.cmd == "decrypt" else encrypt_bytes(src, args.version, custom)
    Path(args.output).write_bytes(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
