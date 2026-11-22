#!/usr/bin/env python3
"""Text-level rFactor -> GTR2 conversions (SCN -> TRK, AIW rules).

Rules sourced from docs/reuse-rfactortools.md (RacerM tutorial + AIW Repair
Utility). These are best-effort text transformations, not complete converters.
"""
from __future__ import annotations

import re
from pathlib import Path

from simbin_text_tool import aiw_for_simbin

KEYVALUE = re.compile(r"^(\s*)([A-Za-z_][\w]*)\s*=\s*(.*?)(\s*)$")


def scn_to_trk(data: str, track_name: str = "") -> str:
    """Rewrite an rFactor .scn as a SimBin .trk (text level)."""
    out = []
    searchpath_written = False
    for line in data.splitlines(keepends=True):
        m = KEYVALUE.match(line.rstrip("\r\n"))
        newline = "\n" if line.endswith("\n") else ""
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
            ext = ".gtl" if base.upper().endswith("MAP") else ".gtr"
            out.append(f'{indent}MASFile="{base}{ext}"{newline}')
            continue
        out.append(line)
    return "".join(out)


def trk_extensions_to_gtr2(data: str) -> str:
    """Rewrite GTL MASFile `.gtl` references to GTR2 `.gtr` (data-driven rule)."""
    out = []
    for line in data.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.lower().startswith("masfile=") and stripped.lower().endswith(".gtl"):
            prefix = line[:len(line) - len(line.lstrip())]
            name = stripped.split("=", 1)[1].strip().strip('"')
            newline = "\n" if line.endswith("\n") else ""
            out.append(f'{prefix}MASFile={name[:-4]}.gtr{newline}')
        else:
            out.append(line)
    return "".join(out)


def convert_tree(source: str | Path, target: str | Path, check: bool = False) -> dict:
    """Convert an rFactor GameData tree: archives, AIW, SCN -> TRK, copy rest."""
    import mas_tool
    from rf1_to_gtr2 import convert_archive

    src, dst = Path(source), Path(target)
    report = {"archives": 0, "aiw": 0, "scn": 0, "copy": 0}
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        ext = path.suffix.lower()
        if ext in (".mas", ".gtr", ".gtl"):
            out = rel.with_suffix(".gtr")
            if not check:
                (dst / out).parent.mkdir(parents=True, exist_ok=True)
                convert_archive(path, dst / out)
            report["archives"] += 1
        elif ext == ".aiw":
            if not check:
                out = dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(aiw_for_simbin(path.read_bytes().decode("latin-1")).encode("latin-1"))
            report["aiw"] += 1
        elif ext == ".scn":
            if not check:
                out = (dst / rel).with_suffix(".trk")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(scn_to_trk(path.read_bytes().decode("latin-1"), src.name).encode("latin-1"))
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
    args = ap.parse_args(argv)
    report = convert_tree(args.source, args.target or "/tmp/unused", args.check)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
