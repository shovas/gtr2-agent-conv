#!/usr/bin/env python3
"""Partial CUBE MTS mesh parser (4.10 and 4.20 variants).

Verified from ../NascarSimRacing (4,200+ sampled meshes): both variants share
`magic[16], u32 object_count, char name[8]`. Decoded structures: 8-u32 geometry
table (200/200 files), 64-byte marker-based and alternate submesh records,
36-byte vertices (3 position triples), 16-byte normals (3 floats + u32), and
36-byte material records (4.10). This module only reads files, never edits them.
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


SUBMESH_MARKERS = (129, 130)  # 4.20 uses 129, 4.10 uses 130


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
        if v[0] != header.object_count:
            continue
        # 328 is the observed object-table offset in ~99% of files; requiring a
        # header-sized offset avoids false positives on binary noise.
        if v[1] < 0x100 or v[1] >= len(data):
            continue
        if not (0 < v[2] < 100000 and v[3] >= v[1] + 32 and v[3] < len(data)):
            continue
        if v[5] and (v[5] <= v[3] or v[5] >= len(data)):
            continue
        if v[6] and (v[7] < v[5] or v[7] + v[6] * 2 > len(data)):
            continue
        submeshes = []
        p = off + 48  # first submesh record at table+0x30
        while p + 24 <= len(data):
            rec = struct.unpack_from("<6I", data, p)
            if rec[0] not in SUBMESH_MARKERS or rec[1] != len(submeshes):
                break
            if rec[3] >= len(data) or rec[5] >= len(data):
                break
            submeshes.append(rec)
            p += 64  # observed submesh record spacing
        if not submeshes and p + 24 <= len(data):
            # Alternate ("type B") layout: no marker, fields
            # (count_a, 0, count_b, offset_b, count_c, offset_c, 0, 0).
            alt = struct.unpack_from("<8I", data, off + 48)
            if alt[1] == 0 and alt[6] == 0 and 0 < alt[3] < len(data) and 0 < alt[5] < len(data):
                submeshes = [alt]
        return {"table_offset": off, "header": v, "submeshes": submeshes}
    return None


def parse_material_records(data: bytes) -> list[dict]:
    """Parse the 4.10 material-record sequence (marker 128+n, 36-byte stride).

    Observed in TIREMANFRONT.MTS: u32 fields are
    (128+index, 1.0f, 0, 0, 0, 0, packed, small_int, 0).
    """
    out = []
    for off in range(0x1A0, len(data) - 36, 4):
        first = struct.unpack_from("<I", data, off)[0]
        if first != 128 + len(out):
            continue
        vals = struct.unpack_from("<9I", data, off)
        if vals[1] != 0x3F800000 or any(vals[i] != 0 for i in (2, 3, 4, 5, 8)):
            continue
        out.append({"offset": off, "index": first - 128,
                    "packed": vals[6], "small": vals[7]})
        if len(out) > 256:
            break
    return out


def decode_material_numbers(record: dict) -> tuple[int, int, int]:
    """Decode a 4.10 material record's packed/small numeric fields.

    Observed: `packed` is two u16 values (typically ~350-430) and `small` is
    another u16 in the same range. Their semantics are unconfirmed.
    """
    first, second = struct.unpack("<2H", struct.pack("<I", record["packed"]))
    return first, second, record["small"]


VERTEX_STRIDE = 36
NORMAL_STRIDE = 16


def read_geometry(data: bytes) -> dict | None:
    """Decode vertex/normal/index blocks using the validated table offsets.

    Strides derived from consecutive offsets in 200/200 sampled 4.20 files:
    vertices 36 bytes (3 x (x,y,z) float triples), normals 16 bytes
    (3 floats + u32).
    """
    table = parse_mesh_table(data)
    if not table:
        return None
    _, _, vcount, voff, ncount, noff, extra_count, normal_end = table["header"]
    verts = [struct.unpack_from("<9f", data, voff + i * VERTEX_STRIDE)
             for i in range(vcount) if voff + (i + 1) * VERTEX_STRIDE <= len(data)]
    normals = [struct.unpack_from("<3fI", data, noff + i * NORMAL_STRIDE)
               for i in range(ncount) if noff + (i + 1) * NORMAL_STRIDE <= len(data)]
    # Verified: normal_end == noff + ncount*16; the field after it is a count,
    # not a u16 index array (bytes there decode as floats). No index block is
    # present in this layout.
    return {"vertices": verts, "normals": normals, "normal_end": normal_end,
            "extra_count": extra_count, "indices": []}


def rig_table_signature(data: bytes) -> str | None:
    """Return a short digest of a 4.10 file's material-record triple table.

    The 36-byte records are shared across meshes that use the same rig: 22
    sampled files yield only 4 distinct tables (pit crew, R_ARM/R_TGT, L_ARM,
    JET).  This identifies rig reuse; it is not a per-mesh material mapping.
    """
    import hashlib
    recs = parse_material_records(data)
    if not recs:
        return None
    triples = tuple(decode_material_numbers(r) for r in recs)
    return hashlib.sha256(str(triples).encode()).hexdigest()[:10]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--detail", action="store_true",
                    help="print decoded table, geometry and material structures")
    args = ap.parse_args(argv)
    for f in args.files:
        try:
            data = Path(f).read_bytes()
            print(f, parse_header(data))
            if args.detail:
                table = parse_mesh_table(data)
                if table:
                    print("  table:", {k: table[k] for k in ("table_offset", "header")},
                          "submeshes=", len(table["submeshes"]))
                geo = read_geometry(data)
                if geo:
                    print("  geometry:", "vertices=", len(geo["vertices"]),
                          "normals=", len(geo["normals"]),
                          "normal_end=", geo["normal_end"])
                recs = parse_material_records(data)
                if recs:
                    print("  materials:", len(recs), "first=",
                          decode_material_numbers(recs[0]))
        except ValueError as e:
            print(f, "ERROR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
