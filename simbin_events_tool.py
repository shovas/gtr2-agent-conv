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
    driver: str | None = None
    co_driver: str | None = None
    car: str | None = None
    metadata_offset: int = -1


def _printable(data: bytes) -> bool:
    return all(32 <= c < 127 for c in data)


def parse_metadata(data: bytes, off: int, kind: str) -> dict | None:
    """Parse the metadata block immediately following the TRK/AIW filenames.

    GTTF files (time trials): 11-byte prefix, then two 1-byte-length-prefixed
    names (driver, co-driver), then a NUL-terminated car filename.
    GTL-IRSR files (replays): same prefix, one name, then the car filename.
    Other IRSR variants (GTR2 replays, rFactor replays) use a different layout
    and are left undecoded (returns None).
    """
    if off + 12 > len(data) or data[off:off + 3] != b"\0\0\0":
        return None
    q = off + 11
    names = []
    for _ in range(2 if kind == "GTTF" else 1):
        if q >= len(data):
            return None
        size = data[q]
        q += 1
        if not (0 < size < 80) or q + size > len(data):
            return None
        name = data[q:q + size]
        if not name or not all(32 <= c < 127 for c in name):
            return None
        names.append(name.decode("latin-1"))
        q += size
    while q < len(data) and data[q] == 0:
        q += 1
    j = q
    while j < len(data) and 32 <= data[j] < 127:
        j += 1
    car = data[q:j].decode("latin-1") if j > q else ""
    if not car.lower().endswith((".car", ".veh")):
        return None
    return {"offset": off, "driver": names[0],
            "co_driver": names[1] if len(names) > 1 else None, "car": car}


def _read_u32_string(data: bytes, off: int) -> tuple[str, int]:
    size = struct.unpack_from("<I", data, off)[0]
    off += 4
    if size > 4096 or off + size > len(data):
        raise ValueError("invalid filename length")
    return data[off:off + size].decode("latin-1"), off + size


def parse_rf1_metadata(data: bytes, off: int) -> dict | None:
    """Parse rFactor-era IRSR metadata: 9-byte prefix, 1-byte-length driver,
    NUL-terminated vehicle and skin names. Validated on 5 RF1Vanilla replays.
    """
    RF1_PREFIX = bytes.fromhex("000048030100000000")
    if data[off:off + 9] != RF1_PREFIX:
        return None
    q = off + 9
    if q >= len(data):
        return None
    size = data[q]
    if not (0 < size < 80) or q + 1 + size > len(data):
        return None
    driver = data[q + 1:q + 1 + size].decode("latin-1")
    q += 1 + size
    if q >= len(data) or data[q] != 0:
        return None
    j = data.find(b"\0", q + 1)
    if j < 0:
        return None
    vehicle = data[q + 1:j].decode("latin-1")
    if not vehicle.lower().endswith(".veh"):
        return None
    return {"offset": off, "driver": driver, "co_driver": None, "car": vehicle}


def parse_payload(data: bytes) -> EventFile:
    kind = next((m.decode() for m in MAGICS if m in data[:64]), None)
    if kind is None:
        raise ValueError("not a GTTF/IRSR payload")
    off = data.index(kind.encode()) + 4
    version = struct.unpack_from("<f", data, off)[0]
    off += 4
    first, off = _read_u32_string(data, off)
    if first.lower().endswith(".rfm"):
        # rFactor-lineage replay: mod, (empty), SCN, AIW.
        names = [first]
        for _ in range(3):
            name, off = _read_u32_string(data, off)
            names.append(name)
        meta = parse_rf1_metadata(data, off)
        trk, aiw = names[2], names[3]
    else:
        second, off = _read_u32_string(data, off)
        names = [first, second]
        meta = parse_metadata(data, off, kind)
        trk, aiw = names
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
    return EventFile(kind=kind, version=version, trk=trk, aiw=aiw, strings=strings,
                     driver=meta["driver"] if meta else None,
                     co_driver=meta["co_driver"] if meta else None,
                     car=meta["car"] if meta else None,
                     metadata_offset=meta["offset"] if meta else -1)


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
    if e.driver:
        print(f"driver={e.driver!r} co_driver={e.co_driver!r} car={e.car!r} "
              f"meta_offset={e.metadata_offset:#x}")
    print(f"printable_strings={len(e.strings)}")
    for off, s in e.strings[:args.strings]:
        print(f"  {off}: {s[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
