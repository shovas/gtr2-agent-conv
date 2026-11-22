#!/usr/bin/env python3
"""Structural reader for SimBin GTTF (time trial) and IRSR (replay) payloads.

These live inside gzip containers (`gzip_simbin_tool.py`). Verified fields:
  magic 'GTTF'/'IRSR' at 0x2D, f32 version at +4,
  u32-length-prefixed TRK filename, u32-length-prefixed AIW filename,
  then binary records with embedded ASCII strings.

Full lap/frame record semantics are NOT decoded; this tool identifies the
header, filenames, and all printable strings with their offsets.
"""
from __future__ import annotations

import argparse
import gzip
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAGICS = (b"GTTF", b"IRSR")


@dataclass
class EventFile:
    kind: str
    version: float
    trk: str
    aiw: str
    strings: list[tuple[int, str]] = field(default_factory=list)


def _printable(data: bytes) -> bool:
    return all(32 <= c < 127 for c in data)


def parse_payload(data: bytes) -> EventFile:
    kind = next((m.decode() for m in MAGICS if m in data[:64]), None)
    if kind is None:
        raise ValueError("not a GTTF/IRSR payload")
    off = data.index(kind.encode()) + 4
    version = struct.unpack_from("<f", data, off)[0]
    off += 4
    names = []
    for _ in range(2):
        size = struct.unpack_from("<I", data, off)[0]
        off += 4
        if size > 4096 or off + size > len(data):
            raise ValueError("invalid filename length")
        names.append(data[off:off + size].decode("latin-1"))
        off += size
    strings = []
    i = off
    while i < len(data):
        if 32 <= data[i] < 127:
            j = i
            while j < len(data) and 32 <= data[j] < 127:
                j += 1
            if j - i >= 3 and data[i:i + 1].isalpha():
                strings.append((i, data[i:j].decode("latin-1")))
            i = j + 1
        else:
            i += 1
    return EventFile(kind=kind, version=version, trk=names[0], aiw=names[1], strings=strings)


def parse_file(path: str | Path) -> EventFile:
    raw = Path(path).read_bytes()
    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    return parse_payload(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file")
    ap.add_argument("--strings", type=int, default=12)
    args = ap.parse_args(argv)
    e = parse_file(args.file)
    print(f"kind={e.kind} version={e.version} trk={e.trk!r} aiw={e.aiw!r}")
    print(f"printable_strings={len(e.strings)}")
    for off, s in e.strings[:args.strings]:
        print(f"  {off}: {s[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
