#!/usr/bin/env python3
"""GTL -> GTR2 conversion building block: container and .trk MASFile rewrite.

The third-party GTL2GTR2 converter performs two documented offline steps:
rename ``.gtl`` archives to ``.gtr`` and update the ``MASFile=`` entries in
track ``.trk`` files. This module implements those steps natively, with
structural validation against the installed GTL/GTR2 corpora.

Verified corpus rules (25 GTL + 34 GTR2 local ``.trk`` files):
  - GTL: 106/106 MASFile values end in ``.gtl``; 22/25 have ``teammaps.gtl``.
  - GTR2: 187/187 values end in ``.gtr``; 34/34 have ``teammaps2.gtr`` and
    ``Misc.gtr``.
  - ``teammaps.gtl`` -> ``teammaps2.gtr``; ``Misc.gtr`` is added if absent.

LIMITATION: this is a container/path building block only. Geometry, physics,
material names and in-game behaviour are NOT converted or validated here.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import mas_tool

sys.path.insert(0, str(Path(__file__).resolve().parent))

MASFILE_RE = re.compile(rb"(?im)^(\s*MASFile\s*=\s*)([^\r\n]+)")
MISC_RE = re.compile(rb"(?im)^\s*MASFile\s*=\s*Misc\.gtr\s*$")


def masfile_values(data: bytes) -> list[str]:
    return [m.group(2).decode("latin-1").strip()
            for m in MASFILE_RE.finditer(data)]


def convert_trk_bytes(data: bytes, add_misc: bool = True) -> tuple[bytes, dict]:
    """Rewrite a GTL ``.trk`` to GTR2 MASFile conventions.

    Returns the new bytes and a change counters dict. Every other byte of the
    file is preserved exactly (only MASFile values and an optional inserted
    line change).
    """
    changes = {"gtl_ext": 0, "teammaps2": 0, "misc_added": False}

    def repl(m: re.Match) -> bytes:
        prefix, value = m.group(1), m.group(2).decode("latin-1")
        new = value
        if new.lower().endswith(".gtl"):
            new = new[:-4] + ".gtr"
            changes["gtl_ext"] += 1
        if new.lower() == "teammaps.gtr":
            new = "teammaps2.gtr"
            changes["teammaps2"] += 1
        return prefix + new.encode("latin-1")

    out = MASFILE_RE.sub(repl, data)
    if add_misc and not MISC_RE.search(out):
        matches = list(MASFILE_RE.finditer(out))
        if matches:
            eol = out.find(b"\n", matches[-1].end())
            at = eol + 1 if eol >= 0 else len(out)
            ending = b"\r\n" if out[max(0, at - 2):at] == b"\r\n" else b"\n"
            out = out[:at] + b"MASFile=Misc.gtr" + ending + out[at:]
            changes["misc_added"] = True
    return out, changes


def validate_trk(data: bytes) -> list[str]:
    """Return GTR2-convention problems for a ``.trk`` payload (empty = OK)."""
    values = masfile_values(data)
    problems = [f"non-.gtr MASFile: {v}" for v in values
                if not v.lower().endswith(".gtr")]
    if any(v.lower().startswith("teammaps.") and v.lower() != "teammaps2.gtr"
           for v in values):
        problems.append("stale teammaps entry")
    if not MISC_RE.search(data):
        problems.append("missing Misc.gtr")
    return problems


def convert_bytes(name: str, data: bytes) -> tuple[bytes, dict]:
    if name.lower().endswith(".trk"):
        return convert_trk_bytes(data)
    return data, {}


def convert_archive(source: str | Path, target: str | Path | None = None,
                    check: bool = False) -> dict:
    """Convert one GTL ``.gtl`` archive into a GTR2 type-0 ``.gtr`` archive."""
    mtype, entries = mas_tool.read_archive(source)
    converted = []
    trk_count = 0
    for e in entries:
        data, _ = convert_bytes(e.name, e.data or b"")
        if e.name.lower().endswith(".trk"):
            trk_count += 1
            problems = validate_trk(data)
            if problems:
                raise ValueError(f"trk validation failed for {e.name}: {problems}")
        converted.append(mas_tool.Entry(name=e.name, offset=0, size=len(data),
                                        zsize=0, type=e.type, flags=e.flags,
                                        data=data))
    if not check:
        if target is None:
            raise ValueError("target path required unless --check is used")
        mas_tool.write_archive(target, converted, mas_type=0)
    return {"source_type": mtype, "members": len(converted), "trks": trk_count}


def convert_tree(source_root: str | Path, target_root: str | Path | None = None,
                 check: bool = False, include_others: bool = True) -> dict:
    """Convert a GTL GameData subtree into GTR2 layout.

    Loose ``.trk`` files are rewritten in place (logically); ``.gtl`` archives
    are repacked as ``.gtr`` with any ``.trk`` members converted too. Other
    files are copied byte-for-byte unless ``include_others`` is false (useful
    for fast validation of only the conversion-relevant files).
    """
    src = Path(source_root)
    report = {"trk": 0, "archives": 0, "other": 0, "files": 0}
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        suffix = p.suffix.lower()
        out_name = rel
        if suffix == ".trk":
            out = convert_trk_bytes(p.read_bytes())[0]
            report["trk"] += 1
        elif suffix == ".gtl":
            _, entries = mas_tool.read_archive(p)
            converted = []
            for e in entries:
                data = convert_bytes(e.name, e.data or b"")[0]
                converted.append(mas_tool.Entry(name=e.name, offset=0,
                                                size=len(data), zsize=0,
                                                type=e.type, flags=e.flags,
                                                data=data))
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".gtr") as tmp:
                mas_tool.write_archive(tmp.name, converted, mas_type=0)
                out = Path(tmp.name).read_bytes()
            out_name = rel.with_suffix(".gtr")
            report["archives"] += 1
        else:
            if not include_others:
                continue
            out = p.read_bytes()
            report["other"] += 1
        report["files"] += 1
        if not check:
            if target_root is None:
                raise ValueError("target_root required unless --check is used")
            dest = Path(target_root) / out_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(out)
    return report


def validate_gtr2_tree(root: str | Path,
                       known_archives: set[str] | None = None) -> list[str]:
    """Return GTR2-convention problems for a (converted) GameData tree.

    ``known_archives`` may supply lowercase archive basenames when validating a
    subtree whose shared archives live elsewhere (e.g. GameData/Locations/shared).
    Otherwise archives are discovered under ``root``.
    """
    root = Path(root)
    if known_archives is None:
        known_archives = {p.name.lower() for p in root.rglob("*")
                          if p.is_file() and p.suffix.lower() in (".gtr", ".gtl")}
    problems = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        suffix = p.suffix.lower()
        if suffix == ".gtl":
            problems.append(f"stale .gtl archive: {p}")
        if suffix == ".gdb":
            data = p.read_bytes()
            for msg in validate_gdb(data):
                problems.append(f"{p}: {msg}")
            for msg in validate_gdb_times(data):
                problems.append(f"{p}: {msg}")
        if suffix == ".car":
            for msg in validate_car(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".ani":
            for msg in validate_ani(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".dmg":
            for msg in validate_dmg_constants(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".rcd":
            for msg in validate_rcd(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".aud":
            data = p.read_bytes()
            for msg in validate_aud(data):
                problems.append(f"{p}: {msg}")
            for msg in validate_aud_paths(data):
                problems.append(f"{p}: {msg}")
            for msg in validate_aud_roadnoise(data):
                problems.append(f"{p}: {msg}")
        if suffix == ".hdc":
            data = p.read_bytes()
            for msg in validate_hdc(data):
                problems.append(f"{p}: {msg}")
            for msg in validate_hdc_clutch(data):
                problems.append(f"{p}: {msg}")
        if suffix == ".aiw":
            for msg in validate_aiw(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".tyr":
            for msg in validate_tyr(p.read_bytes()):
                problems.append(f"{p}: {msg}")
        if suffix == ".trk":
            data = p.read_bytes()
            for msg in validate_trk(data):
                problems.append(f"{p}: {msg}")
            for value in masfile_values(data):
                if value.lower() not in known_archives:
                    problems.append(f"{p}: unresolved MASFile: {value}")
    return problems


# Session keys present in all 85 local GTR2 .gdb files; only 3 of them are
# present in all 53 local GTL .gdb files (qualify1start, racelaps, racestart).
# Their *values* vary by track, so only the presence rule is corpus-confirmed.
GTR2_SESSION_KEYS = (
    "practice1day", "practice1start", "practice2day",
    "practice2start", "qualify1day", "qualify1start", "qualify2day",
    "qualify2start", "warmupday", "warmupstart", "raceday", "racestart",
    "racelaps", "racetime", "racetimescaled",
)


def gdb_key_values(data: bytes) -> dict[str, str]:
    """Return lowercase GDB key -> value from a decoded ``.gdb`` payload."""
    text = data.decode("latin-1")
    # Use horizontal whitespace only: `\s*` would consume CRLF after an empty
    # value (e.g. "Filter Properties =") and swallow the following key line.
    return {m.group(1).strip().lower(): m.group(2).strip()
            for m in re.finditer(r"(?m)^[ \t]*([A-Za-z_][A-Za-z0-9_ ]*?)[ \t]*=[ \t]*([^\r\n]*)", text)}


def validate_gdb(data: bytes) -> list[str]:
    """Return missing GTR2 session keys for a ``.gdb`` payload (empty = OK)."""
    keys = set(gdb_key_values(data))
    return [f"missing session key: {k}" for k in GTR2_SESSION_KEYS if k not in keys]


# Keys present in all 145 local GTR2 .car files; the 96 GTL .car files lack
# these four. Values are car-specific, so only the presence rule is confirmed.
GTR2_CAR_ONLY_KEYS = (
    "driver1", "driver2", "externaldriverposition", "steeringwheelaxis",
)


def validate_gdb_times(data: bytes) -> list[str]:
    """The session block sets racetime == racetimescaled (85/85 GTR2 GDBs).

    Later event sections may override ``RaceTime`` alone, so only the first
    occurrence of each key (the session block) is compared.
    """
    text = data.decode("latin-1")
    first = {}
    for key in ("racetime", "racetimescaled"):
        m = re.search(r"(?im)^[ \t]*" + key + r"[ \t]*=[ \t]*([^\r\n]*)", text)
        if m:
            first[key] = m.group(1).strip()
    a, b = first.get("racetime"), first.get("racetimescaled")
    if a is not None and b is not None and a != b:
        return [f"racetime {a} != racetimescaled {b}"]
    return []


def validate_car(data: bytes) -> list[str]:
    """Return missing GTR2-only keys for a ``.car`` payload (empty = OK)."""
    keys = set(gdb_key_values(data))
    return [f"missing car key: {k}" for k in GTR2_CAR_ONLY_KEYS if k not in keys]


def adapt_car_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    """Copy the four GTR2-only universal ``.car`` keys from a template.

    Same-name GTL/GTR2 ``.car`` counterparts are rare in the local corpora (1:
    ``safetycar.car``), so this is only meaningful when the template is the
    GTR2 version of the same vehicle. All other lines are preserved byte-for-byte.
    """
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_CAR_ONLY_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks car keys: {missing}")
    out = data
    for k in GTR2_CAR_ONLY_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_CAR_ONLY_KEYS),
                 "already_valid": not validate_car(data)}


# .hdc: where present, clutchengagerate=0.6 in 41/41 GTL handling files and
# 0.8 in 43/43 GTR2 ones; SafetyCar.hdc omits it in both corpora.
HDC_CLUTCH_RE = re.compile(rb"(?im)^([ \t]*clutchengagerate[ \t]*=[ \t]*)0\.6\b")


def rewrite_hdc_clutch(data: bytes) -> tuple[bytes, int]:
    out, count = HDC_CLUTCH_RE.subn(rb"\g<1>0.8", data)
    return out, count


def validate_hdc_clutch(data: bytes) -> list[str]:
    if HDC_CLUTCH_RE.search(data):
        return ["stale clutchengagerate=0.6"]
    return []


# .aud sound paths: 1,374/1,374 path values in 31 GTL audio files start with
# "Cars\\", while 1,094/1,094 in 25 GTR2 audio files start with "GTR\\". This
# prefix is exclusive to .aud in the GTL corpus.
AUD_OLD_PREFIX = re.compile(rb"(?i)Cars\\")
AUD_NEW_PREFIX = b"GTR\\"


def rewrite_aud_sound_paths(data: bytes) -> tuple[bytes, int]:
    """Rewrite GTL ``Cars\\`` sound paths to the GTR2 ``GTR\\`` prefix."""
    out, count = AUD_OLD_PREFIX.subn(lambda _m: AUD_NEW_PREFIX, data)
    return out, count


def validate_aud_paths(data: bytes) -> list[str]:
    if AUD_OLD_PREFIX.search(data):
        return ["stale Cars\\ sound path"]
    return []


# .ani: all 8 motion blocks are present in all 34 GTR2 animation files; 24/26
# GTL files also have them (exceptions are special-purpose variant/pitcrew files).
GTR2_ANI_BLOCKS = (
    "FLAGMOTIONS", "CROWDMOTIONSIDLE1", "CROWDMOTIONSCHEER1",
    "CROWDMOTIONSCHEER2", "CROWDMOTIONSCHEER3",
    "CAMMOTIONS1", "CAMMOTIONS2", "CAMMOTIONS3",
)
_ANI_BLOCK_RE = re.compile(
    rb"(?ims)^[ \t]*Motions[ \t]*=[ \t]*([^\r\n]+?)\r?\n[ \t]*\{(.*?)\r?\n[ \t]*\}")


def ani_blocks(data: bytes) -> dict[str, bytes]:
    return {m.group(1).decode("latin-1").strip().upper(): m.group(2)
            for m in _ANI_BLOCK_RE.finditer(data)}


def validate_ani(data: bytes) -> list[str]:
    blocks = set(ani_blocks(data))
    return [f"missing ani block: {b}" for b in GTR2_ANI_BLOCKS if b not in blocks]


def adapt_ani_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    """Append motion blocks missing from ``data`` using a GTR2 template."""
    tblocks = ani_blocks(template)
    missing = [b for b in GTR2_ANI_BLOCKS if b not in tblocks]
    if missing:
        raise ValueError(f"template lacks ani blocks: {missing}")
    present = set(ani_blocks(data))
    add = [b for b in GTR2_ANI_BLOCKS if b not in present]
    ending = b"\r\n" if b"\r\n" in data[:200] else b"\n"
    out = data
    if add and not out.endswith((b"\n", b"\r")):
        out += ending
    for b in add:
        out += (b"Motions=" + b.encode() + ending + b"{" + ending +
                tblocks[b].strip(b"\r\n") + ending + b"}" + ending)
    return out, {"blocks_added": len(add)}


# .dmg damage constants: each of these key values is single-valued across all
# 29 GTL and all 26 GTR2 damage files. (vertmult 1.00->1.0 is cosmetic and
# deliberately omitted.) Values are literal strings so formatting is preserved.
GTR2_DMG_CONSTANTS = {
    "aerodiv": ("0.0000050", "1.25e-5"),
    "aeromin": ("2750.0", "1100.0"),
    "frontwingcollparams": ("(1750.0, 550.0, 1.00)", "(10000.0, 2400.0, 1.00)"),
    "part0collparams": ("(1750.0, 550.0, 1.00)", "(7200.0, 1000.0, 0.80)"),
    "part2collparams": ("(1750.0, 550.0, 1.00)", "(7200.0, 1000.0, 0.80)"),
    "rearwingcollparams": ("(1750.0, 550.0, 1.00)", "(7500.0, 2000.0, 1.00)"),
    "wallskidthresh": ("1500.0", "2500.0"),
    "wheel0collparams": ("(11150.0, 110.0, 1.00)", "(11250.0, 110.0, 1.00)"),
    "wheel1collparams": ("(11150.0, 110.0, 1.00)", "(11250.0, 110.0, 1.00)"),
    "wheeldetach": ("20000.0", "18000.0"),
}


def _dmg_value_re(key: str, old: str) -> re.Pattern:
    return re.compile(rb"(?im)^([ \t]*" + re.escape(key.encode()) +
                      rb"[ \t]*=[ \t]*)" + re.escape(old.encode()) + rb"(?=[ \t\r\n/]|$)")


def rewrite_dmg_constants(data: bytes) -> tuple[bytes, int]:
    out = data
    total = 0
    for key, (old, new) in GTR2_DMG_CONSTANTS.items():
        out, n = _dmg_value_re(key, old).subn(
            lambda m: m.group(1) + new.encode(), out)
        total += n
    return out, total


def validate_dmg_constants(data: bytes) -> list[str]:
    return [f"stale GTL .dmg value: {k}" for k, (old, _new) in GTR2_DMG_CONSTANTS.items()
            if _dmg_value_re(k, old).search(data)]


# .aud road-noise sample: 30/31 GTL files use gtc_road_roll_int.wav while all
# 25 GTR2 files use road_roll_int.wav (the 31st GTL file omits the key).
AUD_ROADNOISE_RE = re.compile(
    rb"(?im)^([ \t]*vs_inside_roadnoise_dry[ \t]*=[ \t]*)gtc_road_roll_int\.wav\b")


def rewrite_aud_roadnoise(data: bytes) -> tuple[bytes, int]:
    out, count = AUD_ROADNOISE_RE.subn(rb"\g<1>road_roll_int.wav", data)
    return out, count


def validate_aud_roadnoise(data: bytes) -> list[str]:
    if AUD_ROADNOISE_RE.search(data):
        return ["stale GTL road-noise sample"]
    return []


# .rcd: four keys are present in all 223 GTR2 race-config files and in none of
# the 98 GTL ones. Two values are universal constants (qualcoldbraintime=200,
# racecoldbraintime=120); the two "min" values are car-specific.
GTR2_RCD_KEYS = (
    "qualcoldbrainmin", "qualcoldbraintime",
    "racecoldbrainmin", "racecoldbraintime",
)
GTR2_RCD_CONSTANTS = {"qualcoldbraintime": "200", "racecoldbraintime": "120"}


def validate_rcd(data: bytes) -> list[str]:
    keys = set(gdb_key_values(data))
    return [f"missing rcd key: {k}" for k in GTR2_RCD_KEYS if k not in keys]


def adapt_rcd_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_RCD_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks rcd keys: {missing}")
    out = data
    for k in GTR2_RCD_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_RCD_KEYS),
                 "already_valid": not validate_rcd(data)}


def add_rcd_gtr2_constants(data: bytes) -> tuple[bytes, dict]:
    """Add only the two corpus-universal constant keys to a GTL ``.rcd``."""
    vals = gdb_key_values(data)
    out = data
    added = 0
    for k, v in GTR2_RCD_CONSTANTS.items():
        if k not in vals:
            out = _set_gdb_key(out, k, v)
            added += 1
    return out, {"constants_added": added,
                 "remaining_manual": [k for k in GTR2_RCD_KEYS
                                      if k not in GTR2_RCD_CONSTANTS and k not in vals]}


# .aud: 17 keys are present in all 25 GTR2 audio files; 15 of 31 GTL audio
# files lack them. Values are sound-file names / mixing parameters, so only a
# same-name GTR2 template can supply them.
GTR2_AUD_ONLY_KEYS = (
    "playerenginevolumeminimum",
    "trannycoast1rpmtorqueinside", "trannycoast2rpmtorqueinside",
    "trannycoastblendrpminside", "trannypower1rpmtorqueinside",
    "trannypower2rpmtorqueinside", "trannypowerblendrpminside",
    "vs_inside_coast_tranny_1", "vs_inside_coast_tranny_2",
    "vs_inside_power_tranny_1", "vs_inside_power_tranny_2",
    "vs_inside_roadnoise_dirt", "vs_inside_roadnoise_dry",
    "vs_inside_roadnoise_grass", "vs_inside_roadnoise_gravel",
    "vs_inside_roadnoise_rumblestrip", "vs_inside_roadnoise_wet",
)


def validate_aud(data: bytes) -> list[str]:
    keys = set(gdb_key_values(data))
    return [f"missing aud key: {k}" for k in GTR2_AUD_ONLY_KEYS if k not in keys]


def adapt_aud_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_AUD_ONLY_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks aud keys: {missing}")
    out = data
    for k in GTR2_AUD_ONLY_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_AUD_ONLY_KEYS),
                 "already_valid": not validate_aud(data)}


# .hdc: 30 keys are present in all 44 GTR2 handling files and none of the 42
# GTL ones (mostly front/rear wheel aerodynamic and gear-5 parameters). Values
# are car-specific; only a same-name GTR2 template can supply them.
GTR2_HDC_ONLY_KEYS = (
    "fwaft", "fwcenter", "fwdown", "fwdragparams", "fwfore", "fwleft",
    "fwliftheight", "fwliftparams", "fwliftsideways", "fwmaxheight",
    "fwrange", "fwright", "fwrot", "fwsetting", "fwup", "gear5setting",
    "rwaft", "rwcenter", "rwdown", "rwdragparams", "rwfore", "rwleft",
    "rwliftparams", "rwliftsideways", "rwpeakyaw", "rwrange", "rwright",
    "rwrot", "rwsetting", "rwup",
)


def validate_hdc(data: bytes) -> list[str]:
    keys = set(gdb_key_values(data))
    return [f"missing hdc key: {k}" for k in GTR2_HDC_ONLY_KEYS if k not in keys]


def adapt_hdc_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_HDC_ONLY_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks hdc keys: {missing}")
    out = data
    for k in GTR2_HDC_ONLY_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_HDC_ONLY_KEYS),
                 "already_valid": not validate_hdc(data)}


# .aiw: these two keys are present in all 34 GTR2 AIWs and none of the 25 GTL
# AIWs. Values are track-specific, so only a same-name GTR2 template can supply them.
GTR2_AIW_ONLY_KEYS = ("scrpos", "scrori")
# .tyr: present in all 15 GTR2 tire files with the single value "1"; absent in all 26 GTL.
GTR2_TYR_CONSTANTS = {"wetweather": "1"}


def validate_aiw(data: bytes) -> list[str]:
    keys = set(gdb_key_values(data))
    return [f"missing aiw key: {k}" for k in GTR2_AIW_ONLY_KEYS if k not in keys]


def adapt_aiw_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_AIW_ONLY_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks aiw keys: {missing}")
    out = data
    for k in GTR2_AIW_ONLY_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_AIW_ONLY_KEYS),
                 "already_valid": not validate_aiw(data)}


def validate_tyr(data: bytes) -> list[str]:
    vals = gdb_key_values(data)
    return [f"missing tyr key: {k}" for k in GTR2_TYR_CONSTANTS if k not in vals]


def add_tyr_gtr2_defaults(data: bytes) -> tuple[bytes, dict]:
    """Add the corpus-universal ``WetWeather=1`` key to a GTL ``.tyr``."""
    out = data
    added = 0
    for k, v in GTR2_TYR_CONSTANTS.items():
        if k not in gdb_key_values(out):
            out = _set_gdb_key(out, k, v)
            added += 1
    return out, {"keys_added": added}


def _set_gdb_key(data: bytes, key: str, value: str) -> bytes:
    """Replace or insert one GDB key line, preserving all other bytes."""
    lines = data.splitlines(keepends=True)
    pat = re.compile(rb"(?i)^\s*" + re.escape(key.encode()) + rb"\s*=\s*[^\r\n]*")
    session = re.compile(rb"(?i)^\s*(?:test|practice|qualify|warmup|race)[a-z0-9 ]*\s*=")
    last = 1 if lines and lines[0].strip() else 0
    for i, line in enumerate(lines):
        if pat.match(line):
            lines[i] = pat.sub(key.encode() + b" = " + value.encode(), line, count=1)
            return b"".join(lines)
        if session.match(line):
            last = i + 1
    ending = b"\r\n" if any(b"\r\n" in ln for ln in lines[:5]) else b"\n"
    lines.insert(last, key.encode() + b" = " + value.encode() + ending)
    return b"".join(lines)


def adapt_gdb_from_template(data: bytes, template: bytes) -> tuple[bytes, dict]:
    """Apply a GTR2 ``.gdb`` template's session keys to a GTL ``.gdb``.

    Only the 16 session keys are touched; all other lines (names, metadata,
    lighting, filters) are preserved byte-for-byte. Values come from the
    template, so this is only meaningful when the template is the GTR2 version
    of the same track. For tracks without a counterpart, values are unverified.
    """
    tvals = gdb_key_values(template)
    missing = [k for k in GTR2_SESSION_KEYS if k not in tvals]
    if missing:
        raise ValueError(f"template lacks session keys: {missing}")
    out = data
    for k in GTR2_SESSION_KEYS:
        out = _set_gdb_key(out, k, tvals[k])
    return out, {"keys_applied": len(GTR2_SESSION_KEYS),
                 "already_valid": not validate_gdb(data)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate", metavar="DIR",
                    help="report GTR2-convention problems in a GameData tree")
    ap.add_argument("source", nargs="?")
    ap.add_argument("target", nargs="?")
    ap.add_argument("--check", action="store_true",
                    help="validate conversion without writing output")
    args = ap.parse_args(argv)
    if args.validate:
        problems = validate_gtr2_tree(args.validate)
        print(f"validate: {len(problems)} problem(s)")
        for msg in problems[:20]:
            print(" ", msg)
        return 1 if problems else 0
    if not args.source:
        ap.error("source required unless --validate is used")
    report = convert_archive(args.source, args.target, args.check)
    print(f"source_type={report['source_type']} members={report['members']} "
          f"trks={report['trks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
