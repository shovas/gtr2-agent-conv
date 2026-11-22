#!/usr/bin/env python3
"""Inspect SimBin FXM/FXA/LMA animation container files.

Observed magics: b'FXM ', b'FXA ', b'LMA ' (extension does not always match magic).
Header is partially understood; tool validates magic and reports observed fields.
Node/bone name strings can be extracted heuristically; internal record semantics unconfirmed.
Read/write is lossless at file-bytes level.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import struct
from dataclasses import dataclass
from pathlib import Path

MAGICS = {b"FXM ", b"FXA ", b"LMA "}


@dataclass
class FxmHeader:
    path: Path
    size: int
    magic: bytes
    v1: int
    v2: int
    f3: int
    f4: int
    f5: int
    f6: int

    @property
    def known_magic(self) -> bool:
        return self.magic in MAGICS

    @property
    def be_fields(self) -> tuple[int, int, int, int, int, int]:
        # Raw BE interpretation of bytes 4..28; observed plausible for some fields, but
        # some entries may overlap string/table data depending on format variant. Unconfirmed.
        b = Path(self.path).read_bytes()
        return struct.unpack_from(">HHIIII", b, 4)


def read_header(path: str | Path) -> FxmHeader:
    p = Path(path)
    b = p.read_bytes()
    if len(b) < 28:
        raise ValueError("file too small")
    magic, v1, v2, f3, f4, f5, f6 = struct.unpack_from("<4sHHIIII", b, 0)
    return FxmHeader(p, len(b), magic, v1, v2, f3, f4, f5, f6)


def _first_string_offset(b: bytes, min_len: int = 4) -> int | None:
    i = 0
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j < len(b) and b[j] == 0 and j - i >= min_len:
                return i
            i = j + 1
        else:
            i += 1
    return None


def parse_node_records(b: bytes) -> list[dict]:
    """Walk the contiguous skeleton-node table anchored on the `Bip01` record.

    Each record is `name (no NUL), u32 marker=1, u32 size_hint, u32 key_count=3,
    84 bytes of keyframe data`.  The keyframe block decodes as 2 TRS keys
    (see `decode_node_keys`).  Records are contiguous, so a sequential walk from the strong `Bip01\\x01\\x00\\x00\\x00` anchor avoids the
    false positives a free-standing name regex produces on 3ds Max metadata
    (e.g. build timestamps or material names).
    """
    out = []
    pos = b.find(b"Bip01\x01\x00\x00\x00")
    if pos < 0:
        return out
    while 0 <= pos < len(b):
        marker = b.find(b"\x01\x00\x00\x00", pos + 1)
        if marker < 0 or marker + 12 > len(b):
            break
        name = b[pos:marker]
        if not name or not all(32 <= c < 127 for c in name):
            break
        size_hint, key_count = struct.unpack_from("<II", b, marker + 4)
        if key_count != 3 or not (0x50 <= size_hint <= 0x80):
            break
        out.append({"offset": pos, "name": name.decode("ascii"),
                    "size_hint": size_hint, "key_count": key_count,
                    "keyframe_offset": marker + 12,
                    "keyframe_bytes": 84})
        pos = marker + 12 + 84
    return out


def decode_node_keys(b: bytes, node: dict) -> dict:
    """Decode a node's 84-byte keyframe block into TRS keys.

    Layout (validated across all 27 nodes of FU_PreIdle4-R.FXM): 2 keys of
    10 floats each (position xyz, rotation quaternion xyzw, scale xyz) plus a
    4-byte trailer.  Quaternion norms are ~1 in 54/54 keys and scale ~1 in
    52/54; the two keys are usually identical for static/rest-pose nodes.
    """
    ko = node["keyframe_offset"]
    f = struct.unpack_from("<21f", b, ko)
    keys = []
    for k in range(2):
        base = k * 10
        pos = list(f[base:base + 3])
        quat = list(f[base + 3:base + 7])
        scale = list(f[base + 7:base + 10])
        norm = math.sqrt(sum(x * x for x in quat))
        keys.append({"position": pos, "quaternion": quat,
                     "scale": scale, "quat_norm": norm})
    trailer = struct.unpack_from("<I", b, ko + 80)[0]
    return {"node": node["name"], "keys": keys, "trailer": trailer}


def cmd_info(args: argparse.Namespace) -> int:
    h = read_header(args.file)
    b = Path(args.file).read_bytes()
    strings = [s.decode("latin-1", "replace") for s in b.split(b"\x00") if len(s) > 4 and all(32 <= c < 127 or c in (9, 10, 13) for c in s[:20])]
    first = _first_string_offset(b)
    print(f"path: {h.path}")
    print(f"size: {h.size}")
    print(f"magic: {h.magic!r}")
    print(f"known_magic: {h.known_magic}")
    print(f"header_u16_le: {h.v1} {h.v2}")
    print(f"header_u32_le: {h.f3} {h.f4} {h.f5} {h.f6}")
    be = h.be_fields
    print(f"header_be: {be[0]} {be[1]} {be[2]} {be[3]} {be[4]} {be[5]}")
    print(f"sha256: {hashlib.sha256(b).hexdigest()}")
    print(f"first_string_offset: {first}")
    for s in strings[:8]:
        print(f"string: {s[:120]}")
    return 0


def extract_strings(b: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j < len(b) and b[j] == 0 and j - i >= min_len:
                out.append((i, b[i:j].decode('latin-1', 'replace')))
            i = j + 1
        else:
            i += 1
    return out


def cmd_nodes(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    for off, s in extract_strings(b):
        # heuristic: bone/node names often contain Bip01, Driver, or spaces/underscores
        if args.all or any(k in s for k in ('Bip01', 'Driver', 'Bone', 'Node')):
            print(f'{off}\t{s}')
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    Path(args.out).write_bytes(b)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)
    p = sub.add_parser("nodes", help="extract likely node/bone names (heuristic)")
    p.add_argument("file")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_nodes)
    p = sub.add_parser("roundtrip", help="lossless byte copy")
    p.add_argument("file")
    p.add_argument("out")
    p.set_defaults(func=cmd_roundtrip)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
