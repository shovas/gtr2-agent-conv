#!/usr/bin/env python3
"""Run the unittest suite in Quick, Normal, or Full mode.

Modes are progressive (Quick ⊆ Normal ⊆ Full) and use explicit module lists
so selection is deterministic. Default mode is ``normal``.

    python3 run_tests.py                    # normal (≤5 min target)
    python3 run_tests.py --mode quick       # ≤1 min target
    python3 run_tests.py --mode full        # all tests (no budget)
    python3 run_tests.py --list             # show module tiers, run nothing
    python3 run_tests.py --coverage         # optional line-coverage report
    python3 run_tests.py --jobs 4           # limit parallel workers (default: physical core count)

Tests are parallelised **per module**: each worker process loads one module and
runs its tests in the normal alphabetical order, so module-local ordering and
per-process global state stay intact. Cross-module order is not guaranteed, so
tests must not depend on another module having run first (they do not). Coverage
forces a single process.
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    "test_anm_format", "test_bc6h_format", "test_bc7_format",
)

# Medium-cost tests (corpora read but bounded); target total ≤5 min.
NORMAL_EXTRA = (
    "test_bmw_m3", "test_f12000", "test_f12001", "test_f12002", "test_f1c",
    "test_nt2003", "test_nt2004", "test_simbin_events_tool",
    "test_race07",
    "test_mas_tool", "test_rf1_pipeline", "test_gmt_layout",
    "test_ams", "test_rf1_vanilla",
    "test_gtr1_coverage",
    "test_gsc_exe", "test_gsc_gmt_xor", "test_gtl_to_gtr2",
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


def _run_module(name: str) -> dict:
    """Run one test module in a worker process, returning serialisable results."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromName(f"tests.{name}"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    return {"module": name, "tests_run": result.testsRun,
            "failures": [(str(test), traceback) for test, traceback in result.failures],
            "errors": [(str(test), traceback) for test, traceback in result.errors],
            "skipped": len(result.skipped)}


class AggregatedResult:
    """Minimal unittest-compatible result for the aggregate report."""

    def __init__(self, parts: list[dict]):
        self.parts = sorted(parts, key=lambda item: item["module"])
        self.testsRun = sum(part["tests_run"] for part in self.parts)
        self.failures = [(test, tb)
                         for part in self.parts for test, tb in part["failures"]]
        self.errors = [(test, tb)
                       for part in self.parts for test, tb in part["errors"]]
        self.skipped = [part["module"] for part in self.parts
                        if part["skipped"]]

    def wasSuccessful(self) -> bool:
        return not self.failures and not self.errors


def _physical_cores() -> int:
    """Count physical cores available to this process (excluding hyperthreads).

    Linux exposes ``processor``/``physical id``/``core id`` in /proc/cpuinfo;
    unique (physical id, core id) pairs are physical cores. The affinity mask
    is applied first so container CPU limits are respected. Returns 0 when
    the information is unavailable.
    """
    try:
        allowed = os.sched_getaffinity(0)
    except AttributeError:
        allowed = None
    try:
        text = (Path("/proc/cpuinfo").read_text())
    except OSError:
        return 0
    pairs = set()
    for block in text.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        try:
            processor = int(fields.get("processor", "-1"))
        except ValueError:
            continue
        if allowed is not None and processor not in allowed:
            continue
        if "physical id" in fields and "core id" in fields:
            pairs.add((fields["physical id"], fields["core id"]))
    return len(pairs)


def apply_priority(nice: int, ionice_class: int) -> None:
    """Lower this process's CPU and I/O priority; worker processes inherit both.

    ``nice`` only ever increases niceness (positive values); failures such as
    missing ``ionice`` are ignored so the runner stays portable.
    """
    if nice > 0:
        try:
            current = os.nice(0)
            if current < nice:
                os.nice(nice - current)
        except (OSError, AttributeError):
            pass
    if ionice_class is not None:
        try:
            subprocess.run(["ionice", "-c", str(ionice_class), "-p",
                            str(os.getpid())], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        except OSError:
            pass


def default_jobs() -> int:
    """One worker per available **physical** core, not per hyperthread."""
    cores = _physical_cores()
    if not cores:
        # macOS reports logical CPUs; hw.physicalcpu is the physical count.
        try:
            import subprocess
            cores = int(subprocess.check_output(
                ["sysctl", "-n", "hw.physicalcpu"], text=True).strip())
        except Exception:
            try:
                allowed = len(os.sched_getaffinity(0))
            except AttributeError:
                allowed = os.cpu_count() or 1
            cores = max(1, allowed // 2)
    return max(1, cores)


def run_parallel(modules: tuple[str, ...], jobs: int) -> AggregatedResult:
    parts = []
    workers = max(1, min(jobs, len(modules)))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_module, name): name for name in modules}
        for future in as_completed(futures):
            parts.append(future.result())
    return AggregatedResult(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("quick", "normal", "full"), default="normal")
    ap.add_argument("--jobs", type=int, default=default_jobs(),
                    help=f"parallel worker processes (default: {default_jobs()}, 1 = serial)")
    ap.add_argument("--nice", type=int, default=10,
                    help="CPU niceness for the runner and its workers (default: 10)")
    ap.add_argument("--ionice", type=int, choices=(0, 1, 2, 3), default=3,
                    help="I/O class: 0 none, 1 realtime, 2 best-effort, 3 idle (default: 3)")
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

    apply_priority(args.nice, args.ionice)
    modules = select(args.mode)
    cov = None
    if args.coverage:
        try:
            import coverage  # optional dependency
            cov = coverage.Coverage(source=[str(ROOT)], omit=[str(ROOT / "tests" / "*")])
            cov.start()
        except ImportError:
            print("coverage unavailable (optional: pip install coverage)")

    jobs = args.jobs
    if cov is not None and jobs != 1:
        print("coverage requested: forcing serial execution")
        jobs = 1
    start = time.monotonic()
    result = run_suite(modules) if jobs == 1 else run_parallel(modules, jobs)
    elapsed = time.monotonic() - start
    for test, traceback in result.failures + result.errors:
        print(f"FAIL: {test}\n{traceback}")

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
