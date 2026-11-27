#!/usr/bin/env python3
"""Text-level rFactor -> GTR2 conversions (SCN -> TRK, AIW rules).

Rules sourced from docs/reuse-rfactortools.md (RacerM tutorial + AIW Repair
Utility). These are best-effort text transformations, not complete converters.
"""
from __future__ import annotations

import re
from pathlib import Path

from simbin_text_tool import aiw_for_simbin

def decode_config_bytes(data: bytes) -> str:
    """Decode a SimBin/ISI text config, transparently decrypting JCA-wrapped files."""
    from media_tool import decrypt_jca_text
    return decrypt_jca_text(data).decode("latin-1")


KEYVALUE = re.compile(r"^(\s*)([A-Za-z_][\w]*)\s*=\s*(.*?)(\s*)$")


def scn_to_trk(data: str, track_name: str = "") -> str:
    """Rewrite an rFactor .scn as a SimBin .trk (text level)."""
    out = []
    searchpath_written = False
    for line in data.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        m = KEYVALUE.match(body)
        newline = line[len(body):]
        if not m:
            out.append(line)
            continue
        indent, key, value, trailing = m.groups()
        key_l = key.lower()
        if key_l == "searchpath":
            if searchpath_written:
                continue  # SimBin uses a fixed pair of search paths
            searchpath_written = True
            parts = value.replace("/", "\\").strip("\\").split("\\")
            if track_name:
                out.append(f"{indent}SearchPath=GameData\\Locations\\Shared{newline}")
                out.append(f"{indent}SearchPath=GameData\\Locations\\{track_name}{newline}")
            else:
                out.append(f"{indent}SearchPath=GameData\\Locations\\{parts[-1] if parts else value}{newline}")
            continue
        if key_l == "masfile":
            name = value.replace("/", "\\").strip('"')
            base = Path(name).stem
            ext = ".gtr"  # GTR2 ships 16/16 map archives with this extension
            out.append(f"{indent}MASFile={base}{ext}{newline}")
            continue
        out.append(line)
    # All 34 local GTR2 TRKs reference Misc.gtr; insert it after the last
    # MASFile line when the source SCN has no equivalent.
    if not any(re.match(r"^\s*MASFile\s*=\s*Misc\.gtr\s*$", line, re.I)
               for line in out):
        insertion = None
        for index in range(len(out) - 1, -1, -1):
            if out[index].lstrip().lower().startswith("masfile="):
                insertion = index + 1
                break
        if insertion is None:
            insertion = len(out)  # e.g. all source MASFiles were dropped
        ending = ("\r\n" if out and out[-1].endswith("\r\n") else "\n")
        out.insert(insertion, f"MASFile=Misc.gtr{ending}")
    return "".join(out)


def trk_extensions_to_gtr2(data: str) -> str:
    """Rewrite GTL MASFile `.gtl` references to GTR2 `.gtr` (data-driven rule)."""
    out = []
    for line in data.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        stripped = body.strip()
        code, separator, comment = stripped.partition("//")
        code = code.strip()
        if code.lower().startswith("masfile=") and code.lower().endswith(".gtl"):
            prefix = body[:len(body) - len(body.lstrip())]
            name = code.split("=", 1)[1].strip().strip('"')
            suffix = f" //{comment}" if separator else ""
            out.append(f'{prefix}MASFile={name[:-4]}.gtr{suffix}{newline}')
        else:
            out.append(line)
    return "".join(out)


def tdf_track_vars(data: str) -> dict[str, str]:
    """Extract ``[TRACKVARS]`` overrides from an rF1 per-track `.tdf`.

    The rF1 `.tdf` and GTR2 `specialfx.tec` share the same section/key grammar;
    GTR2 has no per-track `.tdf` files and instead reads these variable names
    from the track's `.gdb`. Only the rF1-specific `RoadMetalGrip`/
    `RoadDustGrip` keys have no GTR2 counterpart and are skipped.
    """
    text = data if isinstance(data, str) else data.decode("latin-1")
    match = re.search(r"(?ms)^\[TRACKVARS\]\s*\r?\n(.*?)(?=^\[|\Z)", text)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        m = KEYVALUE.match(line.rstrip("\r\n"))
        if m:
            out[m.group(2).strip().lower()] = m.group(3).strip()
    return out


def add_tdf_vars_to_gdb(gdb: bytes, variables: dict[str, str]) -> tuple[bytes, int]:
    """Append missing TRACKVARS keys to a GTR2 GDB, preserving CRLF and comments."""
    text = gdb.decode("latin-1")
    existing = set(re.findall(r"(?mi)^\s*([A-Za-z_]\w*)\s*=", text))
    # Canonical GTR2 spelling from GameData/Locations/specialfx.tec.
    GTR2_VAR_NAMES = {
        "roaddrygrip": "RoadDryGrip", "roadwetgrip": "RoadWetGrip",
        "roadbumpamp": "RoadBumpAmp", "roadbumplen": "RoadBumpLen",
        "rumbledrygrip": "RumbleDryGrip", "rumblewetgrip": "RumbleWetGrip",
        "rumblebumpamp": "RumbleBumpAmp", "rumblebumplen": "RumbleBumpLen",
    }
    additions = [(GTR2_VAR_NAMES.get(key, key), value)
                 for key, value in variables.items()
                 if key not in existing and key not in ("roadmetalgrip", "roaddustgrip")]
    if not additions:
        return gdb, 0
    ending = "\r\n" if "\r\n" in text else "\n"
    return (text + ending + "".join(f"{k}={value}{ending}" for k, value in additions)
            ).encode("latin-1"), len(additions)


def convert_tree(source: str | Path, target: str | Path, check: bool = False,
                 templates: dict[str, Path] | None = None,
                 shared_archives: tuple[str | Path, ...] = ()) -> dict:
    """Convert an rFactor GameData tree: archives, AIW, SCN -> TRK, copy rest.

    ``templates`` optionally maps lowercase GTR2 basenames to template files;
    matching ``.gdb``/``.aiw`` outputs receive the GTR2-only session/AIW keys
    from those templates (values come from the template and are unverified for
    tracks without a real GTR2 counterpart). ``shared_archives`` are converted
    into the target root — rF1 keeps shared assets such as ``commonmaps.mas``
    in the parent ``Locations`` folder, outside a single track's directory,
    and the converted TRK still references them as ``.gtr``.
    """
    import mas_tool
    from rf1_to_gtr2 import convert_archive
    from gtl_to_gtr2 import adapt_aiw_from_template, adapt_gdb_from_template

    src, dst = Path(source), Path(target)
    templates = templates or {}
    fallbacks = {}
    for path in templates.values():
        fallbacks.setdefault(path.suffix.lower(), path)
    report = {"archives": 0, "aiw": 0, "scn": 0, "copy": 0, "adapted": 0}
    for shared in shared_archives:
        shared = Path(shared)
        if not shared.is_file():
            continue
        out = dst / (shared.stem + ".gtr")
        if not check:
            out.parent.mkdir(parents=True, exist_ok=True)
            convert_archive(shared, out, relayout=True)
        report["archives"] += 1
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        ext = path.suffix.lower()
        if ext in (".mas", ".gtr", ".gtl"):
            out = rel.with_suffix(".gtr")
            if not check:
                (dst / out).parent.mkdir(parents=True, exist_ok=True)
                # Semantic bridge preserves all submeshes; the structural default
                # rebuilds only the first mesh record of multi-object GMTs.
                convert_archive(path, dst / out, relayout=True)
            report["archives"] += 1
        elif ext == ".aiw":
            if not check:
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                data = aiw_for_simbin(decode_config_bytes(path.read_bytes())).encode("latin-1")
                template = templates.get(path.name.lower(), fallbacks.get(".aiw"))
                if template is not None:
                    data = adapt_aiw_from_template(data, template.read_bytes())[0]
                    report["adapted"] += 1
                out.write_bytes(data)
            report["aiw"] += 1
        elif ext == ".gdb":
            if not check:
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                data = path.read_bytes()
                template = templates.get(path.name.lower(), fallbacks.get(".gdb"))
                if template is not None:
                    data = adapt_gdb_from_template(data, template.read_bytes())[0]
                    report["adapted"] += 1
                # rF1 keeps surface feedback in a per-track .tdf; GTR2 reads
                # the same TRACKVARS names from the track's .gdb instead.
                tdf = src / (path.stem + ".tdf")
                if not tdf.is_file():
                    tdf = next(src.glob("*.tdf"), None)
                if tdf is not None:
                    variables = tdf_track_vars(tdf.read_bytes())
                    data, added = add_tdf_vars_to_gdb(data, variables)
                    report["tdf_vars"] = report.get("tdf_vars", 0) + added
                out.write_bytes(data)
            report["copy"] += 1
        elif ext == ".scn":
            if not check:
                out = (dst / rel).with_suffix(".trk")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(scn_to_trk(decode_config_bytes(path.read_bytes()), src.name).encode("latin-1"))
            report["scn"] += 1
        else:
            if not check:
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(path.read_bytes())
            report["copy"] += 1
    return report


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("target", nargs="?")
    ap.add_argument("--check", action="store_true", help="count conversions without writing")
    ap.add_argument("--templates", metavar="DIR",
                    help="directory of GTR2 .gdb/.aiw templates for key addition")
    ap.add_argument("--shared", nargs="*", default=(),
                    help="extra rF1 archive(s) to convert into the target root, "
                         "e.g. GameData/Locations/commonmaps.mas")
    args = ap.parse_args(argv)
    templates = {}
    if args.templates:
        root = Path(args.templates)
        if not root.is_dir():
            ap.error("--templates requires a directory")
        templates = {p.name.lower(): p for p in root.rglob("*")
                     if p.is_file() and p.suffix.lower() in (".gdb", ".aiw")}
    report = convert_tree(args.source, args.target or "/tmp/unused",
                          args.check, templates=templates,
                          shared_archives=tuple(args.shared))
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
