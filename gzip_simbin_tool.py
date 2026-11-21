#!/usr/bin/env python3
"""Read/write SimBin gzip-wrapped files (.dsi, .hat).

These files are gzip-compressed payloads. DSI/HAT payloads observed as
SimBin text-like data starting with //[[gMb1.000f...]].
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path


def read_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def decompress(path: str | Path) -> bytes:
    return gzip.decompress(read_bytes(path))


def compress_bytes(data: bytes, mtime: int = 0) -> bytes:
    # deterministic for round-trip-friendly writes
    import io
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=mtime) as f:
        f.write(data)
    return buf.getvalue()


def cmd_info(args: argparse.Namespace) -> int:
    raw = read_bytes(args.file)
    dec = gzip.decompress(raw)
    print(f"path: {args.file}")
    print(f"compressed_size: {len(raw)}")
    print(f"decompressed_size: {len(dec)}")
    print(f"sha256_compressed: {hashlib.sha256(raw).hexdigest()}")
    print(f"sha256_decompressed: {hashlib.sha256(dec).hexdigest()}")
    print(f"head: {dec[:80]!r}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    data = decompress(args.file)
    Path(args.out).write_bytes(data)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    data = read_bytes(args.input)
    Path(args.out).write_bytes(compress_bytes(data))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)
    p = sub.add_parser("extract")
    p.add_argument("file")
    p.add_argument("out")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("create")
    p.add_argument("input")
    p.add_argument("out")
    p.set_defaults(func=cmd_create)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
