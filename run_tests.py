#!/usr/bin/env python3
"""Run the unittest suite in Quick, Normal, or Full mode.

Modes are progressive (Quick ⊆ Normal ⊆ Full) and use explicit module lists
so selection is deterministic. Default mode is ``normal``.

    python3 run_tests.py                    # normal (≤5 min target)
    python3 run_tests.py --mode quick       # ≤1 min target
    python3 run_tests.py --mode full        # all tests (no budget)
"""
from __future__ import annotations

import argparse
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Fast, dependency-free unit tests (measured ≤2 s each).
QUICK = (
    "test_aiw_convert", "test_carryover", "test_corpus_diff", "test_isi_crypt",
    "test_pre_push_check", "test_text_convert", "test_validate_conversion",
    "test_validate_materials", "test_gmt_tool", "test_gmt_semantic",
    "test_simbin_text_tool", "test_gtr1_vanilla", "test_scgt", "test_gmt_variants",
    "test_fxm_crosscorpus", "test_simbin_tools",
)

# Medium-cost tests (corpora read but bounded); target total ≤5 min.
NORMAL_EXTRA = (
    "test_bmw_m3", "test_f12000", "test_f12001", "test_f12002", "test_f1c",
    "test_nt2003", "test_nt2004", "test_simbin_events_tool",
    "test_race07_complete", "test_volvo", "test_race07", "test_fixtures",
    "test_mas_tool", "test_rf1_pipeline", "test_gmt_layout", "test_phs_tool",
    "test_copa", "test_ams", "test_stockcar_extreme", "test_rf1_vanilla",
)


def all_modules() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in (ROOT / "tests").glob("test_*.py")))


def select(mode: str) -> tuple[str, ...]:
    if mode == "quick":
        return QUICK
    if mode == "normal":
        return QUICK + NORMAL_EXTRA
    return all_modules()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("quick", "normal", "full"), default="normal")
    args = ap.parse_args(argv)
    modules = select(args.mode)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for name in modules:
        suite.addTests(loader.loadTestsFromName(f"tests.{name}"))
    start = time.monotonic()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    elapsed = time.monotonic() - start
    print(f"mode={args.mode} modules={len(modules)} duration={elapsed:.1f}s "
          f"tests={result.testsRun} failures={len(result.failures)} "
          f"errors={len(result.errors)} skipped={len(result.skipped)}")
    budget = {"quick": 60, "normal": 300}.get(args.mode)
    if budget and elapsed > budget:
        print(f"WARNING: {args.mode} mode exceeded {budget}s budget")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
