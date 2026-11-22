#!/usr/bin/env python3
"""Format-level GMT submesh decoder (GTR2 and rFactor 1 layouts).

Both layouts store a per-submesh header whose u32 magic has a high word of
0x2000 (triangle list) or 0x0000 (strip), and a low word of 0x4011, 0x4015
or 0x4035.  The remaining header fields are at layout-specific offsets.
Vertices are 32-byte records whose first three floats are the position;
UVs live in a separate 32-byte stream; indices are u16 after a 4-byte lead.

This module implements the format observations independently; it does not
copy code from any third-party implementation.  It only reads files.
"""
from __future__ import annotations

import struct
from pathlib import Path

MAGIC_HI = (0x2000, 0x0000)
MAGIC_LO = (0x4011, 0x4015, 0x4035)

SCHEMAS = {
    "gtr2": dict(id=0x04, v_count=0x08, v_off=0x0C, uv_off=0x14,
                 i_count=0x24, i_off=0x28, uv_sub_off=8),
    "rf1": dict(id=0x08, v_count=0x18, v_off=0x04, uv_off=0x0C,
                i_count=0x20, i_off=0x24, uv_sub_off=0),
}

VERTEX_STRIDE = 32
UV_STRIDE = 32


def _field(data: bytes, pos: int, offset: int) -> int:
    return struct.unpack_from("<I", data, pos + offset)[0]


def find_submeshes(data: bytes) -> list[dict]:
    """Scan for valid per-submesh headers in either layout."""
    out = []
    size = len(data)
    for pos in range(0, max(0, size - 0x30), 4):
        magic = struct.unpack_from("<I", data, pos)[0]
        hi, lo = magic >> 16, magic & 0xFFFF
        if hi not in MAGIC_HI or lo not in MAGIC_LO:
            continue
        for name, schema in SCHEMAS.items():
            fields = (schema["id"], schema["v_count"], schema["v_off"],
                      schema["uv_off"], schema["i_count"], schema["i_off"])
            if pos + max(fields) + 4 > size:
                continue
            vc = _field(data, pos, schema["v_count"])
            vo = _field(data, pos, schema["v_off"])
            uo = _field(data, pos, schema["uv_off"])
            ic = _field(data, pos, schema["i_count"])
            io = _field(data, pos, schema["i_off"])
            if not (0 < vc < 200000 and 0 < ic < 600000):
                continue
            if vo == 0 or io == 0 or vo <= pos or io <= pos:
                continue
            if vo + 4 + vc * VERTEX_STRIDE > size:
                continue
            if io + 4 + ic * 2 > size:
                continue
            if uo and uo + 4 + vc * UV_STRIDE > size:
                continue
            out.append({"offset": pos, "schema": name, "id": _field(data, pos, schema["id"]),
                        "is_strip": hi == 0x0000, "v_count": vc, "v_off": vo,
                        "uv_off": uo, "i_count": ic, "i_off": io,
                        "uv_sub_off": schema["uv_sub_off"]})
            break
    return out


def read_positions(data: bytes, sub: dict) -> list[tuple[float, float, float]]:
    start = sub["v_off"] + 4
    return [struct.unpack_from("<3f", data, start + i * VERTEX_STRIDE)
            for i in range(sub["v_count"])]


def read_uvs(data: bytes, sub: dict) -> list[tuple[float, float]]:
    if not sub["uv_off"]:
        return [(0.0, 0.0)] * sub["v_count"]
    start = sub["uv_off"] + 4
    return [struct.unpack_from("<2f", data, start + i * UV_STRIDE + sub["uv_sub_off"])
            for i in range(sub["v_count"])]


def _is_sequential(data: bytes, sub: dict) -> bool:
    start = sub["i_off"] + 4
    for i in range(min(20, sub["i_count"])):
        if struct.unpack_from("<H", data, start + i * 2)[0] != i:
            return False
    return True


def read_faces(data: bytes, sub: dict) -> list[tuple[int, int, int]]:
    ic, io, vc = sub["i_count"], sub["i_off"], sub["v_count"]
    if ic == 0 or _is_sequential(data, sub):
        return [(i, i + 1, i + 2) for i in range(0, vc - 2, 3)]
    start = io + 4
    raw = [struct.unpack_from("<H", data, start + i * 2)[0] for i in range(ic)]
    if sub["is_strip"]:
        faces = [(raw[i], raw[i + 2], raw[i + 1]) if i % 2
                 else (raw[i], raw[i + 1], raw[i + 2])
                 for i in range(len(raw) - 2)]
    else:
        faces = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw) - 2, 3)]
    return [f for f in faces if max(f) < vc and len(set(f)) == 3]


def read_gmt(data: bytes) -> dict:
    """Decode all submeshes of a GMT into a layout-independent representation."""
    subs = []
    for sub in find_submeshes(data):
        item = dict(sub)
        item["positions"] = read_positions(data, sub)
        item["uvs"] = read_uvs(data, sub)
        item["faces"] = read_faces(data, sub)
        subs.append(item)
    return {"submeshes": subs,
            "vertex_count": sum(len(s["positions"]) for s in subs),
            "face_count": sum(len(s["faces"]) for s in subs)}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    for f in args.files:
        try:
            g = read_gmt(Path(f).read_bytes())
            print(f, "submeshes=", len(g["submeshes"]),
                  "vertices=", g["vertex_count"], "faces=", g["face_count"])
            for s in g["submeshes"][:5]:
                print("  ", hex(s["offset"]), s["schema"], "id", s["id"],
                      "v", s["v_count"], "f", len(s["faces"]))
        except Exception as exc:
            print(f, "ERROR", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
