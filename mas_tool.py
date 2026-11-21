#!/usr/bin/env python3
"""Minimal GMOTORMAS10 / ISI MAS archive tool.

Supports create, list, extract, add, update, delete for MAS type 0 (.gtr/.gtl/.mas).
Format reference: rfactortools.mas and quickbms_scripts/mas.bms.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

MAS_TYPE0 = b"GMOTORMAS10\x00\x00\x00\x00\x00"
MAS_TYPE1 = b"\xc8\xcf\xd2\xd8\xce\xd8\xe6\xc9\xca\xdd\xd8\xbe\xbb\xa6\xbf\x90"
MAS_TYPE3 = b"CUBEMAS4.10\x00\x00\x00\x00\x00"


@dataclass
class Entry:
    name: str
    offset: int
    size: int
    zsize: int
    type: int = 0
    flags: int = 0
    data: bytes | None = None


def _mas_type(signature: bytes) -> int:
    if signature == MAS_TYPE0:
        return 0
    if signature == MAS_TYPE1:
        return 1
    if signature == MAS_TYPE3:
        return 3
    raise ValueError(f"unsupported MAS signature: {signature!r}")


def read_archive(path: str | os.PathLike) -> tuple[int, list[Entry]]:
    with open(path, "rb") as f:
        sig = f.read(16)
        mtype = _mas_type(sig)
        if mtype == 1:
            f.seek(16)
            file_count, _data_size = struct.unpack("<4xll", f.read(12))
            table_off = 28
        else:
            f.seek(16)
            file_count, _data_size = struct.unpack("<ll", f.read(8))
            table_off = 24
        f.seek(table_off)
        entries: list[Entry] = []
        for _ in range(file_count):
            raw = f.read(256)
            if mtype == 0:
                offset, size, zsize, name = struct.unpack("<4xlll240s", raw)
                entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"), offset=offset, size=size, zsize=zsize)
            elif mtype == 1:
                etype, flags, name, offset, size, zsize = struct.unpack("<BBxx236slll4x", raw)
                entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"), offset=offset, size=size, zsize=zsize, type=etype, flags=flags)
            elif mtype == 3:
                offset, size, zsize, name = struct.unpack("<4xlll4x236s", raw)
                entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"), offset=offset, size=size, zsize=zsize)
            else:
                raise ValueError(mtype)
            entries.append(entry)
        base = f.tell()
        for e in entries:
            e.offset += base
            f.seek(e.offset)
            blob = f.read(e.zsize)
            e.data = zlib.decompress(blob) if e.size != e.zsize else blob
            if len(e.data) != e.size:
                raise ValueError(f"size mismatch for {e.name}: {len(e.data)} != {e.size}")
    return mtype, entries


def write_archive(path: str | os.PathLike, entries: list[Entry], mas_type: int = 0) -> None:
    if mas_type == 0:
        sig = MAS_TYPE0
        table_off = 24
    elif mas_type == 1:
        sig = MAS_TYPE1
        table_off = 28
    elif mas_type == 3:
        sig = MAS_TYPE3
        table_off = 24
    else:
        raise ValueError(f"unsupported mas_type {mas_type}")

    packed = []
    for e in entries:
        data = e.data if e.data is not None else b""
        z = zlib.compress(data)
        packed.append((e, data, z))

    base = table_off + 256 * len(packed)
    with open(path, "wb") as f:
        f.write(sig)
        if mas_type == 1:
            f.write(struct.pack("<4xll", len(packed), sum(len(z) for _, _, z in packed)))
        else:
            f.write(struct.pack("<ll", len(packed), sum(len(z) for _, _, z in packed)))
        f.write(b"\x00" * (table_off - f.tell()))
        f.seek(base)
        table = []
        offset = 0
        for e, data, z in packed:
            f.write(z)
            table.append((e, len(data), len(z), offset))
            offset += len(z)
        f.seek(table_off)
        for e, size, zsize, offset in table:
            name = e.name.encode("latin-1", "replace")
            if mas_type == 0:
                f.write(struct.pack("<4xlll240s", offset, size, zsize, name))
            elif mas_type == 1:
                f.write(struct.pack("<BBxx236slll4x", e.type, e.flags, name, offset, size, zsize))
            elif mas_type == 3:
                f.write(struct.pack("<4xlll4x236s", 0, offset, size, zsize, name))
            else:
                raise ValueError(mas_type)


def cmd_list(args: argparse.Namespace) -> int:
    _mtype, entries = read_archive(args.archive)
    for e in entries:
        if args.verbose:
            print(f"{e.offset:10d} {e.size:10d} {e.zsize:10d} {e.name}")
        else:
            print(e.name)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    _mtype, entries = read_archive(args.archive)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(args.files) if args.files else None
    for e in entries:
        if wanted and e.name not in wanted and os.path.basename(e.name) not in wanted:
            continue
        dest = out / e.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(e.data or b"")
        if args.verbose:
            print(dest)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    entries = []
    for p in args.files:
        pp = Path(p)
        entries.append(Entry(name=pp.name, offset=0, size=0, zsize=0, data=pp.read_bytes()))
    write_archive(args.archive, entries, mas_type=args.type)
    return 0


def _upsert(entries: list[Entry], path: str, replace: bool) -> None:
    pp = Path(path)
    name = pp.name
    for i, e in enumerate(entries):
        if e.name.lower() == name.lower():
            if not replace:
                raise ValueError(f"{name} already exists (use update)")
            entries[i] = Entry(name=e.name, offset=0, size=0, zsize=0, data=pp.read_bytes(), type=e.type, flags=e.flags)
            return
    if replace:
        raise ValueError(f"{name} not found for update")
    entries.append(Entry(name=name, offset=0, size=0, zsize=0, data=pp.read_bytes()))


def cmd_add(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    for p in args.files:
        _upsert(entries, p, replace=False)
    write_archive(args.archive, entries, mas_type=mtype)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    for p in args.files:
        _upsert(entries, p, replace=True)
    write_archive(args.archive, entries, mas_type=mtype)
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    wanted = {n.lower() for n in args.names}
    kept = [e for e in entries if e.name.lower() not in wanted and os.path.basename(e.name).lower() not in wanted]
    if len(kept) == len(entries):
        print("no matching entries removed", file=sys.stderr)
        return 1
    write_archive(args.archive, kept, mas_type=mtype)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list archive contents")
    p.add_argument("archive")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("extract", help="extract files")
    p.add_argument("archive")
    p.add_argument("-o", "--outdir", default=".")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("files", nargs="*")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("create", help="create archive from files")
    p.add_argument("archive")
    p.add_argument("files", nargs="+")
    p.add_argument("-t", "--type", type=int, default=0, choices=[0, 1, 3])
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("add", help="add files to archive")
    p.add_argument("archive")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="replace existing files in archive")
    p.add_argument("archive")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="delete files from archive")
    p.add_argument("archive")
    p.add_argument("names", nargs="+")
    p.set_defaults(func=cmd_delete)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
