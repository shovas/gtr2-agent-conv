#!/usr/bin/env python3
"""Partial parser for the `RaceGMT\\0` mesh variant (Race 07 DLC content).

Verified from ../Race07Complete (643 files): `magic[8], u32 name_len, name,
u32 flags (0x04000020), bounding-box floats ...`. Vertex/index table layout is
NOT decoded — do not assume new-layout GMT geometry offsets apply.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"RaceGMT\0"
FLAGS = 0x04000020


@dataclass
class RaceGmtHeader:
    name: str
    flags: int
    floats: tuple[float, ...]
    size: int


def parse_header(data: bytes) -> RaceGmtHeader:
    if data[:8] != MAGIC or len(data) < 0x20:
        raise ValueError("not a RaceGMT file")
    n = struct.unpack_from("<I", data, 8)[0]
    if not (0 < n < 256) or 12 + n + 4 > len(data):
        raise ValueError("invalid RaceGMT name length")
    name = data[12:12 + n].decode("latin-1").rstrip("\0")
    flags = struct.unpack_from("<I", data, 12 + n)[0]
    off = 16 + n
    floats = struct.unpack_from("<12f", data, off) if off + 48 <= len(data) else ()
    return RaceGmtHeader(name=name, flags=flags, floats=floats, size=len(data))


def diff_strides(a: bytes, b: bytes, gap: int = 4) -> dict:
    """Infer record strides from two same-size files of the same asset.

    Runs of differing bytes are grouped; distances between run starts reveal
    the record stride. Observed on PEOPLE_STAND_01/02: differences lie on a
    36-byte grid (3 x position triples); occasional 64-byte gaps are simply
    alternating differing records, not a separate section.
    """
    from collections import Counter

    if len(a) != len(b):
        raise ValueError("files must be the same size")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if not diff:
        return {}
    runs = []
    start = prev = diff[0]
    for i in diff[1:]:
        if i - prev > gap:
            runs.append((start, prev))
            start = i
        prev = i
    runs.append((start, prev))
    starts = [s for s, _ in runs]
    distances = Counter(starts[i + 1] - starts[i] for i in range(len(starts) - 1))
    return {"runs": len(runs), "distances": dict(distances), "first_starts": starts[:8]}


def read_positions(data: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    """Experimental raw-grid reader: decode each 36-byte block as 9 floats.

    WARNING: not a validated triangle decoder — sampled blocks contain mixed
    position, UV, index and material data (e.g. PEOPLE_STAND_01 has ASCII
    material strings starting at 0x30AF, inside the nominal grid).
    """
    header = parse_header(data)
    off = 16 + len(header.name.encode("latin-1"))
    out = []
    while off + 36 <= len(data):
        vals = struct.unpack_from("<9f", data, off)
        out.append(tuple((vals[i], vals[i + 1], vals[i + 2]) for i in (0, 3, 6)))
        off += 36
    return out


def read_material_strings(data: bytes) -> list[str]:
    """Extract NUL-terminated ASCII material/stage strings from the payload."""
    import re
    return [m.group().decode("ascii")
            for m in re.finditer(rb"[A-Za-z0-9_]{4,40}\x00", data[16:])]


STAGE_STRIDE = 264


def read_material_blocks(data: bytes) -> list[dict]:
    """Resolve material/stage blocks from the validated 264-byte stage grid.

    Observed across 60 sampled files: stage strings (`L0`/`L1`/`L2` ...) are
    spaced 264 bytes and each stage has u32 (1, 1) at +256.
    """
    import re
    matches = [m.start() for m in re.finditer(rb"L[012][A-Z0-9_]{3,39}\x00", data)]
    blocks = []
    for off in matches:
        if off + STAGE_STRIDE > len(data):
            continue
        tail = struct.unpack_from("<2I", data, off + 256)
        name = data[off:data.find(b"\0", off)].decode("ascii")
        blocks.append({"offset": off, "name": name, "tail": tail})
    return blocks


def build_stage_type_map(blocks: list[dict]) -> dict[str, tuple[int, int, int]]:
    """Map stage name to its dominant semantic type (first u32 tail).

    The first tail u32 at +256 is a stage-type enum driven by the stage name:
    diffuse -> 1/2, cubemap -> 3, specular -> 5, bump+specular -> 7, etc.
    Returns `{name: (dominant_type, count, total_samples)}`. Blocks whose first
    tail is >= 100 are skipped (false-positive stage-string offsets).
    """
    from collections import Counter
    counts: dict[str, Counter] = {}
    for block in blocks:
        first = block["tail"][0]
        if first >= 100:
            continue
        counts.setdefault(block["name"], Counter())[first] += 1
    return {name: (c.most_common(1)[0][0], c.most_common(1)[0][1], sum(c.values()))
            for name, c in counts.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    for f in args.files:
        try:
            print(f, parse_header(Path(f).read_bytes()))
        except ValueError as e:
            print(f, "ERROR", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
