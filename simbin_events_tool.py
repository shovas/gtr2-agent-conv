#!/usr/bin/env python3
"""Structural reader for SimBin GTTF (time trial) and IRSR (replay) payloads.

These live inside gzip containers (`gzip_simbin_tool.py`). Verified fields:
  magic 'GTTF'/'IRSR' at 0x2D, f32 version at +4,
  u32-length-prefixed TRK filename, u32-length-prefixed AIW filename,
  then binary records with embedded ASCII strings.

Frame grid (63-byte stride) decodes position, heading, pitch and time per
sample; the meaning of the remaining per-frame fields is NOT decoded. This
tool also identifies the header, filenames, and printable strings.
"""
from __future__ import annotations

import argparse
import gzip
import math
import statistics
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAGICS = (b"GTTF", b"IRSR")


@dataclass
class EventFile:
    kind: str
    version: float
    trk: str
    aiw: str
    strings: list[tuple[int, str]] = field(default_factory=list)
    driver: str | None = None
    co_driver: str | None = None
    team: str | None = None
    car: str | None = None
    metadata_offset: int = -1


def _printable(data: bytes) -> bool:
    return all(32 <= c < 127 for c in data)


def parse_metadata(data: bytes, off: int, kind: str) -> dict | None:
    """Parse the metadata block immediately following the TRK/AIW filenames.

    GTTF files (time trials): 11-byte prefix, then two 1-byte-length-prefixed
    names (driver, co-driver), then a NUL-terminated car filename.
    GTL-IRSR files (replays): same prefix, one name, then the car filename.
    Other IRSR variants (GTR2 replays, rFactor replays) use a different layout
    and are left undecoded (returns None).
    """
    if off + 12 > len(data) or data[off:off + 3] != b"\0\0\0":
        return None
    q = off + 11
    names = []
    for _ in range(2 if kind == "GTTF" else 1):
        if q >= len(data):
            return None
        size = data[q]
        q += 1
        if not (0 < size < 80) or q + size > len(data):
            return None
        name = data[q:q + size]
        if not name or not all(32 <= c < 127 for c in name):
            return None
        names.append(name.decode("latin-1"))
        q += size
    while q < len(data) and data[q] == 0:
        q += 1
    j = q
    while j < len(data) and 32 <= data[j] < 127:
        j += 1
    car = data[q:j].decode("latin-1") if j > q else ""
    if not car.lower().endswith((".car", ".veh")):
        return None
    return {"offset": off, "driver": names[0],
            "co_driver": names[1] if len(names) > 1 else None, "car": car}


def parse_gtr2_irsr_metadata(data: bytes, off: int) -> dict | None:
    """Parse GTR2-IRSR metadata: 11-byte prefix, 5-byte field, two Pascal names
    (team, driver), then a NUL-terminated car filename. Validated on 9 files.
    """
    if off + 16 >= len(data):
        return None
    q = off + 16
    names = []
    for _ in range(2):
        size = data[q]
        q += 1
        if not (0 < size < 80) or q + size > len(data):
            return None
        name = data[q:q + size]
        if not name or not all(32 <= c < 127 for c in name):
            return None
        names.append(name.decode("latin-1"))
        q += size
    while q < len(data) and data[q] == 0:
        q += 1
    j = q
    while j < len(data) and 32 <= data[j] < 127:
        j += 1
    car = data[q:j].decode("latin-1")
    if not car.lower().endswith(".car"):
        return None
    return {"offset": off, "driver": names[1], "co_driver": None,
            "team": names[0], "car": car}


def _read_u32_string(data: bytes, off: int) -> tuple[str, int]:
    size = struct.unpack_from("<I", data, off)[0]
    off += 4
    if size > 4096 or off + size > len(data):
        raise ValueError("invalid filename length")
    return data[off:off + size].decode("latin-1"), off + size


def parse_rf1_metadata(data: bytes, off: int) -> dict | None:
    """Parse rFactor-era IRSR metadata: 9-byte prefix, 1-byte-length driver,
    NUL-terminated vehicle and skin names. Validated on 5 RF1Vanilla replays.
    """
    # rF1 uses 0x4803 in bytes 2-3; Superleague Formula 2009 replays use
    # 0xffff in the same slot (corpus-verified: 5/6 local Superleague .Vcr).
    RF1_PREFIXES = (bytes.fromhex("000048030100000000"),
                    bytes.fromhex("0000ffff0100000000"))
    if data[off:off + 9] not in RF1_PREFIXES:
        return None
    q = off + 9
    if q >= len(data):
        return None
    size = data[q]
    if not (0 < size < 80) or q + 1 + size > len(data):
        return None
    driver = data[q + 1:q + 1 + size].decode("latin-1")
    q += 1 + size
    if q >= len(data) or data[q] != 0:
        return None
    j = data.find(b"\0", q + 1)
    if j < 0:
        return None
    vehicle = data[q + 1:j].decode("latin-1")
    if not vehicle.lower().endswith(".veh"):
        return None
    return {"offset": off, "driver": driver, "co_driver": None, "car": vehicle}


def parse_payload(data: bytes) -> EventFile:
    kind = next((m.decode() for m in MAGICS if m in data[:64]), None)
    if kind is None:
        raise ValueError("not a GTTF/IRSR payload")
    off = data.index(kind.encode()) + 4
    version = struct.unpack_from("<f", data, off)[0]
    off += 4
    first, off = _read_u32_string(data, off)
    if first.lower().endswith(".rfm"):
        # rFactor-lineage replay: mod, (empty), SCN, AIW.
        names = [first]
        for _ in range(3):
            name, off = _read_u32_string(data, off)
            names.append(name)
        meta = parse_rf1_metadata(data, off)
        trk, aiw = names[2], names[3]
    else:
        second, off = _read_u32_string(data, off)
        names = [first, second]
        meta = parse_metadata(data, off, kind)
        if meta is None and kind == "IRSR":
            meta = parse_gtr2_irsr_metadata(data, off)
        trk, aiw = names
    strings = []
    i = off
    while i < len(data):
        if 32 <= data[i] < 127:
            j = i
            while j < len(data) and 32 <= data[j] < 127:
                j += 1
            if j - i >= 3 and data[i:i + 1].isalpha():
                strings.append((i, data[i:j].decode("latin-1")))
            i = j + 1
        else:
            i += 1
    return EventFile(kind=kind, version=version, trk=trk, aiw=aiw, strings=strings,
                     driver=meta["driver"] if meta else None,
                     co_driver=meta["co_driver"] if meta else None,
                     team=meta.get("team") if meta else None,
                     car=meta["car"] if meta else None,
                     metadata_offset=meta["offset"] if meta else -1)


def parse_file(path: str | Path) -> EventFile:
    raw = Path(path).read_bytes()
    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    return parse_payload(data)


# The ghost replay stores one frame sample every 63 bytes. An earlier reader
# used 252 (4 samples) as the stride, which collapsed four consecutive frames
# into one; a 63-byte stride yields 4x as many frames with smooth per-frame
# position/time deltas (verified across the GTR2 GTTF corpus).
FRAME_STRIDE = 63
FRAME_TIME_OFF = 20


def find_frame_grid(data: bytes) -> dict | None:
    """Locate the GTTF frame-record grid.

    Records are 63 bytes apart; the f32 at +20 increases monotonically by
    ~0.01..0.2 per frame and the first three floats are car positions.  The
    grid start varies with metadata length, so each phase (mod 63) is tried.
    """
    best_run, best_start = 0, None
    for phase in range(0, FRAME_STRIDE):
        run, start = 0, None
        for off in range(phase, len(data) - FRAME_STRIDE - 24, FRAME_STRIDE):
            if off + FRAME_STRIDE + 24 > len(data):
                break
            t0 = struct.unpack_from("<f", data, off + FRAME_TIME_OFF)[0]
            t1 = struct.unpack_from("<f", data, off + FRAME_STRIDE + FRAME_TIME_OFF)[0]
            if math.isfinite(t0) and math.isfinite(t1) and 0.001 < t1 - t0 < 1.0:
                if run == 0:
                    start = off
                run += 1
            else:
                if run > best_run:
                    best_run, best_start = run, start
                run = 0
        if run > best_run:
            best_run, best_start = run, start
    if best_run < 8 or best_start is None:
        return None
    return {"offset": best_start, "stride": FRAME_STRIDE, "count": best_run + 1}


def read_frames(data: bytes, grid: dict) -> list[dict]:
    """Decode frame positions and timestamps from a located grid."""
    out = []
    for i in range(grid["count"]):
        off = grid["offset"] + i * grid["stride"]
        if off + 24 > len(data):
            break
        out.append({"offset": off,
                    "position": struct.unpack_from("<3f", data, off),
                    "heading": struct.unpack_from("<f", data, off + 12)[0],
                    "pitch": struct.unpack_from("<f", data, off + 16)[0],
                    "time": struct.unpack_from("<f", data, off + FRAME_TIME_OFF)[0]})
    return out


# GTR2 Driving School `.dsi` instructor lines use the same 63-byte record and
# marker as GTTF ghost frames, but place four floats between position and the
# marker (GTTF has three), so the marker sits at record +0 and the position at
# +35/+39/+43. The reference-only gtr2-agent-tools ghost loader documents this.
GHOST_MARKER = b"\x01\x00\x00\x34\x00\x20\x00"
GHOST_POS_OFF = (35, 39, 43)


def read_ghost_line(data: bytes) -> list[tuple[float, float, float]]:
    """Read the (x, y, z) polyline from a decompressed GTR2 ``.dsi`` payload.

    Records are 63 bytes apart. Walking by stride (rather than re-searching for
    the marker) avoids false positives in the surrounding metadata.
    """
    start = data.find(GHOST_MARKER)
    if start < 0:
        return []
    points = []
    off = start
    while off + GHOST_POS_OFF[2] + 4 <= len(data):
        if data[off:off + len(GHOST_MARKER)] != GHOST_MARKER:
            break
        xyz = struct.unpack_from("<3f", data, off + GHOST_POS_OFF[0])
        if not all(math.isfinite(x) and abs(x) < 1e5 for x in xyz):
            break
        points.append(xyz)
        off += FRAME_STRIDE
    return points


def ghost_marker_records(data: bytes, kind: str) -> list[bytes]:
    """Return 63-byte ghost records aligned so the marker starts at offset 0.

    ``kind`` is ``"dsi"`` (marker already at record +0) or ``"gtt"`` (marker at
    frame +24, found via :func:`find_frame_grid`).
    """
    if kind == "dsi":
        rows = []
        off = data.find(GHOST_MARKER)
        while off >= 0 and off + FRAME_STRIDE <= len(data):
            rows.append(data[off:off + FRAME_STRIDE])
            off = data.find(GHOST_MARKER, off + FRAME_STRIDE)
        return rows
    if kind == "gtt":
        grid = find_frame_grid(data)
        if not grid:
            return []
        out = []
        for frame in read_frames(data, grid):
            off = frame["offset"] + 24
            if off + FRAME_STRIDE <= len(data):
                out.append(data[off:off + FRAME_STRIDE])
        return out
    raise ValueError(f"unknown ghost kind: {kind}")


def byte_field_stats(rows: list[bytes]) -> tuple[list[float], list[float], list[float]]:
    """Per-byte (63 positions) zero fraction, mean and std, normalised to 0..1."""
    n = len(rows)
    if not n:
        raise ValueError("no rows")
    zero = [0.0] * FRAME_STRIDE
    mean = [0.0] * FRAME_STRIDE
    std = [0.0] * FRAME_STRIDE
    for k in range(FRAME_STRIDE):
        col = [row[k] for row in rows]
        m = sum(col) / n
        zero[k] = sum(1 for b in col if b == 0) / n
        mean[k] = m / 255.0
        std[k] = (sum((b - m) ** 2 for b in col) / n) ** 0.5 / 255.0
    return zero, mean, std


def _corr(x: list[float], y: list[float]) -> float:
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else 0.0


def field_alignment_score(a: tuple, b: tuple, lag: int) -> float:
    """Correlate post-marker byte statistics of two record sets at ``lag``."""
    total = 0.0
    for k in range(3):
        left = a[k][8:FRAME_STRIDE]
        right = [b[k][(i + lag) % FRAME_STRIDE] for i in range(8, FRAME_STRIDE)]
        total += _corr(left, right)
    return total


def best_field_alignment(a: tuple, b: tuple) -> tuple[float, int]:
    """Return ``(best_score, lag)`` over all 63 possible byte alignments."""
    best = (float("-inf"), 0)
    for lag in range(FRAME_STRIDE):
        score = field_alignment_score(a, b, lag)
        if score > best[0]:
            best = (score, lag)
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file")
    ap.add_argument("--strings", type=int, default=12)
    ap.add_argument("--frames", action="store_true", help="report the GTTF frame grid")
    ap.add_argument("--ghost-line", action="store_true", help="report a .dsi instructor polyline")
    args = ap.parse_args(argv)
    raw = Path(args.file).read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    if args.ghost_line:
        pts = read_ghost_line(raw)
        print(f"ghost_points={len(pts)} first={pts[0] if pts else None} "
              f"last={pts[-1] if pts else None}")
        return 0
    e = parse_payload(raw)
    print(f"kind={e.kind} version={e.version} trk={e.trk!r} aiw={e.aiw!r}")
    if e.driver:
        print(f"driver={e.driver!r} co_driver={e.co_driver!r} team={e.team!r} "
              f"car={e.car!r} meta_offset={e.metadata_offset:#x}")
    print(f"printable_strings={len(e.strings)}")
    for off, s in e.strings[:args.strings]:
        print(f"  {off}: {s[:80]}")
    if args.frames:
        grid = find_frame_grid(raw)
        if grid:
            frames = read_frames(raw, grid)
            print(f"frame_grid={grid} first_time={frames[0]['time']:.3f} "
                  f"last_time={frames[-1]['time']:.3f}")
        else:
            print("frame_grid=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
