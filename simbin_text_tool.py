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
    score_checkpoint: int | None = None
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
                elif key == "wp_score":
                    parts = value.split(",")
                    if parts:
                        try:
                            waypoint.score_checkpoint = int(float(parts[0].strip("() ")))
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

    Verified on 1,189 cameras across GTR2/GTL/Race07/BMW: ActivationRadius is
    never negative, and the "deactivated camera" encoding is an exact
    biconditional — all 23 cameras whose ActivationLocation is an FLT_MAX
    triplet have ActivationRadius=1, and no other camera has radius 1. The
    Turbo Basic reference documents a 99999 sentinel instead; that value does
    not occur locally, so both encodings are accepted here.
    """
    problems: list[str] = []
    for i, cam in enumerate(info.cameras):
        radius = cam.activation_radius
        if radius is not None and radius < 0:
            problems.append(f"camera {i}: negative ActivationRadius {radius}")
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


RCD_CORE_STATS = ("aggression", "reputation", "courtesy", "composure",
                  "speed", "crash", "recovery", "completedlaps", "minracingskill")
RCD_NASCAR_STATS = ("speed", "concentration", "fitness", "intimidation",
                    "aggression", "status", "courtesy", "script")
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
