#!/usr/bin/env python3
"""Prototype structural old->new GMT layout conversion.

Verified observations (see docs/gmt-format.md):
  old layout (rF1/Copa/AMS/SCE): magic `...bba8bf90` at 0x1D4, 8-u32 table at 0x174
  new layout (GTL/GTR2):         magic `...bba7bf90` at 0x08,  mesh table at 0x16C

The 8-u32 table at old 0x174 has the same shape as the tail of the new table at
0x16C: (vertex_count, vertex_offset, extra_count, extra_offset, index_count,
index_offset, ...). The old header stores (mesh_count=0, first_record=0) at
0x16C, i.e. no new-style mesh records; this tool synthesizes one 108-byte
mesh record at 0x210 (528) from the old object table.

LIMITATION: geometry semantics are NOT fully converted. The old vertex records
(u16 indices + position floats) are copied verbatim into the new vertex block,
so a rendered result is not guaranteed. This is a structural bridge only;
validate in-game before relying on it.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

OLD_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")
NEW_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")

TABLE_OFF = 0x174
MESH_TABLE_OFF = 0x16C
NAME_OFF = 0x194
MAGIC_OFF_OLD = 0x1D4
MAGIC_OFF_NEW = 0x08
FIRST_RECORD = 0x210
RECORD_SIZE = 108


def is_old(data: bytes) -> bool:
    return len(data) >= 0x1E4 and data[MAGIC_OFF_OLD:MAGIC_OFF_OLD + 16] == OLD_MAGIC


def is_new(data: bytes) -> bool:
    return len(data) >= 24 and data[MAGIC_OFF_NEW:MAGIC_OFF_NEW + 16] == NEW_MAGIC


def old_to_new(data: bytes) -> bytes:
    """Return a new-layout GMT assembled from an old-layout GMT."""
    if not is_old(data):
        raise ValueError("input is not an old-layout GMT")
    obj_off, flags = struct.unpack_from("<II", data, 0)
    table = struct.unpack_from("<8I", data, TABLE_OFF)
    obj_count, obj_offset, vcount, voff, ecount, eoff, icount, ioff = table
    if obj_count < 1:
        raise ValueError("old GMT has no objects")

    out = bytearray(data)

    # Header: magic moves from 0x1D4 to 0x08 (one byte changes: A8 -> A7).
    out[MAGIC_OFF_NEW:MAGIC_OFF_NEW + 16] = NEW_MAGIC
    out[MAGIC_OFF_OLD:MAGIC_OFF_OLD + 16] = bytes(16)
    out[0x04:0x08] = struct.pack("<I", flags)

    # Mesh table at 0x16C: (mesh_count, first_record) + the old 8-u32 table.
    new_table = (obj_count, FIRST_RECORD) + table[:8]
    out[MESH_TABLE_OFF:NAME_OFF] = struct.pack("<10I", *new_table)

    # One 108-byte mesh record at 0x210, filled from the old object table.
    rec = [0] * 27
    rec[1] = 0x20          # observed flag bit in normal-magic GMTs
    rec[2] = 0             # material index
    rec[3] = vcount
    rec[4] = voff
    rec[5] = eoff
    rec[6] = eoff + ecount * 16
    rec[10] = icount
    rec[11] = ioff
    out[FIRST_RECORD:FIRST_RECORD + RECORD_SIZE] = struct.pack("<27I", *rec)

    # Keep obj_list_offset and all payload bytes as-is.
    out[0:4] = struct.pack("<I", obj_off)
    return bytes(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args(argv)
    data = Path(args.input).read_bytes()
    Path(args.output).write_bytes(old_to_new(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
