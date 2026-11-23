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
PTR4_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


@dataclass
class Waypoint:
    pos: tuple[float, float, float] | None = None
    bitfields: int | None = None
    branch_id: int | None = None
    ptrs: tuple[int, int, int, int] | None = None

    def wp_class(self) -> int | None:
        """WP_PTRS class field (index 3): 0=track, 1=pit, 2..105=grid, >=106=pitbox."""
        return self.ptrs[3] if self.ptrs is not None else None

    def kind(self) -> str | None:
        value = self.wp_class()
        if value is None:
            return None
        if value == 0:
            return "track"
        if value == 1:
            return "pit"
        return "grid" if value <= 105 else "pitbox"


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
                elif key == "wp_ptrs":
                    match = PTR4_RE.match(value)
                    if match:
                        waypoint.ptrs = tuple(int(match.group(i)) for i in (1, 2, 3, 4))
    return aiw


@dataclass
class Camera:
    name: str = ""
    kind: str = ""
    position: tuple[float, float, float] | None = None
    orientation: tuple[float, float, float] | None = None
    fov: tuple[float, float] | None = None
    clip_planes: tuple[float, float] | None = None
    activation_location: tuple[float, float, float] | None = None
    activation_radius: float | None = None
    tracking_rate: float | None = None

    def aiw_position(self) -> tuple[float, float, float] | None:
        """Camera X/Z use the opposite sign convention from AIW waypoints.

        Corpus-verified on 8 paired AIW/CAM tracks (GTL/GTR2/BMW/Race07):
        negating X and Z brings every camera measurably closer to the track's
        waypoints (ratios 1.4x-5.7x); the Y axis is unchanged.
        """
        if self.position is None:
            return None
        return (-self.position[0], self.position[1], -self.position[2])


@dataclass
class CamInfo:
    cameras: list[Camera] = field(default_factory=list)


_FLOAT_RE = re.compile(r"-?[\d.]+")


def _floats(value: str, count: int) -> tuple[float, ...] | None:
    found = _FLOAT_RE.findall(value)
    return tuple(float(x) for x in found[:count]) if len(found) >= count else None


def parse_cam(data: str) -> CamInfo:
    """Parse a SimBin .CAM file into camera records and their numeric fields."""
    info = CamInfo()
    current: Camera | None = None
    for line in data.splitlines():
        stripped = line.strip()
        header = re.match(r"^(StaticCam|TrackingCam|LocalCam)\s*=\s*(.*)$", stripped)
        if header:
            current = Camera(name=header.group(2).strip(), kind=header.group(1))
            info.cameras.append(current)
            continue
        if current is None:
            continue
        m = KEYVALUE_RE.match(stripped)
        if not m:
            continue
        key, value = m.group(1).strip().lower(), m.group(2).strip()
        if key == "position":
            current.position = _floats(value, 3)
        elif key == "orientation":
            current.orientation = _floats(value, 3)
        elif key == "fov":
            current.fov = _floats(value, 2)
        elif key == "clipplanes":
            current.clip_planes = _floats(value, 2)
        elif key == "activationlocation":
            current.activation_location = _floats(value, 3)
        elif key == "activationradius":
            v = _floats(value, 1)
            current.activation_radius = v[0] if v else None
        elif key == "trackingrate":
            v = _floats(value, 1)
            current.tracking_rate = v[0] if v else None
    return info


def validate_aiw_waypoints(aiw: AIW) -> list[str]:
    """Check corpus-verified waypoint invariants; return a list of problems.

    Verified on 30,710 waypoints across 26 AIW files (rF1/GTL/GTR2/Race07/
    BMW/F1 2002): ``WP_PTRS`` always has 4 fields, and its fourth field equals
    ``wp_branchID`` exactly. Its value buckets are 0=track, 1=pit, 2..105=grid,
    >=106=pitbox. The second field is normally the next waypoint index, but
    branch-start waypoints legitimately break that chain, so linkage is not
    enforced here.
    """
    problems: list[str] = []
    for i, wp in enumerate(aiw.waypoints):
        if wp.ptrs is None:
            problems.append(f"waypoint {i}: missing WP_PTRS")
            continue
        if len(wp.ptrs) != 4:
            problems.append(f"waypoint {i}: WP_PTRS has {len(wp.ptrs)} fields")
            continue
        if wp.branch_id is not None and wp.branch_id != wp.ptrs[3]:
            problems.append(f"waypoint {i}: branchID={wp.branch_id} != WP_PTRS[3]={wp.ptrs[3]}")
    return problems


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


# rFactor -> SimBin AIW conversion rules, documented by the freeware
# "AIW Repair Utility v1.0" in ../gtr2-tools (idea: petrs73, code: dhaman).
# SimBin games (GTR2/GTL/GTR Evolution) cap wp_galpha at 0.45 whereas rFactor
# uses 1.0; rFactor-only waypoint tags must be removed/replaced.
RFACTOR_ONLY_AIW_TAGS = frozenset({
    "wp_normal", "wp_vect", "wp_lockedalpha", "wp_test_speed", "wp_cheat",
    "wp_pathabstractionspeed", "wp_pathabstraction", "wp_wpse",
    "wp_lockedlats", "wp_multipathlat", "wp_translat", "wp_pitlane",
})
AIW_TAG_REPLACEMENTS = {"wp_cheat": "wp_event=(1.000,0,0)"}
GALPHA_SCALE = 0.45
_VEC1_RE = re.compile(r"^\s*\(\s*(-?[\d.]+)\s*\)\s*$")


def aiw_for_simbin(data: str) -> str:
    """Convert an rFactor-style AIW to SimBin conventions (text-level rules)."""
    out = []
    for line in data.splitlines(keepends=True):
        stripped = line.strip()
        m = KEYVALUE_RE.match(stripped)
        if not m:
            out.append(line)
            continue
        key, value = m.group(1).strip().lower(), m.group(2).strip()
        if key in AIW_TAG_REPLACEMENTS:
            indent = line[:len(line) - len(line.lstrip())]
            out.append(f"{indent}{AIW_TAG_REPLACEMENTS[key]}\n" if line.endswith("\n")
                       else f"{indent}{AIW_TAG_REPLACEMENTS[key]}")
            continue
        if key in RFACTOR_ONLY_AIW_TAGS:
            continue
        if key == "wp_galpha":
            scalar = _VEC1_RE.match(value)
            if scalar:
                scaled = float(scalar.group(1)) * GALPHA_SCALE
                prefix = line[:len(line) - len(stripped)]
                newline = "\n" if line.endswith("\n") else ""
                out.append(f"{prefix}wp_galpha=({scaled:.4f}){newline}")
                continue
        out.append(line)
    return "".join(out)


def _cmd_aiw(args: argparse.Namespace) -> int:
    aiw = parse_aiw(read_text(args.file))
    print(f"features: {len(aiw.features)}")
    for key, value in aiw.features.items():
        print(f"  {key} = {value}")
    print(f"waypoints: {len(aiw.waypoints)}")
    print(f"branches: {sorted(aiw.branches())}")
    for w in aiw.waypoints[:args.limit]:
        print(f"  pos={w.pos} branch={w.branch_id} ptrs={w.ptrs} kind={w.kind()}")
    problems = validate_aiw_waypoints(aiw)
    print(f"waypoint problems: {len(problems)}")
    for msg in problems[:args.limit]:
        print(f"  {msg}")
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


def _cmd_cam(args: argparse.Namespace) -> int:
    info = parse_cam(read_text(args.file))
    print(f"cameras: {len(info.cameras)}")
    kinds: dict[str, int] = {}
    for cam in info.cameras:
        kinds[cam.kind] = kinds.get(cam.kind, 0) + 1
    print(f"kinds: {kinds}")
    for cam in info.cameras[:args.limit]:
        print(f"  {cam.name} [{cam.kind}] pos={cam.position} aiw_pos={cam.aiw_position()} "
              f"fov={cam.fov} clip={cam.clip_planes}")
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
    p = sub.add_parser("cam", help="parse a SimBin .CAM file")
    p.add_argument("file")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=_cmd_cam)
    p = sub.add_parser("aiw-convert", help="apply rFactor->SimBin AIW text rules to stdout")
    p.add_argument("file")
    p.set_defaults(func=lambda a: print(aiw_for_simbin(read_text(a.file)), end=""))
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
