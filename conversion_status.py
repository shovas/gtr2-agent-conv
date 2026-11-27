#!/usr/bin/env python3
"""Report verified conversion coverage by source family and file type.

This is a *status dashboard*, not a converter. All numbers come from the
full-tier regression tests and docs already in this repository; it prints a
compact, reproducible summary of what is convertible, what is offline-validated,
and what remains blocked. Use ``--json`` for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Status values: "validated" = full offline validation passes on sampled data;
# "partial" = a bounded conversion path exists but coverage is limited;
# "read-only" = decoded/inspected but no converter; "blocked" = no path.
FAMILIES = (
    {"family": "rFactor 1", "source": "RF1Vanilla", "format": "GMT meshes",
     "status": "validated", "coverage": "253/253 archived members",
     "validation": "validate_conversion + independent reader",
     "tool": "rf1_to_gtr2.py", "gap": "in-game acceptance; per-track config values"},
    {"family": "rFactor 1", "source": "RF1Vanilla", "format": "whole track tree",
     "status": "validated", "coverage": "Joesville: 0 validator problems",
     "validation": "validate_gtr2_tree",
     "tool": "text_convert.py --templates DIR --shared commonmaps.mas",
     "gap": "template values for other tracks; in-game acceptance"},
    {"family": "GT Legends", "source": "GTLSteam", "format": "container/TRK tree",
     "status": "validated", "coverage": "944 files / 60 archives",
     "validation": "validate_gtr2_tree", "tool": "gtl_to_gtr2.py --tree",
     "gap": "geometry/physics/config adaptation; in-game acceptance"},
    {"family": "GT Legends", "source": "GTLSteam", "format": "HAT heights",
     "status": "partial", "coverage": "1/2 GTL layouts have a GTR2 reference",
     "validation": "hat_height_match + validate_hat",
     "tool": "media_tool.py hat-transfer-heights",
     "gap": "node-tree serializer for layouts without a reference"},
    {"family": "GTR 2004", "source": "GTR1Vanilla", "format": "third-magic GMT meshes",
     "status": "partial", "coverage": "34,816/36,128 batch members",
     "validation": "parse + material tail", "tool": "gtr1_to_gmt.py / batch_convert.py",
     "gap": "in-game acceptance; descriptor-less placeholders"},
    {"family": "Race 07 DLC", "source": "Race07Complete", "format": "RaceGMT meshes",
     "status": "partial", "coverage": "641/643 meshes",
     "validation": "parse + material tail", "tool": "race_gmt.py --to-gtr2",
     "gap": "2 meshes use the 0x2000403d variant; column 4 unassigned"},
    {"family": "F1 2002 / F1C / NASCAR", "source": "F12002,F1C,NascarSimRacing",
     "format": "CUBE MTS 4.10 meshes", "status": "partial",
     "coverage": "389 convertible of ~1,715 with triangles",
     "validation": "parse + index bounds", "tool": "mts_format.to_gtr2_gmt",
     "gap": "skinned meshes need external bone data; 4.20 variant undecoded"},
    {"family": "Sports Car GT", "source": "SportsCarGtUsa", "format": "VRL meshes",
     "status": "partial", "coverage": "13,292/13,293 batch members",
     "validation": "parse + material tail", "tool": "vrl_to_gmt / batch_convert.py",
     "gap": "one invalid table; in-game acceptance"},
    {"family": "F1 2000 / 2001", "source": "F12000,F12001", "format": "textures",
     "status": "validated", "coverage": "315 + 5,243 sampled textures",
     "validation": "valid BMP headers", "tool": "mas_tool.py extract --as-bmp",
     "gap": "four tiny transparency blobs"},
    {"family": "BMW M3 Challenge", "source": "BMWM3Challenge", "format": "mesh carry-over",
     "status": "partial", "coverage": "26/26 same-name GMTs byte-identical to GTR2",
     "validation": "hash comparison", "tool": "corpus_diff.py",
     "gap": "no whole-game pipeline"},
)

BLOCKERS = (
    {"issue": "in-game acceptance", "state": "blocked",
     "detail": "Wine starts GTR2Dedicated and loads GameData/HAT names, but D3D window creation fails"},
    {"issue": "HAT node-tree serializer", "state": "blocked",
     "detail": "34-byte frame pinned from code; variable/interleaved on-disk framing still undecoded"},
    {"issue": "GMT f0 exact encoding", "state": "open",
     "detail": "mod-256 low-byte signal and family-level material association only"},
    {"issue": "RaceGMT column 4", "state": "open",
     "detail": "no relationship to decoded geometry, UVs, normals or axes"},
    {"issue": "replay small_b identity", "state": "open",
     "detail": "slow state channel correlated with smoothed steering, no unit mapping"},
    {"issue": "FXM animation binding", "state": "partial",
     "detail": "TRS keyframes decode; .ani files give explicit GMT/LMA/Motions bindings (7,489 records), but in-game animation playback is untested"},
    {"issue": "CUBE MTS 4.20 / skinned geometry", "state": "open",
     "detail": "different record structure; external bone data required"},
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)
    report = {"families": list(FAMILIES), "blockers": list(BLOCKERS),
              "legend": {"validated": "offline validation passes on sampled data",
                         "partial": "bounded conversion path exists",
                         "read-only": "decoded but no converter",
                         "blocked": "no path without new evidence"}}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("ISIMotor -> GTR2 conversion status (offline validation only)\n")
        for family in FAMILIES:
            print(f"{family['source']:24s} {family['format']:26s} "
                  f"{family['status']:9s} {family['coverage']}")
            print(f"  tool: {family['tool']}")
            print(f"  gap:  {family['gap']}")
        print("\nOpen blockers:")
        for blocker in BLOCKERS:
            print(f"  [{blocker['state']:7s}] {blocker['issue']}: {blocker['detail']}")
        print("\nNo path currently reaches in-game acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
