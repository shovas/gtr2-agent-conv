#!/usr/bin/env python3
"""Compare the post-marker byte fields of GTR2 ``.dsi`` and ``.gtt`` records.

Both formats store 63-byte records with the same 7-byte marker, but the marker
sits 35 bytes after the position in ``.dsi`` and 39 bytes after it in ``.gtt``
(a 4-byte phase shift confined to the pre-marker region). This script aligns
records by marker and searches all 63 lags for the best match of per-byte
statistics in the post-marker region (+8..+62).

    python3 ghost_align.py [gamedata_dir]
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import simbin_events_tool as se

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "GTR2Steam"


def collect(root: Path, kind: str) -> list[bytes]:
    rows = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() != f".{kind}":
            continue
        raw = p.read_bytes()
        data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        rows.extend(se.ghost_marker_records(data, kind))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=str(DEFAULT_ROOT))
    ap.add_argument("--show-lags", action="store_true", help="print the top 8 lags")
    args = ap.parse_args(argv)
    root = Path(args.root)
    dsi = collect(root, "dsi")
    gtt = collect(root, "gtt")
    if not dsi or not gtt:
        print(f"no .dsi ({len(dsi)}) or .gtt ({len(gtt)}) records under {root}")
        return 1
    sd = se.byte_field_stats(dsi)
    sg = se.byte_field_stats(gtt)
    best_score, best_lag = se.best_field_alignment(sd, sg)
    print(f"dsi_records={len(dsi)} gtt_records={len(gtt)}")
    print(f"best_lag={best_lag} score={best_score:.3f} (max 3.0)")
    for lag in (0, 4, 59):
        print(f"  lag={lag:2d} score={se.field_alignment_score(sd, sg, lag):.3f}")
    diffs = [abs(sd[0][k] - sg[0][k]) for k in range(8, se.FRAME_STRIDE)]
    print(f"zero-fraction |diff| over +8..+62: mean={sum(diffs)/len(diffs):.4f} "
          f"max={max(diffs):.4f}")
    if args.show_lags:
        ranks = sorted(((se.field_alignment_score(sd, sg, l), l)
                        for l in range(se.FRAME_STRIDE)), reverse=True)
        print("top lags:", [(round(s, 3), l) for s, l in ranks[:8]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
