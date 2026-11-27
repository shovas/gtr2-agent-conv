"""Tests for the deterministic Quick/Normal/Full test-mode selection."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_tests  # noqa: E402


class TestModesTest(unittest.TestCase):
    def test_progressive_coverage(self):
        quick = set(run_tests.select("quick"))
        normal = set(run_tests.select("normal"))
        full = set(run_tests.select("full"))
        self.assertTrue(quick)
        self.assertTrue(quick <= normal <= full)
        self.assertEqual(run_tests.select("normal"), run_tests.QUICK + run_tests.NORMAL_EXTRA)

    def test_deterministic_order(self):
        for mode in ("quick", "normal", "full"):
            self.assertEqual(run_tests.select(mode), run_tests.select(mode))
        self.assertEqual(run_tests.select("full"), tuple(sorted(run_tests.select("full"))))

    def test_all_modules_exist(self):
        for name in run_tests.select("full"):
            self.assertTrue((ROOT / "tests" / f"{name}.py").is_file(), name)

    def test_priority_application(self):
        """Nice/ionice options apply without breaking the runner."""
        import os
        import subprocess

        run_tests.apply_priority(10, 3)
        self.assertGreaterEqual(os.nice(0), 10)
        ionice = subprocess.run(["ionice", "-p", str(os.getpid())],
                                capture_output=True, text=True)
        if ionice.returncode == 0 and ionice.stdout.strip():
            self.assertIn("idle", ionice.stdout.lower())

    def test_parallel_runs_match_serial(self):
        """Module-level parallelism preserves the aggregate test counts."""
        modules = ("test_bc6h_format", "test_bc7_format")
        serial = run_tests.run_suite(modules)
        parallel = run_tests.run_parallel(modules, 2)
        self.assertEqual(serial.testsRun, parallel.testsRun)
        self.assertEqual(len(serial.failures), len(parallel.failures))
        self.assertEqual(len(serial.errors), len(parallel.errors))
        self.assertEqual(serial.wasSuccessful(), parallel.wasSuccessful())

    def test_default_jobs_tracks_physical_cores(self):
        jobs = run_tests.default_jobs()
        self.assertGreaterEqual(jobs, 1)
        import os
        logical = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") \
            else (os.cpu_count() or 1)
        self.assertLessEqual(jobs, logical)
        if (Path("/proc/cpuinfo").is_file()
                and hasattr(os, "sched_getaffinity")):
            self.assertEqual(jobs, max(1, run_tests._physical_cores()))

    def test_list_tiers(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = run_tests.main(["--list"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        for mode in ("quick", "normal", "full"):
            self.assertIn(f"{mode}: {len(run_tests.select(mode))} modules", out)
        self.assertIn("full-only:", out)


if __name__ == "__main__":
    unittest.main()
