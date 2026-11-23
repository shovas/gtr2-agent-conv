#!/usr/bin/env python3
"""Run the unittest suite in Quick, Normal, or Full mode.

Modes are progressive (Quick ⊆ Normal ⊆ Full) and use explicit module lists
so selection is deterministic. Default mode is ``normal``.

    python3 run_tests.py                    # normal (≤5 min target)
    python3 run_tests.py --mode quick       # ≤1 min target
    python3 run_tests.py --mode full        # all tests (no budget)
    python3 run_tests.py --list             # show module tiers, run nothing
    python3 run_tests.py --coverage         # optional line-coverage report
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
    "test_fxm_crosscorpus", "test_simbin_tools", "test_run_tests_modes",
)

# Medium-cost tests (corpora read but bounded); target total ≤5 min.
NORMAL_EXTRA = (
    "test_bmw_m3", "test_f12000", "test_f12001", "test_f12002", "test_f1c",
    "test_nt2003", "test_nt2004", "test_simbin_events_tool",
    "test_race07_complete", "test_volvo", "test_race07", "test_fixtures",
    "test_mas_tool", "test_rf1_pipeline", "test_gmt_layout", "test_phs_tool",
    "test_copa", "test_ams", "test_stockcar_extreme", "test_rf1_vanilla",
    "test_gtr1_coverage", "test_gmt_relayout",
)


def all_modules() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in (ROOT / "tests").glob("test_*.py")))


def select(mode: str) -> tuple[str, ...]:
    if mode == "quick":
        return QUICK
    if mode == "normal":
        return QUICK + NORMAL_EXTRA
    return all_modules()


def run_suite(modules: tuple[str, ...]):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for name in modules:
        suite.addTests(loader.loadTestsFromName(f"tests.{name}"))
    return unittest.TextTestRunner(verbosity=1).run(suite)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("quick", "normal", "full"), default="normal")
    ap.add_argument("--list", action="store_true", help="list tier membership and exit")
    ap.add_argument("--coverage", action="store_true",
                    help="report line coverage (needs optional 'coverage' package)")
    args = ap.parse_args(argv)

    if args.list:
        for mode in ("quick", "normal", "full"):
            mods = select(mode)
            print(f"{mode}: {len(mods)} modules")
        print("quick-only:", ", ".join(QUICK))
        print("normal-extra:", ", ".join(NORMAL_EXTRA))
        print("full-only:", ", ".join(sorted(set(all_modules()) - set(QUICK) - set(NORMAL_EXTRA))))
        return 0

    modules = select(args.mode)
    cov = None
    if args.coverage:
        try:
            import coverage  # optional dependency
            cov = coverage.Coverage(source=[str(ROOT)], omit=[str(ROOT / "tests" / "*")])
            cov.start()
        except ImportError:
            print("coverage unavailable (optional: pip install coverage)")

    start = time.monotonic()
    result = run_suite(modules)
    elapsed = time.monotonic() - start

    if cov is not None:
        cov.stop()
        cov.save()
        print("--- coverage (project modules only) ---")
        cov.report()

    print(f"mode={args.mode} modules={len(modules)} duration={elapsed:.1f}s "
          f"tests={result.testsRun} failures={len(result.failures)} "
          f"errors={len(result.errors)} skipped={len(result.skipped)}")
    budget = {"quick": 60, "normal": 300}.get(args.mode)
    if budget and elapsed > budget:
        print(f"WARNING: {args.mode} mode exceeded {budget}s budget")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
