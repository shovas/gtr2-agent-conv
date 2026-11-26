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
    # Header fields recovered from GTR2.exe's reader (fcn.0052be30). They are
    # written immediately after the TRK/AIW filenames, before the names.
    flags_a: int | None = None
    flags_b: int | None = None
    session_seconds: float | None = None
    flags_c: int | None = None
    flags_u: int | None = None


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


def parse_header_fields(data: bytes, off: int) -> dict | None:
    """Read the five header fields that follow the TRK/AIW filenames.

    Layout recovered from the GTR2.exe reader: u8, u8, f32, u8, u32.
    The f32 takes only 36000 / 43200 / 46800 in the local corpus — exactly
    10 / 12 / 13 hours in seconds, consistent with a session time limit.
    """
    if off + 12 > len(data):
        return None
    return {
        "flags_a": data[off],
        "flags_b": data[off + 1],
        "session_seconds": struct.unpack_from("<f", data, off + 2)[0],
        "flags_c": data[off + 6],
        "flags_u": struct.unpack_from("<I", data, off + 7)[0],
    }


def session_field_offset(data: bytes) -> int | None:
    """Return the byte offset of the header's session_seconds f32."""
    kind = next((magic.decode() for magic in MAGICS if magic in data[:64]), None)
    if kind is None:
        return None
    offset = data.index(kind.encode()) + 4 + 4
    first, offset = _read_u32_string(data, offset)
    if first.lower().endswith(".rfm"):
        return None
    _, offset = _read_u32_string(data, offset)
    return offset + 2


def set_session_seconds(data: bytes, seconds: float) -> bytes:
    """Return a copy of a GTTF/IRSR payload with session_seconds replaced.

    Only the four f32 bytes change; all other payload bytes (including the
    frame grid and tail) are preserved verbatim.
    """
    offset = session_field_offset(data)
    if offset is None or offset + 6 > len(data):
        raise ValueError("no writable session field")
    output = bytearray(data)
    struct.pack_into("<f", output, offset, seconds)
    return bytes(output)


def shift_frame_times(data: bytes, delta: float) -> bytes:
    """Return a copy with every grid frame's +20 time offset shifted by delta.

    Only the f32 time words are modified; frame positions, controls and the
    20-byte tail are preserved verbatim. Useful for constructing shifted
    ghosts without rebuilding the payload from scratch.
    """
    grid = find_frame_grid(data)
    if grid is None:
        raise ValueError("no frame grid found")
    output = bytearray(data)
    for index in range(grid["count"]):
        offset = grid["offset"] + index * grid["stride"] + FRAME_TIME_OFF
        current = struct.unpack_from("<f", output, offset)[0]
        struct.pack_into("<f", output, offset, current + delta)
    return bytes(output)


UNBOUNDED_TIME = 0xF49DC5AE  # f32 -1e32: the game's "no bound" sentinel


def parse_object_records(data: bytes, search_limit: int = 4096) -> list[dict]:
    """Parse the variable-length object records in a replay payload.

    Layout recovered from `GTR2.exe` writer `fcn.005267f0` / reader
    `fcn.005268e0`: one flags byte (its top bit stored at in-memory +0xcc),
    then two u8-length-prefixed strings, two 64-byte blocks and two u32s.
    The longest consecutive chain found near the payload start is returned;
    in the local corpus these are the replay's participants (driver entries
    and a `Safety Marshal` entry). No field semantics are claimed.
    """
    def record_at(position: int) -> dict | None:
        if position + 8 > len(data):
            return None
        first_length = data[position + 1]
        if not 1 <= first_length <= 32 or position + 2 + first_length + 1 > len(data):
            return None
        first = data[position + 2:position + 2 + first_length]
        if not all(32 <= byte < 127 for byte in first):
            return None
        second_length = data[position + 2 + first_length]
        end_of_strings = position + 3 + first_length + second_length
        if not 0 <= second_length <= 32 or end_of_strings + 136 > len(data):
            return None
        second = data[position + 3 + first_length:end_of_strings]
        if second_length and not all(32 <= byte < 127 for byte in second):
            return None
        def fixed_string(start: int) -> str:
            return data[start:start + 64].split(b"\0", 1)[0].decode("latin-1", "replace")

        return {
            "offset": position,
            "flags": data[position],
            "name": first.decode("latin-1"),
            "label": second.decode("latin-1"),
            "car": fixed_string(end_of_strings),
            "skin": fixed_string(end_of_strings + 64),
            "value": struct.unpack_from("<f", data, end_of_strings + 128)[0],
            "trailing_u32": struct.unpack_from("<I", data, end_of_strings + 132)[0],
            "window_start": struct.unpack_from("<f", data, end_of_strings + 128)[0],
            "window_end": (None if struct.unpack_from("<I", data, end_of_strings + 132)[0]
                           == UNBOUNDED_TIME
                           else struct.unpack_from("<f", data, end_of_strings + 132)[0]),
            "next_offset": end_of_strings + 136,
        }

    def chain_from(position: int) -> list[dict]:
        chain = []
        while len(chain) < 64:
            record = record_at(position)
            if record is None:
                break
            chain.append(record)
            position = record["next_offset"]
        return chain

    best: list[dict] = []
    for index in range(1, min(len(data) - 16, search_limit)):
        if not 1 <= data[index] <= 32:
            continue
        candidate = chain_from(index - 1)
        if len(candidate) > len(best):
            best = candidate
    return best


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
    header = parse_header_fields(data, off) if not first.lower().endswith(".rfm") else None
    return EventFile(kind=kind, version=version, trk=trk, aiw=aiw, strings=strings,
                     driver=meta["driver"] if meta else None,
                     co_driver=meta["co_driver"] if meta else None,
                     team=meta.get("team") if meta else None,
                     car=meta["car"] if meta else None,
                     metadata_offset=meta["offset"] if meta else -1,
                     flags_a=header["flags_a"] if header else None,
                     flags_b=header["flags_b"] if header else None,
                     session_seconds=header["session_seconds"] if header else None,
                     flags_c=header["flags_c"] if header else None,
                     flags_u=header["flags_u"] if header else None)


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
# Slot +32 is a 24-bit integer (byte +35 is always zero). Its ceiling is
# car-specific: ~5,873,841 for the GTR2 Ferrari F550 and ~6.19M for the BMW
# M3. Divided by 1024 those are 5736 / 6190, consistent with engine rpm and
# abrupt downward jumps consistent with gear shifts. Exact units unverified.
FRAME_RPM_OFF = 32
RPM_SCALE = 1024.0


def frame_s36_word(data: bytes, offset: int) -> int:
    """Return the raw u32 at frame offset +36 (a quantized-float slot)."""
    return struct.unpack_from("<I", data, offset + 36)[0]


def frame_s40_word(data: bytes, offset: int) -> int:
    """Return the raw u32 at frame offset +40 (unresolved field)."""
    return struct.unpack_from("<I", data, offset + 40)[0]


def is_quantized_s36(word: int) -> bool:
    """Whether +36 has the corpus-invariant quantized-float shape.

    Across all 31 local GTT files the low 16 bits are zero (except rare
    artifacts) and the high mantissa bits are only 8 or 12, so the float can
    only be zero or ±(17/8 or 35/16) * 4^k.
    """
    return (word & 0xFFFF) == 0 and ((word >> 16) & 0x7F) in (8, 12)


def frame_slot48(data: bytes, offset: int) -> tuple[int | None, int | None]:
    """Return the two signed 16-bit channels packed in frame slot +48.

    The low half tracks steering +8 and the high half tracks engine +32
    (permutation-controlled corpus evidence); exact units are unknown.
    """
    if offset + 52 > len(data):
        return None, None
    value = int.from_bytes(data[offset + 48:offset + 52], "little")
    return (struct.unpack("<h", struct.pack("<H", value & 0xFFFF))[0],
            struct.unpack("<h", struct.pack("<H", (value >> 16) & 0xFFFF))[0])


def frame_rpm(data: bytes, offset: int) -> int | None:
    """Return the raw 24-bit engine-speed word at a GTTF frame offset."""
    if offset + 35 > len(data) or data[offset + 35] != 0:
        return None
    return int.from_bytes(data[offset + FRAME_RPM_OFF:offset + 35], "little")


def find_frame_grid(data: bytes) -> dict | None:
    """Locate the GTTF frame-record grid.

    Records are 63 bytes apart; the f32 at +20 increases monotonically by
    ~0.01..0.2 per frame and the first three floats are car positions.  The
    grid start varies with metadata length, so each phase (mod 63) is tried.
    """
    # GTTF frames carry a verified 7-byte marker at +24. Finding those bytes
    # with bytes.find() avoids scanning all 63 phases over the whole payload
    # (the old loop cost ~42 s across the simbin_events_tool tests).
    marker = bytes.fromhex("01000034002000")
    candidates = []
    if b"GTTF" in data[:64]:
        index = data.find(marker)
        while index >= 0:
            if index >= 24:
                candidates.append(index - 24)
            index = data.find(marker, index + 1)

    def run_length(start: int) -> int:
        run = 0
        offset = start
        while offset + FRAME_STRIDE + FRAME_TIME_OFF + 4 <= len(data):
            t0 = struct.unpack_from("<f", data, offset + FRAME_TIME_OFF)[0]
            t1 = struct.unpack_from("<f", data, offset + FRAME_STRIDE + FRAME_TIME_OFF)[0]
            if math.isfinite(t0) and math.isfinite(t1) and 0.001 < t1 - t0 < 1.0:
                run += 1
                offset += FRAME_STRIDE
            else:
                break
        return run

    # The first marker in a GTTF payload is the grid start; later markers
    # belong to individual frames. Cap the attempts to avoid O(n^2) walks.
    for candidate in candidates[:8]:
        run = run_length(candidate)
        if run >= 8:
            return {"offset": candidate, "stride": FRAME_STRIDE, "count": run + 1}

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


def find_preframe_records(data: bytes, grid_offset: int) -> list[tuple[float, ...]]:
    """Return the 24-byte path records immediately preceding a frame grid.

    Each record is six f32 values: ``(y, z, heading, f3, f4, x)``.  The 6th
    float is the world x coordinate missing from the 63-byte frame records.
    Records are found by walking backwards from the grid while all floats are
    finite and bounded; the chain is verified by a non-empty result.
    """
    end = grid_offset
    start = None
    limit = max(0, grid_offset - 24 * 3000)
    for cursor in range(grid_offset, limit, -24):
        chunk = data[cursor - 24:cursor]
        if len(chunk) < 24:
            break
        values = struct.unpack("<6f", chunk)
        if not all(math.isfinite(value) and abs(value) < 1e6 for value in values):
            break
        start = cursor - 24
    if start is None:
        return []
    return [struct.unpack("<6f", data[off:off + 24])
            for off in range(start, grid_offset, 24)]


def reconstruct_path_controls(records: list[tuple[float, ...]],
                              positions: list[tuple[float, float, float]],
                              window: int = 30) -> list[tuple[float | None, float | None]]:
    """Map frames to records and return the normalized path fields f3/f4.

    Uses the same chronological monotone search as :func:`reconstruct_frame_x`
    so every frame is paired with the same path record for all fields.
    """
    if not records:
        return [(None, None)] * len(positions)
    index = 0
    out = []
    for position in positions:
        y, z = position[0], position[1]
        candidates = range(max(0, index - 3), min(len(records), index + window))
        chosen = min(candidates,
                     key=lambda k: (records[k][0] - y) ** 2 + (records[k][1] - z) ** 2)
        index = chosen
        out.append((records[chosen][3], records[chosen][4]))
    return out


def reconstruct_frame_x(records: list[tuple[float, ...]],
                        positions: list[tuple[float, float, float]],
                        window: int = 30) -> list[float | None]:
    """Map frames onto the pre-frame path and return the reconstructed x.

    Frames follow the path in order, so the search index only advances (with a
    small look-back window).  This avoids mixing spatially close but
    chronologically distant parts of the track.
    """
    if not records:
        return [None] * len(positions)
    index = 0
    out = []
    index = 0
    for position in positions:
        y, z = position[0], position[1]
        candidates = range(max(0, index - 3), min(len(records), index + window))
        chosen = min(candidates,
                     key=lambda k: (records[k][0] - y) ** 2 + (records[k][1] - z) ** 2)
        index = chosen
        out.append(records[chosen][5])
    return out


def read_frames(data: bytes, grid: dict) -> list[dict]:
    """Decode frame positions, timestamps and reconstructed world x."""
    out = []
    for i in range(grid["count"]):
        off = grid["offset"] + i * grid["stride"]
        if off + 24 > len(data):
            break
        steering = struct.unpack_from("<f", data, off + 16)[0]
        out.append({"offset": off,
                    "position": struct.unpack_from("<3f", data, off),
                    "heading": struct.unpack_from("<f", data, off + 12)[0],
                    "pitch": steering,  # legacy alias
                    "steering": steering,
                    "time": struct.unpack_from("<f", data, off + FRAME_TIME_OFF)[0],
                    "engine_speed": frame_rpm(data, off),
                    "rpm": (value / RPM_SCALE if (value := frame_rpm(data, off)) is not None
                            else None)})
        low, high = frame_slot48(data, off)
        out[-1]["slot48_low"], out[-1]["slot48_high"] = low, high
    records = find_preframe_records(data, grid["offset"])
    positions = [frame["position"] for frame in out]
    xs = reconstruct_frame_x(records, positions)
    controls = reconstruct_path_controls(records, positions)
    for frame, x, control in zip(out, xs, controls):
        frame["x"] = x
        frame["world_position"] = (x, frame["position"][0], frame["position"][1]) \
            if x is not None else None
        frame["path_f3"], frame["path_f4"] = control
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
            first = frames[0]
            print(f"frame_grid={grid} first_time={frames[0]['time']:.3f} "
                  f"last_time={frames[-1]['time']:.3f}")
            print(f"first_world={first['world_position']} "
                  f"engine_speed={first['engine_speed']} "
                  f"slot48=({first['slot48_low']},{first['slot48_high']}) "
                  f"path_controls=({first['path_f3']},{first['path_f4']})")
        else:
            print("frame_grid=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
