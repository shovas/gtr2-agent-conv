"""Tests for the GTTF/IRSR structural reader (29 GTT + 13 VCR files)."""
import glob
import gzip
import struct
import math
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simbin_events_tool as setool  # noqa: E402


def _files(ext):
    base = ROOT.parent / "GTR2Steam"
    return [p for p in (Path(x) for x in glob.glob(str(base / "**" / "*"), recursive=True))
            if p.is_file() and p.suffix.lower() == ext.lower()]


class SimbinEventsToolTest(unittest.TestCase):
    def test_gtt_headers(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        self.assertEqual(len(files), 29)
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "GTTF")
                self.assertEqual(e.version, 1.0)
                self.assertTrue(e.trk.lower().endswith(".trk"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))

    def test_vcr_headers(self):
        files = _files(".vcr")
        if not files:
            self.skipTest("GTR2 VCR files not present")
        self.assertGreater(len(files), 0)
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertAlmostEqual(e.version, 1.05, places=4)
                self.assertTrue(e.trk.lower().endswith(".trk"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))

    def test_gttf_frame_grid(self):
        import gzip
        import re
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        checked = 0
        for p in files[:6]:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            self.assertEqual(grid["stride"], 63)
            frames = setool.read_frames(data, grid)
            self.assertGreater(len(frames), 400)
            # At a 63-byte stride consecutive samples are adjacent frames, so
            # position deltas are small; a 252-byte stride skipped 4 frames.
            deltas = [abs(frames[i + 1]["position"][0] - frames[i]["position"][0])
                      for i in range(len(frames) - 1)]
            self.assertLess(max(deltas), 5.0)
            self.assertTrue(all(0 < frames[i + 1]["time"] - frames[i]["time"] < 1.0
                                for i in range(len(frames) - 1)))
            self.assertTrue(any(abs(x) > 1 for x in frames[0]["position"]))
            self.assertTrue(all(-math.pi <= fr["heading"] <= math.pi for fr in frames))
            self.assertTrue(any(abs(fr["pitch"]) > 0.001 for fr in frames))
            m = re.search(r"(\d)_(\d+)_(\d+)_", p.name)
            if m:
                lap = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 1000
                span = frames[-1]["time"] - frames[0]["time"]
                self.assertLess(abs(span - lap), 2.0)
            checked += 1
        if not checked:
            self.skipTest("no GTTF frame grids detected")
        self.assertGreaterEqual(checked, 1)

    def test_gttf_slots48_52_56_60_no_car_ceiling(self):
        """Slots +48/+52/+56/+60 are sentinel-like for both cars."""
        import gzip
        import statistics
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        maxima = {off: [] for off in (48, 52, 56, 60)}
        clusters = []
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            frames = setool.read_frames(data, grid)
            for off in maxima:
                maxima[off].append(max(
                    int.from_bytes(data[fr["offset"] + off:fr["offset"] + off + 4],
                                   "little") for fr in frames))
            values = [int.from_bytes(data[fr["offset"] + 52:fr["offset"] + 56],
                                     "little") for fr in frames]
            clusters.append(sum(v < 10_000 or (1 << 23) - 10_000 <= v < (1 << 23) + 10_000
                                for v in values) / len(values))
        if not maxima[48]:
            self.skipTest("no GTTF frame grids detected")
        for off, values in maxima.items():
            self.assertTrue(all(v > 4_000_000_000 for v in values), f"slot {off}")
        self.assertLess(statistics.median(clusters), 0.35)

    def test_gttf_slot44_no_car_ceiling(self):
        """Slot +44 has no car-specific ceiling; its byte-pair structure is shared."""
        import gzip
        import statistics
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        equal_fractions = []
        maxima = []
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            words = [data[fr["offset"] + 44:fr["offset"] + 48]
                     for fr in setool.read_frames(data, grid)]
            equal_fractions.append(sum(w[0] == w[2] for w in words) / len(words))
            maxima.append(max(int.from_bytes(w, "little") for w in words))
        if not equal_fractions:
            self.skipTest("no GTTF frame grids detected")
        self.assertTrue(all(0.7 < f < 0.95 for f in equal_fractions))
        self.assertTrue(all(m > 4_200_000_000 for m in maxima))
        self.assertLess(statistics.median(equal_fractions), 0.9)

    def test_gttf_slot7_byte31_exponent_artifact(self):
        """Slot +7's varying byte is car-independent and centred on 0x40."""
        import collections
        import gzip
        import statistics
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        modes = []
        medians = []
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            values = [data[fr["offset"] + 31] for fr in setool.read_frames(data, grid)]
            modes.append(collections.Counter(values).most_common(1)[0][0])
            medians.append(statistics.median(values))
        if not modes:
            self.skipTest("no GTTF frame grids detected")
        self.assertGreaterEqual(sum(m in (64, 65) for m in modes), len(modes) - 1)
        self.assertTrue(all(60 <= m <= 70 for m in medians))
        self.assertEqual(statistics.median(medians), 64)

    def test_gttf_slot40_not_counter_or_state(self):
        """Slot +40 is neither monotonic nor a stable hi/lo state across files."""
        import gzip
        import statistics
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        monotonic = []
        transitions = []
        time_correlations = []
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            rows = setool.read_frames(data, grid)
            values = [setool.frame_s40_word(data, r["offset"]) for r in rows]
            clusters = ["hi" if v > 2 ** 30 else "lo" for v in values]
            monotonic.append(sum(b >= a for a, b in zip(values, values[1:]))
                             / (len(values) - 1))
            transitions.append(sum(a != b for a, b in zip(clusters, clusters[1:]))
                               / (len(clusters) - 1))
            time_correlations.append(abs(setool._corr(values, [r["time"] for r in rows])))
        if not monotonic:
            self.skipTest("no GTTF frame grids detected")
        self.assertLess(statistics.median(monotonic), 0.6)
        self.assertGreater(statistics.median(transitions), 0.2)
        self.assertLess(statistics.median(time_correlations), 0.05)

    def test_gttf_slot36_quantized_shape(self):
        """Frame slot +36 is a quantized float with only two mantissa classes."""
        import gzip
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        total = shaped = 0
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            for fr in setool.read_frames(data, grid):
                word = setool.frame_s36_word(data, fr["offset"])
                total += 1
                shaped += int(setool.is_quantized_s36(word))
        if not total:
            self.skipTest("no GTTF frame grids detected")
        self.assertGreater(shaped / total, 0.98)

    def test_gttf_engine_speed_ceiling(self):
        """Frame slot +32 has a car-specific ceiling and shift-like drops."""
        import gzip
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        ceilings = []
        shift_files = 0
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            frames = setool.read_frames(data, grid)
            speeds = [fr["engine_speed"] for fr in frames]
            if not speeds or any(v is None for v in speeds):
                continue
            ceilings.append(max(speeds))
            drops = sum(1 for a, b in zip(speeds, speeds[1:]) if a - b > 200000)
            shift_files += int(drops >= 10)
        if not ceilings:
            self.skipTest("no GTTF frame grids detected")
        self.assertTrue(all(5_500_000 <= c <= 6_300_000 for c in ceilings))
        self.assertGreaterEqual(sum(1 for c in ceilings if 5_860_000 <= c <= 5_890_000), 5)
        self.assertGreaterEqual(shift_files, 3)

    def test_gttf_frame_count_matches_record_marker(self):
        """The 63-byte record marker independently validates the frame grid."""
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        # Documented by the (reference-only) gtr2-agent-tools ghost loader:
        # 63-byte records marked by this 7-byte prefix; the trailing byte varies.
        mark = b"\x01\x00\x00\x34\x00\x20\x00"
        checked = 0
        corrs = []
        for p in files:
            data = gzip.decompress(p.read_bytes())
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            self.assertLessEqual(abs(data.count(mark) - grid["count"]), 2, p.name)
            checked += 1
        self.assertGreaterEqual(checked, 1)

    def test_dsi_ghost_line(self):
        """Read every local Driving School instructor polyline."""
        import math
        import struct
        files = [p for p in (Path(x) for x in glob.glob(
                     str(ROOT.parent / "GTR2Steam" / "**" / "*"), recursive=True))
                 if p.is_file() and p.suffix.lower() == ".dsi"]
        if not files:
            self.skipTest("GTR2 DSI files not present")
        checked = 0
        corrs = []
        for p in files:
            with self.subTest(path=p.name):
                raw = p.read_bytes()
                data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
                pts = setool.read_ghost_line(data)
                self.assertGreater(len(pts), 10)
                self.assertTrue(all(math.isfinite(v) and abs(v) < 1e5
                                    for pt in pts for v in pt))
                # Marker sits at record +0; position floats at +35/+39/+43.
                start = data.find(setool.GHOST_MARKER)
                for i in (0, 1, min(4, len(pts) - 1)):
                    off = start + i * setool.FRAME_STRIDE
                    expected = struct.unpack_from("<3f", data, off + 35)
                    self.assertEqual(pts[i], expected)
                checked += 1
        self.assertGreaterEqual(checked, 1)
        # Reference fixture from gtr2-agent-tools: Anderstorp A1_Level 4 starts
        # near x=-251.2 and ends near x=210.
        fixture = next((p for p in files if p.name.lower() == "a1_level 4.dsi"), None)
        if fixture is not None:
            raw = fixture.read_bytes()
            data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
            pts = setool.read_ghost_line(data)
            self.assertAlmostEqual(pts[0][0], -251.2, delta=0.5)
            self.assertAlmostEqual(pts[-1][0], 210.0, delta=0.5)

    def test_field_alignment_synthetic(self):
        import ghost_align  # noqa: F401
        # Two identical record sets must align at lag 0 with score 3.0.
        rows = [bytes((i * 7 + j * 13) & 0xFF for i in range(63)) for j in range(40)]
        s = setool.byte_field_stats(rows)
        score, lag = setool.best_field_alignment(s, s)
        self.assertEqual(lag, 0)
        self.assertAlmostEqual(score, 3.0, places=5)

    def test_dsi_gtt_postmarker_alignment(self):
        """Post-marker fields align at lag 0 across all GTR2 .dsi/.gtt files."""
        import ghost_align
        root = ROOT.parent / "GTR2Steam"
        if not root.is_dir():
            self.skipTest("GTR2Steam corpus not present")
        dsi = ghost_align.collect(root, "dsi")
        gtt = ghost_align.collect(root, "gtt")
        if not dsi or not gtt:
            self.skipTest("ghost records not present")
        sd = setool.byte_field_stats(dsi)
        sg = setool.byte_field_stats(gtt)
        score, lag = setool.best_field_alignment(sd, sg)
        self.assertEqual(lag, 0)
        self.assertGreater(score, 2.5)
        self.assertLess(setool.field_alignment_score(sd, sg, 4), 1.0)
        diffs = [abs(sd[0][k] - sg[0][k]) for k in range(8, setool.FRAME_STRIDE)]
        self.assertLess(sum(diffs) / len(diffs), 0.05)
        # The one clear exception is marker+12, where .dsi has extra data.
        self.assertGreater(abs(sd[0][12] - sg[0][12]), 0.3)

    def test_gtt_metadata_framing(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.driver, "Henrik Roos")
                self.assertEqual(e.co_driver, "Gabriele Gardel")
                self.assertTrue(e.car.lower().endswith(".car"))
                self.assertGreater(e.metadata_offset, 0)

    def test_gtr2_replay_metadata(self):
        files = _files(".vcr")
        if not files:
            self.skipTest("GTR2 VCR files not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertTrue(e.team)
                self.assertTrue(e.driver)
                self.assertIsNone(e.co_driver)
                self.assertTrue(e.car.lower().endswith(".car"))

    def test_rf1_replay_metadata(self):
        base = ROOT.parent / "RF1Vanilla"
        files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() == ".vcr"]
        if not files:
            self.skipTest("rF1 replays not present")
        for p in files:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, "IRSR")
                self.assertTrue(e.trk.lower().endswith(".scn"))
                self.assertTrue(e.aiw.lower().endswith(".aiw"))
                self.assertEqual(e.driver, "Shovas")
                self.assertTrue(e.car.lower().endswith(".veh"))
                self.assertIsNone(e.co_driver)

    def test_bmw_and_gtl_metadata(self):
        bmw = ROOT.parent / "BMWM3Challenge"
        gtl = ROOT.parent / "GTLSteam"
        cases = []
        for base, kind in ((bmw, "GTTF"), (gtl, "IRSR")):
            if not base.exists():
                continue
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if Path(p).is_file() and Path(p).suffix.lower() in (".gtt", ".vcr"):
                    cases.append((Path(p), kind))
        if not cases:
            self.skipTest("BMW M3 / GTL events not present")
        for p, kind in cases:
            with self.subTest(path=p.name):
                e = setool.parse_file(p)
                self.assertEqual(e.kind, kind)
                self.assertTrue(e.driver)
                self.assertTrue(e.car.lower().endswith((".car", ".veh")))
                if kind == "GTTF":
                    self.assertTrue(e.co_driver)
                else:
                    self.assertIsNone(e.co_driver)

    def test_driver_and_car_strings_extracted(self):
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        e = setool.parse_file(files[0])
        joined = " ".join(s for _, s in e.strings)
        self.assertIn("Henrik Roos", joined)
        self.assertIn(".CAR", joined)


    def test_superleague_rf1_irsr_prefix(self):
        """Superleague replays use an ffff prefix variant and still parse."""
        import os
        paths = [p for p in glob.glob(
            str(ROOT.parent / "SuperleagueFormula2009" / "**" / "*"), recursive=True)
            if os.path.isfile(p) and p.lower().endswith(".vcr")]
        if len(paths) < 6:
            self.skipTest("Superleague replay corpus not present")
        prefixes = set()
        for p in paths:
            ev = setool.parse_file(p)
            self.assertEqual(ev.kind, "IRSR")
            self.assertTrue(ev.driver, p)
            self.assertTrue(ev.car.lower().endswith(".veh"), p)
            raw = Path(p).read_bytes()
            data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
            i = data.find(b"IRSR") + 8
            for _ in range(4):
                n = struct.unpack_from("<I", data, i)[0]
                i += 4 + n
            prefixes.add(data[i:i+4].hex())
        self.assertIn("0000ffff", prefixes)
        self.assertIn("00004803", prefixes)


    def test_gtt_steering_field(self):
        """GTTF frame +16 is steering (bounded -1..1, tracks heading rate)."""
        import gzip
        import struct
        files = _files(".gtt")
        if len(files) < 20:
            self.skipTest("GTT corpus not present")
        checked = 0
        corrs = []
        for p in files:
            raw = Path(p).read_bytes()
            data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
            grid = setool.find_frame_grid(data)
            if not grid:
                continue
            frames = setool.read_frames(data, grid)
            if len(frames) < 100:
                continue
            for f in frames:
                self.assertGreaterEqual(f["steering"], -1.01, p)
                self.assertLessEqual(f["steering"], 1.01, p)
            head = [f["heading"] for f in frames]
            dh = [(head[i+1]-head[i]+math.pi) % (2*math.pi)-math.pi
                  for i in range(len(head)-1)]
            sv = [f["steering"] for f in frames][:len(dh)]
            # Pearson r
            mx = sum(sv)/len(sv); my = sum(dh)/len(dh)
            vx = sum((a-mx)**2 for a in sv); vy = sum((b-my)**2 for b in dh)
            if vx and vy:
                r = sum((a-mx)*(b-my) for a, b in zip(sv, dh))/math.sqrt(vx*vy)
                corrs.append(r)
            checked += 1
        self.assertGreater(checked, 20)
        # Corpus-level: most files show a clear steering/heading-rate relation.
        self.assertGreater(sum(1 for r in corrs if abs(r) > 0.2), len(corrs)//2)


    def test_cli_reports_decoded_fields(self):
        """--frames exposes world position, engine speed and recovered channels."""
        import subprocess
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        result = subprocess.run(
            [sys.executable, str(ROOT / "simbin_events_tool.py"), "--frames", str(files[0])],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for token in ("first_world=", "engine_speed=", "slot48=", "path_controls="):
            self.assertIn(token, result.stdout)


    def test_slot48_signed_channels(self):
        """Frame slot +48 exposes two signed channel readings."""
        import gzip
        files = _files(".gtt")
        if not files:
            self.skipTest("GTR2 GTT files not present")
        data = gzip.decompress(files[0].read_bytes())
        frames = setool.read_frames(data, setool.find_frame_grid(data))
        self.assertGreater(len(frames), 100)
        for frame in frames[:10]:
            self.assertIsNotNone(frame["slot48_low"])
            self.assertIsNotNone(frame["slot48_high"])
            self.assertGreaterEqual(frame["slot48_low"], -32768)
            self.assertLessEqual(frame["slot48_high"], 32767)


    def test_replay_cli_reports_decoded_stream(self):
        """--replay reports participants, summary and the parsed frame stream."""
        import subprocess
        import sys
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Anderstorp.Vcr"
        if not path.is_file():
            self.skipTest("Anderstorp.Vcr not present")
        result = subprocess.run(
            [sys.executable, str(ROOT / "simbin_events_tool.py"), str(path),
             "--replay", "--strings", "0"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("participants=2", result.stdout)
        self.assertIn("summary=", result.stdout)
        self.assertIn("frames_declared=121", result.stdout)
        self.assertIn("frames_total=203", result.stdout)
        self.assertIn("exact_end=True", result.stdout)
        self.assertIn("first_driver_position=", result.stdout)
        self.assertIn("first_driver_angle=", result.stdout)
        gtl = ROOT.parent / "GTLSteam" / "ReplayData" / "Anderstorp North.Vcr"
        if gtl.is_file():
            result = subprocess.run(
                [sys.executable, str(ROOT / "simbin_events_tool.py"), str(gtl),
                 "--replay", "--strings", "0"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("'version': 'v1.01'", result.stdout)
            self.assertIn("frames_declared=10564", result.stdout)
            self.assertIn("exact_end=True", result.stdout)


    def test_replay_shift_corpus_round_trip(self):
        """Shifting every shipped replay preserves structure and EOF."""
        import math
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st

        paths = sorted((ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"))
        paths += sorted((ROOT.parent / "GTLSteam" / "ReplayData").glob("*.Vcr"))
        self.assertGreaterEqual(len(paths), 13)
        checked = 0
        for path in paths:
            original = gz.decompress(str(path))
            parsed = st.parse_vcr_frames(original)
            if not parsed:
                continue
            self.assertEqual(parsed["end_offset"], len(original))
            offsets = [frame["offset"] for frame in parsed["frames"]]

            def times(payload):
                return [struct.unpack_from("<f", payload, offset)[0]
                        for offset in offsets]

            before = times(original)
            for delta in (64.0, -64.0):
                shifted = st.shift_replay_times(original, delta)
                after_parsed = st.parse_vcr_frames(shifted)
                self.assertEqual(after_parsed["end_offset"], len(shifted))
                self.assertEqual(len(after_parsed["frames"]), len(offsets))
                after = times(shifted)
                for first, second in zip(before, after):
                    self.assertTrue(math.isfinite(second))
                    self.assertAlmostEqual(second, first + delta, delta=0.02)
                self.assertEqual(after_parsed["summary"]["duration"],
                                 parsed["summary"]["duration"])
                self.assertEqual(gz.compress_simbin(shifted)[:2], b"\x1f\x8b")
            checked += 1
        self.assertGreaterEqual(checked, 13)

    def test_replay_channels_csv(self):
        """--channels emits the verified channels as parseable CSV rows."""
        import csv
        import io
        import subprocess
        import sys
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        path = (ROOT.parent / "GTR2Steam" / "ReplayData"
                / "Brno HOT LAP.Vcr")
        if not path.is_file():
            self.skipTest("Brno HOT LAP.Vcr not present")
        result = subprocess.run(
            [sys.executable, str(ROOT / "simbin_events_tool.py"), str(path),
             "--channels"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        self.assertGreater(len(rows), 10)
        self.assertEqual(list(rows[0]), ["frame", "time", "position_x",
                                         "position_y", "position_z", "angle",
                                         "pair_diff", "small_a"])
        states = []
        for frame in st.parse_vcr_frames(gz.decompress(str(path)))["frames"]:
            for record in frame["records"]:
                if st.vcr_record_tag(record["header"]) == 0:
                    state = st.vcr_driver_state(record["data"])
                    if state:
                        states.append(state)
                    break
        self.assertEqual(len(rows), len(states))
        for row, state in zip(rows, states):
            self.assertAlmostEqual(float(row["pair_diff"]),
                                   state["short_pair_difference"], places=3)
            self.assertAlmostEqual(float(row["small_a"]),
                                   state["small_a"], places=5)

        # Every shipped replay exports parseable rows with the same schema.
        total = 0
        for directory in (ROOT.parent / "GTR2Steam" / "ReplayData",
                          ROOT.parent / "GTLSteam" / "ReplayData"):
            for candidate in sorted(directory.glob("*.Vcr")):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "simbin_events_tool.py"),
                     str(candidate), "--channels"],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                exported = list(csv.DictReader(io.StringIO(result.stdout)))
                self.assertEqual(list(exported[0]), list(rows[0]))
                total += len(exported)
        self.assertGreater(total, 10000)

    def test_replay_exposes_pair_difference(self):
        """The steering-like short pair difference is available in API and CLI."""
        import subprocess
        import sys
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Brno.Vcr"
        if not path.is_file():
            self.skipTest("Brno.Vcr not present")
        parsed = st.parse_vcr_frames(gz.decompress(str(path)))
        states = []
        for frame in parsed["frames"]:
            for record in frame["records"]:
                if st.vcr_record_tag(record["header"]) == 0:
                    state = st.vcr_driver_state(record["data"])
                    if state:
                        states.append(state)
                    break
        self.assertTrue(states)
        for state in states:
            self.assertEqual(state["short_pair_difference"],
                             state["shorts"][0] - state["shorts"][1])
        result = subprocess.run(
            [sys.executable, str(ROOT / "simbin_events_tool.py"), str(path),
             "--replay", "--strings", "0"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("first_driver_pair_diff=", result.stdout)

    def test_replay_shift_cli(self):
        """--shift writes a valid container with consistently shifted times."""
        import subprocess
        import sys
        import tempfile
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Brno.Vcr"
        if not path.is_file():
            self.skipTest("Brno.Vcr not present")
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "shifted.Vcr"
            result = subprocess.run(
                [sys.executable, str(ROOT / "simbin_events_tool.py"), str(path),
                 "--shift", "64", "--out", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_bytes()[:2], b"\x1f\x8b")
            report = subprocess.run(
                [sys.executable, str(ROOT / "simbin_events_tool.py"), str(output),
                 "--replay", "--strings", "0"], capture_output=True, text=True)
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn("first_time=2412.187", report.stdout)
            self.assertIn("exact_end=True", report.stdout)


if __name__ == "__main__":
    unittest.main()
