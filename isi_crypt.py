"""Pure-Python ISI/rFactor GMT/MAS decryption and encryption.

Based on rfactordec 0.2.2 by Luigi Auriemma (GPLv2) and
rfactortools_crypt.cpp by Ingo Ruhnke (GPLv3). Algorithm reimplemented
from the public rfactordec.c logic for interoperability.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import time
from pathlib import Path

MASK64 = 0xFFFFFFFFFFFFFFFF

GAMES = {
    0x38af5637e81bc9a0: ("rFactor", 0),
    0x2eb8f5cc9b14ea3b: ("ARCA Sim Racing", 0),
    0x6a9d37283a9f3d9f: ("Simulador Turismo Carretera", 0),
    0xde4139f961fa2817: ("Top Race Simulador 2009", 0),
    0x38af3150902cc55b: ("Superleague Formula", 1),
    0x4b1dca9f960524e8: ("Game Stock Car", 1),
    0x06a66ad328aeaed6: ("Simulador Turismo Carretera 2012", 1),
    0x28b7856a3a5996da: ("Game Stock Car: Formula Truck", 1),
}

_KEYZ0 = [
    [0xe56f8aa2ed826faa, 0x2f777cf9c70031d8, 0x12b42c082f7753a9, 0xe5c4f0aca218138d, 0xff00000000000000, 0x00000000000000ff],
    [0x9367a56ab8f1d3ff, 0xe734c80097dadd31, 0x0ff5793be2d23f51, 0xa418d4ea4e115ebb, 0x0000ff0000000000, 0x0000000000ff0000],
    [0x06a6fb1e97facec0, 0x2301031342e7afa0, 0x38af6d7a7a9f146b, 0xe281193b8565c2e0, 0x00000000ff000000, 0x000000ff00000000],
    [0x69531562d7ce1b70, 0x1415b6af3cdfb64e, 0x514f29eeaaba7a93, 0xb1de75ad972ed241, 0x000000000000ff00, 0x00ff000000000000],
    [0x0ff5793be2d23f51, 0xe734c80097dadd31, 0x9367a56ab8f1d3ff, 0xa418d4ea4e115ebb, 0x00000000000000ff, 0xff00000000000000],
    [0x8cffa4096b4af822, 0xbd0e595d83943946, 0x3285a8ddd8d47599, 0x5f196cfd07285957, 0x0000000000ff0000, 0x0000ff0000000000],
    [0x50c90b123d76ea44, 0xb4733727295f38d6, 0x13bb309071f26fb5, 0xfcdcdb8e48b1c147, 0x000000ff00000000, 0x00000000ff000000],
    [0x0ff5793be2d23f51, 0xa418d4ea4e115ebb, 0x2d17e8d3ec148292, 0x8cffa4096b4af822, 0x00ff000000000000, 0x000000000000ff00],
]
_KEYZ1 = [
    [0xe56f8aa2ed826faa, 0xe734c80097dadd31, 0x38af6d7a7a9f146b, 0xb1de75ad972ed241, 0xff00000000000000, 0x0000000000ff0000],
    [0x9367a56ab8f1d3ff, 0x2301031342e7afa0, 0x514f29eeaaba7a93, 0xa418d4ea4e115ebb, 0x0000ff0000000000, 0x000000ff00000000],
    [0x06a6fb1e97facec0, 0x1415b6af3cdfb64e, 0x9367a56ab8f1d3ff, 0x5f196cfd07285957, 0x00000000ff000000, 0x00ff000000000000],
    [0x69531562d7ce1b70, 0xe734c80097dadd31, 0x3285a8ddd8d47599, 0xfcdcdb8e48b1c147, 0x000000000000ff00, 0xff00000000000000],
    [0x0ff5793be2d23f51, 0xbd0e595d83943946, 0x13bb309071f26fb5, 0x8cffa4096b4af822, 0x00000000000000ff, 0x0000ff0000000000],
    [0x8cffa4096b4af822, 0xb4733727295f38d6, 0x2d17e8d3ec148292, 0xe5c4f0aca218138d, 0x0000000000ff0000, 0x00000000ff000000],
    [0x50c90b123d76ea44, 0xa418d4ea4e115ebb, 0x12b42c082f7753a9, 0xa418d4ea4e115ebb, 0x000000ff00000000, 0x000000000000ff00],
    [0x0ff5793be2d23f51, 0x2f777cf9c70031d8, 0x0ff5793be2d23f51, 0xe281193b8565c2e0, 0x00ff000000000000, 0x00000000000000ff],
]
_SHZ = [
    [0x0c, 0x07, 0x38],
    [0x10, 0x11, 0x18],
    [0x06, 0x17, 0x08],
    [0x03, 0x06, 0x28],
    [0x26, 0x0e, 0x38],
    [0x12, 0x0a, 0x18],
    [0x0c, 0x07, 0x08],
    [0x16, 0x07, 0x28],
]
_TABLE0 = [0x00, 0x28, 0x18, 0x08, 0x20, 0x38, 0x10, 0x30]
_TABLE1 = [0x38, 0x20, 0x30, 0x10, 0x28, 0x00, 0x08, 0x18]


def _u64(x: int) -> int:
    return x & MASK64


def isi_keyz(enctype: int, key: int, ret: int, n: int) -> int:
    key = _u64(key)
    ret = _u64(ret)
    shz = _SHZ[n]
    keyz = _KEYZ0[n] if enctype == 0 else _KEYZ1[n] if enctype == 1 else None
    if keyz is None:
        raise ValueError(f"unsupported enctype {enctype}")
    t1 = _u64(((ret & keyz[0]) ^ key) << shz[0])
    # t1 % keyz[1] in C unsigned 64; Python % is fine for positive
    t2 = _u64(((key & t1) ^ (t1 % keyz[1])) & keyz[2])
    key = _u64(key ^ t2)
    t1 = _u64((((t2 & keyz[3]) >> shz[1]) ^ t1) & t1)
    key = _u64(key ^ t2)
    if n == 0:
        t3 = _u64((key & keyz[4]) >> shz[2])
    elif n == 1:
        t3 = _u64((ret & keyz[4]) >> shz[2])
    elif n in (2, 3, 4, 5):
        t3 = _u64((ret & keyz[4]) << shz[2])
    elif n in (6, 7):
        t3 = _u64((ret & keyz[4]) >> shz[2])
    else:
        t3 = 0
    ret = _u64((t3 ^ (key & keyz[5])) | ret)
    n += 1
    if n < 8:
        ret = isi_keyz(enctype, key, ret, n)
    return ret


def isi_key(enctype: int, key: int) -> int:
    return isi_keyz(enctype, key, 0, 0)


def isi_crypt2(enctype: int, pos: int, key: int) -> int:
    if enctype == 0:
        t = _TABLE0[pos & 7]
    elif enctype == 1:
        t = _TABLE1[key & 7]
    else:
        raise ValueError(f"unsupported enctype {enctype}")
    return _u64(((_u64(0x000000ff000000ff) << t) & _u64(key)) >> t)


def _isi_stream_values(enctype: int, key: int) -> tuple[int, ...]:
    """Precompute the cipher's 8 possible output bytes for one key/block.

    For enctype 0 the shift depends only on `position & 7`; for enctype 1 it
    depends only on `key & 7`, which is constant within a block. Avoids
    ~50 million redundant Python calls on a large GMT member.
    """
    if enctype == 0:
        shifts = _TABLE0
    elif enctype == 1:
        shifts = (_TABLE1[key & 7],) * 8
    else:
        raise ValueError(f"unsupported enctype {enctype}")
    return tuple((((0x000000ff000000ff << shift) & key) >> shift) & 0xFF
                 for shift in shifts)


def isi_crypt(enctype: int, data: bytes | bytearray, key: int, encrypt: bool = False, skip: int = 0) -> bytes:
    if enctype == 0:
        blocksz = 0x40
    elif enctype == 1:
        blocksz = 0x80
    else:
        raise ValueError(f"unsupported enctype {enctype}")
    buf = bytearray(data)
    start = skip
    length = len(buf) - start
    if length < 0:
        return bytes(buf)
    t = 0
    x = start
    mask = 1
    n = length % blocksz
    stream = _isi_stream_values(enctype, key)
    for i in range(n):
        c = buf[x]
        outb = stream[(x - start) & 7] ^ c
        buf[x] = outb & 0xFF
        if encrypt:
            c = outb
        t |= ((c & mask) << (i & 0x3f))
        x += 1
    nblocks = 0
    for _ in range(length // blocksz):
        key = _u64(key ^ t)
        t = 0
        nblocks += 1
        mask = 1 << (nblocks & 7)
        stream = _isi_stream_values(enctype, key)
        for i in range(blocksz):
            c = buf[x]
            outb = stream[(x - start) & 7] ^ c
            buf[x] = outb & 0xFF
            if encrypt:
                c = outb
            t = _u64(t | ((c & mask) << (i & 63)))
            x += 1
    return bytes(buf)


def get_skip(filename: str | os.PathLike) -> int:
    return 4 if Path(filename).suffix.lower() == ".gmt" else 0


def crypt_info(data: bytes) -> tuple[int, int]:
    if len(data) < 16:
        return 0, 0
    sign, key = struct.unpack_from("<QQ", data, 0)
    sign = _u64(sign ^ key)
    return sign, key


def decrypt_bytes(data: bytes, skip: int = 0, force_enctype: int | None = None) -> bytes:
    if len(data) < 16:
        return data
    sign, key = crypt_info(data)
    if sign not in GAMES and force_enctype is None:
        raise ValueError(f"unknown ISI signature 0x{sign:016x}")
    enctype = GAMES[sign][1] if sign in GAMES else force_enctype
    data2 = data[16:]
    dec_key = isi_key(enctype, key)
    out = bytearray(data2)
    # isi_crypt in C was called with data+skip, datasz-skip, key, encrypt
    # our isi_crypt takes full buf and skip
    dec = isi_crypt(enctype, bytes(out), dec_key, encrypt=False, skip=skip)
    # if multiple layers, loop
    sign2, _ = crypt_info(dec)
    if sign2 in GAMES:
        return decrypt_bytes(dec, skip, force_enctype)
    return dec


def encrypt_bytes(data: bytes, skip: int = 0, sign: int = 0x4b1dca9f960524e8, key: int | None = None) -> bytes:
    if sign not in GAMES:
        raise ValueError(f"unknown sign 0x{sign:016x}")
    enctype = GAMES[sign][1]
    if key is None:
        key = _u64(sign * int(time.time()) * len(data))
    enc_key = isi_key(enctype, key)
    enc_data = isi_crypt(enctype, data, enc_key, encrypt=True, skip=skip)
    header = struct.pack("<QQ", _u64(sign ^ key), _u64(key))
    return header + enc_data


def main(argv=None):
    p = argparse.ArgumentParser(description="Decrypt/encrypt ISI rFactor/GTL/GTR2 files")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("-e", "--encrypt", action="store_true")
    p.add_argument("-s", "--sign", default="4b1dca9f960524e8")
    p.add_argument("--skip", type=int, default=None)
    args = p.parse_args(argv)
    skip = args.skip if args.skip is not None else get_skip(args.input)
    data = Path(args.input).read_bytes()
    if args.encrypt:
        out = encrypt_bytes(data, skip=skip, sign=int(args.sign, 16))
    else:
        out = decrypt_bytes(data, skip=skip)
    Path(args.output).write_bytes(out)
    print(f"wrote {args.output} ({len(out)} bytes)")

if __name__ == "__main__":
    main()
