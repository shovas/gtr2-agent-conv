#!/usr/bin/env python3
"""Structural scanner for GTL `.phs` archive members.

The five GTL PHS members are not uniformly encrypted.  They contain a chain of
PAR2-style packets with a 64-byte header:

    magic `PAR2\\0PKT` (8), u64 packet length, 16-byte set id,
    16-byte constant hash (MD5 of the canonical Main-packet body),
    16-byte type string (`PAR 2.0\\0Main\\0`, `PAR 2.0\\0FileDesc`,
    `PAR 2.0\\0RecvSlic:`), then the packet body.

The Main and FileDesc packets carry recognisable PAR2 metadata (slice size,
file id, and a filename such as `GTL_Update_0901.exe`); the large RecoverySlice
bodies are high-entropy parity data.  Payload semantics beyond that are not
decoded.
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

PAR2_MAGIC = b"PAR2\0PKT"
HEADER_SIZE = 64


def _type_label(raw: bytes) -> str:
    """Decode a 16-byte PAR2 type field (`PAR 2.0\\0Main\\0...` -> `Main`)."""
    parts = raw.split(b"\0")
    return parts[1].decode("latin-1") if len(parts) > 1 else raw.decode("latin-1")


def find_packets(data: bytes) -> list[dict]:
    """Walk the contiguous PAR2-style packet chain from the first magic."""
    out = []
    pos = data.find(PAR2_MAGIC)
    while pos >= 0 and pos + HEADER_SIZE <= len(data):
        length = struct.unpack_from("<Q", data, pos + 8)[0]
        if length < HEADER_SIZE or pos + length > len(data):
            break
        out.append({"offset": pos, "length": length,
                    "set_id": data[pos + 16:pos + 32].hex(),
                    "hash": data[pos + 32:pos + 48].hex(),
                    "type": _type_label(data[pos + 48:pos + 64]),
                    "body": data[pos + HEADER_SIZE:pos + length]})
        pos = data.find(PAR2_MAGIC, pos + length)
    return out


def parse_main(body: bytes) -> dict | None:
    """Parse a Main packet body: u64 slice size, u32 file count, 16-byte file id."""
    if len(body) < 28:
        return None
    slice_size = struct.unpack_from("<Q", body, 0)[0]
    count = struct.unpack_from("<I", body, 8)[0]
    return {"slice_size": slice_size, "file_count": count,
            "file_ids": [body[12 + i * 16:28 + i * 16].hex()
                         for i in range(min(count, (len(body) - 12) // 16))]}


def parse_filedesc(body: bytes) -> dict | None:
    """Parse a FileDesc body: file id, hash16k, and a NUL-terminated filename."""
    if len(body) < 34:
        return None
    # The filename is the longest printable NUL-terminated ASCII run; its
    # offset varies with the number of optional hash fields in the body.
    match = max(re.finditer(rb"[ -~]{6,}\x00", body),
                key=lambda m: m.end() - m.start(), default=None)
    if match is None:
        return None
    name = match.group().rstrip(b"\0").decode("latin-1")
    return {"file_id": body[:16].hex(), "hash16k": body[16:32].hex(),
            "filename": name}


def read_strings(data: bytes, minimum: int = 6) -> list[tuple[int, str]]:
    out = []
    for m in re.finditer(rb"[A-Za-z][A-Za-z0-9_ .:/\\-]{%d,}\x00" % (minimum - 1), data):
        text = m.group().rstrip(b"\0").decode("latin-1")
        if len(text) >= minimum:
            out.append((m.start(), text))
    return out


def scan(data: bytes) -> dict:
    packets = find_packets(data)
    mains = [parse_main(p["body"]) for p in packets if p["type"] == "Main"]
    descs = [parse_filedesc(p["body"]) for p in packets if p["type"] == "FileDesc"]
    return {"packets": packets,
            "main": [m for m in mains if m],
            "filedesc": [d for d in descs if d],
            "strings": read_strings(data)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    for f in args.files:
        report = scan(Path(f).read_bytes())
        print(f, "packets=", len(report["packets"]),
              "main=", report["main"], "filedesc=", report["filedesc"])
        for p in report["packets"][:5]:
            print("  ", hex(p["offset"]), p["type"], "len", p["length"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
