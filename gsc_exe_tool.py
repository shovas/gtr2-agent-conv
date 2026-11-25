#!/usr/bin/env python3
"""List/extract resources embedded in GSC-family game EXEs (``AXS.GS.0``).

The container was documented by Luigi Auriemma's GPLv2 ``gamestockcar_exe.bms``
(QuickBMS script in ``../aluigi-mirror-261124``).  This module is an
independent Python implementation of the verified parts of that format:

* the resource directory (ver 1 and ver 2 GSC / Marcas / SCE / AMS EXEs);
* the ``.keyMan`` key table (SHA-1 key strings, one per encrypted resource);
* Blowfish-CBC decryption (big-endian blocks, IV = BF-ECB of eight zero bytes);
* ``lzma86head`` decompression (13-byte header followed by raw LZMA).

Other compression modes (snappy, jcalg, lz4, lzma86 without header) are not
implemented; those resources are returned raw and flagged as unsupported.
No third-party code or binaries are stored in this repository.

Verified against the extraction produced by QuickBMS 0.12.0 with the original
script on ``../CopaPetrobrasdeMarcas/Marcas.exe``: all 31 encrypted LZMA
resources decode to the same size and content (a known one-byte LZMA decoder
difference in a few files; see ``docs/open-issues-research.md``).
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
import struct
from dataclasses import dataclass
from pathlib import Path

from jca_crypt import Blowfish

CONTAINER_MAGIC = b"AXS.GS.0"


@dataclass
class Resource:
    name: str
    section: str
    offset: int
    data: bytes

    @property
    def kind(self) -> int:
        return self.data[0] | (self.data[1] << 8) | (self.data[2] << 16) if len(self.data) >= 3 else -1


@dataclass
class Container:
    version: int
    resources: list[Resource]
    exe_name: str = ""
    source: str = ""

    def key_list(self) -> list[str]:
        """Return the ``.keyMan`` decryption keys in QuickBMS order."""
        for res in self.resources:
            if res.name.lower().endswith(".keyman"):
                return parse_keyman(res.data, self.version, self.exe_name)
        return []

    def get(self, name: str) -> Resource | None:
        lowered = name.replace("/", "\\").lower()
        for res in self.resources:
            if res.name.lower() == lowered:
                return res
        return None


def read_container(path: str | Path) -> Container:
    """Parse the ``AXS.GS.0`` directory; no game data is modified."""
    data = Path(path).read_bytes()
    pos = data.find(CONTAINER_MAGIC)
    if pos < 0:
        raise ValueError(f"no {CONTAINER_MAGIC!r} in {path}")
    version, count = struct.unpack_from("<II", data, pos + 8)
    off = pos + 16
    resources = []
    for _ in range(count):
        if off + 8 > len(data):
            raise ValueError("truncated resource directory")
        _is_file, sec_len = struct.unpack_from("<II", data, off)
        off += 8
        section = data[off:off + sec_len].decode("latin-1")
        off += sec_len
        name_len = struct.unpack_from("<I", data, off)[0]
        off += 4
        name = data[off:off + name_len].decode("latin-1")
        off += name_len
        size = struct.unpack_from("<Q", data, off)[0]
        off += 8
        if off + size > len(data):
            raise ValueError(f"truncated resource {name}")
        resources.append(Resource(name, section, off, data[off:off + size]))
        off += size
    return Container(version, resources, Path(path).name, str(path))


def keyman_name_pairs(data: bytes) -> list[tuple[str, str]]:
    """Return all ``(name1, name2)`` string pairs from a ``.keyMan`` table."""
    pairs = []
    off = 0
    while off + 12 <= len(data):
        len1 = struct.unpack_from("<I", data, off + 4)[0]
        if not 0 < len1 <= 256 or off + 8 + len1 + 4 > len(data):
            break
        off += 8
        name1 = data[off:off + len1].decode("latin-1")
        off += len1
        len2 = struct.unpack_from("<I", data, off)[0]
        off += 4
        if not 0 < len2 <= 256 or off + len2 > len(data):
            break
        name2 = data[off:off + len2].decode("latin-1")
        off += len2
        pairs.append((name1, name2))
    return pairs


def parse_keyman(data: bytes, version: int, exe_name: str = "") -> list[str]:
    """Extract key strings from the ``.keyMan`` record table.

    Each record is ``u32 flags, u32 len, name1, u32 len, name2``.  QuickBMS
    uses ``name2`` as the key, keeps records whose flags have bit 1 set, and
    skips records with ``{`` in ``name1`` (version 2+) or ``name2`` (version 1
    and the ``Marcas.exe`` workaround).
    """
    keys: list[str] = []
    off = 0
    while off + 12 <= len(data):
        flags = struct.unpack_from("<I", data, off)[0]
        len1 = struct.unpack_from("<I", data, off + 4)[0]
        if not 0 < len1 <= 256 or off + 8 + len1 + 4 > len(data):
            break
        off += 8
        name1 = data[off:off + len1].decode("latin-1")
        off += len1
        len2 = struct.unpack_from("<I", data, off)[0]
        off += 4
        if not 0 < len2 <= 256 or off + len2 > len(data):
            break
        name2 = data[off:off + len2].decode("latin-1")
        off += len2
        # QuickBMS reads NUM from the following record's flags field.
        if off + 4 <= len(data):
            num = struct.unpack_from("<I", data, off)[0]
        else:
            num = flags
        if not num & 2:
            continue
        if version <= 1:
            if "{" in name2:
                continue
        elif "{" in name1:
            continue
        if exe_name.lower() == "marcas.exe" and "{" in name2:
            continue
        keys.append(name2)
    return keys


class _BlowfishBE:
    """Standard Blowfish with big-endian blocks, as used by QuickBMS/OpenSSL."""

    def __init__(self, key_material: bytes):
        self._bf = Blowfish(hashlib.sha1(key_material).digest())

    @staticmethod
    def _pack(left: int, right: int) -> bytes:
        return struct.pack(">II", left, right)

    def encrypt_block(self, block: bytes) -> bytes:
        left, right = struct.unpack(">II", block)
        return self._pack(*self._bf._encipher(left, right))

    def decrypt_block(self, block: bytes) -> bytes:
        left, right = struct.unpack(">II", block)
        return self._pack(*self._bf._decipher(left, right))

    def cbc_decrypt(self, data: bytes) -> bytearray:
        iv = self.encrypt_block(bytes(8))
        out = bytearray(len(data))
        previous = iv
        for pos in range(0, len(data) - 7, 8):
            block = bytes(data[pos:pos + 8])
            plain = self.decrypt_block(block)
            for i in range(8):
                out[pos + i] = plain[i] ^ previous[i]
            previous = block
        return out


def _decrypt_chunk(raw: bytes, cipher: _BlowfishBE) -> bytearray:
    """BF-CBC decrypt one chunk, including QuickBMS's unaligned-tail fix."""
    odd = len(raw) % 8
    chunk = cipher.cbc_decrypt(raw)
    if odd:
        tail = len(raw) - odd
        mask = cipher.encrypt_block(raw[tail - 8:tail])
        for i in range(odd):
            chunk[tail + i] = raw[tail + i] ^ mask[i]
    return chunk


def _lz4_block(data: bytes) -> bytes:
    """Minimal LZ4 block decoder (QuickBMS ``comtype lz4``)."""
    out = bytearray()
    pos = 0
    while pos < len(data):
        token = data[pos]
        pos += 1
        literal = token >> 4
        if literal == 15:
            while pos < len(data) and data[pos] == 255:
                literal += 255
                pos += 1
            literal += data[pos]
            pos += 1
        out.extend(data[pos:pos + literal])
        pos += literal
        if pos >= len(data):
            break
        if pos + 2 > len(data) or not out:
            raise ValueError("truncated LZ4 match")
        offset = data[pos] | (data[pos + 1] << 8)
        pos += 2
        if offset == 0 or offset > len(out):
            raise ValueError(f"invalid LZ4 offset {offset}")
        match = token & 0x0F
        if match == 15:
            while pos < len(data) and data[pos] == 255:
                match += 255
                pos += 1
            match += data[pos]
            pos += 1
        match += 4
        start = len(out) - offset
        for _ in range(match):
            out.append(out[start])
            start += 1
    return bytes(out)


def _lzma86head(data: bytes) -> bytes:
    """QuickBMS ``lzma86head``: 5-byte props/dict + u64 size + raw LZMA."""
    if len(data) < 13:
        raise ValueError("short lzma86head chunk")
    prop = data[0]
    lc, lp, pb = prop % 9, (prop // 9) % 5, prop // 45
    if lc > 8 or lp > 4 or pb > 4:
        raise ValueError(f"invalid LZMA properties byte 0x{prop:02x}")
    dict_size = struct.unpack_from("<I", data, 1)[0]
    expected = struct.unpack_from("<Q", data, 5)[0]
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{
        "id": lzma.FILTER_LZMA1, "dict_size": dict_size,
        "lc": lc, "lp": lp, "pb": pb,
    }])
    result = dec.decompress(data[13:])
    # The header's size field is authoritative; Python's decoder may emit a
    # few trailing bytes that QuickBMS's LZMA SDK does not.
    return result[:expected]


def _type100_header(data: bytes) -> tuple[int, int, int] | None:
    """Return ``(compressed, encrypted, data_offset)`` for type 0x100 chunks."""
    if len(data) < 30 or (data[0], data[1], data[2]) != (0, 1, 0):
        return None
    dummy_size = struct.unpack_from("<I", data, 16)[0]
    off = 20 + dummy_size
    if off + 10 > len(data):
        return None
    return data[off], data[off + 1], off + 10


def resource_encrypted(res: Resource) -> bool:
    """Whether the resource's first chunk is Blowfish-encrypted."""
    if len(res.data) < 10:
        return False
    if res.kind == 1:
        return bool(res.data[4])
    header = _type100_header(res.data)
    return bool(header[1]) if header else False


def decode_resource(res: Resource, key: str | None, exe_name: str = "") -> tuple[bytes, bool]:
    """Return ``(data, fully_decoded)``; ``fully_decoded`` is False for raw data."""
    if len(res.data) < 10:
        return res.data, False
    if res.kind == 0x100:
        header = _type100_header(res.data)
        if header is None:
            return res.data, False
        compression = struct.unpack_from("<I", res.data, 12)[0]
        zsize = struct.unpack_from("<I", res.data, header[2] - 4)[0]
        payload = res.data[header[2]:header[2] + zsize]
        if header[1] and key:
            chunk = _decrypt_chunk(payload, _BlowfishBE(key.encode("latin-1")))
            if exe_name.lower() != "ams.exe":
                try:
                    chunk = bytearray(_lzma86head(bytes(chunk)))
                except (ValueError, lzma.LZMAError):
                    return res.data, False
            return bytes(chunk), True
        if not header[1] and compression == 6 and payload[:2] != b"JC":
            try:
                return _lz4_block(payload), True
            except ValueError:
                return res.data, False
        if not header[1] and compression == 1:
            try:
                return _lzma86head(payload), True
            except (ValueError, lzma.LZMAError):
                return res.data, False
        return res.data, False
    if res.kind != 1:
        return res.data, False
    encrypted = bool(res.data[4])
    chunk_size = struct.unpack_from("<I", res.data, 5)[0]
    pos = 9
    remaining = len(res.data) - pos
    out = bytearray()
    cipher = _BlowfishBE(key.encode("latin-1")) if encrypted and key else None
    while remaining > 0:
        compressed = res.data[pos]
        pos += 1
        remaining -= 1
        if compressed:
            if remaining < 4:
                return res.data, False
            zsize = struct.unpack_from("<I", res.data, pos)[0]
            pos += 4
            remaining -= 4
        else:
            zsize = min(chunk_size, remaining)
        if zsize > remaining:
            return res.data, False
        raw = bytes(res.data[pos:pos + zsize])
        pos += zsize
        remaining -= zsize
        chunk = _decrypt_chunk(raw, cipher) if cipher is not None else bytearray(raw)
        if compressed and exe_name.lower() != "ams.exe":
            if encrypted:
                try:
                    chunk = bytearray(_lzma86head(bytes(chunk)))
                except (ValueError, lzma.LZMAError):
                    return res.data, False
            else:
                return res.data, False  # snappy is not implemented
        out.extend(chunk)
    return bytes(out), True


def extract_all(container: Container, output_dir: str | Path) -> list[tuple[str, bool]]:
    """Decode every supported resource into ``output_dir``; return status list."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = container.key_list()
    key_index = 0
    sce_type1_index = 0
    sce = "stockcarextreme" in container.source.lower() and container.version == 2
    results = []
    for res in container.resources:
        key = None
        if resource_encrypted(res):
            if sce and res.kind == 1:
                # Validated on 204/204 SCE type-1 resources: key at +11 in the
                # .keyMan list, in encrypted-resource order.
                pos = sce_type1_index + 11
                if pos < len(keys):
                    key = keys[pos]
                sce_type1_index += 1
            else:
                if keys:
                    key = keys[min(key_index, len(keys) - 1)]
                key_index += 1
        data, ok = decode_resource(res, key, container.exe_name)
        name = res.name.replace("\\", "/")
        target = out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        results.append((name, ok))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("list", "extract"))
    ap.add_argument("exe", help="GSC-family EXE with an AXS.GS.0 container")
    ap.add_argument("output", nargs="?", help="output directory for extract")
    args = ap.parse_args(argv)
    try:
        container = read_container(args.exe)
        if args.command == "list":
            print(f"{args.exe}: version {container.version}, {len(container.resources)} resources")
            for res in container.resources:
                print(f"{res.offset:08x}  {len(res.data):9}  {res.name}")
            return 0
        if not args.output:
            ap.error("extract requires an output directory")
        results = extract_all(container, args.output)
        ok = sum(1 for _, flag in results if flag)
        print(f"extracted {len(results)} resources ({ok} decoded, {len(results) - ok} raw)")
        return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
