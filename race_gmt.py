#!/usr/bin/env python3
"""Partial parser for the `RaceGMT\\0` mesh variant (Race 07 DLC content).

Verified from ../Race07Complete (643 files): `magic[8], u32 name_len, name,
u32 flags (0x04000020), bounding-box floats ...`. Vertex/index table layout is
NOT decoded — do not assume new-layout GMT geometry offsets apply.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"RaceGMT\0"
FLAGS = 0x04000020


@dataclass
class RaceGmtHeader:
    name: str
    flags: int
    floats: tuple[float, ...]
    size: int


def parse_header(data: bytes) -> RaceGmtHeader:
    if data[:8] != MAGIC or len(data) < 0x20:
        raise ValueError("not a RaceGMT file")
    n = struct.unpack_from("<I", data, 8)[0]
    if not (0 < n < 256) or 12 + n + 4 > len(data):
        raise ValueError("invalid RaceGMT name length")
    name = data[12:12 + n].decode("latin-1").rstrip("\0")
    flags = struct.unpack_from("<I", data, 12 + n)[0]
    off = 16 + n
    floats = struct.unpack_from("<12f", data, off) if off + 48 <= len(data) else ()
    return RaceGmtHeader(name=name, flags=flags, floats=floats, size=len(data))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    for f in args.files:
        try:
            print(f, parse_header(Path(f).read_bytes()))
        except ValueError as e:
            print(f, "ERROR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
