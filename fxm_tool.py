#!/usr/bin/env python3
"""Inspect SimBin FXM/FXA/LMA animation container files.

Observed magics: b'FXM ', b'FXA ', b'LMA ' (extension does not always match magic).
Header is partially understood; tool validates magic and reports observed fields.
Node/bone name strings can be extracted heuristically; internal record semantics unconfirmed.
Read/write is lossless at file-bytes level.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

MAGICS = {b"FXM ", b"FXA ", b"LMA "}


@dataclass
class FxmHeader:
    path: Path
    size: int
    magic: bytes
    v1: int
    v2: int
    f3: int
    f4: int
    f5: int
    f6: int

    @property
    def known_magic(self) -> bool:
        return self.magic in MAGICS

    @property
    def be_fields(self) -> tuple[int, int, int, int, int, int]:
        # Raw BE interpretation of bytes 4..28; observed plausible for some fields, but
        # some entries may overlap string/table data depending on format variant. Unconfirmed.
        b = Path(self.path).read_bytes()
        return struct.unpack_from(">HHIIII", b, 4)


def read_header(path: str | Path) -> FxmHeader:
    p = Path(path)
    b = p.read_bytes()
    if len(b) < 28:
        raise ValueError("file too small")
    magic, v1, v2, f3, f4, f5, f6 = struct.unpack_from("<4sHHIIII", b, 0)
    return FxmHeader(p, len(b), magic, v1, v2, f3, f4, f5, f6)


def _first_string_offset(b: bytes, min_len: int = 4) -> int | None:
    i = 0
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j < len(b) and b[j] == 0 and j - i >= min_len:
                return i
            i = j + 1
        else:
            i += 1
    return None


def parse_node_records(b: bytes) -> list[dict]:
    """Walk the contiguous skeleton-node table anchored on the `Bip01` record.

    Each record is `name (no NUL), u32 marker=1, u32 size_hint, u32 key_count=3,
    84 bytes of keyframe data`.  The keyframe block decodes as 2 TRS keys
    (see `decode_node_keys`).  Records are contiguous, so a sequential walk from the strong `Bip01\\x01\\x00\\x00\\x00` anchor avoids the
    false positives a free-standing name regex produces on 3ds Max metadata
    (e.g. build timestamps or material names).
    """
    out = []
    pos = b.find(b"Bip01\x01\x00\x00\x00")
    if pos < 0:
        return out
    while 0 <= pos < len(b):
        marker = b.find(b"\x01\x00\x00\x00", pos + 1)
        if marker < 0 or marker + 12 > len(b):
            break
        name = b[pos:marker]
        if not name or not all(32 <= c < 127 for c in name):
            break
        size_hint, key_count = struct.unpack_from("<II", b, marker + 4)
        if key_count != 3 or not (0x50 <= size_hint <= 0x80):
            break
        out.append({"offset": pos, "name": name.decode("ascii"),
                    "size_hint": size_hint, "key_count": key_count,
                    "keyframe_offset": marker + 12,
                    "keyframe_bytes": 84})
        pos = marker + 12 + 84
    return out


def decode_node_keys(b: bytes, node: dict) -> dict:
    """Decode a node's 84-byte keyframe block into TRS keys.

    Layout (validated across all 27 nodes of FU_PreIdle4-R.FXM): 2 keys of
    10 floats each (position xyz, rotation quaternion xyzw, scale xyz) plus a
    4-byte trailer.  Quaternion norms are ~1 in 54/54 keys and scale ~1 in
    52/54; the two keys are usually identical for static/rest-pose nodes.
    """
    ko = node["keyframe_offset"]
    f = struct.unpack_from("<21f", b, ko)
    keys = []
    for k in range(2):
        base = k * 10
        pos = list(f[base:base + 3])
        quat = list(f[base + 3:base + 7])
        scale = list(f[base + 7:base + 10])
        norm = math.sqrt(sum(x * x for x in quat))
        keys.append({"position": pos, "quaternion": quat,
                     "scale": scale, "quat_norm": norm})
    trailer = struct.unpack_from("<I", b, ko + 80)[0]
    return {"node": node["name"], "keys": keys, "trailer": trailer}


def check_node_consistency(b: bytes, node: dict) -> list[str]:
    """Return structural problems for one standard-format FXM node.

    Corpus-verified invariants (148/148 nodes across GTR2/Race07/Volvo/BMW):
      * keyframe block is always 84 bytes (two 10-float TRS keys + 4-byte trailer)
      * quaternion norms are unit length, scale is identity
      * the trailer u32 equals ``size_hint - 84`` (no exceptions)
    """
    problems = []
    if node["keyframe_bytes"] != 84:
        problems.append("keyframe block is not 84 bytes")
    dec = decode_node_keys(b, node)
    if node["size_hint"] - 84 != dec["trailer"]:
        problems.append(f"trailer {dec['trailer']} != size_hint-84 {node['size_hint'] - 84}")
    for i, key in enumerate(dec["keys"]):
        if not 0.9 < key["quat_norm"] < 1.1:
            problems.append(f"key {i}: non-unit quaternion {key['quat_norm']}")
        # Scale components are all +/-1 (one mirrored bone has (-1,-1,-1));
        # the vector norm is sqrt(3), not 1.
        if any(abs(abs(s) - 1.0) > 0.1 for s in key["scale"]):
            problems.append(f"key {i}: non-unit-component scale {key['scale']}")
    return problems


def parse_length_prefixed_nodes(b: bytes) -> list[dict]:
    """Decode length-prefixed bone records used by SimBin FXM files.

    Layout: ``u32 name_len, name, u32 marker=1, u32 size_hint, u32 key_count=3,
    two 40-byte TRS keys``. Unlike the standard variant the name is prefixed by
    its length and the file's root node may use a different marker, so the
    ``Bip01\\x01`` anchor in :func:`parse_node_records` finds nothing. Only
    ``Bip01``-prefixed bone names are accepted: corpus scans show plain
    length-prefixed strings also occur as 3ds Max metadata and material names.
    """
    out: list[dict] = []
    i = 0
    while i + 100 <= len(b):
        name_len = struct.unpack_from("<I", b, i)[0]
        if not (6 <= name_len <= 64):
            i += 1
            continue
        name_at = i + 4
        if name_at + name_len + 12 + 80 > len(b):
            i += 1
            continue
        name = b[name_at:name_at + name_len]
        if not name.startswith(b"Bip01") or not all(32 <= c < 127 for c in name):
            i += 1
            continue
        marker, size_hint, key_count = struct.unpack_from("<III", b, name_at + name_len)
        if marker != 1 or key_count != 3 or not (0x50 <= size_hint <= 0x80):
            i += 1
            continue
        keys_at = name_at + name_len + 12
        if not all(_valid_trs_key(b, keys_at + k * 40) for k in range(2)):
            i += 1
            continue
        out.append({"offset": i, "name": name.decode("ascii"),
                    "size_hint": size_hint, "key_count": key_count,
                    "keyframe_offset": keys_at, "keyframe_bytes": 84})
        # The four bytes after the two keys are the next record's name length.
        i = keys_at + 80
    return out


def _valid_trs_key(b: bytes, off: int) -> bool:
    if off + 40 > len(b):
        return False
    f = struct.unpack_from("<10f", b, off)
    q = math.sqrt(sum(x * x for x in f[3:7]))
    return 0.98 < q < 1.02 and all(0.9 < s < 1.1 for s in f[7:10])


def parse_rotation_track_nodes(b: bytes) -> list[dict]:
    """Decode marker=2 length-prefixed FXM nodes: rotation-only keyframe tracks.

    Layout: ``u32 name_len, name, u32 marker=2, u32 size_hint, u32 key_count=1,
    u32 frames, u32 unknown, frames × (f32 time, 4f32 quaternion)`` with
    ``size_hint == 8 + 20 * frames``. Corpus-verified on 532 nodes / 12,955
    keys in 26 GTR2 and Race 07 files: all quaternion norms are unit length
    and all time sequences are finite and monotonic.
    """
    out: list[dict] = []
    i = 0
    while i + 16 <= len(b):
        name_len = struct.unpack_from("<I", b, i)[0]
        if not (6 <= name_len <= 64):
            i += 1
            continue
        name_at = i + 4
        if name_at + name_len + 12 > len(b):
            i += 1
            continue
        name = b[name_at:name_at + name_len]
        if not name.startswith(b"Bip01") or not all(32 <= c < 127 for c in name):
            i += 1
            continue
        marker, size_hint, key_count = struct.unpack_from("<III", b, name_at + name_len)
        if marker != 2 or key_count != 1:
            i += 1
            continue
        keys_at = name_at + name_len + 12
        if keys_at + 8 > len(b):
            i += 1
            continue
        frames = struct.unpack_from("<I", b, keys_at)[0]
        if not (1 <= frames <= 1000) or 8 + 20 * frames != size_hint:
            i += 1
            continue
        if keys_at + size_hint > len(b):
            i += 1
            continue
        times: list[float] = []
        quats: list[list[float]] = []
        ok = True
        for k in range(frames):
            t, qx, qy, qz, qw = struct.unpack_from("<5f", b, keys_at + 8 + k * 20)
            qn = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
            if not (0.98 < qn < 1.02) or not math.isfinite(t):
                ok = False
                break
            times.append(t)
            quats.append([qx, qy, qz, qw])
        if not ok:
            i += 1
            continue
        out.append({"offset": i, "name": name.decode("ascii"),
                    "size_hint": size_hint, "frames": frames,
                    "times": times, "quaternions": quats})
        # A nameless standard TRS record follows each rotation track.
        i = keys_at + size_hint + 16
    return out


def parse_trailing_name_nodes(b: bytes) -> list[dict]:
    """Decode FXM nodes whose name follows the keyframe block.

    Layout: ``u32 marker=1, u32 size_hint, u32 key_count=3, two 40-byte TRS
    keys, u32 name_len, name``. The standard parser anchors on ``name + marker``
    and misses these; they occur in cockpit-wiper and driver animation files.
    Corpus-verified: recovers 90 previously zero-node files / 472 nodes with
    unit quaternion keys and printable names.
    """
    out: list[dict] = []
    for i in range(len(b) - 100):
        marker, size_hint, key_count = struct.unpack_from("<III", b, i)
        if marker != 1 or key_count != 3 or not (0x50 <= size_hint <= 0x80):
            continue
        keys_at = i + 12
        if not all(_valid_trs_key(b, keys_at + k * 40) for k in range(2)):
            continue
        name_len = struct.unpack_from("<I", b, keys_at + 80)[0]
        if not (3 <= name_len <= 64) or keys_at + 84 + name_len > len(b):
            continue
        name = b[keys_at + 84:keys_at + 84 + name_len]
        if not all(32 <= c < 127 for c in name) or name[:1].isdigit():
            continue
        out.append({"offset": i, "name": name.decode("latin-1"),
                    "size_hint": size_hint, "key_count": key_count,
                    "keyframe_offset": keys_at, "keyframe_bytes": 84})
    return out


def parse_single_key_nodes(b: bytes) -> list[dict]:
    """Decode FXM nodes with one validated key and a marker-dependent tail.

    Layout: ``u32 marker, u32 size_hint, u32 key_count=3, 40-byte TRS key,
    tail, u32 name_len, name``. Corpus-verified tail sizes are exactly 28 bytes
    for marker=0 (`.fxa` wipers) and 40 bytes for marker=1 (`.fxm` wipers whose
    second key has non-unit scale). Recovers 115 of 119 otherwise zero-node
    files / 280 nodes. The trailing floats are retained verbatim as ``tail``;
    their semantics are not claimed.
    """
    out: list[dict] = []
    for i in range(len(b) - 100):
        marker, size_hint, key_count = struct.unpack_from("<III", b, i)
        if key_count != 3 or not (60 <= size_hint <= 200):
            continue
        gap = 28 if marker == 0 else 40 if marker == 1 else -1
        if gap < 0:
            continue
        keys_at = i + 12
        if keys_at + 40 + gap + 4 > len(b):
            continue
        f = struct.unpack_from("<10f", b, keys_at)
        q = math.sqrt(sum(x * x for x in f[3:7]))
        if not (0.98 < q < 1.02) or not all(math.isfinite(x) for x in f):
            continue
        name_len_at = keys_at + 40 + gap
        name_len = struct.unpack_from("<I", b, name_len_at)[0]
        if not (3 <= name_len <= 64) or name_len_at + 4 + name_len > len(b):
            continue
        name = b[name_len_at + 4:name_len_at + 4 + name_len]
        if not all(32 <= c < 127 for c in name) or name[:1].isdigit():
            continue
        out.append({"offset": i, "name": name.decode("latin-1"), "marker": marker,
                    "size_hint": size_hint, "key_count": key_count,
                    "keyframe_offset": keys_at,
                    "tail": b[keys_at + 40:name_len_at],
                    "position": f[:3], "quaternion": f[3:7], "scale": f[7:10]})
    return out


def decode_fxm_semantic(b: bytes) -> dict:
    """Decode an FXM file into a layout-independent, validated node list.

    Both on-disk variants are normalised to the same representation:
      ``{variant, nodes: [{name, position, quaternion, scale, issues}], stats}``
    ``issues`` is empty for well-formed nodes; suspect nodes (e.g. NUL-variant
    records whose parser-selected keyframe offset yields non-unit scale) are
    retained but flagged instead of silently discarded.
    """
    std = parse_node_records(b)
    if std:
        nodes = []
        for node in std:
            dec = decode_node_keys(b, node)
            issues = [f"key {i}: non-unit quaternion" for i, k in enumerate(dec["keys"])
                      if abs(k["quat_norm"] - 1.0) > 0.01]
            for i, k in enumerate(dec["keys"]):
                if any(abs(abs(s) - 1.0) > 0.02 for s in k["scale"]):
                    issues.append(f"key {i}: non-unit scale")
            k0 = dec["keys"][0]
            nodes.append({"name": node["name"],
                          "position": k0["position"],
                          "quaternion": k0["quaternion"],
                          "scale": k0["scale"],
                          "key_count": len(dec["keys"]),
                          "issues": issues})
        return {"variant": "standard", "nodes": nodes,
                "stats": {"nodes": len(nodes),
                          "flagged": sum(1 for n in nodes if n["issues"])}}

    lp = parse_length_prefixed_nodes(b)
    if lp:
        nodes = []
        for node in lp:
            dec = decode_node_keys(b, node)
            k0 = dec["keys"][0]
            issues = [f"key {i}: non-unit quaternion" for i, k in enumerate(dec["keys"])
                      if abs(k["quat_norm"] - 1.0) > 0.01]
            nodes.append({"name": node["name"], "position": k0["position"],
                          "quaternion": k0["quaternion"], "scale": k0["scale"],
                          "key_count": len(dec["keys"]), "issues": issues})
        for track in parse_rotation_track_nodes(b):
            nodes.append({"name": track["name"], "kind": "rotation",
                          "position": None, "quaternion": track["quaternions"][0],
                          "scale": None, "key_count": track["frames"],
                          "times": track["times"],
                          "rotation_quaternions": track["quaternions"],
                          "issues": []})
        return {"variant": "length-prefixed", "nodes": nodes,
                "stats": {"nodes": len(nodes),
                          "rotation_tracks": sum(1 for n in nodes if n.get("kind") == "rotation"),
                          "flagged": sum(1 for n in nodes if n["issues"])}}

    trailing = parse_trailing_name_nodes(b)
    if trailing:
        nodes = []
        for node in trailing:
            dec = decode_node_keys(b, node)
            k0 = dec["keys"][0]
            issues = [f"key {i}: non-unit quaternion" for i, k in enumerate(dec["keys"])
                      if abs(k["quat_norm"] - 1.0) > 0.01]
            for i, k in enumerate(dec["keys"]):
                if any(abs(abs(s) - 1.0) > 0.02 for s in k["scale"]):
                    issues.append(f"key {i}: non-unit scale")
            nodes.append({"name": node["name"], "position": k0["position"],
                          "quaternion": k0["quaternion"], "scale": k0["scale"],
                          "key_count": len(dec["keys"]), "issues": issues})
        return {"variant": "trailing-name", "nodes": nodes,
                "stats": {"nodes": len(nodes),
                          "flagged": sum(1 for n in nodes if n["issues"])}}

    single = parse_single_key_nodes(b)
    if single:
        nodes = []
        for n in single:
            issues = []
            if any(abs(abs(s) - 1.0) > 0.02 for s in n["scale"]):
                issues.append("non-unit scale")
            nodes.append({"name": n["name"], "position": n["position"],
                          "quaternion": n["quaternion"], "scale": n["scale"],
                          "key_count": 1, "issues": issues})
        return {"variant": "single-key", "nodes": nodes,
                "stats": {"nodes": len(nodes),
                          "flagged": sum(1 for n in nodes if n["issues"])}}

    nul = parse_nul_name_nodes(b)
    nodes = []
    for n in nul:
        issues = []
        if abs(math.sqrt(sum(x * x for x in n["quaternion"])) - 1.0) > 0.01:
            issues.append("non-unit quaternion")
        if any(abs(abs(s) - 1.0) > 0.02 for s in n["scale"]):
            issues.append("non-unit scale")
        nodes.append({"name": n["name"], "position": n["position"],
                      "quaternion": n["quaternion"], "scale": n["scale"],
                      "key_count": 1, "issues": issues})
    return {"variant": "nul", "nodes": nodes,
            "stats": {"nodes": len(nodes),
                      "flagged": sum(1 for n in nodes if n["issues"])}}


def cmd_info(args: argparse.Namespace) -> int:
    h = read_header(args.file)
    b = Path(args.file).read_bytes()
    strings = [s.decode("latin-1", "replace") for s in b.split(b"\x00") if len(s) > 4 and all(32 <= c < 127 or c in (9, 10, 13) for c in s[:20])]
    first = _first_string_offset(b)
    print(f"path: {h.path}")
    print(f"size: {h.size}")
    print(f"magic: {h.magic!r}")
    print(f"known_magic: {h.known_magic}")
    print(f"header_u16_le: {h.v1} {h.v2}")
    print(f"header_u32_le: {h.f3} {h.f4} {h.f5} {h.f6}")
    be = h.be_fields
    print(f"header_be: {be[0]} {be[1]} {be[2]} {be[3]} {be[4]} {be[5]}")
    print(f"sha256: {hashlib.sha256(b).hexdigest()}")
    print(f"first_string_offset: {first}")
    for s in strings[:8]:
        print(f"string: {s[:120]}")
    return 0


def extract_strings(b: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j < len(b) and b[j] == 0 and j - i >= min_len:
                out.append((i, b[i:j].decode('latin-1', 'replace')))
            i = j + 1
        else:
            i += 1
    return out


def cmd_nodes(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    for off, s in extract_strings(b):
        # heuristic: bone/node names often contain Bip01, Driver, or spaces/underscores
        if args.all or any(k in s for k in ('Bip01', 'Driver', 'Bone', 'Node')):
            print(f'{off}\t{s}')
    return 0


def build_node_id_map(nodes: list[dict]) -> dict[str, int]:
    """Map node name -> its stable integer id (size_hint - 84).

    Verified across 148 nodes in 91 files: every one of 27 distinct names maps
    to exactly one id, so this is a name-stable bone id assigned by the
    exporter, not per-file data. It equals the 4-byte trailer decoded by
    `decode_node_keys()`.
    """
    out: dict[str, int] = {}
    for node in nodes:
        value = node["size_hint"] - 84
        if node["name"] in out and out[node["name"]] != value:
            raise ValueError(f"inconsistent node id for {node['name']}")
        out[node["name"]] = value
    return out


def parse_nul_name_nodes(data: bytes) -> list[dict]:
    """Parse the FXM variant with NUL-terminated node names and 1 TRS keyframe.

    Observed in `LMA `-magic files (e.g. FPDRIVER_Vectra-SteerL_01.FXM): each
    node is `name\\0, ~40 bytes header, 40-byte TRS key (pos, quat, scale),
    12-byte trailer (1, 0x50, 1)`. Validated on 69/79 nodes with a unit
    quaternion at name_offset+52.
    """
    import re
    import math as _math
    out = []
    for m in re.finditer(rb"[A-Za-z][A-Za-z0-9 _\-]{2,40}\x00", data):
        off = m.start()
        # Keyframe offset varies by file: try common positions relative to name.
        # Several deltas can yield a plausible-looking quaternion. Require
        # scale components near +/-1 as well (corpus-verified for genuine
        # nodes), then prefer the candidate with the smallest scale error.
        # This rejects false name matches inside longer strings.
        found = None
        for delta in (40, 80, 44, 76):
            ks = off + delta
            if ks + 40 > len(data):
                continue
            f = struct.unpack_from("<10f", data, ks)
            norm = _math.sqrt(sum(x * x for x in f[3:7]))
            if not (_math.isfinite(norm) and 0.9 < norm < 1.1):
                continue
            if not all(_math.isfinite(s) and abs(abs(s) - 1.0) < 0.02
                       for s in f[7:10]):
                continue
            penalty = sum(abs(abs(s) - 1.0) for s in f[7:10])
            if found is None or penalty < found[3]:
                found = (ks, f, norm, penalty)
        if found is None:
            continue
        ks, f, norm, _penalty = found
        out.append({"offset": off, "name": m.group().rstrip(b"\0").decode("latin-1"),
                    "keyframe_offset": ks, "position": f[:3],
                    "quaternion": f[3:7], "scale": f[7:10], "quat_norm": norm})
    return out


def cmd_keys(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    for node in parse_node_records(b):
        dec = decode_node_keys(b, node)
        print(f"{node['offset']}\t{node['name']}\tkeys={len(dec['keys'])}"
              f"\tid={node['size_hint'] - 84}")
        for i, key in enumerate(dec["keys"]):
            pos = ",".join(f"{x:g}" for x in key["position"])
            quat = ",".join(f"{x:g}" for x in key["quaternion"])
            print(f"  key{i}\tpos=({pos})\tquat=({quat})\tnorm={key['quat_norm']:.4f}")
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    Path(args.out).write_bytes(b)
    return 0


def cmd_semantic(args: argparse.Namespace) -> int:
    b = Path(args.file).read_bytes()
    doc = decode_fxm_semantic(b)
    print(f"variant={doc['variant']} nodes={doc['stats']['nodes']} "
          f"flagged={doc['stats']['flagged']}")
    for n in doc["nodes"][:args.limit]:
        issues = (" issues=" + ",".join(n["issues"])) if n["issues"] else ""
        print(f"  {n['name'][:32]:33s} keys={n['key_count']}{issues}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)
    p = sub.add_parser("nodes", help="extract likely node/bone names (heuristic)")
    p.add_argument("file")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_nodes)
    p = sub.add_parser("keys", help="decode skeleton node TRS keyframes")
    p.add_argument("file")
    p.set_defaults(func=cmd_keys)
    p = sub.add_parser("roundtrip", help="lossless byte copy")
    p.add_argument("file")
    p.add_argument("out")
    p.set_defaults(func=cmd_roundtrip)
    p = sub.add_parser("semantic", help="decode and validate FXM node semantics")
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_semantic)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
