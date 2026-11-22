#!/usr/bin/env python3
"""Prototype rFactor-lineage -> GTR2 archive conversion pipeline.

Steps per archive:
  1. unpack MAS members with mas_tool
  2. decrypt ISI 16-byte-header members (skip=4 for GMTs)
  3. structurally convert old-layout GMTs to the GTR2 layout (gmt_layout)
  4. repack as a type-0 .gtr and validate the GMTs with gmt_format

LIMITATION: gmt_layout is a structural bridge only; geometry semantics and
in-game behaviour are not validated. Use --check to run without writing output.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import gmt_format
import gmt_layout
import isi_crypt
import mas_tool


def convert_bytes(name: str, data: bytes) -> tuple[bytes, str]:
    """Return (data, action) for one member."""
    if len(data) >= 16:
        sign, key = struct.unpack_from("<QQ", data, 0)
        if (sign ^ key) & 0xFFFFFFFFFFFFFFFF in isi_crypt.GAMES:
            data = isi_crypt.decrypt_bytes(data, skip=4)
    if name.lower().endswith(".gmt") and gmt_layout.is_old(data):
        data = gmt_layout.old_to_new(data)
        return data, "decrypt+layout"
    return data, "copy"


def convert_archive(source: str | Path, target: str | Path | None = None,
                    check: bool = False) -> dict:
    mtype, entries = mas_tool.read_archive(source)
    actions = {}
    converted = []
    for e in entries:
        data, action = convert_bytes(e.name, e.data or b"")
        actions[action] = actions.get(action, 0) + 1
        out = mas_tool.Entry(name=e.name, offset=0, size=len(data), zsize=0,
                             type=e.type, flags=e.flags, data=data)
        converted.append(out)
        if e.name.lower().endswith(".gmt") and gmt_layout.is_new(data):
            g = gmt_format.parse_gmt(e.name, data)
            if gmt_format.write_gmt(g) != data:
                raise ValueError(f"GMT validation failed for {e.name}")
    if not check:
        if target is None:
            raise ValueError("target path required unless --check is used")
        mas_tool.write_archive(target, converted, mas_type=0)
    return {"source_type": mtype, "members": len(converted), "actions": actions}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("target", nargs="?")
    ap.add_argument("--check", action="store_true", help="run conversions and validation without writing")
    args = ap.parse_args(argv)
    report = convert_archive(args.source, args.target, args.check)
    print(f"source_type={report['source_type']} members={report['members']} actions={report['actions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
