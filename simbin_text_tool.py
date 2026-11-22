#!/usr/bin/env python3
"""Semantic readers for SimBin text formats (AIW, SCN/TRK).

Standalone reimplementation of the parsing patterns in `../rfactortools`
(GPLv3, Ingo Ruhnke) — no code copied, no external dependencies. All files are
read as latin-1 with CRLF preserved; writers keep the original bytes.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

KEYVALUE_RE = re.compile(r"^\s*([^=]+)\s*=\s*(.*)\s*$")
VEC3_RE = re.compile(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")
INT1_RE = re.compile(r"\(\s*(-?\d+)\s*\)")


@dataclass
class Waypoint:
    pos: tuple[float, float, float] | None = None
    bitfields: int | None = None
    branch_id: int | None = None


@dataclass
class AIW:
    features: dict[str, str] = field(default_factory=dict)
    waypoints: list[Waypoint] = field(default_factory=list)

    def branches(self) -> set[int]:
        return {w.branch_id for w in self.waypoints if w.branch_id is not None}


@dataclass
class ScnInfo:
    search_path: list[str] = field(default_factory=list)
    mas_files: list[str] = field(default_factory=list)
    has_skyboxi: bool = False


def read_text(path: str | Path) -> str:
    return Path(path).read_bytes().decode("latin-1")


def parse_aiw(data: str) -> AIW:
    aiw = AIW()
    section = ""
    waypoint = None
    for line in data.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        m = KEYVALUE_RE.match(line)
        if not m:
            continue
        key, value = m.group(1).strip().lower(), m.group(2).strip()
        if section == "features":
            aiw.features[key] = value
        elif section == "waypoint":
            if key == "wp_pos":
                match = VEC3_RE.match(value)
                if match:
                    waypoint = Waypoint(pos=tuple(float(match.group(i)) for i in (1, 2, 3)))
                    aiw.waypoints.append(waypoint)
            elif waypoint is not None:
                if key == "wp_bitfields":
                    match = INT1_RE.match(value)
                    if match:
                        waypoint.bitfields = int(match.group(1))
                elif key == "wp_branchid":
                    match = INT1_RE.match(value)
                    if match:
                        waypoint.branch_id = int(match.group(1))
    return aiw


def parse_scn(data: str) -> ScnInfo:
    info = ScnInfo()
    section = 0
    for raw in data.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line == "{":
            section += 1
            continue
        if line == "}":
            section = max(0, section - 1)
            continue
        m = KEYVALUE_RE.match(line)
        if not m or section != 0:
            continue
        key, value = m.group(1).strip().lower(), m.group(2).strip()
        if key == "searchpath":
            info.search_path.append(value)
        elif key == "masfile":
            info.mas_files.append(value)
        elif key == "instance" and value.lower() == "skyboxi":
            info.has_skyboxi = True
    return info


def _cmd_aiw(args: argparse.Namespace) -> int:
    aiw = parse_aiw(read_text(args.file))
    print(f"features: {len(aiw.features)}")
    for key, value in aiw.features.items():
        print(f"  {key} = {value}")
    print(f"waypoints: {len(aiw.waypoints)}")
    print(f"branches: {sorted(aiw.branches())}")
    for w in aiw.waypoints[:args.limit]:
        print(f"  pos={w.pos} branch={w.branch_id} bits={w.bitfields}")
    return 0


def _cmd_scn(args: argparse.Namespace) -> int:
    info = parse_scn(read_text(args.file))
    print("search_path:")
    for p in info.search_path:
        print(f"  {p}")
    print("mas_files:")
    for f in info.mas_files:
        print(f"  {f}")
    print(f"skyboxi: {info.has_skyboxi}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("aiw")
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=_cmd_aiw)
    p = sub.add_parser("scn")
    p.add_argument("file")
    p.set_defaults(func=_cmd_scn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
