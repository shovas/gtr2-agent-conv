#!/usr/bin/env python3
"""Decoder for the ISI ``.anm`` animation format (single- and multi-bone).

Header: 12-byte name, u32 flag, u32 version (always 1), duration, rate and
u32 bone count at +28; key count at +68. Each bone occupies a 40-byte header
followed by that many 32-byte TRS/time keys: position (3 f32), quaternion
(4 f32) and time (1 f32). The first bone header starts at +36.

Corpus-verified across all 2,436 archived ANM members in 21 `../` game
folders: 2,435 decode; the sole exception (F12001 ``CATSTEER.ANM``) carries a
genuinely degenerate quaternion (0,0,0,-0.7071) and is reported as unsupported
rather than guessed at. Note the value at +28 is the *bone count* (tests that
called it "version" were mislabelled; the real version at +16 is always 1).
"""
from __future__ import annotations

import argparse
import math
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AnmKey:
    position: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]
    time: float


@dataclass
class AnmBone:
    name: str
    keys: list[AnmKey]


@dataclass
class AnmFile:
    name: str
    bone: str
    version: int
    duration: float
    rate: float
    bone_count: int
    keys: list[AnmKey]  # first bone's keys (backward-compatible flat view)
    bones: list[AnmBone]


def read_anm(data: bytes) -> AnmFile:
    if len(data) < 108:
        raise ValueError("ANM too small")
    name = data[:12].split(b"\0", 1)[0].decode("latin-1", "replace")
    flag, version, duration, rate, bone_count = struct.unpack_from("<IIffI", data, 12)
    if version != 1:
        raise ValueError(f"unsupported ANM version {version}")
    bone = data[32:40].split(b"\0", 1)[0].decode("latin-1", "replace")
    declared = struct.unpack_from("<I", data, 68)[0]
    if declared == 0 or bone_count == 0:
        raise ValueError("ANM has no keyframes")
    # Corpus-verified multi-bone layout: each bone occupies a 40-byte header
    # followed by `declared` 32-byte TRS/time keys. The first header starts at
    # +36 (the 8-byte bone name is at its beginning), so the first key is at +76.
    stride = 40 + declared * 32
    if stride < 32:
        raise ValueError("invalid ANM stride")
    bones = []
    for bi in range(bone_count):
        header = 36 + bi * stride
        key_start = header + 40
        if key_start + 32 > len(data):
            break
        bone_name = data[header:header + 12].split(b"\0", 1)[0].decode("latin-1", "replace")
        count = min(declared, (len(data) - key_start) // 32)
        keys = []
        for i in range(count):
            f = struct.unpack_from("<8f", data, key_start + i * 32)
            qn = math.sqrt(sum(x * x for x in f[3:7]))
            if not (0.9 < qn < 1.1 and math.isfinite(f[7])):
                raise ValueError(f"bone {bi} key {i}: quaternion norm {qn}")
            # Some files carry a trailing time=0 sentinel key; stop there.
            if keys and f[7] <= keys[-1].time:
                break
            keys.append(AnmKey(f[:3], f[3:7], f[7]))
        if keys:
            bones.append(AnmBone(bone_name, keys))
    if not bones:
        raise ValueError("ANM has no decodable bones")
    return AnmFile(name, bone, version, duration, rate, bone_count,
                   bones[0].keys, bones)


def validate_anm(anm: AnmFile) -> list[str]:
    """Check corpus-verified ANM keyframe invariants.

    Verified on 236 F1C/F12002 archived files: every bone has strictly
    increasing key times for non-sentinel keys, and every quaternion is unit
    norm within 1%. A trailing sentinel key (time <= 0) is common and is
    excluded from the monotonicity check.
    """
    problems: list[str] = []
    if not anm.bones:
        return ["no bones"]
    if anm.version != 1:
        problems.append(f"version {anm.version} != 1")
    for i, bone in enumerate(anm.bones):
        if not bone.keys:
            problems.append(f"bone {i}: no keys")
            continue
        times = [k.time for k in bone.keys if k.time > 0 and math.isfinite(k.time)]
        if any(a >= b for a, b in zip(times, times[1:])):
            problems.append(f"bone {i}: non-monotonic key times")
        for j, key in enumerate(bone.keys):
            qn = sum(x * x for x in key.quaternion)
            if abs(qn - 1.0) > 0.01:
                problems.append(f"bone {i} key {j}: quaternion norm {math.sqrt(qn):.3f}")
                break
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file")
    a = ap.parse_args(argv)
    try:
        anm = read_anm(Path(a.file).read_bytes())
    except ValueError as e:
        print(f"unsupported: {e}")
        return 1
    print(f"name={anm.name!r} bone={anm.bone!r} version={anm.version} "
          f"duration={anm.duration} rate={anm.rate} bones={len(anm.bones)} "
          f"keys={sum(len(b.keys) for b in anm.bones)} "
          f"first_time={anm.keys[0].time} last_time={anm.keys[-1].time}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
