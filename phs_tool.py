#!/usr/bin/env python3
"""Structural scanner for GTL `.phs` containers.

The five GTL PHS members (PHYSICS/CARS/DRIVERS/AI/TRACKS) are not uniformly
encrypted: they contain PAR2-style packet headers (`PAR2\\0PKT`, 8-byte length,
16-byte set id, 16-byte hashed type) interleaved with high-entropy blocks.
Plaintext labels such as `PAR 2.0\\0Main`, `FileDesc`, `RecvSlic:` and
`Update_0901.exe` are embedded in packet bodies.  Full payload semantics are
not decoded; this tool locates packets and extracts readable strings.
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

PAR2_MAGIC = b"PAR2\0PKT"


def find_packets(data: bytes) -> list[dict]:
    """Locate PAR2-style packet headers and return their fields."""
    out = []
    for m in re.finditer(re.escape(PAR2_MAGIC), data):
        off = m.start()
        if off + 64 > len(data):
            continue
        length = struct.unpack_from("<Q", data, off + 8)[0]
        if length < 64 or off + length > len(data):
            continue
        out.append({"offset": off, "length": length,
                    "set_id": data[off + 16:off + 32].hex(),
                    "type_hash": data[off + 32:off + 48].hex(),
                    "body_start": off + 48})
    return out


def read_strings(data: bytes, minimum: int = 4) -> list[tuple[int, str]]:
    """Extract printable ASCII runs with their offsets."""
    out = []
    for m in re.finditer(rb"[A-Za-z][A-Za-z0-9_ .:/\\-]{%d,}\x00" % (minimum - 1), data):
        text = m.group().rstrip(b"\0").decode("latin-1")
        if len(text) >= minimum:
            out.append((m.start(), text))
    return out


def scan(data: bytes) -> dict:
    return {"packets": find_packets(data), "strings": read_strings(data)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    for f in args.files:
        report = scan(Path(f).read_bytes())
        print(f, "packets=", len(report["packets"]), "strings=", len(report["strings"]))
        for p in report["packets"][:5]:
            print("  packet@", hex(p["offset"]), "len", p["length"], "type", p["type_hash"][:16])
        for off, text in report["strings"][:8]:
            print("  ", hex(off), repr(text[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
