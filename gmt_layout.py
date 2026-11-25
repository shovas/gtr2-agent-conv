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

    # The 8-u32 table at 0x174 does not describe object 0 of multi-object rF1
    # GMTs (e.g. BUILDING43: table vc=313/ic=0 vs submesh 0 vc=753/ic=753).
    # Use the N submesh headers found by gmt_semantic for all N records;
    # validated on 4,703/4,703 multi-object rF1 GMTs (parse + round-trip +
    # relayout). Single-object GMTs keep the original table-based record.
    if obj_count > 1:
        import gmt_semantic
        subs = gmt_semantic.find_submeshes(data)
        for i in range(min(obj_count, len(subs))):
            sub = subs[i]
            extra = [0] * 27
            extra[1] = 0x20
            extra[3] = sub["v_count"]
            extra[4] = sub["v_off"]
            extra[5] = 0
            extra[6] = sub["v_off"] + sub["v_count"] * 32
            extra[10] = sub["i_count"]
            extra[11] = sub["i_off"]
            pos = FIRST_RECORD + i * RECORD_SIZE
            if pos + RECORD_SIZE <= len(out):
                out[pos:pos + RECORD_SIZE] = struct.pack("<27I", *extra)

    # Keep obj_list_offset and all payload bytes as-is.
    out[0:4] = struct.pack("<I", obj_off)
    return bytes(out)


def gsc_member_to_gtr2(encrypted: bytes) -> bytes | None:
    """Convert an ISI-encrypted GSC-family GMT member to a GTR2-layout GMT.

    Uses ``gmt_semantic.decode_gsc_member()`` (ISI skip=4) to recover verified
    positions/UVs/faces, then rebuilds the new layout via
    :func:`old_to_new_semantic`.  Returns ``None`` when the member fails any
    geometry quality gate.  No game data is embedded in this module.
    """
    import gmt_semantic
    decoded = gmt_semantic.decode_gsc_member(encrypted)
    if not decoded:
        return None
    return old_to_new_semantic(decoded["data"])


def old_to_new_semantic(data: bytes) -> bytes:
    """Convert an old-layout GMT to new layout with decoded geometry.

    Unlike `old_to_new()` (which copies old vertex records verbatim), this
    decodes submeshes via `gmt_semantic` and rebuilds the new-layout vertex,
    UV and index blocks.  Positions, UVs, triangle indices and the material
    tail are preserved; the result parses with `gmt_format.parse_gmt()`.
    """
    import gmt_semantic

    if not is_old(data):
        raise ValueError("input is not an old-layout GMT")
    decoded = gmt_semantic.read_gmt(data)
    subs = decoded["submeshes"]
    if not subs:
        raise ValueError("no decodable submeshes")

    old_obj = struct.unpack_from("<I", data, 0)[0]
    flags = struct.unpack_from("<I", data, 4)[0]
    mat_tail = data[old_obj:]

    cursor = FIRST_RECORD + len(subs) * RECORD_SIZE
    records, blocks = [], bytearray()
    for sub in subs:
        vc = len(sub["positions"])
        indices = [idx for face in sub["faces"] for idx in face]
        ic = len(indices)
        vo = cursor
        cursor += 4 + vc * VERTEX_STRIDE
        uo = cursor
        cursor += 4 + vc * VERTEX_STRIDE
        io = cursor
        cursor += 4 + ic * 2
        obj_off = cursor

        rec = [0] * 27
        rec[1] = 0x20004011
        rec[3] = vc
        # The 4-byte u32 count precedes the vertex records; point the record
        # at the first real 32-byte vertex so f0/normals/f7 survive intact.
        rec[4] = vo + 4
        rec[6] = uo
        rec[10] = ic
        rec[11] = io
        records.append(rec)

        raw_vertices = data[sub["v_off"]:sub["v_off"] + vc * VERTEX_STRIDE]
        if len(raw_vertices) != vc * VERTEX_STRIDE:
            raise ValueError("truncated old vertex block")
        blocks += struct.pack("<I", vc) + raw_vertices
        blocks += struct.pack("<I", vc)
        for uv in sub["uvs"]:
            blocks += bytes(8) + struct.pack("<2f", *uv) + bytes(VERTEX_STRIDE - 16)
        blocks += struct.pack("<I", ic)
        blocks += struct.pack("<%dH" % ic, *indices) if ic else b""

    out = bytearray(obj_off + len(mat_tail))
    out[0x18:MESH_TABLE_OFF] = data[0x18:MESH_TABLE_OFF]
    struct.pack_into("<II16s", out, 0, obj_off, flags, NEW_MAGIC)
    first = FIRST_RECORD
    struct.pack_into("<10I", out, MESH_TABLE_OFF, len(subs), first,
                     len(subs), first, 0, 0, 0, 0, 0, 0)
    for i, rec in enumerate(records):
        struct.pack_into("<27I", out, first + i * RECORD_SIZE, *rec)
    start = first + len(subs) * RECORD_SIZE
    out[start:start + len(blocks)] = blocks
    out[obj_off:] = mat_tail
    return bytes(out)


VERTEX_STRIDE = 32


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--gsc", action="store_true",
                    help="input is an ISI-encrypted GSC-family GMT member")
    args = ap.parse_args(argv)
    data = Path(args.input).read_bytes()
    if args.gsc:
        converted = gsc_member_to_gtr2(data)
        if converted is None:
            print("error: member failed geometry validation")
            return 1
    else:
        converted = old_to_new(data)
    Path(args.output).write_bytes(converted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
