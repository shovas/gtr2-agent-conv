#!/usr/bin/env python3
"""Partial parser for the `RaceGMT\\0` mesh variant (Race 07 DLC content).

Verified from ../Race07Complete (643 files): `magic[8], u32 name_len, name,
u32 flags (0x04000020), then four f32 triples (the third repeated as the fourth in all 643 files) ...`. Vertex/index table layout is
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
    the record stride. Observed on PEOPLE_STAND_01/02: differences lie on a
    36-byte grid (3 x position triples); occasional 64-byte gaps are simply
    alternating differing records, not a separate section.
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
    """Experimental raw-grid reader: decode each 36-byte block as 9 floats.

    WARNING: not a validated triangle decoder — sampled blocks contain mixed
    position, UV, index and material data (e.g. PEOPLE_STAND_01 has ASCII
    material strings starting at 0x30AF, inside the nominal grid).
    """
    header = parse_header(data)
    off = 16 + len(header.name.encode("latin-1"))
    out = []
    while off + 36 <= len(data):
        vals = struct.unpack_from("<9f", data, off)
        out.append(tuple((vals[i], vals[i + 1], vals[i + 2]) for i in (0, 3, 6)))
        off += 36
    return out


def read_triangle_records(data: bytes) -> list[dict]:
    """Decode the 36-byte triangle records that begin at body offset 292.

    Verified on the five PEOPLE_STAND_* meshes in ``../Race07Complete``: each
    record is ``3 u16 vertex indices, u16 zero, u32 group, u32 ordinal, 5 f32``.
    The ordinal equals the record index and the group increments at submesh
    boundaries; indices restart at 0,1,2 for each group. Reading stops at the
    first record that breaks this framing, before the following float tables.

    Returns empty for RaceGMT files that use a different payload layout (the
    corpus is heterogeneous — only 113/643 files carry this table at 292).
    """
    header = parse_header(data)
    off = 16 + len(header.name.encode("latin-1")) + 48 + 292
    out = []
    while off + 36 <= len(data):
        indices = struct.unpack_from("<3H", data, off)
        pad = struct.unpack_from("<H", data, off + 6)[0]
        group, ordinal = struct.unpack_from("<II", data, off + 8)
        if pad or group > 63 or ordinal != len(out):
            break
        floats = struct.unpack_from("<5f", data, off + 16)
        out.append({"indices": indices, "group": group, "ordinal": ordinal,
                    "floats": floats})
        off += 36
    return out


def read_texture_axes(data: bytes) -> list[tuple[float, float]]:
    """Return one ``(cos, sin)`` texture axis per 36-byte triangle record.

    Verified on `PEOPLE_STAND_01..05`: immediately after the 48 triangle
    records there is a count word then one **16-byte** entry per record, laid
    out as ``[cos, 0, sin, 0]``. The record's column-0 value (its texture U)
    is ``sin * x + cos * y`` using columns 3 and 1 as world x/y, matching all
    240 records to <8e-6. Returns an empty list for other RaceGMT layouts.
    """
    header = parse_header(data)
    base = 16 + len(header.name.encode("latin-1")) + 48 + 292
    records = read_triangle_records(data)
    if not records:
        return []
    off = base + 36 * len(records)
    if off + 4 + 16 * len(records) > len(data):
        return []
    count = struct.unpack_from("<I", data, off)[0]
    if count != len(records):
        return []
    return [(struct.unpack_from("<f", data, off + 4 + 16 * k)[0],
             struct.unpack_from("<f", data, off + 12 + 16 * k)[0])
            for k in range(count)]


def read_racegmt_vertices(data: bytes) -> list[dict]:
    """Return the vertex table that follows the texture-axis entries.

    Verified on `PEOPLE_STAND_01..05`: a count word, a 12-byte section header,
    then one 64-byte record per vertex holding ``[y, z, x]`` world position,
    the ``[cos, 0, sin]`` texture axis, two padding words (first is NaN), and
    four repeated ``(u, v)`` pairs. All five files have 5 vertices with the
    same UV corners (0.73711, -0.00631) and (0.73711, -0.99574). Returns an
    empty list for other RaceGMT layouts.
    """
    header = parse_header(data)
    base = 16 + len(header.name.encode("latin-1")) + 48 + 292
    records = read_triangle_records(data)
    axes = read_texture_axes(data)
    if not records or len(axes) != len(records):
        return []
    off = base + 36 * len(records) + 4 + 16 * len(axes)
    if off + 4 + 12 > len(data):
        return []
    row = off + 16
    out = []
    while row + 64 <= len(data):
        y, z, x = struct.unpack_from("<3f", data, row)
        cos, zero, sin = struct.unpack_from("<3f", data, row + 12)
        # A unit 3-vector; upward/downward faces carry (0, +/-1, 0), so no
        # single component is guaranteed to be non-zero.
        if not 0.99 < cos * cos + zero * zero + sin * sin < 1.01:
            break
        uvs = struct.unpack_from("<8f", data, row + 32)
        out.append({"position": (x, y, z), "axis": (cos, sin),
                    "uv": (uvs[0], uvs[1]),
                    "uv_sets": tuple((uvs[2 * k], uvs[2 * k + 1])
                                     for k in range(4))})
        row += 64
    return out


def read_racegmt_indices(data: bytes) -> list[int]:
    """Return the u16 index buffer following ``read_racegmt_vertices()``.

    Verified on `PEOPLE_STAND_01`: after 24 vertex records a u32 count (24)
    is followed by the sequential u16 indices 0..23. Returns an empty list
    when that framing is absent.
    """
    header = parse_header(data)
    base = 16 + len(header.name.encode("latin-1")) + 48 + 292
    records = read_triangle_records(data)
    axes = read_texture_axes(data)
    if not records or len(axes) != len(records):
        return []
    vertices = read_racegmt_vertices(data)
    if not vertices:
        return []
    off = base + 36 * len(records) + 4 + 16 * len(axes) + 16 + 64 * len(vertices)
    if off + 4 > len(data):
        return []
    count = struct.unpack_from("<I", data, off)[0]
    if not 0 < count <= 4096 or off + 4 + 2 * count > len(data):
        return []
    return list(struct.unpack_from(f"<{count}H", data, off + 4))


SUBMESH_MAGIC = 0x20004051
VARIANT_MAGIC = 0x2000403D
VARIANT_VERTEX_STRIDE = 88


def read_variant_submeshes(data: bytes) -> list[dict]:
    """Decode the `0x2000403d` submesh variant used by the Zolder09 plots.

    Unlike `0x20004051`, each vertex is **88 bytes**: ``[y,z,x]`` position,
    ``[x,y,z]`` unit normal, a NaN/zero pad pair, unit tangent and bitangent
    triples, then four ``(u,v)`` pairs. The index table follows all vertices.

    Verified on `plots01.gmt` (37 vertices, 51 indices) and `plots02.gmt`
    (32 vertices, 36 indices): every vertex normal is unit-length, and the
    index count fits immediately after the vertex table.
    """
    out = []
    needle = struct.pack("<I", VARIANT_MAGIC)
    position = 0
    while True:
        position = data.find(needle, position)
        if position < 0:
            break
        magic, group, count = struct.unpack_from("<III", data, position)
        verts_at = position + 12
        index_at = verts_at + VARIANT_VERTEX_STRIDE * count
        if index_at + 4 > len(data):
            position += 1
            continue
        index_count = struct.unpack_from("<I", data, index_at)[0]
        if not 0 < index_count <= 8 * count or \
                index_at + 4 + 2 * index_count > len(data):
            position += 1
            continue
        vertices = []
        for k in range(count):
            row = verts_at + VARIANT_VERTEX_STRIDE * k
            y, z, x = struct.unpack_from("<3f", data, row)
            normal = struct.unpack_from("<3f", data, row + 12)
            tangent = struct.unpack_from("<3f", data, row + 32)
            bitangent = struct.unpack_from("<3f", data, row + 44)
            if not (0.99 < sum(v * v for v in normal) < 1.01 and
                    0.99 < sum(v * v for v in tangent) < 1.01 and
                    0.99 < sum(v * v for v in bitangent) < 1.01):
                break
            uvs = struct.unpack_from("<8f", data, row + 56)
            vertices.append({"position": (x, y, z),
                             "uv": (uvs[0], uvs[1]),
                             "uv_sets": tuple((uvs[2 * j], uvs[2 * j + 1])
                                              for j in range(4))})
        if len(vertices) == count:
            indices = struct.unpack_from(f"<{index_count}H", data, index_at + 4)
            if max(indices) < count:
                out.append({"group": group, "vertices": vertices,
                            "indices": indices})
        position += 1
    return out


def read_racegmt_submeshes(data: bytes) -> list[dict]:
    """Decode all `0x20004051` submeshes in a RaceGMT payload.

    Verified on `PEOPLE_STAND_01..05`: each section is a 12-byte header
    ``[magic=0x20004051, group index, vertex count]``, then that many 64-byte
    vertices (``[y,z,x], [cos,~0,sin], pad, (u,v) x4``), then a u32 count and
    that many u16 indices. The five groups have 24/36/24/42/18 vertices —
    exactly 3x the 8/12/8/14/6 triangle records of the opening table, whose
    sequential indices address the matching group's vertex array.
    """
    out = []
    for position in range(len(data) - 12):
        magic, group, count = struct.unpack_from("<III", data, position)
        # Group indices are not guaranteed to start at 0 (e.g. LOD meshes
        # may begin at 1); accept any small index and use it as reported.
        if magic != SUBMESH_MAGIC or group > 63 or not 0 < count <= 65535:
            continue
        verts_at = position + 12
        index_at = verts_at + 64 * count
        if index_at + 4 + 2 * count > len(data):
            continue
        vertices = []
        for k in range(count):
            row = verts_at + 64 * k
            y, z, x = struct.unpack_from("<3f", data, row)
            cos, zero, sin = struct.unpack_from("<3f", data, row + 12)
            # The three words are a unit normal/facing vector; horizontal
            # faces carry (0,1,0), so no single component is guaranteed.
            norm2 = cos * cos + zero * zero + sin * sin
            # Some meshes contain degenerate vertices with a zero vector; they
            # are typically unreferenced by the index buffer. Keep them.
            if not (norm2 == 0 or 0.99 < norm2 < 1.01):
                break
            uvs = struct.unpack_from("<8f", data, row + 32)
            # The final 32 bytes are four exported UV sets (A/B/C/D), each a
            # (u,v) pair — the rF2 GMT UVW exporter's documented layout. They
            # may be identical or differ by texture slot; both are valid.
            vertices.append({"position": (x, y, z), "uv": (uvs[0], uvs[1]),
                             "uv_sets": tuple((uvs[2 * k], uvs[2 * k + 1])
                                              for k in range(4))})
        if len(vertices) != count:
            continue
        index_count = struct.unpack_from("<I", data, index_at)[0]
        if not 0 < index_count <= 8 * count or index_at + 4 + 2 * index_count > len(data):
            continue
        indices = struct.unpack_from(f"<{index_count}H", data, index_at + 4)
        if any(index >= count for index in indices):
            continue
        out.append({"group": group, "vertices": vertices, "indices": indices})
    return out


def to_gtr2_gmt(data: bytes, template: bytes) -> bytes | None:
    """Build a GTR2-layout GMT from a decoded RaceGMT mesh.

    Concatenates all submesh vertices (world positions and UVs) and their
    triangle indices with per-submesh offsets, then uses
    ``vrl_to_gmt.build_gmt()`` to emit a one-submesh GTR2 GMT. Normals are
    computed from the triangles. Returns ``None`` when no submeshes decode.
    """
    import vrl_to_gmt

    submeshes = read_racegmt_submeshes(data)
    if not submeshes:
        submeshes = read_variant_submeshes(data)
    if not submeshes:
        return None
    positions = []
    uvs = []
    triangles = []
    for submesh in submeshes:
        offset = len(positions)
        positions.extend(v["position"] for v in submesh["vertices"])
        uvs.extend(v["uv"] for v in submesh["vertices"])
        indices = list(submesh["indices"])
        for i in range(0, len(indices) - 2, 3):
            triangles.append(tuple(offset + indices[i + j] for j in range(3)))
    if not triangles:
        return None
    return vrl_to_gmt.build_gmt(positions, triangles, template, uvs=uvs)


def read_material_strings(data: bytes) -> list[str]:
    """Extract NUL-terminated ASCII material/stage strings from the payload."""
    import re
    return [m.group().decode("ascii")
            for m in re.finditer(rb"[A-Za-z0-9_]{4,40}\x00", data[16:])]


STAGE_STRIDE = 264


def read_material_blocks(data: bytes) -> list[dict]:
    """Resolve material/stage blocks from the validated 264-byte stage grid.

    Observed across 60 sampled files: stage strings (`L0`/`L1`/`L2` ...) are
    spaced 264 bytes and each stage has u32 (1, 1) at +256.
    """
    import re
    matches = [m.start() for m in re.finditer(rb"L[012][A-Z0-9_]{3,39}\x00", data)]
    blocks = []
    for off in matches:
        if off + STAGE_STRIDE > len(data):
            continue
        tail = struct.unpack_from("<2I", data, off + 256)
        name = data[off:data.find(b"\0", off)].decode("ascii")
        blocks.append({"offset": off, "name": name, "tail": tail})
    return blocks


def build_stage_type_map(blocks: list[dict]) -> dict[str, tuple[int, int, int]]:
    """Map stage name to its dominant semantic type (first u32 tail).

    The first tail u32 at +256 is a stage-type enum driven by the stage name:
    diffuse -> 1/2, cubemap -> 3, specular -> 5, bump+specular -> 7, etc.
    Returns `{name: (dominant_type, count, total_samples)}`. Blocks whose first
    tail is >= 100 are skipped (false-positive stage-string offsets).
    """
    from collections import Counter
    counts: dict[str, Counter] = {}
    for block in blocks:
        first = block["tail"][0]
        if first >= 100:
            continue
        counts.setdefault(block["name"], Counter())[first] += 1
    return {name: (c.most_common(1)[0][0], c.most_common(1)[0][1], sum(c.values()))
            for name, c in counts.items()}


def group_stages(blocks: list[dict]) -> list[list[dict]]:
    """Group flat stage blocks into material groups (contiguous 264-byte stride)."""
    groups: list[list[dict]] = []
    for block in blocks:
        if not groups or block["offset"] - groups[-1][-1]["offset"] != STAGE_STRIDE:
            groups.append([])
        groups[-1].append(block)
    return groups


def decode_stage_channels(blocks: list[dict]) -> list[dict]:
    """Return per-material stage (type, channel) pairs.

    The u32 at +260 is a per-material texture-channel index. Observed domain:
    1, 3, 4, 5, 6 for L0/L1 stages, always 0 for L2 stages (see tests).
    """
    return [{"offset": group[0]["offset"],
             "stages": [{"name": s["name"], "type": s["tail"][0],
                         "channel": s["tail"][1]} for s in group]}
            for group in group_stages(blocks)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--materials", action="store_true",
                    help="print decoded material groups with stage types/channels")
    ap.add_argument("--triangles", action="store_true",
                    help="print decoded 36-byte triangle records (offset-292 tables)")
    ap.add_argument("--to-gtr2", metavar="OUT",
                    help="convert one RaceGMT mesh to a GTR2-layout GMT")
    ap.add_argument("--template", metavar="GMT",
                    help="GTR2 GMT structural template for --to-gtr2")
    args = ap.parse_args(argv)
    if args.to_gtr2:
        if not args.template or len(args.files) != 1:
            ap.error("--to-gtr2 requires --template and exactly one input file")
        source = Path(args.files[0]).read_bytes()
        template = Path(args.template).read_bytes()
        converted = to_gtr2_gmt(source, template)
        if converted is None:
            print("no decodable RaceGMT submeshes")
            return 1
        Path(args.to_gtr2).write_bytes(converted)
        print(f"{args.to_gtr2}: {len(converted)} bytes")
        return 0
    for f in args.files:
        try:
            data = Path(f).read_bytes()
            print(f, parse_header(data))
            if args.materials:
                blocks = read_material_blocks(data)
                for group in decode_stage_channels(blocks):
                    stages = ", ".join(f"{s['name']}(type={s['type']},ch={s['channel']})"
                                       for s in group["stages"])
                    print(f"  material@{group['offset']:#x}: {stages}")
            if args.triangles:
                records = read_triangle_records(data)
                print(f"  triangles={len(records)} "
                      f"groups={sorted(set(r['group'] for r in records))}")
                for record in records[:5]:
                    print(f"    ord={record['ordinal']} group={record['group']} "
                          f"idx={record['indices']} f32={record['floats']}")
        except ValueError as e:
            print(f, "ERROR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
