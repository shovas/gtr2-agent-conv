#!/usr/bin/env python3
"""Semantic readers for SimBin text formats (AIW, SCN/TRK).

Standalone reimplementation of the parsing patterns in `../rfactortools`
(GPLv3, Ingo Ruhnke) — no code copied, no external dependencies. All files are
read as latin-1 with CRLF preserved; writers keep the original bytes.
"""
from __future__ import annotations

import argparse
import math
import re
import struct
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
    path: tuple[float, float] | None = None
    score_checkpoint: int | None = None
    score_distance: float | None = None
    perp: tuple[float, float, float] | None = None

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
                elif key == "wp_perp":
                    match = VEC3_RE.match(value)
                    if match:
                        waypoint.perp = tuple(float(match.group(i)) for i in (1, 2, 3))
                elif key == "wp_ptrs":
                    match = PTR4_RE.match(value)
                    if match:
                        waypoint.ptrs = tuple(int(match.group(i)) for i in (1, 2, 3, 4))
                elif key == "wp_path":
                    match = re.match(r"\(\s*([^,]+),\s*([^)]+)\)", value)
                    if match:
                        try:
                            waypoint.path = (float(match.group(1)), float(match.group(2)))
                        except ValueError:
                            pass
                elif key == "wp_score":
                    parts = value.split(",")
                    if parts:
                        try:
                            waypoint.score_checkpoint = int(float(parts[0].strip("() ")))
                        except ValueError:
                            pass
                    if len(parts) > 1:
                        try:
                            waypoint.score_distance = float(parts[1].strip("() "))
                        except ValueError:
                            pass
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
    movement_rate: float | None = None
    shake_rate: float | None = None
    shake_magnitude: float | None = None
    flags1: int | None = None
    flags2: int | None = None

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
        elif key == "movementrate":
            v = _floats(value, 1)
            current.movement_rate = v[0] if v else None
        elif key == "shakerate":
            v = _floats(value, 1)
            current.shake_rate = v[0] if v else None
        elif key == "shakemagnitude":
            v = _floats(value, 1)
            current.shake_magnitude = v[0] if v else None
        elif key in ("flags1", "flags2"):
            v = _floats(value, 1)
            if v:
                setattr(current, key, int(v[0]))
    return info


def validate_cam(info: CamInfo) -> list[str]:
    """Check corpus-verified CAM invariants; return a list of problems.

    Verified on 1,153 cameras across GTR2/GTL/Race07: ActivationRadius is
    always a positive integer (1,153/1,153; 635 are multiples of five). The
    "deactivated camera" encoding is an exact
    biconditional — all 23 cameras whose ActivationLocation is an FLT_MAX
    triplet have ActivationRadius=1, and no other camera has radius 1. The
    Turbo Basic reference documents a 99999 sentinel instead; that value does
    not occur locally, so both encodings are accepted here.
    """
    problems: list[str] = []
    for i, cam in enumerate(info.cameras):
        radius = cam.activation_radius
        if radius is not None and (radius <= 0 or abs(radius - round(radius)) > 1e-6):
            problems.append(f"camera {i}: ActivationRadius {radius} is not a positive integer")
        location = cam.activation_location
        if location is None:
            continue
        sentinel = all(x > 1e30 for x in location) or all(abs(x - 99999) < 1 for x in location)
        if sentinel and radius is not None and radius != 1:
            problems.append(f"camera {i}: deactivated sentinel with ActivationRadius {radius}")
        if not sentinel and radius == 1:
            problems.append(f"camera {i}: ActivationRadius=1 without deactivation sentinel")
    return problems


def validate_aiw_waypoints(aiw: AIW) -> list[str]:
    """Check corpus-verified waypoint invariants; return a list of problems.

    Verified on 30,710 waypoints across 26 AIW files (rF1/GTL/GTR2/Race07/
    BMW/F1 2002): ``WP_PTRS`` always has 4 fields, and its fourth field equals
    ``wp_branchID`` exactly. Its value buckets are 0=track, 1=pit, 2..105=grid,
    >=106=pitbox. ``wp_bitfields`` is 0 for track/pit and 1 for all other
    classes (30,710/30,710), and the first field of ``wp_score`` is a checkpoint
    in 0..2 (30,710/30,710). The second field is normally the next waypoint
    index, but branch-start waypoints legitimately break that chain, so linkage
    is not enforced here.
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
        if wp.bitfields is not None:
            expected = 0 if wp.ptrs[3] in (0, 1) else 1
            if wp.bitfields != expected:
                problems.append(f"waypoint {i}: bitfields={wp.bitfields} != {expected} "
                                f"for class {wp.ptrs[3]}")
        if wp.score_checkpoint is not None and wp.score_checkpoint not in (0, 1, 2):
            problems.append(f"waypoint {i}: wp_score checkpoint {wp.score_checkpoint} "
                            "outside 0..2")
        if wp.perp is not None and wp.ptrs[3] in (0, 1):
            norm = math.sqrt(sum(x * x for x in wp.perp))
            if abs(norm - 1.0) > 0.01:
                problems.append(f"waypoint {i}: track/pit wp_perp norm {norm:.4f} != 1")
    return problems


def aiw_lap_distance_coherence(aiw: AIW) -> float | None:
    """Fraction of non-decreasing lap distances within contiguous track runs.

    ``WP_SCORE``'s second field is lap distance. Across 464 AIWs from eight
    corpora, class-0 (track) waypoints are non-decreasing in 332,656/333,117
    adjacent pairs (99.86%); decreases are lap-wrap discontinuities at run
    starts. This is calibrated evidence, not a strict waypoint-order rule.
    """
    runs: list[list[float]] = []
    current: list[float] = []
    for wp in aiw.waypoints:
        if wp.wp_class() == 0 and wp.score_distance is not None:
            current.append(wp.score_distance)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    pairs = [(a, b) for run in runs for a, b in zip(run, run[1:])]
    return sum(1 for a, b in pairs if b >= a) / len(pairs) if pairs else None


def validate_aiw_pointers(aiw: AIW) -> list[str]:
    """Check corpus-verified waypoint pointer/path bounds.

    Verified on 457,832 waypoints across 465 AIWs from eight corpora
    (Race07Vanilla, GTLSteam, GTR2Steam, Race07Complete, RF1Vanilla,
    Automobilista, StockCarExtreme, F1 2002): every pointer is either -1
    ("no link") or a valid waypoint index, and ``wp_path`` always carries two
    finite lateral offsets with |value| < 100. Pointer 2 is -1 in a large
    minority of records; pointers 0/1 are -1 in only 7 records, all in the
    addon track ``Hill.AIW``.
    """
    problems: list[str] = []
    count = len(aiw.waypoints)
    for i, wp in enumerate(aiw.waypoints):
        if wp.ptrs is not None:
            for j in range(3):
                value = wp.ptrs[j]
                if value != -1 and not (0 <= value < count):
                    problems.append(f"waypoint {i}: pointer {j} {value} out of range")
                    return problems
        if wp.path is not None:
            if len(wp.path) != 2 or not all(math.isfinite(x) and abs(x) < 100
                                           for x in wp.path):
                problems.append(f"waypoint {i}: invalid wp_path {wp.path}")
                return problems
    return problems


def parse_veh(data: bytes | str) -> dict[str, str]:
    """Parse an rFactor ``.veh`` vehicle descriptor into key/value strings.

    Corpus-verified on 2,763 files (57 distinct keys): ``Graphics`` is present
    in all of them, and ``Classes``/``Driver``/``Number``/``Team``/``Sounds``/
    ``HDVehicle`` in all but 2. Values are de-quoted and trailing ``//``
    comments are stripped; quoted ``//`` inside a value is preserved.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", stripped)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2)
        if value.startswith('"'):
            end = value.find('"', 1)
            if end >= 0:
                value = value[1:end]
            else:
                value = value.split("//", 1)[0].strip()
        else:
            value = value.split("//", 1)[0].strip()
        out[key] = value
    return out


@dataclass
class ConfigInfo:
    values: dict[str, str] = field(default_factory=dict)
    keys: set[str] = field(default_factory=set)
    sections: set[str] = field(default_factory=set)


def _parse_config(data: bytes | str) -> ConfigInfo:
    """Shared key/value + [SECTION] parser for .gdb/.car text configs."""
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = ConfigInfo()
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        if not code:
            continue
        m = re.match(r"^\[([^\]]+)\]$", code)
        if m:
            info.sections.add(m.group(1).strip().lower())
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", code)
        if m:
            key = m.group(1).lower()
            info.keys.add(key)
            info.values[key] = m.group(2).strip().strip('"')
    return info


def parse_gdb(data: bytes | str) -> ConfigInfo:
    """Parse a `.gdb` race/event config into keys and named sections.

    Corpus-verified on 1,280 files: 667 distinct keys and no cross-corpus
    universal key; only family-specific universals exist (e.g. `racelaps` in
    81/81 rF1 `.gdb`). Pass decrypted bytes for JCA-wrapped files.
    """
    return _parse_config(data)


def parse_car(data: bytes | str) -> ConfigInfo:
    """Parse a `.car` vehicle config into its key/value pairs.

    Corpus-verified on 3,385 files: 173 distinct keys, no cross-corpus
    universal; GTR2-family files (165) all carry `genstring`, `pitgroup`,
    `number`, `driver1` and `team` (the existing GTR2-only key set).
    """
    return _parse_config(data)


def validate_config(info: ConfigInfo) -> list[str]:
    """Structural validation for generic .gdb/.car configs."""
    problems: list[str] = []
    # Zero-length .gdb fixtures exist in ../rfactortools/tests/data, so an
    # empty config is structurally valid; only malformed keys are flagged.
    if any(not re.match(r"^[A-Za-z_]\w*$", k) for k in info.keys):
        problems.append("malformed key name")
    return problems


@dataclass
class AudInfo:
    values: dict[str, list[str]] = field(default_factory=dict)
    path_keys: set[str] = field(default_factory=set)
    numeric_keys: set[str] = field(default_factory=set)


def parse_aud(data: bytes | str) -> AudInfo:
    """Parse a SimBin ``.aud`` sound-event map (JCA or plain).

    Corpus-verified on 360 files (plain and JCA-wrapped) with 80,821 mappings:
    193 distinct keys split cleanly into 139 path-valued and 34 numeric-valued
    keys — **no key mixes the two**. Path values always use backslashes and
    may carry a ``time,path`` prefix. Pass decrypted bytes for JCA files (see
    ``media_tool.decrypt_jca_text``).
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = AudInfo()
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-z_][\w]*)\s*=\s*([^\r\n]+)", line)
        if not m:
            continue
        key = m.group(1).lower()
        value = m.group(2).split("//", 1)[0].strip().strip('"')
        info.values.setdefault(key, []).append(value)
        if "\\" in value:
            info.path_keys.add(key)
        elif re.fullmatch(r"[+-]?[\d.eE]+", value):
            info.numeric_keys.add(key)
    return info


def validate_aud_map(info: AudInfo) -> list[str]:
    """Check corpus-verified .aud invariants; return a list of problems."""
    problems: list[str] = []
    for key in sorted(info.path_keys & info.numeric_keys):
        problems.append(f"key {key} mixes path and numeric values")
    for key in info.path_keys:
        for value in info.values[key]:
            if "/" in value and "\\" not in value:
                problems.append(f"key {key}: forward-slash path {value}")
    return problems


DMG_UNIVERSAL_KEYS = frozenset((
    "activateinstance",
    "aerodiv",
    "aeromin",
    "deactivateinstance",
    "defaultlimit",
    "engine",
    "frontwingcollparams",
    "frontwingdetach",
    "frontwingmassinertia",
    "frontwingpos",
    "frontwingrandom",
    "part0collparams",
    "part0detach",
    "part0massinertia",
    "part0pos",
    "part0random",
    "part2collparams",
    "part2detach",
    "part2massinertia",
    "part2pos",
    "part2random",
    "radiatorcoverinstance",
    "radiusadd",
    "radiusmax",
    "radiusmult",
    "rearwingcollparams",
    "rearwingdetach",
    "rearwingmassinertia",
    "rearwingpos",
    "rearwingrandom",
    "vertmult",
    "wallskidthresh",
    "wheel0collparams",
    "wheel0massinertia",
    "wheel1collparams",
    "wheel1massinertia",
    "wheel2collparams",
    "wheel2massinertia",
    "wheel3collparams",
    "wheel3massinertia",
    "wheelbend",
    "wheeldetach",
    "wheelrandom",
))


def parse_dmg(data: bytes | str) -> ConfigInfo:
    """Parse an rFactor/GTR2 ``.dmg`` damage config.

    Corpus-verified on 200 files (plain and JCA-wrapped): 102 distinct keys,
    43 of which are universal across every file (collision params, instance
    names, radius multipliers). Pass decrypted bytes for JCA files.
    """
    return _parse_config(data)


def validate_dmg(info: ConfigInfo) -> list[str]:
    """Check corpus-verified .dmg invariants; return a list of problems."""
    return [f"missing {key}" for key in sorted(DMG_UNIVERSAL_KEYS)
            if key not in info.keys]


CIN_EVENT_TYPES = frozenset((
    "CAMERA_SELECT", "WAIT", "CAMERA_SET_LAST", "CAMERA_ACQUIRE_CONTROL",
    "SCRIPT_END", "GRIDWALK", "COMMENTARY_START",
))


@dataclass
class CinEvent:
    type: str = ""
    probability: str = ""
    time: str = ""
    iterations: str = ""
    wait: str = ""
    camera: str = ""
    commentary: str = ""


@dataclass
class CinInfo:
    sections: list[str] = field(default_factory=list)
    events: list[CinEvent] = field(default_factory=list)


def parse_cin(data: bytes | str) -> CinInfo:
    """Parse an rFactor ``.cin`` cinematic script into its events.

    Corpus-verified on 409 files (5,798 ``CinematicEvent`` blocks): every
    event carries Type/Probability/Time/Iterations. ``Probability`` is 1.00 and
    ``Iterations`` is 1 in all 5,798; ``Type`` is drawn from a closed set of 7
    values, ``Wait`` is YES/NO, and ``Time`` is a non-negative ``+N`` offset.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = CinInfo()
    current: CinEvent | None = None
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        if not code:
            continue
        if code == "CinematicEvent":
            current = CinEvent()
            info.events.append(current)
            continue
        if not code.startswith("CinematicEvent") and code.endswith("Presentation"):
            info.sections.append(code)
            continue
        if current is None:
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", code)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2).strip().strip('"')
        if hasattr(current, key):
            setattr(current, key, value)
    return info


def validate_cin(info: CinInfo) -> list[str]:
    """Check corpus-verified .cin invariants; return a list of problems."""
    problems: list[str] = []
    if not info.sections:
        problems.append("no presentation section")
    for i, event in enumerate(info.events):
        for field in ("type", "probability", "time", "iterations"):
            if not getattr(event, field):
                problems.append(f"event {i}: missing {field}")
        if event.type and event.type not in CIN_EVENT_TYPES:
            problems.append(f"event {i}: unknown Type {event.type}")
        if event.probability and event.probability != "1.00":
            problems.append(f"event {i}: Probability {event.probability} != 1.00")
        if event.iterations and event.iterations != "1":
            problems.append(f"event {i}: Iterations {event.iterations} != 1")
        if event.wait and event.wait not in ("YES", "NO"):
            problems.append(f"event {i}: Wait {event.wait} not YES/NO")
    return problems


@dataclass
class ScrActor:
    name: str = ""
    detail: str = ""
    position: tuple[float, ...] | None = None
    mesh: str = ""
    move: str = ""
    parent: str = ""


@dataclass
class ScrInfo:
    actors: list[ScrActor] = field(default_factory=list)


def parse_scr(data: bytes | str) -> ScrInfo:
    """Parse an rFactor ``.scr`` scene script into its Actor blocks.

    Corpus-verified on 123 files (1,998 ``Actor`` blocks): every actor has
    Detail, Position and Mesh; Move (1,959) and Parent (1,816) are optional.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = ScrInfo()
    actor: ScrActor | None = None
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        if not code:
            continue
        m = re.match(r'^Actor\s+"([^"]*)"', code)
        if m:
            actor = ScrActor(name=m.group(1))
            info.actors.append(actor)
            continue
        if actor is None:
            continue
        m = re.match(r"^(Detail|Position|Mesh|Move|Parent)\s+(.*)$", code)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2).strip()
        if key == "position":
            actor.position = _all_floats(value)
        elif key == "detail":
            actor.detail = value
        elif key == "mesh":
            actor.mesh = value.strip('"')
        elif key == "move":
            actor.move = value
        elif key == "parent":
            actor.parent = value.strip('"')
    return info


def validate_scr(info: ScrInfo) -> list[str]:
    """Check corpus-verified .scr invariants; return a list of problems."""
    problems: list[str] = []
    for i, actor in enumerate(info.actors):
        for field in ("detail", "position", "mesh"):
            if not getattr(actor, field):
                problems.append(f"actor {i}: missing {field}")
    return problems


ENG_UNIVERSAL_KEYS = (
    "startertiming", "enginemaprange", "launchrpmlogic", "revlimitlogic",
    "rpmtorque", "lifetimeenginerpm", "lifetimeoiltemp", "fuelestimate",
    "engineinertia", "idlerpmlogic", "radiatorcooling", "fuelconsumption",
    "idlethrottle", "oilwaterheattransfer", "launchefficiency",
    "enginemapsetting", "enginebrakingmapsetting", "onboardstarter",
    "lifetimeavg", "optimumoiltemp", "combustionheat", "waterminimumcooling",
    "enginebrakingmaprange", "engineemission", "lifetimevar",
    "oilminimumcooling", "revlimitrange", "enginespeedheat",
)


@dataclass
class EngInfo:
    torque_curve: list[tuple[float, float, float]] = field(default_factory=list)
    values: dict[str, str] = field(default_factory=dict)
    keys: set[str] = field(default_factory=set)


def parse_eng(data: bytes | str) -> EngInfo:
    """Parse an rFactor/GTR2 ``.eng`` engine file.

    Corpus-verified on 333 files (plain and JCA-wrapped): 28 scalar keys are
    universal and every file has an ``RPMTorque`` curve with strictly
    increasing RPM values (verified in all 333). Each curve point is
    ``(rpm, friction_torque, torque)``; pass decrypted bytes for JCA files.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = EngInfo()
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        m = re.match(r"^RPMTorque\s*=\s*\(([^)]*)\)", code, re.I)
        if m:
            info.keys.add("rpmtorque")
            nums = _all_floats(m.group(1))
            if nums and len(nums) >= 3:
                info.torque_curve.append((nums[0], nums[1], nums[2]))
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", code)
        if m:
            key = m.group(1).lower()
            info.keys.add(key)
            info.values[key] = m.group(2).strip().strip('"')
    return info


def validate_eng(info: EngInfo) -> list[str]:
    """Check corpus-verified .eng invariants; return a list of problems."""
    problems: list[str] = []
    for required in ENG_UNIVERSAL_KEYS:
        if required not in info.keys:
            problems.append(f"missing {required}")
    if not info.torque_curve:
        problems.append("no RPMTorque points")
    rpms = [p[0] for p in info.torque_curve]
    if any(a >= b for a, b in zip(rpms, rpms[1:])):
        problems.append("RPMTorque RPM values not strictly increasing")
    return problems


@dataclass
class GrbInfo:
    gear_ratios: list[tuple[int, int]] = field(default_factory=list)
    final_ratio: tuple[int, int] | None = None
    bevel: tuple[int, int] | None = None
    sections: set[str] = field(default_factory=set)


def parse_grb(data: bytes | str) -> GrbInfo:
    """Parse an ISIMotor ``.grb`` gearbox-ratio file.

    Corpus-verified on 248 files (171 plain, 77 JCA-wrapped): all carry
    ``[GEAR_RATIOS]`` and ``[FINAL_DRIVE]``. Gear ratios are ``(a,b)`` tooth
    pairs whose effective ratio is **b/a** — verified against the inline
    decimal comments on 214/214 commented ratios. Bevel defaults to (1,1)
    in 155/171 plain files.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = GrbInfo()
    section = ""
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        m = re.match(r"^\[([^\]]+)\]$", code)
        if m:
            section = m.group(1).strip().upper()
            info.sections.add(section)
            continue
        m = re.match(r"^(ratio|bevel)\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", code, re.I)
        if not m:
            continue
        pair = (int(m.group(2)), int(m.group(3)))
        if m.group(1).lower() == "ratio":
            if section == "GEAR_RATIOS":
                info.gear_ratios.append(pair)
            elif section == "FINAL_DRIVE":
                info.final_ratio = pair
        elif m.group(1).lower() == "bevel" and section == "FINAL_DRIVE":
            info.bevel = pair
    return info


def validate_grb(info: GrbInfo) -> list[str]:
    """Check corpus-verified .grb invariants; return a list of problems."""
    problems: list[str] = []
    for required in ("GEAR_RATIOS", "FINAL_DRIVE"):
        if required not in info.sections:
            problems.append(f"missing [{required}]")
    if not info.gear_ratios:
        problems.append("no gear ratios")
    for i, (a, b) in enumerate(info.gear_ratios):
        if a == 0 or b == 0:
            problems.append(f"gear {i}: zero tooth count")
    if info.final_ratio is None:
        problems.append("missing final drive ratio")
    if info.bevel is None:
        problems.append("missing bevel")
    elif info.bevel == (0, 0):
        problems.append("zero bevel")
    return problems


RF1_GDB_CORE_KEYS = frozenset(("attrition", "dayambientrgb", "daydirectionalrgb", "dayfogrgb", "eventname", "garagedepth", "grandprixname", "latitude", "length", "location", "nightambientrgb", "nightdirectionalrgb", "nightfogrgb", "northdirection", "racedate", "settingsai", "settingsfolder", "shadowminsunangle", "sunriseambientrgb", "sunrisedirectionalrgb", "sunrisefogrgb", "sunsetambientrgb", "sunsetdirectionalrgb", "sunsetfogrgb", "terraindatafile", "trackname", "tracktype", "venuename", ))
RF1_CAM_CORE_KEYS = frozenset(("center", "clear", "clipplanes", "color", "flags1", "flags2", "fov", "lodmultiplier", "mipmaplodbias", "size", ))
RF1_AIW_CORE_KEYS = frozenset(("aibrakingstiffness", "aidraftstickiness", "airange", "aispec", "autogenaltgrid", "autogengrid", "auxspots", "bestadjust", "delaypitcrewload", "drivinglines", "fogdensity", "fueluse", "garagespots", "garori", "garpos", "gridindex", "grooveheightoffset", "groovewidth", "groovewidthwet", "intermediatefogcolor", "intermediatefoglevel", "intermediatefogplanes", "lanespacing", "lap_length", "lefthandedpits", "locationindex", "midadjust", "multilinetimes", "number_waypoints", "ori", "pitlanepaths", "pitlanes", "pitori", "pitpos", "pitspots", "pos", "rainydarkness", "rainyfogcolor", "rainyfogplanes", "safetycarreleasedist", "sector_1_length", "sector_2_length", "slowwhenpushed", "startinggrid", "teamindex", "teleportwp", "times", "trackstate", "ultracarefulyellow", "worstadjust", "wp_bitfields", "wp_branchid", "wp_cheat", "wp_dwidth", "wp_galpha", "wp_groove_lat", "wp_lockedalpha", "wp_lockedlats", "wp_multipathlat", "wp_normal", "wp_path", "wp_perp", "wp_pitlane", "wp_pos", "wp_ptrs", "wp_score", "wp_test_speed", "wp_vect", "wp_width", "wp_wpse", ))


def validate_rf1_config(keys: set[str], ext: str) -> list[str]:
    """Validate universal keys of an rF1-era .gdb/.cam/.aiw config."""
    needed = {".gdb": RF1_GDB_CORE_KEYS, ".cam": RF1_CAM_CORE_KEYS,
              ".aiw": RF1_AIW_CORE_KEYS}.get(ext)
    if needed is None:
        raise ValueError(f"unsupported config extension {ext}")
    return [f"missing {ext} key {key}" for key in sorted(needed) if key not in keys]


RFM_UNIVERSAL_KEYS = frozenset((
    "basecreditmult",
    "driveanyunlocked",
    "fineexpmult",
    "finemoneymult",
    "lapexpmult",
    "lapmoneymult",
    "loading bar color",
    "matchmaker",
    "matchmaker tcp port",
    "matchmaker udp port",
    "max opponents",
    "min championship opponents",
    "mod name",
    "pitgroup",
    "pointscareerexpmult",
    "pointscareermoneymult",
    "pointsmultiexpmult",
    "pointsmultimoneymult",
    "pointssingleexpmult",
    "pointssinglemoneymult",
    "polecareerexpmult",
    "polecareermoneymult",
    "polemultiexpmult",
    "polemultimoneymult",
    "polesingleexpmult",
    "polesinglemoneymult",
    "safetycar",
    "startingmoney",
    "startingvehicle",
    "track filter",
    "vehicle filter",
    "wincareerexpmult",
    "wincareermoneymult",
    "winmultiexpmult",
    "winmultimoneymult",
    "winsingleexpmult",
    "winsinglemoneymult",
))


def parse_rfm(data: bytes | str) -> set[str]:
    """Parse an rF1 ``.rfm`` mod descriptor's key names (keys may contain spaces)."""
    text = data if isinstance(data, str) else data.decode("latin-1")
    return set(x.strip().lower() for x in re.findall(
        r"(?m)^\s*([A-Za-z][^=]*?)\s*=", text))


def validate_rfm(keys: set[str]) -> list[str]:
    """Check corpus-verified .rfm invariants."""
    return [f"missing {key}" for key in sorted(RFM_UNIVERSAL_KEYS)
            if key not in keys]


RCS_UNIVERSAL_KEYS = frozenset((
    "name", "readonly", "device1", "device2", "device3"))


def parse_rcs(data: bytes | str) -> ConfigInfo:
    """Parse an rFactor ``.rcs`` control-set config (name + 3 device slots)."""
    return _parse_config(data)


def validate_rcs(info: ConfigInfo) -> list[str]:
    """Check corpus-verified .rcs invariants."""
    return [f"missing {key}" for key in sorted(RCS_UNIVERSAL_KEYS)
            if key not in info.keys]


TDF_UNIVERSAL_KEYS = frozenset((
    "dry", "legal", "materials", "reaction", "roadbumpamp", "roadbumplen",
    "roaddrygrip", "roadwetgrip", "rumblebumpamp", "rumblebumplen",
    "rumbledrygrip", "rumblewetgrip",
))
TDF_SECTIONS = frozenset(("feedback", "trackvars", "loose"))


def parse_tdf(data: bytes | str) -> ConfigInfo:
    """Parse an rF1 ``.tdf`` terrain-definition file."""
    return _parse_config(data)


def validate_tdf(info: ConfigInfo) -> list[str]:
    """Check corpus-verified .tdf invariants."""
    problems = [f"missing key {k}" for k in sorted(TDF_UNIVERSAL_KEYS)
                if k not in info.keys]
    problems += [f"missing section [{s}]" for s in sorted(TDF_SECTIONS)
                 if s not in info.sections]
    return problems


VEH_CORE_KEYS = frozenset((
    "cameras", "category", "classes", "cockpit", "defaultlivery", "description",
    "driver", "engine", "fullteamname", "genstring", "graphics", "hdvehicle",
    "headphysics", "manufacturer", "number", "pitgroup", "sounds", "spinner",
    "team", "teamfounded", "teamheadquarters", "teampoles", "teamstarts",
    "teamwins", "teamworldchampionships",
))
VEH_SL_CORE_KEYS = VEH_CORE_KEYS - frozenset((
    "cockpit", "aiupgradeclass", "upgrades", "spinner", "cameras"))
SVM_TC2000_KEYS = frozenset((
    "balance", "custom", "downforce", "gear1setting", "gear2setting",
    "gear3setting", "gear4setting", "gear5setting", "gear6setting", "gearing",
    "notes", "ride", "symmetric", "upgradesetting", "vehicleclasssetting",
))


def validate_veh_core(keys: set[str], family: str = "core") -> list[str]:
    """Validate the corpus-verified core key set of an rF1 `.veh` file."""
    required = VEH_SL_CORE_KEYS if family == "superleague" else VEH_CORE_KEYS
    return [f"missing veh key {key}" for key in sorted(required) if key not in keys]


def validate_svm_tc2000(keys: set[str]) -> list[str]:
    """Validate the 15 universal keys of TC2000 6-speed `.svm` setups."""
    return [f"missing svm key {key}" for key in sorted(SVM_TC2000_KEYS)
            if key not in keys]


def parse_ani_text(data: bytes) -> list[dict]:
    """Parse a plain-text Sports Car GT ``.ani`` animation rule file.

    Unlike binary ANM files, SCGT ``ANI.ANI`` is CRLF text containing named
    rule blocks. Corpus-verified on the single shipped member (12 rules).
    """
    text = data.decode("latin-1")
    rules = []
    block_re = re.compile(r"(?ms)^\s*AnimRuleName=(\S+)\s*\r?\n\s*\{(.*?)\r?\n\s*\}")
    for name, body in block_re.findall(text):
        fields = dict(re.findall(r"(\w+)\s*=\s*([^\r\n]+)", body))
        frames_m = re.search(r"\((\d+)\)", fields.get("AnimFrames", ""))
        seq_m = re.search(r"\(([^)]*)\)", fields.get("AnimSequence", ""))
        rate_m = re.search(r"\(([-\d.]+)\)", fields.get("AnimRate", ""))
        rules.append({
            "name": name,
            "base": fields.get("AnimBaseName", "").strip(),
            "frames": int(frames_m.group(1)) if frames_m else None,
            "sequence": [int(x) for x in re.findall(r"-?\d+", seq_m.group(1))]
            if seq_m else [],
            "method": fields.get("AnimMethod", "").strip(),
            "rate": float(rate_m.group(1)) if rate_m else None,
        })
    return rules


def validate_ani_text(rules: list[dict]) -> list[str]:
    """Check corpus-verified invariants of a text ANI rule list."""
    problems: list[str] = []
    if not rules:
        return ["no animation rules"]
    for rule in rules:
        label = rule["name"]
        if any(rule[k] is None or rule[k] == "" for k in ("base", "frames", "rate", "method")):
            problems.append(f"{label}: missing required field")
            continue
        if rule["base"] != label:
            problems.append(f"{label}: base name mismatch")
        if rule["frames"] != len(rule["sequence"]):
            problems.append(f"{label}: frame count != sequence length")
        if any(not 0 <= i < rule["frames"] for i in rule["sequence"]):
            problems.append(f"{label}: sequence index out of range")
        if rule["rate"] <= 0:
            problems.append(f"{label}: non-positive rate")
        if rule["method"] not in ("manual", "transient"):
            problems.append(f"{label}: unknown method {rule['method']}")
    return problems


def validate_prt(data: bytes) -> list[str]:
    """Check corpus-verified structure of a Sports Car GT ``.prt`` scene.

    Verified on all 5 archived members: ASCII text, CRLF-only line endings,
    balanced braces, and every non-brace line is ``Key=...``. Object names in
    ``ObjFile`` do not resolve to shipped members or scene objects, so no
    reference-resolution rule is asserted.
    """
    problems: list[str] = []
    if b"\n" not in data:
        return ["no line breaks"]
    if data.count(b"\r\n") != data.count(b"\n"):
        problems.append("mixed line endings")
    if any(c < 9 or (13 < c < 32 and c != 27) or c > 126 for c in data):
        problems.append("non-ASCII byte")
    depth = 0
    for line in data.decode("latin-1").splitlines():
        stripped = line.strip()
        if stripped == "{":
            depth += 1
        elif stripped == "}":
            depth -= 1
            if depth < 0:
                problems.append("unbalanced braces")
                break
        elif stripped and "=" not in stripped:
            problems.append(f"line without key=value: {stripped[:40]!r}")
            break
    if depth != 0:
        problems.append("unbalanced braces")
    return problems


def validate_vrl(data: bytes) -> list[str]:
    """Check corpus-verified Sports Car GT ``.vrl`` track-mesh invariants.

    Verified on 1,500 archived members: the first 60 bytes are zero and the
    u32 at +60 is a valid offset into the file. Deeper mesh-table semantics
    (offset tables, vertex blocks) are not decoded here.
    """
    problems: list[str] = []
    if len(data) < 64:
        return ["too short"]
    if any(data[:60]):
        problems.append("non-zero bytes in 60-byte header")
    first = struct.unpack_from("<I", data, 60)[0]
    if not (0 < first < len(data)):
        problems.append(f"invalid first offset {first}")
    if len(data) >= 160:
        problems.extend(_vrl_table_problems(data))
    return problems


def _vrl_table_problems(data: bytes) -> list[str]:
    """Arithmetic invariants of the 24-u32 table at +60.

    Verified on 4,000 SCGT .vrl members: the vertex block at +64 holds N
    16-byte records; the following six offsets are spaced N*4 bytes; the
    second count M at +96 governs three offsets spaced M*4 bytes.
    """
    table = struct.unpack_from("<24I", data, 60)
    count, vertex_off = table[0], table[1]
    problems: list[str] = []
    if not (0 < count < 100000) or vertex_off + count * 16 > len(data):
        return ["invalid vertex block"]
    if table[2] != vertex_off + count * 16:
        problems.append("vertex block end mismatch")
    if table[3] - table[2] != count * 32:
        problems.append("first section stride mismatch")
    if any(table[i + 1] - table[i] != count * 4 for i in range(3, 8)):
        problems.append("N*4 section stride mismatch")
    second = table[9]
    if not (0 < second < 100000):
        problems.append("invalid second count")
    elif any(table[i + 1] - table[i] != second * 4 for i in (10, 11)):
        problems.append("M*4 section stride mismatch")
    if any(table[i] >= len(data) for i in range(13) if table[i]):
        problems.append("table offset outside file")
    # M u32 vertex indices at +100 followed by two M-float coordinate arrays.
    if second >= len(data) or table[12] + second * 4 > len(data):
        return ["invalid index/coordinate blocks"]
    indices = struct.unpack_from(f"<{second}I", data, table[10])
    if any(i >= count for i in indices):
        problems.append("vertex index out of range")
    coords = struct.unpack_from(f"<{second * 2}f", data, table[11])
    if not all(math.isfinite(x) and abs(x) < 1e5 for x in coords):
        problems.append("non-finite or implausible coordinate")
    # 13 consecutive N*4 flag/group blocks start at table[2]: eight zero
    # blocks, one constant-15 block, two more zero blocks, a vertex map and
    # small per-vertex group IDs. Verified on 3,000 files (2 CONE10.VRL
    # exceptions have non-increasing maps and zero group IDs).
    if table[2] + 13 * count * 4 > len(data):
        return ["truncated flag blocks"]
    blocks = [struct.unpack_from(f"<{count}I", data, table[2] + i * count * 4)
              for i in range(13)]
    if any(any(v for v in b) for b in blocks[:8] + blocks[9:11]):
        problems.append("zero flag blocks corrupted")
    if any(v != 15 for v in blocks[8]):
        problems.append("constant-15 flag block corrupted")
    vertex_map, group_ids = blocks[11], blocks[12]
    if vertex_map[0] != 0 or max(vertex_map) > second:
        problems.append("vertex map out of bounds")
    if max(group_ids) >= 256:
        problems.append("group ID out of bounds")
    return problems


def read_vrl(data: bytes) -> dict | None:
    """Decode the corpus-verified header table and vertex positions of a VRL.

    Exposes the 24-u32 table, the N x 16-byte vertex block (first three
    floats = position), the M u32 vertex-index buffer, and the two M-float
    coordinate arrays. The six N*4 flag sections and the exact coordinate
    semantics remain undecoded.
    """
    if len(data) < 160 or any(data[:60]) or _vrl_table_problems(data):
        return None
    table = struct.unpack_from("<24I", data, 60)
    count, vertex_off = table[0], table[1]
    vertices = [struct.unpack_from("<4f", data, vertex_off + i * 16)
                for i in range(count)]
    sections = []
    for start, size in ((2, 1), (3, 6), (10, 3)):
        for i in range(start, start + size):
            sections.append({"offset": table[i],
                             "next": table[i + 1] if i + 1 < 24 else None})
    second = table[9]
    indices = struct.unpack_from(f"<{second}I", data, table[10])
    coords = struct.unpack_from(f"<{second * 2}f", data, table[11])
    blocks = [struct.unpack_from(f"<{count}I", data, table[2] + i * count * 4)
              for i in range(13)]
    return {"vertex_count": count, "vertices": vertices, "table": table,
            "sections": sections, "index_count": second, "indices": indices,
            "coords": list(zip(coords[:second], coords[second:])),
            "vertex_map": blocks[11], "group_ids": blocks[12],
            "zero_flags": sum(len(b) for b in blocks[:8] + blocks[9:11]),
            "constant_flag": 15}


def vrl_uv_quad_score(vrl: dict) -> float | None:
    """Score how UV-like a decoded VRL coordinate stream is.

    For files whose index count is divisible by four, returns the fraction
    of consecutive four-corner groups whose U and V values each take at most
    two distinct values (quad-corner texture coordinates). Corpus-verified on
    1,046 SCGT `.vrl` files: mean 0.753 vs 0.271 for randomly shuffled corners,
    supporting per-corner UV semantics (seams explain repeated vertex indices
    with different coordinates). Returns None when the count is not divisible
    by four.
    """
    uv = vrl["coords"]
    if not uv or len(uv) % 4:
        return None
    good = 0
    for k in range(0, len(uv), 4):
        quad = uv[k:k + 4]
        if len({round(u, 4) for u, _ in quad}) <= 2 and \
                len({round(v, 4) for _, v in quad}) <= 2:
            good += 1
    return good / (len(uv) // 4)


RCD_CORE_STATS = ("aggression", "reputation", "courtesy", "composure",
                  "speed", "crash", "recovery", "completedlaps", "minracingskill")
RCD_NASCAR_STATS = ("speed", "concentration", "fitness", "intimidation",
                    "aggression", "status", "courtesy", "script")
RCD_TALENT_STATS = ("aggression", "completedlaps", "composure", "crash",
                    "dateofbirth", "driverschampionships", "minracingskill",
                    "nationality", "poles", "speed", "starts", "wins")
RCD_EVENT_KEYS = ("crash", "nationality", "passing", "qualifyingability",
                  "raceability", "rainability", "recovery", "startsdry",
                  "startstalls", "startswet")


@dataclass
class RcdInfo:
    name: str = ""
    family: str = ""  # driver | event | unknown
    values: dict[str, str] = field(default_factory=dict)


def parse_rcd(data: bytes | str) -> RcdInfo:
    """Parse an rFactor/GTR2 ``.rcd`` race-config descriptor.

    Corpus-verified on 5,047 files (all plain text): the first non-comment
    line before ``{`` is the driver/event name; key/value lines carry the
    fields. Two families occur — driver records (3,038 files carry all nine
    core stat keys) and event records (1,830 files with StartsDry/StartsWet).
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = RcdInfo()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if stripped == "{":
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", stripped)
        if m:
            value = m.group(2).split("//", 1)[0].strip().strip('"')
            info.values[m.group(1).lower()] = value
            continue
        if not info.name and "{" not in stripped:
            info.name = stripped
    lower = set(info.values)
    if "startswet" in lower or "startsdry" in lower or "passing" in lower:
        info.family = "event"
    elif "concentration" in lower or "fitness" in lower:
        info.family = "nascar"
    elif "dateofbirth" in lower and "reputation" not in lower:
        info.family = "talent"
    elif "basefuelusage" in lower:
        info.family = "fueluse"
    elif "aggression" in lower or "nationality" in lower:
        info.family = "driver"
    else:
        info.family = "unknown"
    return info


def validate_rcd(info: RcdInfo) -> list[str]:
    """Check corpus-verified .rcd invariants; return a list of problems."""
    problems: list[str] = []
    if not info.name:
        problems.append("missing name")
    keys = set(info.values)
    if info.family == "event":
        for required in RCD_EVENT_KEYS:
            if required not in keys:
                problems.append(f"event: missing {required}")
    elif info.family == "driver":
        for required in RCD_CORE_STATS:
            if required not in keys:
                problems.append(f"driver: missing {required}")
    elif info.family == "nascar":
        for required in RCD_NASCAR_STATS:
            if required not in keys:
                problems.append(f"nascar: missing {required}")
    elif info.family == "talent":
        for required in RCD_TALENT_STATS:
            if required not in keys:
                problems.append(f"talent: missing {required}")
    elif info.family == "fueluse":
        pass  # single fuel-usage table, no driver/event schema
    else:
        problems.append(f"unknown family (keys: {sorted(keys)[:5]})")
    return problems


@dataclass
class SknLayer:
    texture: str = ""
    color: tuple[float, ...] | None = None


@dataclass
class SknWord:
    text: str = ""
    font: str = ""
    color: tuple[float, ...] | None = None
    pos: tuple[float, ...] | None = None
    ori: tuple[float, ...] | None = None
    size: tuple[float, ...] | None = None


@dataclass
class SknInfo:
    name: str = ""
    model: str = ""
    style: str = ""
    stamps: list[str] = field(default_factory=list)
    decals: list[str] = field(default_factory=list)
    alpha_stamps: list[str] = field(default_factory=list)
    layers: list[SknLayer] = field(default_factory=list)
    words: list[SknWord] = field(default_factory=list)
    mas_file: str = ""


def parse_skn(data: bytes | str) -> SknInfo:
    """Parse an rFactor ``.skn`` skin descriptor.

    Corpus-verified on 262 files: ``Skin``/``Model``/``Style``/``Stamp`` are
    universal; every one of 788 ``Layer`` blocks carries exactly ``Color`` and
    every one of 786 ``Word`` blocks carries ``Font``/``Color``/``Pos``/``Ori``/
    ``Size``. ``Decal`` (261) and ``AlphaStamp`` (231) are optional scalars.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = SknInfo()
    current = ""
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        if not code:
            continue
        m = re.match(r'^(Skin|Layer|Word)\s*=\s*"([^"]*)"', code)
        if m:
            key, value = m.group(1).lower(), m.group(2)
            current = key
            if key == "skin":
                info.name = value
            elif key == "layer":
                info.layers.append(SknLayer(texture=value))
            elif key == "word":
                info.words.append(SknWord(text=value))
            continue
        if code == "{" or code == "}":
            continue
        m = re.match(r'^([A-Za-z_][\w]*)\s*=\s*(.*)$', code)
        if not m:
            continue
        key, raw = m.group(1).lower(), m.group(2).strip()
        value = raw.strip('"')
        nums = _all_floats(raw)
        if key == "model":
            info.model = value
        elif key == "style":
            info.style = value
        elif key == "stamp":
            info.stamps.append(value)
        elif key == "decal":
            info.decals.append(value)
        elif key == "alphastamp":
            info.alpha_stamps.append(value)
        elif key == "masfile":
            info.mas_file = value
        elif current == "layer" and info.layers and key == "color":
            info.layers[-1].color = nums
        elif current == "word" and info.words:
            word = info.words[-1]
            if key == "font":
                word.font = value
            elif key == "color":
                word.color = nums
            elif key == "pos":
                word.pos = nums
            elif key == "ori":
                word.ori = nums
            elif key == "size":
                word.size = nums
    return info


def validate_skn(info: SknInfo) -> list[str]:
    """Check corpus-verified .skn invariants; return a list of problems."""
    problems: list[str] = []
    for field in ("name", "model", "style"):
        if not getattr(info, field):
            problems.append(f"missing {field}")
    if not info.stamps:
        problems.append("missing Stamp")
    for i, layer in enumerate(info.layers):
        if layer.color is None:
            problems.append(f"layer {i}: missing Color")
    for i, word in enumerate(info.words):
        for field in ("font", "color", "pos", "ori", "size"):
            if getattr(word, field) is None:
                problems.append(f"word {i}: missing {field}")
    return problems


@dataclass
class HedSpring:
    kind: str = ""
    direction: tuple[float, ...] | None = None
    head: tuple[float, ...] | None = None
    body: tuple[float, ...] | None = None
    coll_len: tuple[float, ...] | None = None
    params: tuple[float, ...] | None = None


@dataclass
class HedInfo:
    head_mass: float | None = None
    head_inertia: tuple[float, ...] | None = None
    min_pos: tuple[float, ...] | None = None
    max_pos: tuple[float, ...] | None = None
    min_ori: tuple[float, ...] | None = None
    max_ori: tuple[float, ...] | None = None
    springs: list[HedSpring] = field(default_factory=list)


HED_SPRING_TYPES = ("Sliding", "Sliding", "Sliding",
                    "FreeDamping", "FreeDamping")


def parse_hed(data: bytes | str) -> HedInfo:
    """Parse an ISIMotor ``.hed`` head-physics file.

    Corpus-verified on 88 files (31 plain ``gMb1.000f``, 56 JCA-wrapped, 1
    rF2 comment-header): 11 global keys are universal and every file has
    exactly five springs in the fixed order Sliding x3 then FreeDamping x2.
    Pass decrypted bytes for JCA-wrapped files (see ``media_tool.decrypt_jca_text``).
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = HedInfo()
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", code)
        if not m:
            continue
        key, raw = m.group(1).lower(), m.group(2).strip()
        nums = _all_floats(raw)
        if key == "headmass":
            scalar = _floats(raw, 1)
            info.head_mass = scalar[0] if scalar else None
        elif key == "headinertia":
            info.head_inertia = nums
        elif key == "minpos":
            info.min_pos = nums
        elif key == "maxpos":
            info.max_pos = nums
        elif key == "minori":
            info.min_ori = nums
        elif key == "maxori":
            info.max_ori = nums
        elif key == "spring":
            info.springs.append(HedSpring(kind=raw.strip('"')))
        elif info.springs:
            spring = info.springs[-1]
            if key == "springdir":
                spring.direction = nums
            elif key == "springhead":
                spring.head = nums
            elif key == "springbody":
                spring.body = nums
            elif key == "springcolllen":
                spring.coll_len = nums
            elif key == "springparams":
                spring.params = nums
    return info


def validate_hed(info: HedInfo) -> list[str]:
    """Check corpus-verified .hed invariants; return a list of problems."""
    problems: list[str] = []
    for field in ("head_mass", "head_inertia", "min_pos", "max_pos",
                  "min_ori", "max_ori"):
        if getattr(info, field) is None:
            problems.append(f"missing {field}")
    kinds = tuple(s.kind for s in info.springs)
    if kinds != HED_SPRING_TYPES:
        problems.append(f"spring sequence {kinds} != {HED_SPRING_TYPES}")
    for i, spring in enumerate(info.springs):
        # SpringDir is documented as invalid for FreeDamping springs.
        fields = ("direction", "head", "body", "params") if spring.kind == "Sliding" \
            else ("head", "body", "params")
        for field in fields:
            if getattr(spring, field) is None:
                problems.append(f"spring {i}: missing {field}")
    return problems


@dataclass
class SpBody:
    name: str = ""
    mass: tuple[float, ...] | None = None
    inertia: tuple[float, ...] | None = None
    pos: tuple[float, ...] | None = None
    ori: tuple[float, ...] | None = None


@dataclass
class SpBar:
    name: str = ""
    posbody: str = ""
    negbody: str = ""
    pos: tuple[float, ...] | None = None
    neg: tuple[float, ...] | None = None


@dataclass
class SpJointHinge:
    posbody: str = ""
    negbody: str = ""
    pos: tuple[float, ...] | None = None
    ori: tuple[float, ...] | None = None
    axis: tuple[float, ...] | None = None


@dataclass
class SpInfo:
    bodies: list[SpBody] = field(default_factory=list)
    bars: list[SpBar] = field(default_factory=list)
    joints: list[SpJointHinge] = field(default_factory=list)
    search_paths: list[str] = field(default_factory=list)


def parse_sp(data: bytes | str) -> SpInfo:
    """Parse an rFactor ``.sp`` suspension-geometry file.

    Corpus-verified on 172 plain files: three block types occur — ``[BODY]``
    (1,872; name/mass/inertia/pos always, ori in 1,852), ``[BAR]`` (3,320;
    posbody/negbody/pos/neg always, name optional) and ``[JOINT&HINGE]`` (688;
    posbody/negbody/axis always, pos or ori). All 8,016 ``posbody``/``negbody``
    references resolve to a BODY name defined in the same file. ``axis`` is not
    required to be a unit vector (observed norms 0.59-1.0).
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = SpInfo()
    block = ""
    current: SpBody | SpBar | SpJointHinge | None = None
    for line in text.splitlines():
        code = line.split("//", 1)[0].strip()
        m = re.match(r"^\[([^\]]+)\]$", code)
        if m:
            block = m.group(1).strip().upper()
            if block == "BODY":
                current = SpBody()
                info.bodies.append(current)
            elif block == "BAR":
                current = SpBar()
                info.bars.append(current)
            elif block == "JOINT&HINGE":
                current = SpJointHinge()
                info.joints.append(current)
            else:
                current = None
            continue
        if not code or current is None:
            if not code:
                continue
            ms = re.search(r"SearchPath\s*=\s*([^\s]+)", code)
            if ms:
                info.search_paths.append(ms.group(1))
            continue
        for key, raw in _SET_KV_RE.findall(code):
            kl = key.lower()
            nums = _all_floats(raw)
            if kl == "name":
                current.name = raw.strip('"')
            elif kl == "mass":
                current.mass = nums
            elif kl == "inertia":
                current.inertia = nums
            elif kl == "pos":
                current.pos = nums
            elif kl == "ori":
                current.ori = nums
            elif kl == "posbody":
                current.posbody = raw
            elif kl == "negbody":
                current.negbody = raw
            elif kl == "neg":
                current.neg = nums
            elif kl == "axis":
                current.axis = nums
    return info


SP_UNIVERSAL_BODIES = ("body", "fl_spindle", "fr_spindle", "fl_wheel",
                       "fr_wheel", "rl_wheel", "rr_wheel", "fuel_tank",
                       "driver_head")
SP_UNIVERSAL_BARS = ("fl_fore_upper", "fl_fore_lower", "fl_steering",
                     "fr_fore_upper", "fr_fore_lower", "fr_steering")


def validate_sp(info: SpInfo) -> list[str]:
    """Check corpus-verified .sp invariants; return a list of problems."""
    problems: list[str] = []
    names = {b.name for b in info.bodies if b.name}
    for required in SP_UNIVERSAL_BODIES:
        if required not in names:
            problems.append(f"missing universal body {required}")
    bar_names = {bar.name for bar in info.bars if bar.name}
    for required in SP_UNIVERSAL_BARS:
        if required not in bar_names:
            problems.append(f"missing universal bar {required}")
    for i, b in enumerate(info.bodies):
        for field in ("name", "mass", "inertia", "pos"):
            if not getattr(b, field):
                problems.append(f"body {i}: missing {field}")
    for label, items in (("bar", info.bars), ("joint", info.joints)):
        for i, obj in enumerate(items):
            for field in ("posbody", "negbody"):
                if not getattr(obj, field):
                    problems.append(f"{label} {i}: missing {field}")
                elif getattr(obj, field) not in names:
                    problems.append(f"{label} {i}: unknown {field} {getattr(obj, field)}")
            if label == "bar" and (obj.pos is None or obj.neg is None):
                problems.append(f"bar {i}: missing pos/neg")
            if label == "joint" and obj.axis is None:
                problems.append(f"joint {i}: missing axis")
    return problems


@dataclass
class SetView:
    name: str = ""
    clear: str | None = None
    color: tuple[float, ...] | None = None
    size: tuple[float, ...] | None = None
    center: tuple[float, ...] | None = None
    fov: tuple[float, ...] | None = None
    clip_planes: tuple[float, ...] | None = None
    dont_clear_target: str | None = None


@dataclass
class SetLight:
    name: str = ""
    kind: str = ""  # Type= (e.g. Directional)
    direction: tuple[float, ...] | None = None
    intensity: tuple[float, ...] | None = None
    color: tuple[float, ...] | None = None


@dataclass
class SetInstance:
    name: str = ""
    mesh_files: list[str] = field(default_factory=list)
    coll_target: str | None = None
    hat_target: str | None = None
    lod_in: tuple[float, ...] | None = None
    lod_out: tuple[float, ...] | None = None


@dataclass
class SetInfo:
    views: list[SetView] = field(default_factory=list)
    lights: list[SetLight] = field(default_factory=list)
    instances: list[SetInstance] = field(default_factory=list)
    ambient_color: tuple[float, ...] | None = None
    search_paths: list[str] = field(default_factory=list)


_SET_KV_RE = re.compile(r'([A-Za-z_]\w*)\s*=\s*(\([^)]*\)|"[^"]*"|[^\s]+)')


def _all_floats(value: str) -> tuple[float, ...] | None:
    out: list[float] = []
    for token in _FLOAT_RE.findall(value):
        try:
            out.append(float(token))
        except ValueError:  # e.g. a lone '.' in a filename like foo.gmt
            continue
    return tuple(out) if out else None


def parse_set(data: bytes | str) -> SetInfo:
    """Parse an rFactor ``.set`` CUBEASF camera/scene descriptor.

    Corpus-verified on 22 local files: 20 distinct keys organised into View,
    Light and optional Instance blocks plus global ``AmbientColor`` and
    ``SearchPath``. Multiple key=value pairs can share a line (e.g.
    ``Size=(.5,0.5) Center=(0.5,0.5)``), so a line may yield several fields.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = SetInfo()
    block: str = ""  # '' | 'view' | 'light' | 'instance'
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        code = stripped.split("//", 1)[0]
        for key, raw in _SET_KV_RE.findall(code):
            kl = key.lower()
            value = raw.strip('"')
            if kl == "view":
                info.views.append(SetView(name=value))
                block = "view"
                continue
            if kl == "light":
                info.lights.append(SetLight(name=value))
                block = "light"
                continue
            if kl == "instance":
                info.instances.append(SetInstance(name=value))
                block = "instance"
                continue
            nums = _all_floats(raw)
            if kl == "ambientcolor" and nums:
                info.ambient_color = nums
                continue
            if kl == "searchpath":
                info.search_paths.append(value)
                continue
            if block == "view" and info.views:
                v = info.views[-1]
                if kl == "clear":
                    v.clear = value
                elif kl == "color":
                    v.color = nums
                elif kl == "size":
                    v.size = nums
                elif kl == "center":
                    v.center = nums
                elif kl == "fov":
                    v.fov = nums
                elif kl == "clipplanes":
                    v.clip_planes = nums
                elif kl == "dontcleartarget":
                    v.dont_clear_target = value
            elif block == "light" and info.lights:
                light = info.lights[-1]
                if kl == "type":
                    light.kind = value
                elif kl == "dir":
                    light.direction = nums
                elif kl == "intensity":
                    light.intensity = nums
                elif kl == "color":
                    light.color = nums
            elif block == "instance" and info.instances:
                inst = info.instances[-1]
                if kl == "meshfile":
                    inst.mesh_files.append(value)
                elif kl == "colltarget":
                    inst.coll_target = value
                elif kl == "hattarget":
                    inst.hat_target = value
                elif kl == "lodin":
                    inst.lod_in = nums
                elif kl == "lodout":
                    inst.lod_out = nums
            else:
                if kl == "ambientcolor":
                    info.ambient_color = nums
                elif kl == "searchpath":
                    info.search_paths.append(value)
    return info


@dataclass
class HdvInfo:
    sections: set[str] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)
    values: dict[str, str] = field(default_factory=dict)


def parse_hdv(data: bytes | str) -> HdvInfo:
    """Parse an rFactor ``.hdv`` high-detail physics file.

    Corpus-verified on 156 files (17 sections, 496 distinct keys): nine
    sections ([GENERAL], [BODYAERO], [SUSPENSION], [CONTROLS], [ENGINE] and
    the four wheel-corner sections) appear in every file, and a core set of
    80 physics keys is likewise universal. Values are de-commented at ``//``
    and quoted strings are handled; keys are lowercased for comparison.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    info = HdvInfo()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            info.sections.add(stripped[1:-1].strip().lower())
            continue
        if stripped.startswith("//"):
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", stripped)
        if not m:
            continue
        key = m.group(1).lower()
        value = m.group(2)
        if value.startswith('"'):
            end = value.find('"', 1)
            value = value[1:end] if end >= 0 else value.split("//", 1)[0].strip()
        else:
            value = value.split("//", 1)[0].strip()
        info.keys.add(key)
        info.values[key] = value
    return info


@dataclass
class SvmInfo:
    variant: str  # rf1 | gtr2 | encrypted
    keys: set[str] = field(default_factory=set)
    sections: set[str] = field(default_factory=set)


def parse_svm(data: bytes) -> SvmInfo:
    """Parse an ISIMotor ``.svm`` car setup into its sections and key names.

    Corpus-verified on 21,141 setup files: rF1 uses the ``gMa1.000f`` header,
    GTR2 uses plain ``[GENERAL]``/``[CONTROLS]`` sections, and a handful of
    shipped GTR2 files have an opaque encrypted ``gMb1.000f`` payload. The
    rF1 key vocabulary (77 keys across 517 files) is a strict subset of the
    GTR2 vocabulary (86 keys across 20,593 files), so no rF1-only key needs
    remapping on conversion.
    """
    if data.startswith(b"//[[gMa1."):
        variant = "rf1"
    elif data.startswith(b"//[[gMb1."):
        return SvmInfo("encrypted")
    else:
        variant = "gtr2"
    text = data.decode("latin-1")
    info = SvmInfo(variant)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            info.sections.add(stripped[1:-1].lower())
            continue
        # Setup comments are trailing // after a value, not full-line markers.
        code = stripped.split("//", 1)[0].strip()
        m = KEYVALUE_RE.match(code)
        if m:
            info.keys.add(m.group(1).strip().lower())
    return info


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
