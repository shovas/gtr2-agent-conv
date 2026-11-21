#!/usr/bin/env python3
"""Inspect SimBin FXM/FXA/LMA animation container files.

Observed magics: b'FXM ', b'FXA ', b'LMA ' (extension does not always match magic).
Header is partially understood; tool validates magic and reports observed fields.
Read/write is lossless at file-bytes level.
"""
from __future__ import annotations

import argparse
import hashlib
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


def cmd_info(args: argparse.Namespace) -> int:
    h = read_header(args.file)
    b = Path(args.file).read_bytes()
    strings = [s.decode("latin-1", "replace") for s in b.split(b"\x00") if len(s) > 4 and all(32 <= c < 127 or c in (9, 10, 13) for c in s[:20])]
    print(f"path: {h.path}")
    print(f"size: {h.size}")
    print(f"magic: {h.magic!r}")
    print(f"known_magic: {h.known_magic}")
    print(f"header_u16_le: {h.v1} {h.v2}")
    print(f"header_u32_le: {h.f3} {h.f4} {h.f5} {h.f6}")
    be = h.be_fields
    print(f"header_be: {be[0]} {be[1]} {be[2]} {be[3]} {be[4]} {be[5]}")
    print(f"sha256: {hashlib.sha256(b).hexdigest()}")
    for s in strings[:8]:
        print(f"string: {s[:120]}")
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
    p = sub.add_parser("roundtrip", help="lossless byte copy")
    p.add_argument("file")
    p.add_argument("out")
    p.set_defaults(func=cmd_roundtrip)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
