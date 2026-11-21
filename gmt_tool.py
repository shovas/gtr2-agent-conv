#!/usr/bin/env python3
"""Minimal GMT inspection/validation tool for GTL/GTR2 conversion.

First-pass, evidence-based: validates observed GTR2/GT Legends GMT header family.
It does NOT convert GMT geometry; use for inventory, sanity checks, and diffs.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
from dataclasses import dataclass
from pathlib import Path

# Observed in GTR2/GT Legends GMTs and hand_selected GOALPOST.GMT.
GMT_MAGIC_GTR_GTL = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")


@dataclass
class GmtHeader:
    path: Path
    size: int
    v0: int
    flags: int
    magic: bytes

    @property
    def known_magic(self) -> bool:
        return self.magic == GMT_MAGIC_GTR_GTL


def read_header(path: str | os.PathLike) -> GmtHeader:
    p = Path(path)
    data = p.read_bytes()
    if len(data) < 24:
        raise ValueError(f"file too small for GMT header: {p}")
    v0, flags, magic = struct.unpack_from("<II16s", data, 0)
    return GmtHeader(path=p, size=len(data), v0=v0, flags=flags, magic=magic)


def sha256(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_gmts(root: str | os.PathLike) -> list[Path]:
    root = Path(root)
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".gmt")


def cmd_info(args: argparse.Namespace) -> int:
    h = read_header(args.file)
    print(f"path: {h.path}")
    print(f"size: {h.size}")
    print(f"v0: {h.v0} (0x{h.v0:08x})")
    print(f"flags: {h.flags} (0x{h.flags:08x})")
    print(f"magic: {h.magic.hex()}")
    print(f"known_gtr_gtl_magic: {h.known_magic}")
    print(f"sha256: {sha256(h.path)}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    bad = 0
    for p in scan_gmts(args.root):
        try:
            h = read_header(p)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR\t{p}\t{e}")
            bad += 1
            continue
        status = "OK" if h.known_magic else "UNKNOWN_MAGIC"
        if status != "OK":
            bad += 1
        if args.verbose or status != "OK":
            print(f"{status}\t{h.size}\t0x{h.flags:08x}\t{h.magic.hex()}\t{p}")
    if args.verbose or bad:
        print(f"scanned={len(scan_gmts(args.root))} issues={bad}")
    else:
        print(f"scanned={len(scan_gmts(args.root))} issues=0")
    return 0 if bad == 0 else 1


def cmd_diff(args: argparse.Namespace) -> int:
    left = {p.name.lower(): p for p in scan_gmts(args.left)}
    right = {p.name.lower(): p for p in scan_gmts(args.right)}
    names = sorted(set(left) | set(right))
    same = diff = left_only = right_only = 0
    for name in names:
        lp, rp = left.get(name), right.get(name)
        if lp and not rp:
            left_only += 1
            print(f"LEFT_ONLY\t{name}\t{lp}")
        elif rp and not lp:
            right_only += 1
            print(f"RIGHT_ONLY\t{name}\t{rp}")
        else:
            la, ra = lp.read_bytes(), rp.read_bytes()
            if la == ra:
                same += 1
                if args.verbose:
                    print(f"SAME\t{name}")
            else:
                diff += 1
                lh, rh = read_header(lp), read_header(rp)
                print(f"DIFF\t{name}\t{lh.size}\t{rh.size}\t0x{lh.flags:08x}\t0x{rh.flags:08x}")
    print(f"same={same} diff={diff} left_only={left_only} right_only={right_only}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="show GMT header info")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("scan", help="scan directory for .gmt files and validate header magic")
    p.add_argument("root")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("diff", help="compare GMT files by basename between two trees")
    p.add_argument("left")
    p.add_argument("right")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_diff)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
