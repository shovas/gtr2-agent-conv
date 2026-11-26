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

import gmt_format

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
    raw = Path(args.file).read_bytes()
    import race_gmt
    if raw.startswith(race_gmt.MAGIC):
        header = race_gmt.parse_header(raw)
        print(f"path: {args.file}")
        print(f"size: {len(raw)}")
        print("variant: racegmt")
        print(f"racegmt_name: {header.name}")
        print(f"racegmt_flags: {header.flags} (0x{header.flags:08x})")
        print(f"payload_offset: {16 + len(header.name)}")
        triples = [header.floats[i:i + 3] for i in range(0, len(header.floats), 3)]
        print(f"quad_triples: {len(triples)}")
        print(f"triple3_equals_triple4: {len(triples) == 4 and triples[2] == triples[3]}")
        print("geometry: not decoded (RaceGMT container only)")
        return 0
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
        import gmt_format
        parsed = gmt_format.parse_gmt(args.file, Path(args.file).read_bytes())
        for m in h.meshes:
            print(
                f"mesh[{m.index}]: flags=0x{m.flags:08x} vc={m.vertex_count} vo={m.vertex_offset} "
                f"ic={m.index_count} io={m.index_offset}"
            )
            raw = Path(args.file).read_bytes()
            if m.vertex_offset + 4 <= len(raw):
                marker = struct.unpack_from("<I", raw, m.vertex_offset)[0]
                low, high, delta = gmt_format.split_f0(marker)
                print(f"  f0=0x{marker:08x} halves=({low},{high}) delta={delta}")
                byte_low, byte_high = gmt_format.f0_byte_pair(marker)
                print(f"  f0_bytes=({byte_low},{byte_high}) consecutive={byte_high == byte_low + 1}")
            if m.index < len(parsed.meshes):
                stream = parsed.meshes[m.index].stream2_data
                vertex_count = parsed.meshes[m.index].record.vertex_count
                if stream and vertex_count:
                    signature = gmt_format.stream_column_signature(stream, vertex_count)
                    triples = gmt_format.decode_stream_records(stream, vertex_count)
                    print(f"  stream_cols={signature} decoded_triples={triples is not None}")
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


def cmd_relayout(args: argparse.Namespace) -> int:
    """Repack a GMT with rebuilt offsets (useful after mesh data changes size)."""
    data = Path(args.file).read_bytes()
    g = gmt_format.parse_gmt(args.file, data)
    out = gmt_format.relayout_gmt(g, align=args.align)
    Path(args.output).write_bytes(out)
    print(f"relayout: {g.mesh_count} meshes, {len(data)} -> {len(out)} bytes "
          f"obj_list_offset {g.obj_list_offset} -> {struct.unpack_from('<I', out, 0)[0]}")
    return 0


def cmd_f0(args: argparse.Namespace) -> int:
    """Report per-mesh f0 markers and their verified structure."""
    data = Path(args.file).read_bytes()
    parsed = gmt_format.parse_gmt(args.file, data)
    near_equal = 0
    reported = 0
    for ordinal, mesh in enumerate(parsed.meshes):
        marker = gmt_format.mesh_marker(mesh)
        if marker is None:
            print(f"mesh[{ordinal}]: f0=none")
            continue
        low, high, delta = gmt_format.split_f0(marker)
        near_equal += int(delta <= 1)
        reported += 1
        note = ""
        if ordinal == 0 and delta <= 1:
            note = " note=mesh0_normally_has_large_delta"
        elif ordinal > 0 and delta > 8:
            note = " note=later_mesh_delta_unusually_large"
        print(f"mesh[{ordinal}]: f0=0x{marker:08x} halves=({low},{high}) "
              f"delta={delta} first={ordinal == 0}{note}")
    print(f"meshes={len(parsed.meshes)} markers={reported} near_equal<=1={near_equal}")
    return 0


def cmd_f0_compare(args: argparse.Namespace) -> int:
    """Compare two meshes' f0 marker lists (cross-game preservation check)."""
    def markers(path):
        data = Path(path).read_bytes()
        parsed = gmt_format.parse_gmt(path, data)
        return [gmt_format.mesh_marker(mesh) or 0 for mesh in parsed.meshes]

    left = markers(args.left)
    right = markers(args.right)
    same_length = len(left) == len(right)
    tail_equal = same_length and left[1:] == right[1:]
    first_equal = bool(left) and left[0] == right[0]
    print(f"left_markers={len(left)} right_markers={len(right)}")
    print(f"same_length={same_length} tail_equal={tail_equal} "
          f"first_equal={first_equal}")
    if same_length and left:
        print(f"first=({left[0]}, {right[0]}) "
              f"tail={'(equal)' if tail_equal else '(different)'}")
    return 0 if tail_equal and left else 1


def cmd_decode_gsc(args: argparse.Namespace) -> int:
    """Decode an ISI-encrypted GSC GMT member and write a GTR2-layout GMT."""
    import gmt_layout
    import gmt_semantic
    raw = Path(args.file).read_bytes()
    decoded = gmt_semantic.decode_gsc_member(raw)
    if decoded is None:
        print("error: member failed ISI/geometry validation")
        return 1
    out = gmt_layout.gsc_member_to_gtr2(raw)
    Path(args.output).write_bytes(out)
    parsed = gmt_format.parse_gmt(args.output, out)
    quality = decoded["quality"]
    print(f"gsc->gtr2: meshes={len(parsed.meshes)} vertices="
          f"{sum(len(m.base_vertices) for m in parsed.meshes)} "
          f"faces={quality['face_count']} plausible={quality['plausible_positions']}")
    return 0


def cmd_uv(args: argparse.Namespace) -> int:
    """Report each mesh's GTR2 UV block and its first UV pairs."""
    import gmt_format
    data = Path(args.file).read_bytes()
    parsed = gmt_format.parse_gmt(args.file, data)
    if not parsed.meshes:
        print("no meshes")
        return 1
    for index, mesh in enumerate(parsed.meshes):
        vertex_count = mesh.record.vertex_count
        stream = mesh.stream2_data
        print(f"mesh[{index}]: vc={vertex_count} uv_bytes={len(stream)} "
              f"rec6={mesh.record.raw[6]} rec7={mesh.record.raw[7]}")
        if not stream or vertex_count <= 0:
            continue
        signature = gmt_format.stream_column_signature(stream, vertex_count)
        triples = gmt_format.decode_stream_records(stream, vertex_count)
        ratios = gmt_format.uv_tiling_factors(stream, vertex_count)
        ratio_text = "None" if ratios is None else f"{ratios[0]:g},{ratios[1]:g}"
        print(f"  signature={signature} decoded_triples={triples is not None} "
              f"tiling={ratio_text}")
        pairs = [struct.unpack_from("<2f", stream, i * 32 + 4)
                 for i in range(min(vertex_count, args.limit))]
        for i, pair in enumerate(pairs):
            print(f"  uv[{i}]={pair[0]:.5f},{pair[1]:.5f}")
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

    p = sub.add_parser("decode-gsc", help="convert an encrypted GSC GMT member to GTR2 layout")
    p.add_argument("file")
    p.add_argument("output")
    p.set_defaults(func=cmd_decode_gsc)

    p = sub.add_parser("f0", help="report per-mesh f0 marker structure")
    p.add_argument("file")
    p.set_defaults(func=cmd_f0)

    p = sub.add_parser("f0-compare", help="compare f0 marker lists of two GMTs")
    p.add_argument("left")
    p.add_argument("right")
    p.set_defaults(func=cmd_f0_compare)

    p = sub.add_parser("uv", help="report GTR2 UV blocks and decoded UV pairs")
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=5, help="max UV pairs to print per mesh")
    p.set_defaults(func=cmd_uv)

    p = sub.add_parser("relayout", help="rebuild all offsets and pack a GMT to a new file")
    p.add_argument("file")
    p.add_argument("output")
    p.add_argument("--align", type=int, default=4, help="blob alignment (power of two, default 4)")
    p.set_defaults(func=cmd_relayout)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
