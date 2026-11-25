#!/usr/bin/env python3
"""Convert a decoded Sports Car GT ``.vrl`` mesh to a GTR2-layout GMT.

The structural GMT writer/relayout code lives in :mod:`gmt_format`; this module
only maps the corpus-verified parts of a VRL mesh into a one-submesh GMT:

* VRL vertex fields 0-2 -> position (16-byte records: xyz + constant zero in
  300/300 sampled files; triangle-adjacency/random distance ratio 0.356)
* normals are computed from the converted triangles (VRL has no normal stream)
* VRL index buffer -> u16 triangle indices (quads triangulated) after the
  standard 4-byte lead
* VRL UV-like coordinate pairs are **not** transferred: the GTR2 32-byte base
  vertex layout's f0/f7 fields have unconfirmed semantics, so guessing there
  would violate the project's "no speculative decoder" rule.

A real GTR2 GMT is required as a structural template (header region, mesh
record defaults and material tail). It is read at runtime and never copied into
this repository. The output is verified by re-parsing it with
:func:`gmt_format.parse_gmt`.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import gmt_format
import simbin_text_tool as stt


def prepare_geometry(vrl: dict) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    """Return positions and triangles derived from a decoded VRL mesh."""
    positions = [tuple(v[:3]) for v in vrl["vertices"]]
    raw = list(vrl["indices"])
    if len(raw) % 4 == 0:
        triangles = []
        for i in range(0, len(raw), 4):
            a, b, c, d = raw[i:i + 4]
            triangles.extend(((a, b, c), (a, c, d)))
    elif len(raw) % 3 == 0:
        triangles = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    else:
        triangles = [tuple(raw[i:i + 3]) for i in range(len(raw) - 2)]
    valid = [t for t in triangles if len(set(t)) == 3 and all(i < len(positions) for i in t)]
    return positions, valid


def _normals(positions: list[tuple[float, float, float]],
             triangles: list[tuple[int, int, int]]) -> list[tuple[float, float, float]]:
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    for a, b, c in triangles:
        p, q, r = positions[a], positions[b], positions[c]
        u = [q[k] - p[k] for k in range(3)]
        v = [r[k] - p[k] for k in range(3)]
        cross = (u[1] * v[2] - u[2] * v[1],
                 u[2] * v[0] - u[0] * v[2],
                 u[0] * v[1] - u[1] * v[0])
        for idx in (a, b, c):
            for k in range(3):
                accum[idx][k] += cross[k]
    out = []
    for n in accum:
        length = sum(x * x for x in n) ** 0.5
        out.append(tuple(x / length for x in n) if length > 1e-12 else (0.0, 1.0, 0.0))
    return out


def _vertex_blob(positions, normals) -> bytes:
    out = bytearray()
    for pos, normal in zip(positions, normals):
        out.extend(struct.pack("<I6fI", 0, *pos, *normal, 0))
    return bytes(out)


def _index_blob(triangles: list[tuple[int, int, int]]) -> bytes:
    flat = [i for triangle in triangles for i in triangle]
    if not flat:
        return struct.pack("<I", 0)
    if max(flat) >= 65536:
        raise ValueError("VRL vertex index exceeds u16 range; mesh needs splitting")
    return struct.pack("<I", 0) + struct.pack(f"<{len(flat)}H", *flat)


def build_gmt(positions: list[tuple[float, float, float]],
              triangles: list[tuple[int, int, int]],
              template: bytes,
              normals: list[tuple[float, float, float]] | None = None,
              uvs: list[tuple[float, float]] | None = None) -> bytes:
    """Build a one-submesh GTR2 GMT from positions/triangles and a template.

    ``uvs``, when supplied, are written into the GTR2 UV block (u at +4,
    v at +8 of each 32-byte record), matching the dominant real layout.
    """
    base = gmt_format.parse_gmt("template.gmt", data=template)
    if not base.meshes:
        raise ValueError("template GMT has no mesh record to use as a default")
    template_record = list(base.meshes[0].record.raw)

    if normals is None:
        normals = _normals(positions, triangles)
    vertices = _vertex_blob(positions, normals)
    indices = _index_blob(triangles)
    vc, ic = len(positions), len(triangles) * 3
    if vc == 0:
        raise ValueError("VRL mesh has no vertices")

    record = template_record[:27] + [0] * max(0, 27 - len(template_record))
    record = record[:27]
    record[3] = vc
    record[4] = 0  # relayout_gmt recomputes all offsets
    record[10] = ic
    record[11] = 0

    stream = b""
    if uvs:
        if len(uvs) != vc:
            raise ValueError("UV count does not match vertex count")
        stream = b"".join(bytes(4) + struct.pack("<2f", u, v) + bytes(20)
                          for u, v in uvs)
    mesh = gmt_format.GmtMesh(
        record=gmt_format.GmtMeshRecord(raw=record),
        vertex_data=vertices,
        index_data=indices,
        stream2_data=stream,
    )
    output = gmt_format.GmtFile(
        source_path=Path("converted.gmt"),
        original=template,
        obj_list_offset=base.obj_list_offset,
        flags=base.flags,
        magic=base.magic,
        header_18_16c=base.header_18_16c,
        mesh_first=0x174,
        meshes=[mesh],
        tail=base.tail,
        gaps=b"",
    )
    return gmt_format.relayout_gmt(output)


def vrl_to_gmt(vrl: dict, template: bytes) -> bytes:
    """Build a one-submesh GTR2 GMT from a decoded VRL mesh dict."""
    positions, triangles = prepare_geometry(vrl)
    return build_gmt(positions, triangles, template)


def verify_gmt_geometry(data: bytes, positions, triangles, normals) -> list[str]:
    """Re-parse a generated GMT against expected geometry."""
    problems: list[str] = []
    try:
        parsed = gmt_format.parse_gmt("generated.gmt", data=data)
    except Exception as exc:
        return [f"parse failed: {exc}"]
    if len(parsed.meshes) != 1:
        return [f"expected 1 mesh, got {len(parsed.meshes)}"]
    mesh = parsed.meshes[0]
    if mesh.record.vertex_count != len(positions):
        problems.append("vertex count mismatch")
    if mesh.record.index_count != len(triangles) * 3:
        problems.append("index count mismatch")
    if mesh.base_vertices and len(mesh.base_vertices) != len(positions):
        problems.append("decoded vertex count mismatch")
    if mesh.base_vertices:
        for out, pos, normal in zip(mesh.base_vertices, positions, normals):
            if any(abs(a - b) > 1e-3 for a, b in zip((out.x, out.y, out.z), pos)):
                problems.append("position mismatch")
                break
            if any(abs(a - b) > 1e-3 for a, b in zip((out.nx, out.ny, out.nz), normal)):
                problems.append("normal mismatch")
                break
    return problems


def verify_gmt(data: bytes, vrl: dict) -> list[str]:
    """Re-parse a VRL-generated GMT; return problems (empty means verified)."""
    positions, triangles = prepare_geometry(vrl)
    return verify_gmt_geometry(data, positions, triangles, _normals(positions, triangles))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("vrl", help="decoded .vrl member (binary file)")
    ap.add_argument("template", help="real GTR2 .gmt used as a structural template")
    ap.add_argument("output", help="destination .gmt path")
    args = ap.parse_args(argv)
    vrl = stt.read_vrl(Path(args.vrl).read_bytes())
    if vrl is None:
        print("invalid .vrl")
        return 1
    data = vrl_to_gmt(vrl, Path(args.template).read_bytes())
    problems = verify_gmt(data, vrl)
    if problems:
        print("verification failed:", problems)
        return 1
    Path(args.output).write_bytes(data)
    print(f"wrote {args.output}: {vrl['vertex_count']} vertices, "
          f"{vrl['index_count']} indices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
