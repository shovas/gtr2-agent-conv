#!/usr/bin/env python3
"""Offline validation of rF1→GTR2 GMT semantic conversion.

Because running the game is out of scope, this tool provides the strongest
available offline evidence: it decodes the original rF1 GMT and the converted
GTR2-layout GMT, compares positions/UVs/faces exactly, checks the material tail
is preserved, and re-parses the converted file with an independent reader whose
field offsets follow the published Blender GMT importer schema (not gmt_semantic).

This establishes *offline compatibility confidence*, not runtime validation.
"""
from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import gmt_semantic
import gmt_layout

# Independent schema (Blender GTR2/rFactor GMT importer field offsets).
SCHEMAS = {
    "gtr2": dict(id=0x04, v_count=0x08, v_off=0x0C, uv_off=0x14,
                 i_count=0x24, i_off=0x28, uv_sub_off=8),
    "rf1": dict(id=0x08, v_count=0x18, v_off=0x04, uv_off=0x0C,
                i_count=0x20, i_off=0x24, uv_sub_off=0),
}


def independent_read(data: bytes, schema_name: str) -> dict:
    """Re-read submeshes using only the schema offsets, independent of gmt_semantic."""
    schema = SCHEMAS[schema_name]
    size = len(data)
    out = []
    for pos in range(0, max(0, size - 0x30), 4):
        magic = struct.unpack_from("<I", data, pos)[0]
        hi, lo = magic >> 16, magic & 0xFFFF
        if hi not in (0x2000, 0x0000) or lo not in (0x4011, 0x4015, 0x4035):
            continue
        get = lambda key: struct.unpack_from("<I", data, pos + schema[key])[0]
        vc, vo, uo, ic, io = (get("v_count"), get("v_off"), get("uv_off"),
                              get("i_count"), get("i_off"))
        if not (0 < vc < 200000 and 0 < ic < 600000 and vo > pos and io > pos):
            continue
        if vo + 4 + vc * 32 > size or io + 4 + ic * 2 > size:
            continue
        verts = [struct.unpack_from("<3f", data, vo + 4 + i * 32) for i in range(vc)]
        uvs = ([(0.0, 0.0)] * vc if uo == 0 else
               [struct.unpack_from("<2f", data, uo + 4 + i * 32 + schema["uv_sub_off"])
                for i in range(vc)])
        idx = struct.unpack_from("<%dH" % ic, data, io + 4)
        out.append({"positions": verts, "uvs": uvs, "indices": idx})
        break  # one submesh is enough for an independent cross-check
    return {"submeshes": out}


def _float_lists_equal(a, b) -> bool:
    """Compare float tuples with NaN-aware equality (two NaNs count as equal).

    Some rF1 GMT UVs contain NaN payloads that are preserved byte-for-byte by
    the conversion; plain tuple equality reports them as unequal.
    """
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if len(x) != len(y):
            return False
        for p, q in zip(x, y):
            if p == q:
                continue
            if isinstance(p, float) and isinstance(q, float) and math.isnan(p) and math.isnan(q):
                continue
            return False
    return True


def validate(old_data: bytes, new_data: bytes) -> dict:
    """Return a validation report for an old→new conversion."""
    old = gmt_semantic.read_gmt(old_data)
    new = gmt_semantic.read_gmt(new_data)
    old_pos = [p for s in old["submeshes"] for p in s["positions"]]
    new_pos = [p for s in new["submeshes"] for p in s["positions"]]
    old_uv = [u for s in old["submeshes"] for u in s["uvs"]]
    new_uv = [u for s in new["submeshes"] for u in s["uvs"]]
    old_faces = [f for s in old["submeshes"] for f in s["faces"]]
    new_faces = [f for s in new["submeshes"] for f in s["faces"]]
    positions_equal = _float_lists_equal(old_pos, new_pos)
    uvs_equal = _float_lists_equal(old_uv, new_uv)
    faces_equal = old_faces == new_faces

    # Independent cross-check of the converted file's first submesh.
    indep = independent_read(new_data, "gtr2")
    cross = False
    if indep["submeshes"] and new["submeshes"]:
        ref = new["submeshes"][0]
        cross = (indep["submeshes"][0]["positions"] == ref["positions"])

    # Material tail preserved: locate u32 obj_list_offset at 0 and compare tail bytes.
    old_obj = struct.unpack_from("<I", old_data, 0)[0]
    new_obj = struct.unpack_from("<I", new_data, 0)[0]
    tail_equal = old_data[old_obj:] == new_data[new_obj:]

    return {"submeshes": (len(old["submeshes"]), len(new["submeshes"])),
            "vertices": (len(old_pos), len(new_pos)), "faces": (len(old_faces), len(new_faces)),
            "positions_equal": positions_equal, "uvs_equal": uvs_equal,
            "faces_equal": faces_equal, "independent_cross_check": cross,
            "material_tail_equal": tail_equal,
            "pass": all((positions_equal, uvs_equal, faces_equal, cross, tail_equal))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("old")
    ap.add_argument("new")
    args = ap.parse_args(argv)
    report = validate(Path(args.old).read_bytes(), Path(args.new).read_bytes())
    for key, value in report.items():
        print(f"{key}={value}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
