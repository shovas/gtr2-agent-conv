#!/usr/bin/env python3
"""Incremental, cached survey of ISI-encrypted GSC GMT members.

The GSC corpora (`../Automobilista`, `../StockCarExtreme`, `../GameStockCar`,
`../CopaPetrobrasdeMarcas`) hold ~150k GMT members inside huge MAS archives.
Reading every member eagerly is prohibitively slow, so this tool:

1. reads each archive's directory table only (``read_data=False``),
2. keys each member by ``archive path + member name + size + zsize`` in a
   persistent JSON cache,
3. classifies only members not yet in the cache, and
4. stores the classification (ISI signature, decodability, geometry quality).

Subsequent runs skip cached members, so the full survey converges incrementally.
Corpus-verified on the decodable subset: ``is_gsc_decodable()`` recall 1.00,
specificity 0.995; geometry invariants (UV==vertex count, in-range faces) hold.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import isi_crypt
import mas_tool
import gmt_semantic

CORPORA = ("Automobilista", "StockCarExtreme", "GameStockCar",
           "CopaPetrobrasdeMarcas")
DEFAULT_CACHE = ROOT / ".cache" / "gsc_gmt_index.json"


def member_key(archive: Path, entry: mas_tool.Entry) -> str:
    """Stable cache key for one archive member."""
    rel = os.path.relpath(archive, ROOT.parent)
    return f"{rel}|{entry.name}|{entry.size}|{entry.zsize}"


def load_cache(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, separators=(",", ":")))
    tmp.replace(path)


def classify(data: bytes) -> dict:
    """Classify one ISI-encrypted GMT member by signature and geometry."""
    try:
        sign, _key = isi_crypt.crypt_info(data)
    except Exception:
        return {"sig": "none"}
    if sign not in isi_crypt.GAMES:
        return {"sig": hex(sign)}
    out: dict = {"sig": isi_crypt.GAMES[sign][0]}
    try:
        plain = isi_crypt.decrypt_bytes(data)
    except Exception:
        out["decrypt"] = "fail"
        return out
    out["decrypt"] = "ok"
    dec = gmt_semantic.is_gsc_decodable(plain)
    out["decodable"] = dec
    if not dec:
        return out
    result = gmt_semantic.read_gsc_geometry(plain)
    if not result or not result["submeshes"]:
        out["subs"] = 0
        return out
    out["subs"] = len(result["submeshes"])
    out["verts"] = result["vertex_count"]
    out["faces"] = result["face_count"]
    out.update(result["quality"])
    return out


def survey(corpora: tuple[str, ...] = CORPORA, budget: float = 0.0,
           max_new: int = 0, cache: dict | None = None,
           cache_path: Path | None = None) -> dict:
    """Classify uncached GMT members; return a report.

    ``budget`` (seconds) and ``max_new`` (member count) bound the run for the
    quick/normal tiers. Full mode uses 0 (unbounded).
    """
    cache = cache if cache is not None else {}
    started = time.time()
    archives = new = hits = members = 0
    for root in corpora:
        base = ROOT.parent / root
        if not base.is_dir():
            continue
        for arc in sorted(base.rglob("*.mas")):
            archives += 1
            try:
                _mtype, entries = mas_tool.read_archive(arc, read_data=False)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt"):
                    continue
                members += 1
                key = member_key(arc, entry)
                if key in cache:
                    hits += 1
                    continue
                data = mas_tool.read_member(arc, entry)
                if data is None:
                    continue
                cache[key] = classify(data)
                new += 1
                if cache_path is not None and new % 100 == 0:
                    save_cache(cache_path, cache)
                if max_new and new >= max_new:
                    break
                if budget and time.time() - started > budget:
                    break
            if (max_new and new >= max_new) or (budget and time.time() - started > budget):
                break
            if cache_path is not None and archives % 25 == 0:
                save_cache(cache_path, cache)
        if (max_new and new >= max_new) or (budget and time.time() - started > budget):
            break
    if cache_path is not None:
        save_cache(cache_path, cache)
    return {"mode": "full" if not (budget or max_new) else "bounded",
            "archives": archives, "members": members, "cached_hits": hits,
            "new": new, "cache_total": len(cache),
            "elapsed": round(time.time() - started, 1)}


def summarize(cache: dict) -> dict:
    counts: dict[str, int] = {}
    for value in cache.values():
        for key, val in value.items():
            counts[f"{key}={val}"] = counts.get(f"{key}={val}", 0) + 1
    return dict(sorted(counts.items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("quick", "normal", "full"), default="normal")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = ap.parse_args(argv)
    budget, max_new = (50, 200) if args.mode == "quick" else \
                     ((280, 2000) if args.mode == "normal" else (0, 0))
    cache = load_cache(args.cache)
    report = survey(budget=budget, max_new=max_new, cache=cache,
                    cache_path=args.cache)
    for key, value in report.items():
        print(f"{key}={value}")
    print("summary:", summarize(cache))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
