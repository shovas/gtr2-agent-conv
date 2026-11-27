#!/usr/bin/env python3
"""Partial CUBE MTS mesh parser (4.10 and 4.20 variants).

Verified from ../NascarSimRacing (4,200+ sampled meshes): both variants share
`magic[16], u32 object_count, char name[8]`. Decoded structures: 8-u32 geometry
table (200/200 files), 64-byte marker-based and alternate submesh records,
36-byte vertices (3 position triples), 16-byte normals (3 floats + u32), and
36-byte records with marker `128+n` (4.10). The latter were first read as
"material records" but are actually **triangle records**: three u16 vertex
indices at +24/+26/+28, verified valid against submesh vertex counts in
1,715 files across F12002/F1C/NascarSimRacing (`read_triangles()`). This
module only reads files, never edits them.
"""
from __future__ import annotations

import argparse
import math
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


def read_triangles(data: bytes) -> list[tuple[int, int, int]]:
    """Return triangle vertex indices from a CUBE MTS 4.10 file.

    The records previously called "material records" are actually **triangle
    records**: the 36-byte structure holds three u16 vertex indices at offsets
    +24, +26 and +28 (plus a sequential marker `128+n`, a 1.0f word and zeros).
    Verified on F1 2002 `FENCE18.MTS`: 11 triangles with indices 126..153,
    all inside the first submesh's 154 decoded vertices; `MESH12.MTS` has 9
    consecutive triangles (585..611) inside a 696-vertex submesh.

    Returns an empty list for non-4.10 files or when no records qualify.
    """
    triangles = []
    for record in parse_material_records(data):
        offset = record["offset"]
        indices = struct.unpack_from("<3H", data, offset + 24)
        triangles.append(indices)
    return triangles


def to_gtr2_gmt(data: bytes, template: bytes) -> bytes | None:
    """Build a GTR2-layout GMT from a CUBE MTS 4.10 file.

    Uses decoded triangle indices (`read_triangles()`) and the first submesh's
    rig-indexed vertex positions (`read_geometry()`). Returns ``None`` when the
    file is not 4.10, has no triangles, or its positions are not plausible
    (skinned meshes with external bone data often contain NaN/huge values).
    """
    import vrl_to_gmt

    if data[:13] != b"CUBE_MTS_4.10":
        return None
    triangles = read_triangles(data)
    geometry = read_geometry(data)
    if not triangles or not geometry or not geometry.get("descriptors"):
        return None
    vertices = geometry["descriptors"][0]["vertices"]
    count = geometry["descriptors"][0]["count_a"]
    if len(vertices) < count:
        return None
    if not all(all(isinstance(v, float) and v == v and abs(v) < 1e5
                   for v in point) for point in vertices[:count]):
        return None
    max_index = max(index for tri in triangles for index in tri)
    if max_index >= count:
        return None
    try:
        return vrl_to_gmt.build_gmt(vertices[:count], triangles, template)
    except (ValueError, struct.error):
        return None


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
    """Decode the descriptor-driven geometry streams of a CUBE MTS file.

    IMPORTANT: the earlier interpretation of the 36-byte records at the table's
    vertex offset as positions was WRONG — those records contain u32 indices and
    material/name fields (e.g. 'NASCAR_FACE'), not position floats. The real
    float streams are located by the per-submesh descriptor records at table+48:

        (marker, index, count_b, offset_b, count_c, offset_c, 0, 0)

    where offset_b and offset_c point to contiguous float triples (normals/UVs).
    No standalone vertex-position array has been identified in these meshes —
    they are skinned assets whose positions may live in external bone data.

    Returns descriptors with their decoded float streams.  `vertices` holds the
    3-float records at each descriptor's offset (the rig-indexed stream_a),
    which for skinned meshes are local coordinates with x often constant.
    """
    table = parse_mesh_table(data)
    if not table:
        return None
    to = table["table_offset"]
    out = []
    for off in range(to + 48, len(data) - 64, 64):
        marker, index, c1, o1, c2, o2, z1, z2 = struct.unpack_from("<8I", data, off)
        if not (0 < c1 < 200000 and 0 < o1 < len(data)):
            break
        if not (0 <= c2 < 600000 and 0 < o2 < len(data)):
            break
        # The descriptor blocks are strided 64-byte records whose first 16 bytes
        # hold a 3-float local coordinate (often planar, x constant) + u32 pad.
        verts_a = [struct.unpack_from("<3f", data, o1 + i * 64)
                   for i in range(min(c1, 100000))
                   if o1 + (i + 1) * 64 <= len(data)]
        verts_b = ([struct.unpack_from("<3f", data, o2 + i * 64)
                    for i in range(min(c2, 100000))
                    if o2 + (i + 1) * 64 <= len(data)] if c2 else [])
        out.append({"offset": off, "marker": marker, "index": index,
                    "count_a": c1, "offset_a": o1, "vertices": verts_a,
                    "count_b": c2, "offset_b": o2, "stream_b": verts_b})
    all_vertices = [v for d in out for v in d["vertices"]]
    return {"descriptors": out, "vertices": all_vertices,
            "positions_available": True,
            "note": "36-byte table records are indices/materials; local "
                    "coordinates come from 64-byte descriptor streams"}


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


def rig_table_triangles(data: bytes) -> dict:
    """Interpret 4.10 per-rig triples as triangles into descriptor stream_a.

    The 36-byte material/rig records at 0x1a68 hold triples of u16 values
    (e.g. 389,392,393). Their range (0..442) matches the count of the first
    descriptor's stream_a (443), and 39/79 triples index finite points with
    plausible edge lengths (0.2..3.0). This is the first geometric validation
    of the per-rig table; exact semantics (collision mesh? skeleton?) unknown.
    """
    geo = read_geometry(data)
    if not geo or not geo["descriptors"]:
        return {"valid": 0, "total": 0, "edges": []}
    pts = geo["descriptors"][0]["vertices"]
    triples = [decode_material_numbers(r) for r in parse_material_records(data)]
    edges = []
    for tri in triples:
        if max(tri) >= len(pts):
            continue
        if any(not all(math.isfinite(x) for x in pts[i]) for i in tri):
            continue
        lengths = [math.dist(pts[tri[a]], pts[tri[b]]) for a, b in ((0, 1), (1, 2), (2, 0))]
        edges.append(max(lengths))
    return {"valid": len(edges), "total": len(triples), "edges": edges}


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
                    print("  geometry: descriptors=", len(geo["descriptors"]),
                          "positions_available=", geo["positions_available"])
                recs = parse_material_records(data)
                if recs:
                    print("  materials:", len(recs), "first=",
                          decode_material_numbers(recs[0]))
        except ValueError as e:
            print(f, "ERROR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
