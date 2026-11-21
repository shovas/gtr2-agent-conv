"""Structural GMT parser/writer for GTR2/GT Legends GMT files.

Parses known structures and preserves unknown bytes for lossless round-trip.
Based on observed GTR2/GT Legends GMTs; not a complete spec.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

GMT_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba7bf90")


@dataclass
class GmtMeshRecord:
    raw: List[int]  # 27 u32s
    vertex_stride: int = 32

    @property
    def flags(self) -> int: return self.raw[1]
    @property
    def material_index(self) -> int: return self.raw[2]
    @property
    def vertex_count(self) -> int: return self.raw[3]
    @property
    def vertex_offset(self) -> int: return self.raw[4]
    @property
    def index_count(self) -> int: return self.raw[10]
    @property
    def index_offset(self) -> int: return self.raw[11]
    @property
    def vertex_end(self) -> int:
        # rec[6] is usually vo+vc*stride; sometimes 0
        v6 = self.raw[6]
        if v6 > self.vertex_offset:
            return v6
        return self.vertex_offset + self.vertex_count * self.vertex_stride

    @property
    def index_bytes_end(self) -> int:
        return self.index_offset + 4 + self.index_count * 2


@dataclass
class GmtMesh:
    record: GmtMeshRecord
    vertex_data: bytes
    index_data: bytes  # includes 4-byte lead + u16 indices as stored


@dataclass
class GmtMaterial:
    index: int
    raw: bytes
    name: str
    strings: List[str]


@dataclass
class GmtFile:
    source_path: Optional[Path]
    original: bytes
    obj_list_offset: int
    flags: int
    magic: bytes
    header_18_16c: bytes  # unknown/preserved
    mesh_first: int
    meshes: List[GmtMesh]
    tail: bytes  # obj_list_offset .. EOF
    materials: List[GmtMaterial] = field(default_factory=list)
    gaps: bytes = b""  # not used; we preserve via original

    @property
    def mesh_count(self) -> int: return len(self.meshes)


def _detect_stride(d: bytes, rec: List[int]) -> int:
    vc, vo = rec[3], rec[4]
    v6 = rec[6]
    if vc <= 0:
        return 32
    if v6 > vo and (v6 - vo) % vc == 0:
        return (v6 - vo) // vc
    # fallback
    if vo + vc * 48 <= len(d) and v6 == vo + vc * 48:
        return 48
    return 32


def _find_material_starts(tail: bytes, count: int) -> List[int]:
    # Heuristic: material records often have "L0..." stage string at +152.
    starts = [m.start() - 152 for m in re.finditer(b'L0', tail) if m.start() >= 152]
    starts = [s for s in starts if s >= 8]
    # Prefer exact count match starting at 8
    if len(starts) == count and starts[0] == 8:
        return starts
    # Try filtering to those that look like aligned record starts (L0 at +152)
    # by keeping starts where the name region looks plausible
    cand = [s for s in starts if s >= 8 and all(0 < s2 - s for s2 in starts if s2 > s)]
    if len(cand) == count and cand[0] == 8:
        return cand
    # Fallback: equal split
    rec_size = (len(tail) - 8) // count if count else 0
    if rec_size <= 0:
        return []
    return [8 + i * rec_size for i in range(count)]


def _parse_materials(tail: bytes) -> List[GmtMaterial]:
    if len(tail) < 8:
        return []
    _h0, _h1, count = struct.unpack_from('<HHI', tail, 0)
    if count <= 0 or count > 4096:
        return []
    starts = _find_material_starts(tail, count)
    if not starts:
        return []
    mats: List[GmtMaterial] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(tail)
        raw = tail[start:end]
        name = raw[:64].split(b'\x00', 1)[0].decode('latin-1', 'replace')
        strings: List[str] = []
        j = 0
        while j < len(raw):
            bch = raw[j]
            if 32 <= bch < 127:
                k = j
                while k < len(raw) and 32 <= raw[k] < 127:
                    k += 1
                if k - j >= 4:
                    strings.append(raw[j:k].decode('latin-1', 'replace'))
                j = k
            else:
                j += 1
        mats.append(GmtMaterial(index=i, raw=raw, name=name, strings=strings))
    return mats


def parse_gmt(path: str | Path, data: bytes | None = None) -> GmtFile:
    p = Path(path)
    d = data if data is not None else p.read_bytes()
    if len(d) < 0x174:
        raise ValueError(f"GMT too small: {p}")
    obj_off, flags, magic = struct.unpack_from("<II16s", d, 0)
    header_18_16c = d[0x18:0x16C]
    mesh_count, mesh_first = struct.unpack_from("<II", d, 0x16C)
    if not (0 <= mesh_count <= 256 and mesh_first >= 0x174 and mesh_first + mesh_count * 108 <= len(d)):
        # still return a best-effort parse
        mesh_count, mesh_first = 0, mesh_first
    meshes: List[GmtMesh] = []
    for i in range(mesh_count):
        raw = list(struct.unpack_from("<27I", d, mesh_first + i * 108))
        stride = _detect_stride(d, raw)
        rec = GmtMeshRecord(raw=raw, vertex_stride=stride)
        v_end = rec.vertex_end
        i_end = rec.index_bytes_end
        v_data = d[rec.vertex_offset:v_end] if rec.vertex_offset <= len(d) else b""
        i_data = d[rec.index_offset:i_end] if rec.index_offset <= len(d) else b""
        meshes.append(GmtMesh(record=rec, vertex_data=v_data, index_data=i_data))
    tail = d[obj_off:] if obj_off <= len(d) else b""
    materials = _parse_materials(tail)
    return GmtFile(
        source_path=p, original=d, obj_list_offset=obj_off, flags=flags, magic=magic,
        header_18_16c=header_18_16c, mesh_first=mesh_first, meshes=meshes, tail=tail, materials=materials, gaps=b""
    )


def write_gmt(g: GmtFile) -> bytes:
    """Reconstruct GMT preserving original bytes for unknown/gap regions.

    This updates known structural fields (header, mesh table, mesh data locations as-is)
    and writes mesh vertex/index blobs and tail at their original offsets. If layout
    changed, caller should use a relayout function (not implemented yet).
    """
    out = bytearray(g.original)
    # header
    struct.pack_into("<II16s", out, 0, g.obj_list_offset, g.flags, g.magic)
    out[0x18:0x16C] = g.header_18_16c[:0x154].ljust(0x154, b"\x00")
    struct.pack_into("<II", out, 0x16C, len(g.meshes), g.mesh_first)
    # mesh records and data
    for i, m in enumerate(g.meshes):
        off = g.mesh_first + i * 108
        struct.pack_into("<27I", out, off, *m.record.raw)
        vo = m.record.vertex_offset
        io = m.record.index_offset
        ve = vo + len(m.vertex_data)
        ie = io + len(m.index_data)
        if ve <= len(out):
            out[vo:ve] = m.vertex_data
        if ie <= len(out):
            out[io:ie] = m.index_data
    # tail
    if g.obj_list_offset + len(g.tail) <= len(out):
        out[g.obj_list_offset:g.obj_list_offset + len(g.tail)] = g.tail
    return bytes(out)
