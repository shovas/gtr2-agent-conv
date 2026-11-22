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

SURFACE_PREFIXES = ("GRAS", "GRVL", "GRAV", "ROAD")


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    total = 0
    for f in args.files:
        warnings = check_gmt(Path(f).read_bytes(), f)
        for w in warnings:
            print(f"{f}: {w}")
        total += len(warnings)
    print(f"warnings={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
