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
# Petrobras de Marcas variant: same type-1 layout, only the first 6 bytes differ.
# Documented in quickbms_scripts/mas.bms as MAS_TYPE1X.
MAS_TYPE1X = b"\xce\xc3\xd5\xc7\xc0\xd9\xe6\xc9\xca\xdd\xd8\xbe\xbb\xa6\xbf\x90"
MAS_TYPE1X_SUFFIX = b"\xca\xdd\xd8\xbe\xbb\xa6\xbf\x90"
MAS_TYPE3 = b"CUBEMAS4.10\x00\x00\x00\x00\x00"
# F1 2000 era: 12-byte magic, u32 count, u32 data_size, then 256-byte records
# of name[244] + size + zsize + 4 padding bytes at offset 0x14.
MAS_TYPE25 = b"CUBEMAS2.50\x00"
# F1 2001 era: 16-byte signature, u32 count/data_size, then 256-byte records
# (u32 type, offset, size, zsize, crc, name[236]) starting at 0x18.
MAS_TYPE400 = b"CUBEMAS4.00\x00\x00\x00\x00\x00"
MAS_TYPE401 = b"CUBEMAS4.01\x00\x00\x00\x00\x00"


@dataclass
class Entry:
    name: str
    offset: int
    size: int
    zsize: int
    type: int = 0
    flags: int = 0
    data: bytes | None = None
    # Type-2/5/6 only: original uncompressed size when the blob is stored undecoded.
    orig_size: int = 0
    # Type-6 only: original file-type field (e.g. 17 for MTS).
    orig_type: int = 0
    # Type-2.5 only: decoded BMP pixels when the raw blob is kept losslessly.
    decoded: bytes | None = None


def _looks_like_type2(data: bytes) -> bool:
    """Sports Car GT era MAS: no signature, 8-byte header, 32-byte records."""
    if len(data) < 40:
        return False
    count, _dsize = struct.unpack_from("<II", data, 0)
    if not (0 < count < 100000):
        return False
    base = 8 + 32 * count
    if base > len(data):
        return False
    name = data[8:24].split(b"\0", 1)[0]
    return bool(name) and all(32 <= c < 127 for c in name)


def _read_type2(data: bytes) -> list[Entry]:
    count, _dsize = struct.unpack_from("<II", data, 0)
    base = 8 + 32 * count
    entries = []
    for i in range(count):
        raw = data[8 + i * 32:8 + (i + 1) * 32]
        name, offset, size, zsize, dummy = struct.unpack_from("<16sIIII", raw, 0)
        blob = data[base + offset:base + offset + (zsize or size)]
        entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"),
                      offset=offset, size=size, zsize=zsize, flags=dummy)
        if size == zsize or zsize == 0:
            entry.data = blob  # stored raw (zsize==0 also means uncompressed)
        elif blob[16:18] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            try:
                raw_data = zlib.decompress(blob[16:])
                if len(raw_data) == size:
                    # Preserve the game's 16-byte texture header, decode the zlib payload.
                    entry.data = blob[:16] + raw_data
                    entry.type = 1
                else:
                    entry.data = blob
                    entry.type = 2
            except zlib.error:
                entry.data = blob
                entry.type = 2
        else:
            # Compression variant not decoded; keep the blob losslessly.
            entry.data = blob
            entry.type = 2
        if entry.type == 2:
            entry.orig_size = size
        entries.append(entry)
    return entries


def reconstruct_type2_member(archive: str | Path, entry: Entry) -> bytes:
    """Return the full on-disk bytes of a MAS type-2 member.

    A few Sports Car GT members store fewer bytes than their declared ``size``
    in the archive; the remainder sits in the gap before the next member. The
    normal reader keeps the short blob for lossless round-tripping, so this
    helper reads the raw archive separately.
    """
    data = Path(archive).read_bytes()
    count, _dsize = struct.unpack_from("<II", data, 0)
    base = 8 + 32 * count
    next_offset = len(data) - base
    for i in range(count):
        name, off, _size, _zsize, _dummy = struct.unpack_from("<16sIIII", data, 8 + i * 32)
        if name.split(b"\0", 1)[0].decode("latin-1") == entry.name:
            start = base + off
            # The next record's offset marks the end of this member's storage.
            for j in range(i + 1, count):
                _n, noff, _s, _z, _d = struct.unpack_from("<16sIIII", data, 8 + j * 32)
                if noff > off:
                    next_offset = noff
                    break
            break
    else:
        raise ValueError(f"member {entry.name!r} not in {archive}")
    return data[start:base + next_offset]


def scgt_raw_texture_to_bmp(data: bytes) -> bytes | None:
    """Decode a Sports Car GT 16-byte-header raw-RGB texture to a 24-bit BMP.

    Corpus-verified on the two AMBC.BMP members in ``Hckamap.mas`` and
    ``Octamap.mas`` (32x8, 16-byte header + 768 raw RGB bytes). Returns ``None``
    when the header does not describe an exact raw-RGB payload.
    """
    if len(data) < 16:
        return None
    width, height, _flags, _zero = struct.unpack_from("<IIII", data, 0)
    if width <= 0 or height <= 0 or 16 + width * height * 3 != len(data):
        return None
    pixels = data[16:]
    rows = b"".join(pixels[y * width * 3:(y + 1) * width * 3]
                    for y in range(height - 1, -1, -1))
    header = b"BM" + struct.pack("<IHHI", 54 + len(rows), 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                          len(rows), 2835, 2835, 0, 0)
    return header + rows


def f12001_texture_to_bmp(data: bytes) -> bytes | None:
    """Decode an F12001 raw RGB texture with 4-byte-aligned scanlines.

    These 16-byte-header members store 24-bit rows padded to the next multiple
    of four bytes, so ``len(data) == 16 + ceil(width*3/4)*4 * height`` rather
    than ``16 + width*height*3``. Verified on 5,243/5,245 sampled textures in
    ``../F12001`` (the two exceptions are tiny transparency blobs). Returns
    ``None`` when the header or stride does not describe an exact raw payload.
    """
    if len(data) < 16:
        return None
    width, height, flags, _zero = struct.unpack_from("<IIII", data, 0)
    if width <= 0 or height <= 0 or flags != 24:
        return None
    stride = ((width * 3 + 3) // 4) * 4
    if 16 + stride * height != len(data):
        return None
    rows = b"".join(data[16 + stride * y:16 + stride * y + width * 3]
                    for y in range(height - 1, -1, -1))
    header = b"BM" + struct.pack("<IHHI", 54 + len(rows), 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                          len(rows), 2835, 2835, 0, 0)
    return header + rows


def _mas_type(signature: bytes) -> int:
    if signature == MAS_TYPE0:
        return 0
    if signature == MAS_TYPE1:
        return 1
    if signature == MAS_TYPE3:
        return 3
    if signature[8:16] == MAS_TYPE1X_SUFFIX:
        return 1
    if signature[:12] == MAS_TYPE25:
        return 5
    if signature in (MAS_TYPE400, MAS_TYPE401):
        return 6
    raise ValueError(f"unsupported MAS signature: {signature!r}")


def _read_type6(data: bytes) -> list[Entry]:
    count, data_size = struct.unpack_from("<II", data, 16)
    base = 24 + 256 * count
    if base > len(data):
        raise ValueError("MAS type-4.0x file table out of bounds")
    entries = []
    offset = 0
    for i in range(count):
        raw = data[24 + i * 256:24 + (i + 1) * 256]
        etype, off, size, zsize, crc, name = struct.unpack_from("<IIIII236s", raw, 0)
        blob = data[base + offset:base + offset + zsize]
        entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"),
                      offset=off, size=size, zsize=zsize, type=etype, flags=crc,
                      orig_type=etype)
        if size == zsize:
            entry.data = blob
        elif blob[:2] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            try:
                entry.data = zlib.decompress(blob)
            except zlib.error:
                entry.data, entry.type, entry.orig_size = blob, 2, size
        elif blob[16:18] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            try:
                entry.data = blob[:16] + zlib.decompress(blob[16:])
                entry.type = 1
            except zlib.error:
                entry.data, entry.type, entry.orig_size = blob, 2, size
        else:
            entry.data, entry.type, entry.orig_size = blob, 2, size
        entries.append(entry)
        offset += zsize
    return entries


def _write_type6(path: str | os.PathLike, entries: list[Entry], signature: bytes) -> None:
    packed = []
    for e in entries:
        data = e.data if e.data is not None else b""
        if e.type == 1 and len(data) >= 16:
            zipped = data[:16] + zlib.compress(data[16:])
            # Textures (orig_type 2) store the header separately; meshes (1) include it.
            size = len(data) if e.orig_type == 1 else len(data) - 16
        elif e.type == 2:
            zipped = data
            size = e.orig_size or len(data)
        elif data[:2] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            zipped, size = data, len(data)
        else:
            zipped, size = zlib.compress(data), len(data)
        packed.append((e, zipped, size))
    with open(path, "wb") as f:
        f.write(signature + struct.pack("<II", len(packed), sum(len(z) for _, z, _ in packed)))
        f.write(b"\x00" * (256 * len(packed)))
        offset = 0
        table = []
        for e, zipped, size in packed:
            f.write(zipped)
            table.append((e, size, len(zipped), offset))
            offset += len(zipped)
        f.seek(24)
        for e, size, zsize, off in table:
            name = e.name.encode("latin-1", "replace")[:236].ljust(236, b"\0")
            f.write(struct.pack("<IIIII236s", e.orig_type, off, size, zsize, e.flags, name))


def decode_type25_member(data: bytes, start: int, zsize: int, size: int) -> bytes | None:
    """Decode an F1 2000 type-2.5 "undecoded" BMP member to its pixels.

    These members carry a 30-byte prefix (16-byte palette, 14-byte metadata)
    followed by a zlib stream at offset 30. The producer writes only the first
    ``zsize`` bytes of that stream inside the member; the final **14 bytes** are
    stored immediately after it (the start of the next member's region, or the
    archive's 14-byte tail for the last member). A 14-byte overread is required
    and sufficient: on all 315 such members in ``../F12000`` the stream then
    ends cleanly and yields exactly ``size`` bytes of pixels.

    ``start`` is the member's absolute data offset; ``data`` is the whole archive.
    Returns ``None`` when the member is not this variant or decoding fails.
    """
    if zsize < 30 or size <= zsize:
        return None
    stream = data[start + 30:start + zsize + 14]
    if stream[:2] not in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
        return None
    try:
        inflater = zlib.decompressobj()
        result = inflater.decompress(stream)
    except zlib.error:
        return None
    if inflater.eof and len(result) == size:
        return result
    return None


def _read_type25(data: bytes) -> list[Entry]:
    count, data_size = struct.unpack_from("<II", data, 12)
    base = 20 + 256 * count
    if base > len(data):
        raise ValueError("MAS type-2.5 file table out of bounds")
    entries = []
    offset = 0
    for i in range(count):
        raw = data[20 + i * 256:20 + (i + 1) * 256]
        name, size, zsize = struct.unpack_from("<244sII", raw, 0)
        blob = data[base + offset:base + offset + zsize]
        entry = Entry(name=name.split(b"\0", 1)[0].decode("latin-1"),
                      offset=offset, size=size, zsize=zsize)
        if size == zsize:
            entry.data = blob
        elif blob[:2] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            try:
                entry.data = zlib.decompress(blob)
            except zlib.error:
                entry.data, entry.type, entry.orig_size = blob, 2, size
        elif blob[16:18] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            try:
                entry.data = blob[:16] + zlib.decompress(blob[16:])
                entry.type = 1
            except zlib.error:
                entry.data, entry.type, entry.orig_size = blob, 2, size
        else:
            # 319 F1 2000 BMPs: keep the blob losslessly for round-trips, and
            # expose the decoded pixels via Entry.decoded when decodable.
            entry.data, entry.type, entry.orig_size = blob, 2, size
            entry.decoded = decode_type25_member(data, base + offset, zsize, size)
        entries.append(entry)
        offset += zsize
    return entries


def _write_type25(path: str | os.PathLike, entries: list[Entry]) -> None:
    packed = []
    for e in entries:
        data = e.data if e.data is not None else b""
        if e.type == 1 and len(data) >= 16:
            zipped = data[:16] + zlib.compress(data[16:])
            size = len(data) - 16
        elif e.type == 2:
            zipped = data
            size = e.orig_size or len(data)
        elif data[:2] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            zipped, size = data, len(data)
        else:
            zipped, size = zlib.compress(data), len(data)
        packed.append((e, zipped, size))
    with open(path, "wb") as f:
        f.write(MAS_TYPE25 + struct.pack("<II", len(packed), sum(len(z) for _, z, _ in packed)))
        f.write(b"\x00" * (256 * len(packed)))
        offset = 0
        table = []
        for e, zipped, size in packed:
            f.write(zipped)
            table.append((e, size, len(zipped), offset))
            offset += len(zipped)
        f.seek(20)
        for e, size, zsize, off in table:
            name = e.name.encode("latin-1", "replace")[:244].ljust(244, b"\0")
            f.write(struct.pack("<244sII4x", name, size, zsize))


def read_signature(path: str | os.PathLike) -> bytes:
    """Return the raw 16-byte archive signature (needed to preserve variants on rewrite)."""
    with open(path, "rb") as f:
        return f.read(16)


def read_member(path: str | os.PathLike, entry: Entry) -> bytes | None:
    """Read and decompress one member at its absolute offset (lazy access).

    Enables incremental surveys over huge archives: read the table once, then
    fetch only the members that need classification. ``entry.offset`` is the
    absolute on-disk offset produced by :func:`read_archive` (or with
    ``read_data=False``).
    """
    with open(path, "rb") as f:
        f.seek(entry.offset)
        blob = f.read(entry.zsize or entry.size)
    if len(blob) != (entry.zsize or entry.size):
        return None
    if entry.size == entry.zsize or not entry.zsize:
        return blob
    try:
        return zlib.decompress(blob)
    except zlib.error:
        return None


# Bounded cache of decompressed members keyed by (archive path, absolute
# member offset). Test suites re-read the same archives many times; profiling
# showed zlib.decompress dominating normal-tier runtime (130 s of 307 s).
_BLOB_CACHE: dict[tuple[str, int], bytes] = {}
_BLOB_CACHE_BYTES = 0
_BLOB_CACHE_LIMIT = 64 * 1024 * 1024


def _cached_member(f, key: tuple[str, int, int], offset: int,
                   zsize: int, size: int) -> bytes:
    global _BLOB_CACHE_BYTES
    data = _BLOB_CACHE.get(key)
    if data is not None:
        return data
    f.seek(offset)
    blob = f.read(zsize)
    data = zlib.decompress(blob) if size != zsize else blob
    if len(data) + _BLOB_CACHE_BYTES <= _BLOB_CACHE_LIMIT:
        _BLOB_CACHE[key] = data
        _BLOB_CACHE_BYTES += len(data)
    return data


def read_archive(path: str | os.PathLike, read_data: bool = True) -> tuple[int, list[Entry]]:
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        stamp = 0
    with open(path, "rb") as f:
        sig = f.read(16)
        try:
            mtype = _mas_type(sig)
        except ValueError:
            f.seek(0)
            whole = f.read()
            if _looks_like_type2(whole):
                return 2, _read_type2(whole)
            raise
        if mtype == 5:
            f.seek(0)
            return 5, _read_type25(f.read())
        if mtype == 6:
            f.seek(0)
            return 6, _read_type6(f.read())
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
            if not read_data:
                continue
            e.data = _cached_member(f, (str(path), stamp, e.offset),
                                    e.offset, e.zsize, e.size)
            if len(e.data) != e.size:
                raise ValueError(f"size mismatch for {e.name}: {len(e.data)} != {e.size}")
    return mtype, entries


def _write_type2(path: str | os.PathLike, entries: list[Entry]) -> None:
    """Write the signature-less Sports Car GT era MAS layout."""
    packed = []
    for e in entries:
        data = e.data if e.data is not None else b""
        if e.type == 1 and len(data) >= 16:
            blob = data[:16] + zlib.compress(data[16:])
            size = len(data) - 16
        elif e.type == 2:
            blob = data
            size = e.orig_size or len(data)
        else:
            blob = data
            size = len(data)
        packed.append((e, blob, size, len(blob)))

    base = 8 + 32 * len(packed)
    with open(path, "wb") as f:
        f.write(struct.pack("<II", len(packed), sum(z for _, _, _, z in packed)))
        f.write(b"\x00" * (32 * len(packed)))  # reserve the file table
        offset = 0
        table = []
        for e, blob, size, zsize in packed:
            f.write(blob)
            table.append((e, size, zsize, offset))
            offset += zsize
        f.seek(8)
        for e, size, zsize, off in table:
            name = e.name.encode("latin-1", "replace")[:16].ljust(16, b"\0")
            f.write(struct.pack("<16sIIII", name, off, size, zsize, e.flags))


def write_archive(path: str | os.PathLike, entries: list[Entry], mas_type: int = 0,
                  signature: bytes | None = None) -> None:
    if mas_type == 2:
        return _write_type2(path, entries)
    if mas_type == 5:
        return _write_type25(path, entries)
    if mas_type == 6:
        return _write_type6(path, entries, signature or MAS_TYPE401)
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
    if signature is not None:
        if len(signature) != 16:
            raise ValueError("signature must be 16 bytes")
        sig = signature

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
                f.write(struct.pack("<4xlll4x236s", offset, size, zsize, name))
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
        payload = e.data or b""
        if args.as_bmp:
            bmp = scgt_raw_texture_to_bmp(payload)
            if bmp is not None:
                dest = dest.with_suffix(".bmp")
                payload = bmp
        dest.write_bytes(payload)
        if args.verbose:
            print(dest)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    entries = []
    for p in args.files:
        pp = Path(p)
        entries.append(Entry(name=pp.name, offset=0, size=0, zsize=0, data=pp.read_bytes()))
    sig = bytes.fromhex(args.signature) if args.signature else None
    write_archive(args.archive, entries, mas_type=args.type, signature=sig)
    return 0


def _upsert(entries: list[Entry], path: str, replace: bool) -> None:
    pp = Path(path)
    name = pp.name
    for i, e in enumerate(entries):
        if e.name.lower() == name.lower():
            if not replace:
                raise ValueError(f"{name} already exists (use update)")
            entries[i] = Entry(name=e.name, offset=0, size=0, zsize=0, data=pp.read_bytes(), type=e.type, flags=e.flags,
                               orig_size=e.orig_size, orig_type=e.orig_type)
            return
    if replace:
        raise ValueError(f"{name} not found for update")
    entries.append(Entry(name=name, offset=0, size=0, zsize=0, data=pp.read_bytes()))


def cmd_add(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    for p in args.files:
        _upsert(entries, p, replace=False)
    write_archive(args.archive, entries, mas_type=mtype, signature=read_signature(args.archive))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    for p in args.files:
        _upsert(entries, p, replace=True)
    write_archive(args.archive, entries, mas_type=mtype, signature=read_signature(args.archive))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    mtype, entries = read_archive(args.archive)
    wanted = {n.lower() for n in args.names}
    kept = [e for e in entries if e.name.lower() not in wanted and os.path.basename(e.name).lower() not in wanted]
    if len(kept) == len(entries):
        print("no matching entries removed", file=sys.stderr)
        return 1
    write_archive(args.archive, kept, mas_type=mtype, signature=read_signature(args.archive))
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
    p.add_argument("--as-bmp", action="store_true",
                   help="write 16-byte-header raw RGB members as real 24-bit BMPs")
    p.add_argument("files", nargs="*")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("create", help="create archive from files")
    p.add_argument("archive")
    p.add_argument("files", nargs="+")
    p.add_argument("-t", "--type", type=int, default=0, choices=[0, 1, 2, 3, 5, 6])
    p.add_argument("--signature", help="override the 16-byte archive signature (hex), e.g. Petrobras type-1X")
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
