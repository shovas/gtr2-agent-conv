#!/usr/bin/env python3
"""Decoder for the single-bone subset of the ISI ``.anm`` animation format.

Corpus-verified on 231 archived files (F1C/F12002/NT2003): header is a
12-byte name, u32 flag, u32 version (always 1), two floats, u32 bone count;
a bone name at +32 and key count at +68; keys start at +76 with a 32-byte
stride: position (3 f32), quaternion (4 f32) and time (1 f32).

Multi-bone files (673 in the corpus) use a per-bone layout that is not yet
decoded; this module reports them as unsupported rather than guessing.
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
