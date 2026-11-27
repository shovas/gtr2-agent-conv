#!/usr/bin/env python3
"""Check SimBin GMT material prefixes (RacerM conversion rule).

SimBin games read the first four characters of material names to decide surface
type: GRAS (grass), GRVL/GRAV (gravel), ROAD (tarmac/asphalt). Wrong prefixes
cause the "quicksand effect". This is a diagnostic only — it never edits files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gmt_format

# Canonical terrain/surface tokens from GTR2's own
# GameData/Locations/specialfx.tec (29 Materials= tokens). Only the
# terrain-related ones are surface prefixes; the rest (wall, logo, brick,
# drain, marbles, ...) are non-terrain effects and are not treated as valid
# surface prefixes here.
SURFACE_PREFIXES = (
    "GRAS", "GRVL", "GRAV", "ROAD",
    "B1ROAD", "B2ROAD", "B3ROAD", "BSAND", "CEMA", "CMWL", "CWAL",
    "DIRT", "DRAIN", "FLDGRASS", "GBER", "GBRM", "GRDR", "GRV",
    "LGROAD", "MARBLES", "RDGRASS", "RDGREEN", "RMBBL", "RMBL",
    "SAND", "SB", "TBWALL", "TWALL",
)


def check_gmt(data: bytes, name: str = "") -> list[str]:
    g = gmt_format.parse_gmt(name, data)
    warnings = []
    for mat in g.materials:
        text = f"{mat.name} " + " ".join(mat.strings)
        for token in text.upper().replace("\\", "/").split("/"):
            token = token.strip().strip('"')
            if len(token) >= 4 and token[:4] in SURFACE_PREFIXES:
                continue
        # Heuristic: name beginning with a known surface prefix is fine;
        # otherwise flag only names that look like terrain surfaces.
        head = mat.name.strip().upper()
        if head and head[:4] not in SURFACE_PREFIXES and any(
            word in head for word in ("GRASS", "GRAVEL", "ASPHALT", "TARMAC", "DIRT", "SAND")
        ):
            warnings.append(f"material {mat.name!r} looks like terrain but lacks a SimBin prefix")
    return warnings


def check_archive(path: str | Path) -> list[tuple[str, str]]:
    """Report SimBin-prefix warnings for every GMT member of a MAS archive.

    Used to audit rF1 track archives before conversion: the RacerM rule says
    SimBin reads only the first four material-name characters, and wrong
    surface prefixes cause the "quicksand effect". Names are *not* edited —
    stage strings can reference the original name.
    """
    import mas_tool
    _mtype, entries = mas_tool.read_archive(path)
    out = []
    for entry in entries:
        if not entry.name.lower().endswith(".gmt") or not entry.data:
            continue
        for warning in check_gmt(entry.data, entry.name):
            out.append((entry.name, warning))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--archive", action="store_true",
                    help="treat inputs as MAS archives and scan their GMT members")
    ap.add_argument("--json", action="store_true",
                    help="emit warnings as JSON")
    args = ap.parse_args(argv)
    warnings = []
    for f in args.files:
        if args.archive:
            warnings.extend((f"{f}::{entry}", warning)
                            for entry, warning in check_archive(f))
        else:
            warnings.extend((f, w) for w in check_gmt(Path(f).read_bytes(), f))
    if args.json:
        import json
        print(json.dumps(warnings, indent=2))
    else:
        for name, warning in warnings:
            print(f"{name}: {warning}")
        print(f"warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
