#!/usr/bin/env python3
"""GMT inspection tool for GTL/GTR2 conversion.

Evidence-based, first-pass: validates observed GTR2/GT Legends GMT headers and
the mesh table at 0x16C. It does NOT convert GMT geometry.
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
GMT_MAGIC_RF1_OLD = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")
GMT_MAGIC_GTR1 = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bdbba6bf90")


def detect_variant(data: bytes) -> str:
    """Identify known GMT-family variants by their observed magic location."""
    if data[:4] == b"\x0f\xb1\xff\xff":
        return "jca-encrypted"
    if data[:8] == b"RaceGMT\0":
        return "racegmt"
    if len(data) >= 24 and data[8:24] == GMT_MAGIC_GTR_GTL:
        return "new-gtr2-gtl"
    if len(data) >= 0x1E4 and data[0x1D4:0x1E4] == GMT_MAGIC_RF1_OLD:
        return "old-rfactor1"
    if len(data) >= 20 and data[4:20] == GMT_MAGIC_GTR1:
        return "old-gtr2004"
    return "unknown"


@dataclass
class GmtMeshRecord:
    index: int
    flags: int
    vertex_count: int
    vertex_offset: int
    index_count: int
    index_offset: int

    @property
    def index_bytes_end(self) -> int:
        # observed: 4-byte lead + u16 indices
        return self.index_offset + 4 + self.index_count * 2

    @property
    def vertex_bytes_end(self) -> int:
        # observed: 32-byte vertices
        return self.vertex_offset + self.vertex_count * 32


@dataclass
class GmtHeader:
    path: Path
    size: int
    obj_list_offset: int
    flags: int
    magic: bytes
    mesh_count: int | None = None
    mesh_first: int | None = None
    mesh_table_ok: bool = False
    meshes: list[GmtMeshRecord] | None = None

    @property
    def v0(self) -> int:
        # Back-compat alias; field is an offset, not a version.
        return self.obj_list_offset

    @property
    def known_magic(self) -> bool:
        return self.magic == GMT_MAGIC_GTR_GTL

    @property
    def likely_encrypted(self) -> bool:
        # GMT encryption skips first 4 bytes, so obj_list_offset may survive but
        # flags/magic become scrambled. Heuristic, not proof.
        return (not self.known_magic) and len(self.magic) == 16


def _parse_mesh_table(data: bytes) -> tuple[int | None, int | None, bool, list[GMTMeshRecord]]:
    if len(data) < 0x174:
        return None, None, False, []
    count, first = struct.unpack_from("<II", data, 0x16C)
    if not (0 < count <= 256 and first >= 0x174 and first + count * 108 <= len(data)):
        return count, first, False, []
    meshes: list[GMTMeshRecord] = []
    for i in range(count):
        rec = struct.unpack_from("<27I", data, first + i * 108)
        meshes.append(GmtMeshRecord(
            index=i,
            flags=rec[1],
            vertex_count=rec[3],
            vertex_offset=rec[4],
            index_count=rec[10],
            index_offset=rec[11],
        ))
    ok = all(m.vertex_bytes_end <= len(data) and m.index_bytes_end <= len(data) for m in meshes)
    return count, first, ok, meshes


def read_header(path: str | os.PathLike, parse_meshes: bool = False) -> GmtHeader:
    p = Path(path)
    data = p.read_bytes()
    if len(data) < 24:
        raise ValueError(f"file too small for GMT header: {p}")
    obj_list_offset, flags, magic = struct.unpack_from("<II16s", data, 0)
    mesh_count, mesh_first, mesh_ok, meshes = _parse_mesh_table(data)
    return GmtHeader(
        path=p,
        size=len(data),
        obj_list_offset=obj_list_offset,
        flags=flags,
        magic=magic,
        mesh_count=mesh_count,
        mesh_first=mesh_first,
        mesh_table_ok=mesh_ok,
        meshes=meshes if parse_meshes else None,
    )


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
    h = read_header(args.file, parse_meshes=args.meshes)
    print(f"path: {h.path}")
    print(f"size: {h.size}")
    print(f"obj_list_offset: {h.obj_list_offset} (0x{h.obj_list_offset:08x})")
    print(f"flags: {h.flags} (0x{h.flags:08x})")
    print(f"magic: {h.magic.hex()}")
    print(f"known_gtr_gtl_magic: {h.known_magic}")
    print(f"variant: {detect_variant(Path(args.file).read_bytes())}")
    print(f"likely_encrypted: {h.likely_encrypted}")
    print(f"mesh_count: {h.mesh_count}")
    print(f"mesh_first: {h.mesh_first}")
    print(f"mesh_table_ok: {h.mesh_table_ok}")
    print(f"sha256: {sha256(h.path)}")
    if args.meshes and h.meshes:
        for m in h.meshes:
            print(
                f"mesh[{m.index}]: flags=0x{m.flags:08x} vc={m.vertex_count} vo={m.vertex_offset} "
                f"ic={m.index_count} io={m.index_offset}"
            )
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    paths = scan_gmts(args.root)
    bad = 0
    for p in paths:
        try:
            h = read_header(p)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR\t{p}\t{e}")
            bad += 1
            continue
        ok = h.known_magic and h.mesh_table_ok
        status = "OK" if ok else ("UNKNOWN_MAGIC" if not h.known_magic else "BAD_MESH_TABLE")
        if status != "OK":
            bad += 1
        if args.verbose or status != "OK":
            print(
                f"{status}\t{h.size}\tobj=0x{h.obj_list_offset:08x}\tfl=0x{h.flags:08x}\t"
                f"meshes={h.mesh_count}\t{h.magic.hex()}\t{p}"
            )
    print(f"scanned={len(paths)} issues={bad}")
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
                print(
                    f"DIFF\t{name}\t{lh.size}\t{rh.size}\t"
                    f"obj=0x{lh.obj_list_offset:08x}/0x{rh.obj_list_offset:08x}\t"
                    f"fl=0x{lh.flags:08x}/0x{rh.flags:08x}\t"
                    f"meshes={lh.mesh_count}/{rh.mesh_count}"
                )
    print(f"same={same} diff={diff} left_only={left_only} right_only={right_only}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="show GMT header/mesh info")
    p.add_argument("file")
    p.add_argument("--meshes", action="store_true", help="print mesh record summary")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("scan", help="scan directory for .gmt files and validate header/mesh table")
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
