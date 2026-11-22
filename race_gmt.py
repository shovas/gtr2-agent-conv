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


def diff_strides(a: bytes, b: bytes, gap: int = 4) -> dict:
    """Infer record strides from two same-size files of the same asset.

    Runs of differing bytes are grouped; distances between run starts reveal
    the record stride. Observed on PEOPLE_STAND_01/02: 36-byte (position) and
    64-byte (4x4 transform) strides.
    """
    from collections import Counter

    if len(a) != len(b):
        raise ValueError("files must be the same size")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if not diff:
        return {}
    runs = []
    start = prev = diff[0]
    for i in diff[1:]:
        if i - prev > gap:
            runs.append((start, prev))
            start = i
        prev = i
    runs.append((start, prev))
    starts = [s for s, _ in runs]
    distances = Counter(starts[i + 1] - starts[i] for i in range(len(starts) - 1))
    return {"runs": len(runs), "distances": dict(distances), "first_starts": starts[:8]}


def read_positions(data: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    """Read the leading 36-byte triangle records as 3 position triples each.

    Verified on PEOPLE_STAND_01..08 (48 records, 144 vertices); only the
    position floats vary across same-size files. Returns one 3-tuple per record.
    """
    header = parse_header(data)
    off = 16 + len(header.name.encode("latin-1"))
    out = []
    while off + 36 <= len(data):
        vals = struct.unpack_from("<9f", data, off)
        out.append(tuple((vals[i], vals[i + 1], vals[i + 2]) for i in (0, 3, 6)))
        off += 36
    return out


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
