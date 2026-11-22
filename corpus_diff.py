#!/usr/bin/env python3
"""Data-driven comparison of same-name files in two corpus directories.

Used to derive conversion rules from real GTL/GTR2 and rFactor-lineage pairs:
identical files are safe carry-over candidates; differing files are candidates
for field-level rule extraction.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def index_tree(root: Path, exts: set[str] | None = None, archives: bool = False) -> dict[str, bytes]:
    """Index files (and optionally MAS members) by lowercase basename."""
    import mas_tool

    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in (".mas", ".gtr", ".gtl"):
            if archives:
                for e in mas_tool.read_archive(p)[1]:
                    if not exts or Path(e.name).suffix.lower() in exts:
                        out.setdefault(e.name.lower(), e.data or b"")
        elif not exts or ext in exts:
            out.setdefault(p.name.lower(), p.read_bytes())
    return out


def compare_trees(a: str | Path, b: str | Path, exts: set[str] | None = None,
                  archives: bool = False) -> dict:
    """Return per-extension counts of common/identical/different file basenames."""
    left = index_tree(Path(a), exts, archives)
    right = index_tree(Path(b), exts, archives)
    common = set(left) & set(right)
    stats = defaultdict(lambda: {"common": 0, "identical": 0, "different": 0})
    identical_names = defaultdict(list)
    for name in common:
        ext = Path(name).suffix.lower()
        stats[ext]["common"] += 1
        key = "identical" if left[name] == right[name] else "different"
        stats[ext][key] += 1
        if key == "identical":
            identical_names[ext].append(name)
    return {"stats": dict(stats), "identical_names": dict(identical_names),
            "left_only": len(set(left) - set(right)), "right_only": len(set(right) - set(left))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--ext", action="append", help="extension filter (repeatable)")
    ap.add_argument("--archives", action="store_true", help="also index files inside MAS archives")
    args = ap.parse_args(argv)
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in (args.ext or [])}
    report = compare_trees(args.left, args.right, exts or None, args.archives)
    for ext, s in sorted(report["stats"].items()):
        print(f"{ext:8s} common={s['common']:5d} identical={s['identical']:5d} different={s['different']:5d}")
    print(f"left_only={report['left_only']} right_only={report['right_only']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
