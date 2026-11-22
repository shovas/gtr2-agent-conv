#!/usr/bin/env python3
"""Partial CUBE MTS mesh parser (4.10 and 4.20 variants).

Verified from ../NascarSimRacing (4,200+ sampled meshes): both variants share
`magic[16], u32 object_count, char name[8]`; the payload after 0x1C is not yet
decoded. This module only reports the verified header, never edits files.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC_410 = b"CUBE_MTS_4.10\x00\x00\x00"
MAGIC_420 = b"CUBE_MTS_4.20\x00\x00\x00"
MAGICS = (MAGIC_410, MAGIC_420)


@dataclass
class MtsHeader:
    variant: str
    object_count: int
    name: str
    size: int


def parse_header(data: bytes) -> MtsHeader:
    magic = data[:16]
    if magic not in MAGICS:
        raise ValueError(f"not a CUBE MTS file (magic {magic!r})")
    if len(data) < 0x1C:
        raise ValueError("MTS too short")
    count = struct.unpack_from("<I", data, 16)[0]
    name = data[20:28].split(b"\0", 1)[0].decode("latin-1")
    return MtsHeader(variant="4.10" if magic == MAGIC_410 else "4.20",
                     object_count=count, name=name, size=len(data))


def submesh_names(data: bytes) -> list[str]:
    """Extract uppercase ASCII submesh names from the payload (heuristic).

    Observed on 644/800 sampled CUBE MTS 4.20 files: ``object_count - len(names)
    == 1``. This is a correlation, not a proven semantic rule.
    """
    import re
    return [m[:-1].decode("ascii") for m in re.findall(rb"[A-Z0-9_]{4,32}\x00", data[28:])]


DESCRIPTOR_STRIDE = 196
DESCRIPTOR_START = 216


def submesh_descriptors(data: bytes) -> list[tuple[int, str]]:
    """Read (offset, name) for submesh descriptors at the verified 196-byte grid.

    Observed on 206/300 sampled CUBE MTS 4.20 files with named submeshes:
    names begin at 0xD8 (216) and repeat every 196 bytes.
    """
    out = []
    for off in range(DESCRIPTOR_START, len(data) - 4, DESCRIPTOR_STRIDE):
        end = data.find(b"\0", off, min(off + 64, len(data)))
        if end < 0:
            break
        name = data[off:end]
        if not (4 <= len(name) <= 32) or not all(48 <= c < 127 for c in name):
            break
        out.append((off, name.decode("ascii")))
    return out


DESCRIPTOR_FLAG_32 = 0x4890
DESCRIPTOR_FLAG_ALT = 0x2890


def descriptor_fields(data: bytes, offset: int) -> tuple[int, int]:
    """Decode the observed packed u32 at descriptor+32 as (flag, low).

    Across 2,001 sampled descriptors the high 16 bits were 0x4890 (1,953)
    or 0x2890 (48); the low 16 bits are small values (0, 2, 32, 96, 2048,
    2080). Semantics of the two halves are unconfirmed.
    """
    u = struct.unpack_from("<I", data, offset + 32)[0]
    return u >> 16, u & 0xFFFF


DESCRIPTOR_164_STATES = (0x00000000, 0x0B4CE680, 0xFFFFFFFF)


def descriptor_tail_u32(data: bytes, offset: int) -> int:
    """Read descriptor+164; observed mostly in three states (see docs)."""
    return struct.unpack_from("<I", data, offset + 164)[0]


SUBMESH_MARKER = 129


def parse_mesh_table(data: bytes) -> dict | None:
    """Locate and decode the CUBE MTS submesh table.

    Observed in LIGHTBOX02.MTS at 0x500:
      (object_count, object_offset, vertex_count, vertex_offset,
       normal_count, normal_offset, index_count, index_offset)
    followed by per-submesh records beginning with marker 129:
      (129, submesh_index, count_a, offset_a, count_b, offset_b, ...)
    """
    header = parse_header(data)
    for off in range(0x100, min(len(data) - 32, 0x2000), 4):
        v = struct.unpack_from("<8I", data, off)
        if v[0] != header.object_count or not (0 < v[1] < len(data)):
            continue
        if not (0 < v[2] < 100000 and 0 < v[3] < len(data)):
            continue
        submeshes = []
        p = off + 48  # first submesh record at table+0x30
        while p + 24 <= len(data):
            rec = struct.unpack_from("<6I", data, p)
            if rec[0] != SUBMESH_MARKER or rec[1] != len(submeshes):
                break
            if rec[3] >= len(data) or rec[5] >= len(data):
                break
            submeshes.append(rec)
            p += 64  # observed submesh record spacing
        if submeshes:
            return {"table_offset": off, "header": v, "submeshes": submeshes}
    return None


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
