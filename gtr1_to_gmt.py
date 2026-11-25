#!/usr/bin/env python3
"""Convert a GTR1 third-magic GMT to a GTR2-layout GMT.

Uses the corpus-verified parts of :func:`gmt_semantic.read_gtr1_geometry`:
descriptor vertex fields 1-3 (position-like, triangle-adjacency evidence) and
fields 4-6 (unit normals, 20,164/20,164 finite records). Per-descriptor index
buffers are rebased into one combined triangle list. Vertex fields 9/10 are
corpus-verified UV pairs (fields 8/11 are always zero) and are written into
the GTR2 single-block UV layout.

A real GTR2 GMT is required as a structural template at runtime; no game data
is stored in this repository.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import gmt_semantic
import vrl_to_gmt


def geometry_from_gtr1(data: bytes) -> tuple[list, list, list] | None:
    """Return (positions, normals, triangles) from all GTR1 descriptors."""
    descriptors = gmt_semantic.read_gtr1_geometry(data)
    if not descriptors:
        # Descriptor-less GTR1 meshes (e.g. shadow/LOD objects) carry an
        # rF1-style object mesh instead: 32-byte positions + u16 triangles.
        obj = gmt_semantic.read_gtr1_object_mesh(data)
        if not obj or not obj["positions"] or not obj["triangles"]:
            return None
        # Some object-mesh records contain NaN sentinel components; zero them
        # rather than dropping vertices, which would break triangle topology.
        positions = [tuple(0.0 if not math.isfinite(x) else x for x in pos[:3])
                     for pos in obj["positions"]]
        triangles = [tuple(t) for t in obj["triangles"]
                     if len(set(t)) == 3 and max(t) < len(positions)]
        if not positions or not triangles:
            return None
        return positions, vrl_to_gmt._normals(positions, triangles), triangles
    positions: list = []
    normals: list = []
    triangles: list = []
    for item in descriptors:
        base = len(positions)
        for vertex in item["vertices"]:
            positions.append(tuple(vertex[1:4]))
            normal = tuple(vertex[4:7])
            if not all(math.isfinite(x) for x in normal):
                normal = (0.0, 1.0, 0.0)
            normals.append(normal)
        # GTR1 index lists are triangle strips with degenerate separator
        # triangles. Use a sliding window so valid triangles between
        # separators are not lost.
        raw = list(item["indices"])
        groups = [tuple(raw[i:i + 3]) for i in range(len(raw) - 2)]
        for a, b, c in groups:
            if len({a, b, c}) == 3 and max(a, b, c) < item["v_count"]:
                triangles.append((base + a, base + b, base + c))
    if not positions or not triangles:
        return None
    return positions, normals, triangles


def uvs_from_gtr1(data: bytes) -> list[tuple[float, float]] | None:
    """Return UV pairs from GTR1 48-byte vertex fields 9/10.

    Corpus-verified on 20,017 sampled GTR1 vertices: fields 8 and 11 are
    always zero, while fields 9/10 hold UV-like values (91.7% / 82.6% within
    [-2, 2], with tiled world-space coordinates outside). Descriptor-less
    meshes carry no such stream and return None.
    """
    descriptors = gmt_semantic.read_gtr1_geometry(data)
    if not descriptors:
        return None
    uvs = []
    for item in descriptors:
        for vertex in item["vertices"]:
            uvs.append((vertex[9], vertex[10]))
    return uvs or None


def gtr1_to_gmt(data: bytes, template: bytes) -> bytes:
    """Build a one-submesh GTR2 GMT from GTR1 third-magic GMT bytes."""
    geometry = geometry_from_gtr1(data)
    if geometry is None:
        raise ValueError("no decodable GTR1 geometry")
    positions, normals, triangles = geometry
    uvs = uvs_from_gtr1(data)
    if uvs is not None and len(uvs) != len(positions):
        uvs = None
    return vrl_to_gmt.build_gmt(positions, triangles, template, normals, uvs)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gmt", help="GTR1 third-magic .gmt file")
    ap.add_argument("template", help="real GTR2 .gmt used as structural template")
    ap.add_argument("output", help="destination .gmt path")
    args = ap.parse_args(argv)
    geometry = geometry_from_gtr1(Path(args.gmt).read_bytes())
    if geometry is None:
        print("no decodable geometry")
        return 1
    positions, normals, triangles = geometry
    data = vrl_to_gmt.build_gmt(positions, triangles, Path(args.template).read_bytes(), normals)
    problems = vrl_to_gmt.verify_gmt_geometry(data, positions, triangles, normals)
    if problems:
        print("verification failed:", problems)
        return 1
    Path(args.output).write_bytes(data)
    print(f"wrote {args.output}: {len(positions)} vertices, {len(triangles)} triangles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
