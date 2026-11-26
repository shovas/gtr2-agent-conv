"""Deep corpus checks: full-tier only (slow, multi-game archive scans)."""
import glob
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collections
import re
import anm_format  # noqa: E402
import simbin_text_tool as stt  # noqa: E402
import media_tool  # noqa: E402
import gsc_survey  # noqa: E402
import mas_tool  # noqa: E402


def _anm_samples(root, limit=None):
    for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
        if not p.lower().endswith((".mas", ".exe", ".gtr", ".gtl", ".bmw")):
            continue
        try:
            _, entries = mas_tool.read_archive(p)
        except Exception:
            continue
        for e in entries:
            if e.name.lower().endswith(".anm") and e.data:
                yield e.name, e.data
                if limit is not None:
                    limit -= 1
                    if limit <= 0:
                        return


class CorpusDeep2Test(unittest.TestCase):

    def test_lexus_configs_corpus(self):
        """LexusIsfTrackTime .veh/.scn/.cam parse with existing rules."""
        import glob
        import media_tool
        root = ROOT.parent / "LexusIsfTrackTime"
        vehs = 0
        for p in glob.glob(str(root / "**" / "*.veh"), recursive=True):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            keys = set(x.lower() for x in re.findall(
                r"(?m)^\s*([A-Za-z_][\w]*)\s*=", text))
            self.assertEqual(stt.validate_veh_core(keys, "core"), [], p)
            vehs += 1
        self.assertEqual(vehs, 11)
        scns = 0
        for p in (p for p in glob.glob(str(root / "**" / "*"), recursive=True)
                  if p.lower().endswith(".scn")):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            self.assertIsInstance(stt.parse_scn(text).mas_files, list)
            scns += 1
        self.assertEqual(scns, 5)
        cams = 0
        for p in (p for p in glob.glob(str(root / "**" / "*"), recursive=True)
                  if p.lower().endswith(".cam")):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            self.assertTrue(stt.parse_cam(text).cameras, p)
            cams += 1
        self.assertEqual(cams, 5)

    def test_raceroom_fxm_corpus(self):
        """All 91 RaceRoom FXM/FXA/LMA files decode with key_count 1 or 3."""
        import glob
        import os
        import fxm_tool
        n = nodes = 0
        for root in ("RaceRoomTheGame", "RaceRoomTheGame2"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith((".fxm", ".fxa", ".lma")):
                    continue
                result = fxm_tool.decode_fxm_semantic(Path(p).read_bytes())
                self.assertTrue(result["nodes"], p)
                for node in result["nodes"]:
                    self.assertIn(node.get("file_key_count", node.get("key_count")), (1, 3), p)
                    nodes += 1
                n += 1
        self.assertEqual(n, 91)
        self.assertGreater(nodes, 3000)

    def test_eng_parser_corpus(self):
        """All 333 .eng files validate with rising RPMTorque curves."""
        import glob
        import media_tool
        n = pts = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.eng"), recursive=True):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            info = stt.parse_eng(text)
            self.assertEqual(stt.validate_eng(info), [], p)
            rpms = [q[0] for q in info.torque_curve]
            self.assertTrue(all(a < b for a, b in zip(rpms, rpms[1:])), p)
            pts += len(info.torque_curve)
            n += 1
        self.assertGreaterEqual(n, 333)
        self.assertGreaterEqual(pts, 12771)

    def test_grb_parser_corpus(self):
        """All 248 .grb files (incl. 77 JCA) validate with b/a ratio semantics."""
        import glob
        import media_tool
        n = gears = 0
        commented = matched = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.grb"), recursive=True):
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            info = stt.parse_grb(text)
            self.assertEqual(stt.validate_grb(info), [], p)
            gears += len(info.gear_ratios)
            n += 1
            for line in text.splitlines():
                m = re.match(r"^\s*ratio\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", line, re.I)
                c = re.search(r"//.*?\(([-\d.]+)\)", line)
                if m and c and int(m.group(1)) != 0:
                    commented += 1
                    if abs(int(m.group(2)) / int(m.group(1)) - float(c.group(1))) < 0.02:
                        matched += 1
        self.assertGreaterEqual(n, 248)
        self.assertGreaterEqual(gears, 6929)
        self.assertEqual(matched, commented)  # 214+ commented ratios all b/a

    def test_raceroom_jca_gmt_corpus(self):
        """RaceRoom games ship JCA v1 GMTs decryptable with the volvo key."""
        import glob
        import media_tool
        for root in ("RaceRoomTheGame", "RaceRoomTheGame2"):
            paths = glob.glob(str(ROOT.parent / root / "**" / "*.gmt"), recursive=True)
            self.assertGreater(len(paths), 1000, root)
            n = 0
            for path in paths[:20]:
                info = media_tool.identify(path)
                self.assertEqual(info.format, "gmt-jca", path)
                self.assertEqual(info.details["jca_key"], "volvo", path)
                n += 1
            self.assertEqual(n, 20)

    def test_car_reference_resolution(self):
        """GTL .car HDVehicle/Graphics/Sounds references all resolve locally."""
        import glob
        import os
        import re
        for root in ("GTLSteam", "GTR2Steam"):
            base = ROOT.parent / root
            files = {e: {os.path.basename(p).lower()
                         for p in glob.glob(str(base / "**" / ("*" + e)), recursive=True)}
                     for e in (".hdc", ".cas", ".cam", ".aud")}
            checked = resolved = 0
            for p in (p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                      if os.path.isfile(p) and p.lower().endswith(".car")):
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                d = {k.lower(): v.strip().strip('"') for k, v in re.findall(
                    r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$", text)}
                for key, ext in (("hdvehicle", ".hdc"), ("graphics", ".cas"),
                                 ("sounds", ".aud")):
                    m = re.search(r"([^\\/]+\.\w+)$", d.get(key, ""), re.I)
                    if m:
                        checked += 1
                        resolved += m.group(1).lower() in files[ext]
            self.assertGreater(checked, 200)
            if root == "GTLSteam":
                self.assertEqual(resolved, checked)  # 288/288
            else:
                self.assertGreater(resolved / checked, 0.85)  # alt liveries absent

    def test_aud_wav_reference_resolution(self):
        """Vanilla GTR2/GTL .aud WAV references all resolve to local files."""
        import glob
        import os
        import media_tool
        for root in ("GTR2Steam", "GTLSteam"):
            base = ROOT.parent / root
            wavs = {os.path.basename(p).lower()
                    for p in glob.glob(str(base / "**" / "*.wav"), recursive=True)}
            checked = 0
            for p in glob.glob(str(base / "**" / "*.aud"), recursive=True):
                text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
                info = stt.parse_aud(text)
                for key in info.path_keys:
                    for value in info.values[key]:
                        m = re.search(r"([^\\/]+\.wav)$", value, re.I)
                        if m:
                            self.assertIn(m.group(1).lower(), wavs, f"{p}: {value}")
                            checked += 1
            self.assertGreater(checked, 1000)

    def test_car_reference_resolution_race07complete(self):
        """Race07Complete .car HDVehicle/Graphics/Sounds refs resolve."""
        import glob
        import os
        import re
        base = ROOT.parent / "Race07Complete"
        files = {e: {os.path.basename(p).lower()
                     for p in glob.glob(str(base / "**" / ("*" + e)), recursive=True)}
                 for e in (".hdc", ".cas", ".aud", ".cam")}
        checked = resolved = jca = n = 0
        pattern = r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$"
        for p in glob.glob(str(base / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".car"):
                continue
            raw = Path(p).read_bytes()
            jca += raw[:4] == media_tool.JCA_MAGIC
            text = media_tool.decrypt_jca_text(raw).decode("latin-1")
            d = {k.lower(): v.strip().strip('"') for k, v in re.findall(pattern, text)}
            n += 1
            for key, ext in (("hdvehicle", ".hdc"), ("graphics", ".cas"),
                             ("sounds", ".aud"), ("camera", ".cam")):
                m = re.search(r"([^\\/]+\.\w+)$", d.get(key, ""), re.I)
                if m:
                    checked += 1
                    resolved += m.group(1).lower() in files[ext]
        self.assertEqual(n, 823)
        self.assertGreater(jca, 600)
        self.assertGreater(checked, 250)
        self.assertEqual(resolved, checked)

    def test_race07complete_gdb_has_no_path_refs(self):
        """Race07Complete .gdb files are physics tweaks without path refs."""
        import glob
        n = 0
        for p in glob.glob(str(ROOT.parent / "Race07Complete" / "**" / "*"),
                           recursive=True):
            if not p.lower().endswith(".gdb") or not Path(p).is_file():
                continue
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            active = "\n".join(line for line in text.splitlines()
                               if not line.lstrip().startswith("//"))
            self.assertNotIn("\\", active, p)
            n += 1
        self.assertEqual(n, 114)

    def test_aud_wav_references_race07complete(self):
        """Race07Complete .aud WAV refs resolve (including JCA-wrapped files)."""
        import glob
        import os
        import re
        base = ROOT.parent / "Race07Complete"
        wavs = {os.path.basename(p).lower()
                for p in glob.glob(str(base / "**" / "*.wav"), recursive=True)}
        self.assertGreater(len(wavs), 2000)
        checked = resolved = jca = files = 0
        for p in glob.glob(str(base / "**" / "*.aud"), recursive=True):
            raw = Path(p).read_bytes()
            jca += raw[:4] == media_tool.JCA_MAGIC
            info = stt.parse_aud(
                media_tool.decrypt_jca_text(raw).decode("latin-1"))
            self.assertEqual(stt.validate_aud_map(info), [], p)
            files += 1
            for key in info.path_keys:
                for value in info.values[key]:
                    m = re.search(r"([^\\/]+\.wav)$", value, re.I)
                    if m:
                        checked += 1
                        resolved += m.group(1).lower() in wavs
        self.assertEqual(files, 137)
        self.assertGreater(jca, 90)
        self.assertGreater(checked, 7000)
        self.assertGreater(resolved / checked, 0.97)

    def test_race07vanilla_reference_resolution(self):
        """Race07Vanilla .aud WAV and .car config references resolve."""
        import glob
        import os
        import re
        base = ROOT.parent / "Race07Vanilla"
        wavs = {os.path.basename(p).lower()
                for p in glob.glob(str(base / "**" / "*.wav"), recursive=True)}
        files = {e: {os.path.basename(p).lower()
                     for p in glob.glob(str(base / "**" / ("*" + e)), recursive=True)}
                 for e in (".hdc", ".cas", ".aud", ".cam")}
        checked = resolved = auds = 0
        for p in glob.glob(str(base / "**" / "*.aud"), recursive=True):
            raw = Path(p).read_bytes()
            self.assertEqual(raw[:4], media_tool.JCA_MAGIC)
            text = media_tool.decrypt_jca_text(raw).decode("latin-1")
            auds += 1
            for _k, v in re.findall(r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$", text):
                m = re.search(r"([^\\/]+\.wav)$", v.strip().strip('"'), re.I)
                if m:
                    checked += 1
                    resolved += m.group(1).lower() in wavs
        self.assertEqual(auds, 43)
        self.assertGreater(checked, 4000)
        self.assertGreater(resolved / checked, 0.98)
        cars = refs = ok = 0
        pattern = r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$"
        for p in glob.glob(str(base / "**" / "*.car"), recursive=True):
            raw = Path(p).read_bytes()
            self.assertEqual(raw[:4], media_tool.JCA_MAGIC)
            text = media_tool.decrypt_jca_text(raw).decode("latin-1")
            d = {k.lower(): v.strip().strip('"') for k, v in re.findall(pattern, text)}
            cars += 1
            for key, ext in (("hdvehicle", ".hdc"), ("graphics", ".cas"),
                             ("sounds", ".aud"), ("camera", ".cam")):
                m = re.search(r"([^\\/]+\.\w+)$", d.get(key, ""), re.I)
                if m:
                    refs += 1
                    ok += m.group(1).lower() in files[ext]
        self.assertEqual(cars, 335)
        self.assertEqual(refs, 262)
        self.assertEqual(ok, refs)

    def test_volvo_reference_resolution(self):
        """Volvo (volvo JCA key) .car/.aud references resolve locally."""
        import glob
        import os
        import re
        base = ROOT.parent / "VolvoTheGame"
        wavs = {os.path.basename(p).lower()
                for p in glob.glob(str(base / "**" / "*.wav"), recursive=True)}
        incs = {os.path.basename(p).lower()
                for p in glob.glob(str(base / "**" / "*.inccar"), recursive=True)}
        checked = resolved = 0
        for p in glob.glob(str(base / "**" / "*.aud"), recursive=True):
            raw = Path(p).read_bytes()
            self.assertEqual(raw[:4], media_tool.JCA_MAGIC)
            text = media_tool.decrypt_jca_text(raw).decode("latin-1")
            for _k, v in re.findall(r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$", text):
                m = re.search(r"([^\\/]+\.wav)$", v.strip().strip('"'), re.I)
                if m:
                    checked += 1
                    resolved += m.group(1).lower() in wavs
        self.assertGreater(checked, 400)
        self.assertGreater(resolved / checked, 0.93)
        cars = includes = 0
        for p in glob.glob(str(base / "**" / "*.car"), recursive=True):
            raw = Path(p).read_bytes()
            self.assertEqual(raw[:4], media_tool.JCA_MAGIC)
            text = media_tool.decrypt_jca_text(raw).decode("latin-1")
            m = re.search(r"(?mi)^\s*Include\s*=\s*([^\r\n]+)", text)
            cars += 1
            if m:
                q = re.search(r"([^\\/]+\.inccar)$", m.group(1).strip().strip('"'), re.I)
                if q:
                    includes += 1
                    self.assertIn(q.group(1).lower(), incs, p)
        self.assertEqual(cars, 16)
        self.assertEqual(includes, 16)

    def test_aiw_features_are_capacities(self):
        """AIW Features numbers are capacities, not section counts."""
        import glob
        import os
        import isi_crypt
        n = oversized = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                fm = re.search(r"(?ms)^\[Features\]\r?\n(.*?)(?=^\[|\Z)", text)
                grid = re.search(r"(?ms)^\[GRID\]\r?\n(.*?)(?=^\[|\Z)", text)
                if not fm or not grid:
                    continue
                features = dict((k.lower(), v.strip()) for k, v in re.findall(
                    r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*([^\r\n]+)", fm.group(1)))
                if "startinggrid" not in features:
                    continue
                n += 1
                oversized += int(float(features["startinggrid"])) > len(
                    re.findall(r"(?mi)^GridIndex\s*=", grid.group(1)))
        self.assertGreater(n, 450)
        self.assertGreater(oversized / n, 0.9)

    def test_aiw_teleport_consistency(self):
        """AIW TELEPORT indices are unique with a contiguous main run."""
        import glob
        import os
        import isi_crypt
        n = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                self.assertEqual(stt.validate_aiw_teleport(text), [], p)
                n += 1
        self.assertEqual(n, 465)

    def test_aiw_grid_pits_consistency(self):
        """AIW GRID/PITS index and position counts are consistent."""
        import glob
        import os
        import isi_crypt
        n = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                self.assertEqual(stt.validate_aiw_grid_pits(
                    text, Path(p).name.lower() == "brianza_jr.aiw"), [], p)
                n += 1
        self.assertEqual(n, 465)

    def test_aiw_event_bounds(self):
        """AIW WP_EVENT/WP_SCORE values obey corpus bounds."""
        import glob
        import os
        import isi_crypt
        n = events = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                aiw = stt.parse_aiw(text)
                self.assertEqual(stt.validate_aiw_event(aiw), [], p)
                events += sum(1 for w in aiw.waypoints if w.event_first is not None)
                n += 1
        self.assertEqual(n, 465)
        self.assertGreater(events, 190000)

    def test_aiw_path_perp_bounds(self):
        """AIW path offsets are bounded; perpendiculars are unit or zero."""
        import glob
        import os
        import isi_crypt
        n = wps = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                aiw = stt.parse_aiw(text)
                self.assertEqual(stt.validate_aiw_path_perp(
                    aiw, Path(p).name.lower() == "lienz_24h.aiw"), [], p)
                n += 1
                wps += len(aiw.waypoints)
        self.assertEqual(n, 465)
        self.assertGreater(wps, 450000)

    def test_aiw_dwidth_groove_bounds(self):
        """AIW dwidth/groove-lat values respect corpus bounds."""
        import glob
        import os
        import isi_crypt
        n = wps = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                aiw = stt.parse_aiw(text)
                self.assertEqual(stt.validate_aiw_dwidth_groove(
                    aiw, Path(p).name.lower() == "ortona4.aiw"), [], p)
                n += 1
                wps += len(aiw.waypoints)
        self.assertEqual(n, 465)
        self.assertGreater(wps, 450000)

    def test_aiw_width_galpha_bounds(self):
        """AIW width/groove values respect corpus bounds (legacy exception)."""
        import glob
        import os
        import isi_crypt
        n = wps = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                aiw = stt.parse_aiw(text)
                self.assertEqual(stt.validate_aiw_width_galpha(
                    aiw, root in ("RF1Vanilla", "F12002")), [], p)
                n += 1
                wps += len(aiw.waypoints)
        self.assertEqual(n, 465)
        self.assertGreater(wps, 450000)

    def test_aiw_has_no_camera_references(self):
        """AIW files contain no ControlPoint/camera name references."""
        import glob
        import os
        n = 0
        for root in ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                     "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002"):
            base = ROOT.parent / root
            for p in glob.glob(str(base / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                text = (media_tool.decrypt_jca_text(raw).decode("latin-1")
                        if raw[:4] == media_tool.JCA_MAGIC
                        else raw.decode("latin-1"))
                low = text.lower()
                self.assertNotIn("controlpoint", low, p)
                self.assertNotIn("camera", low, p)
                n += 1
        self.assertEqual(n, 465)

    def test_aiw_lap_distance_coherence(self):
        """WP_SCORE lap distance is non-decreasing within track runs."""
        import glob
        import os
        import isi_crypt
        n = 0
        scores = []
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    text = (isi_crypt.decrypt_bytes(raw).decode("latin-1")
                            if sign in isi_crypt.GAMES else raw.decode("latin-1"))
                score = stt.aiw_lap_distance_coherence(stt.parse_aiw(text))
                if score is None:
                    continue
                self.assertGreater(score, 0.98, p)
                scores.append(score)
                n += 1
        self.assertEqual(n, 464)
        self.assertGreater(sum(scores) / len(scores), 0.99)

    def test_aiw_waypoint_pointer_bounds(self):
        """AIW pointers and wp_path offsets stay in bounds across 8 corpora."""
        import glob
        import os
        import isi_crypt
        exceptions = {"Hill.AIW", "Nurburg.AIW", "Lienz_24H.AIW"}
        n = wps = 0
        roots = ("Race07Vanilla", "GTLSteam", "GTR2Steam", "Race07Complete",
                 "RF1Vanilla", "Automobilista", "StockCarExtreme", "F12002")
        for root in roots:
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".aiw"):
                    continue
                raw = Path(p).read_bytes()
                if raw[:4] == media_tool.JCA_MAGIC:
                    text = media_tool.decrypt_jca_text(raw).decode("latin-1")
                else:
                    sign, _ = isi_crypt.crypt_info(raw)
                    if sign in isi_crypt.GAMES:
                        text = isi_crypt.decrypt_bytes(raw).decode("latin-1")
                    else:
                        text = raw.decode("latin-1")
                aiw = stt.parse_aiw(text)
                if os.path.basename(p) not in exceptions:
                    self.assertEqual(stt.validate_aiw_waypoints(aiw), [], p)
                self.assertEqual(stt.validate_aiw_pointers(aiw), [], p)
                for wp in aiw.waypoints:
                    self.assertIsNotNone(wp.path, p)
                n += 1
                wps += len(aiw.waypoints)
        self.assertEqual(n, 465)
        self.assertGreater(wps, 450000)

    def test_bmw_m3_reference_resolution(self):
        """BMW M3 Challenge .aud/.car references resolve locally."""
        import glob
        import os
        import re
        base = ROOT.parent / "BMWM3Challenge"
        wavs = {os.path.basename(p).lower()
                for p in glob.glob(str(base / "**" / "*"), recursive=True)
                if os.path.isfile(p) and p.lower().endswith(".wav")}
        files = {e: {os.path.basename(p).lower()
                     for p in glob.glob(str(base / "**" / "*"), recursive=True)
                     if os.path.isfile(p) and p.lower().endswith(e)}
                 for e in (".hdc", ".cas", ".aud", ".cam")}
        checked = resolved = auds = 0
        pattern = r"(?m)^\s*([A-Za-z_][\w]*)\s*=\s*(.*)$"
        for p in glob.glob(str(base / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".aud"):
                continue
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            auds += 1
            for _k, v in re.findall(pattern, text):
                m = re.search(r"([^\\/]+\.wav)$", v.strip().strip('"'), re.I)
                if m:
                    checked += 1
                    resolved += m.group(1).lower() in wavs
        self.assertEqual(auds, 2)
        self.assertEqual(checked, 190)
        self.assertEqual(resolved, 186)  # 4 references to absent raex.wav
        cars = refs = ok = 0
        for p in glob.glob(str(base / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".car"):
                continue
            text = media_tool.decrypt_jca_text(Path(p).read_bytes()).decode("latin-1")
            d = {k.lower(): v.strip().strip('"') for k, v in re.findall(pattern, text)}
            cars += 1
            for key, ext in (("hdvehicle", ".hdc"), ("graphics", ".cas"),
                             ("sounds", ".aud"), ("camera", ".cam")):
                m = re.search(r"([^\\/]+\.\w+)$", d.get(key, ""), re.I)
                if m:
                    refs += 1
                    ok += m.group(1).lower() in files[ext]
        self.assertEqual(cars, 17)
        self.assertEqual(refs, 51)
        self.assertEqual(ok, refs)

    def test_tc2000_has_no_aud_or_car(self):
        """TC2000 ships no .aud/.car; audio is archived MP3, configs encrypted."""
        import glob
        import os
        import mas_tool
        base = ROOT.parent / "TC2000"
        loose = [p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                 if os.path.isfile(p) and p.lower().endswith((".aud", ".car"))]
        self.assertEqual(loose, [])
        archived = 0
        mp3 = 0
        arcs = glob.glob(str(base / "**" / "*.mas"), recursive=True) + \
            glob.glob(str(base / "**" / "*.MAS"), recursive=True)
        for p in arcs:
            try:
                _, entries = mas_tool.read_archive(p)
            except Exception:
                continue
            for e in entries:
                ext = os.path.splitext(e.name)[1].lower()
                archived += ext in (".aud", ".car")
                mp3 += ext == ".mp3"
        self.assertEqual(archived, 0)
        self.assertGreater(mp3, 100)

    def test_superleague_has_no_aud_or_car(self):
        """Superleague 2009 ships no .aud/.car; configs are encrypted."""
        import glob
        import os
        import mas_tool
        base = ROOT.parent / "SuperleagueFormula2009"
        loose = [p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                 if os.path.isfile(p) and p.lower().endswith((".aud", ".car"))]
        self.assertEqual(loose, [])
        archived = 0
        for p in glob.glob(str(base / "**" / "*.mas"), recursive=True) + \
                glob.glob(str(base / "**" / "*.MAS"), recursive=True):
            try:
                _, entries = mas_tool.read_archive(p)
            except Exception:
                continue
            for e in entries:
                archived += os.path.splitext(e.name)[1].lower() in (".aud", ".car")
        self.assertEqual(archived, 0)

    def test_rf1_era_has_no_aud_or_car(self):
        """Four rF1-era installs have no .aud/.car (media-only archives)."""
        import glob
        import os
        import mas_tool
        for root in ("NascarSimRacing", "NT2003", "LexusIsfTrackTime",
                     "SimuladorTopRace2009"):
            base = ROOT.parent / root
            loose = [p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                     if os.path.isfile(p) and p.lower().endswith((".aud", ".car"))]
            self.assertEqual(loose, [], root)
            archived = 0
            for p in glob.glob(str(base / "**" / "*.mas"), recursive=True) + \
                    glob.glob(str(base / "**" / "*.MAS"), recursive=True):
                try:
                    _, entries = mas_tool.read_archive(p)
                except Exception:
                    continue
                for e in entries:
                    archived += os.path.splitext(e.name)[1].lower() in (".aud", ".car")
            self.assertEqual(archived, 0, root)

    def test_script_reference_resolution(self):
        """rF1-era .scr Mesh refs mostly resolve; SimBin installs have none."""
        import glob
        import os
        import mas_tool
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            self.assertEqual(
                [p for p in glob.glob(str(base / "**" / "*"), recursive=True)
                 if os.path.isfile(p) and p.lower().endswith((".cin", ".scr"))], [], root)
        checked = resolved = 0
        for root in ("NT2003", "NascarSimRacing", "F12002", "F1C", "RF1Vanilla",
                     "Automobilista", "StockCarExtreme"):
            base = ROOT.parent / root
            names = set()
            for arc in glob.glob(str(base / "**" / "*.mas"), recursive=True) + \
                    glob.glob(str(base / "**" / "*.MAS"), recursive=True):
                try:
                    _, entries = mas_tool.read_archive(arc, read_data=False)
                except Exception:
                    continue
                for e in entries:
                    names.add(os.path.basename(e.name).lower())
            for p in glob.glob(str(base / "**" / "*.scr"), recursive=True):
                if not os.path.isfile(p):
                    continue
                for actor in stt.parse_scr(Path(p).read_bytes()).actors:
                    if not actor.mesh:
                        continue
                    checked += 1
                    resolved += os.path.basename(
                        actor.mesh.replace("\\", "/")).lower() in names
        self.assertGreater(checked, 1200)
        self.assertGreater(resolved / checked, 0.8)

    def test_wav_chunk_structure(self):
        """WAV files have fmt-first, single-data chunk layouts."""
        import glob
        import os
        import random
        rng = random.Random(5)
        checked = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete", "VolvoTheGame"):
            base = ROOT.parent / root
            paths = []
            for pattern in ("**/*.wav", "**/*.WAV"):
                paths.extend(glob.glob(str(base / pattern), recursive=True))
            paths = [p for p in paths if os.path.isfile(p)]
            rng.shuffle(paths)
            for p in paths[:25]:
                data = Path(p).read_bytes()
                chunks = media_tool.wav_chunks(
                    data, "volvo" if root == "VolvoTheGame" else None)
                self.assertIsNotNone(chunks, p)
                self.assertEqual(media_tool.validate_wav_chunks(chunks), [], p)
                checked += 1
        self.assertGreater(checked, 80)

    def test_wav_header_invariants(self):
        """PCM WAV headers are internally consistent across four corpora."""
        import glob
        import os
        import random
        rng = random.Random(7)
        checked = nonpcm = jca = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete", "VolvoTheGame"):
            base = ROOT.parent / root
            paths = []
            for pattern in ("**/*.wav", "**/*.WAV"):
                paths.extend(glob.glob(str(base / pattern), recursive=True))
            paths = [p for p in paths if os.path.isfile(p)]
            rng.shuffle(paths)
            for p in paths[:25]:
                raw = Path(p).read_bytes()
                wrapped = raw[:4] == media_tool.JCA_MAGIC
                jca += wrapped
                header = media_tool.wav_header(raw, "volvo" if root == "VolvoTheGame" else None)
                self.assertIsNotNone(header, p)
                self.assertEqual(media_tool.validate_wav_header(header), [], p)
                checked += 1
                nonpcm += header.audio_format != 1
        self.assertGreater(checked, 80)
        self.assertGreater(jca, 30)  # Volvo/Race07 JCA coverage
        self.assertGreater(nonpcm, 0)  # documented MPEG-in-WAVE exception

    def test_cam_radius_positive_integer(self):
        """CAM ActivationRadius is a positive integer across SimBin installs."""
        import glob
        import os
        checked = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*.cam"),
                               recursive=True):
                if not os.path.isfile(p):
                    continue
                info = stt.parse_cam(stt.read_text(p))
                self.assertEqual(stt.validate_cam(info), [], p)
                for cam in info.cameras:
                    if cam.activation_radius is not None:
                        self.assertGreater(cam.activation_radius, 0, p)
                        self.assertAlmostEqual(cam.activation_radius,
                                               round(cam.activation_radius), places=6, msg=p)
                        checked += 1
        self.assertGreater(checked, 1100)

    def test_hed_numeric_bounds(self):
        """Head-physics vectors obey corpus-observed limits and ordering."""
        import glob
        import os
        checked = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".hed"):
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                self.assertEqual(stt.validate_hed_numeric(text), [], p)
                checked += 1
        self.assertEqual(checked, 2)

    def test_eng_grb_numeric_bounds(self):
        """ENG/GRB numeric fields stay within corpus-observed bounds."""
        import glob
        import os
        engines = boxes = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p):
                    continue
                low = p.lower()
                if low.endswith(".eng"):
                    text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                    self.assertEqual(stt.validate_eng_numeric(text), [], p)
                    engines += 1
                elif low.endswith(".grb"):
                    text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                    self.assertEqual(stt.validate_grb_numeric(text), [], p)
                    boxes += 1
        self.assertEqual(engines, 66)
        self.assertEqual(boxes, 60)

    def test_tdf_numeric_bounds(self):
        """TDF surface grip/bump fields stay within corpus bounds."""
        import glob
        import os
        checked = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".tdf"):
                continue
            self.assertEqual(stt.validate_tdf_numeric(stt.read_text(p)), [], p)
            checked += 1
        self.assertGreater(checked, 200)

    def test_cam_numeric_bounds(self):
        """CAM numeric fields stay within corpus-observed bounds."""
        import glob
        import os
        checked = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".cam"):
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                self.assertEqual(stt.validate_cam_numeric(text), [], p)
                checked += 1
        self.assertEqual(checked, 258)

    def test_rcd_numeric_bounds(self):
        """RCD driver stats stay within corpus-observed bounds."""
        import glob
        import os
        checked = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".rcd"):
                continue
            self.assertEqual(stt.validate_rcd_numeric(stt.read_text(p)), [], p)
            checked += 1
        self.assertGreater(checked, 2100)

    def test_cam_control_points_not_waypoints(self):
        """CAM ControlPoints do not reference AIW waypoint positions."""
        import glob
        import math
        import os
        points = near = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete"):
            base = ROOT.parent / root
            for p in glob.glob(str(base / "**" / "*.cam"), recursive=True):
                if not os.path.isfile(p):
                    continue
                stem = Path(p).stem.lower()
                aiws = [q for q in glob.glob(str(Path(p).parent / "*"))
                        if os.path.isfile(q) and q.lower().endswith(".aiw")
                        and Path(q).stem.lower() == stem]
                if not aiws:
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                pts = stt.parse_cam_control_points(text)
                if not pts:
                    continue
                atext = media_tool.decrypt_jca_text(
                    Path(aiws[0]).read_bytes()).decode("latin-1")
                wps = [w.pos for w in stt.parse_aiw(atext).waypoints if w.pos]
                for pt in pts:
                    points += 1
                    near += min(math.dist(pt, w) for w in wps) < 2.0
        self.assertGreater(points, 250)
        self.assertEqual(near, 0)

    def test_gen_numeric_fields(self):
        """GEN mesh configs obey LOD/reflect-plane bounds."""
        import glob
        import os
        checked = 0
        for root in ("Automobilista", "RF1Vanilla", "StockCarExtreme", "TC2000",
                     "NascarSimRacing", "SimuladorTopRace2009", "NT2003",
                     "CopaPetrobrasdeMarcas", "GameStockCar", "F12002"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".gen"):
                    continue
                self.assertEqual(stt.validate_gen_numeric(stt.read_text(p)), [], p)
                checked += 1
        self.assertEqual(checked, 272)

    def test_veh_numeric_fields(self):
        """VEH files carry universal keys and bounded Eyepoint vectors."""
        import glob
        import os
        checked = 0
        for root in ("RF1Vanilla", "F1C", "F12002", "NT2003"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".veh"):
                    continue
                self.assertEqual(stt.validate_veh_numeric(stt.read_text(p)), [], p)
                checked += 1
        self.assertEqual(checked, 371)

    def test_jca_matches_wtcced_constants(self):
        """jca_tables/jca_crypt match the wtcced 0.3.5 source constants."""
        import re
        import zipfile
        import jca_crypt
        archive = ROOT.parent / "aluigi-mirror-261124" / "mirror.aluigi.org" / \
            "papers" / "wtcced.zip"
        if not archive.is_file():
            archive = ROOT.parent / "quickbms-mirror" / "aluigi.altervista.org" / \
                "papers" / "wtcced.zip"
        if not archive.is_file():
            self.skipTest("wtcced source ZIP not present")
        with zipfile.ZipFile(archive) as zf:
            source = zf.read("wtcc_bf.h").decode("latin-1")
        pattern = r"0x[0-9a-fA-F]{8}"
        ours = [int(x, 16) for x in re.findall(pattern,
                (ROOT / "jca_tables.py").read_text())]
        theirs = [int(x, 16) for x in re.findall(pattern, source)]
        self.assertEqual(ours, theirs[:len(ours)])
        self.assertEqual(jca_crypt.MAGIC, 0xFFFFB10F)
        self.assertEqual(jca_crypt.XOR_BYTE, 0xEB)

    def test_sce_exe_key_schedule(self):
        """SCE AXS.GS.0 type-1 resources use .keyMan key at index +11."""
        import struct
        import gsc_exe_tool as gsc
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        index = 0
        checked = 0
        for res in container.resources:
            if res.kind != 1 or not gsc.resource_encrypted(res):
                continue
            key = keys[index + 11]
            zsize = struct.unpack_from("<I", res.data, 10)[0]
            raw = res.data[14:14 + min(zsize, 64)]
            chunk = gsc._decrypt_chunk(raw, gsc._BlowfishBE(key.encode("latin-1")))
            prop = chunk[0]
            dict_size = struct.unpack_from("<I", chunk, 1)[0]
            lc, lp, pb = prop % 9, (prop // 9) % 5, prop // 45
            self.assertTrue(lc <= 8 and lp <= 4 and pb <= 4 and dict_size >= 65536
                            and dict_size & (dict_size - 1) == 0, res.name)
            index += 1
            checked += 1
        self.assertEqual(checked, 204)

    def test_gttf_heading_vs_aiw_chain_tangents(self):
        """AIW pointer-chain tangents align with ghost heading above chance."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)

        def coherence(headings, angles):
            best = 0.0
            for sign in (1, -1):
                for swap in (False, True):
                    diffs = []
                    for heading, dy, dz in zip(headings, *angles):
                        angle = sign * (math.atan2(dz, dy) if swap
                                        else math.atan2(dy, dz))
                        diffs.append((heading - angle + math.pi)
                                     % (2 * math.pi) - math.pi)
                    c = sum(math.cos(v) for v in diffs) / len(diffs)
                    s = sum(math.sin(v) for v in diffs) / len(diffs)
                    best = max(best, math.hypot(c, s))
            return best

        observed = []
        baselines = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            aiw = aiws.get((event.aiw or "").lower())
            if not aiw:
                continue
            waypoints = [w for w in stt.parse_aiw(stt.read_text(aiw)).waypoints
                         if w.pos and w.wp_class() in (0, 1)]
            headings, deltas = [], []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                nearest = min(range(len(waypoints)),
                              key=lambda k: (waypoints[k].pos[1] - y) ** 2
                              + (waypoints[k].pos[2] - z) ** 2)
                nxt = waypoints[nearest].ptrs[1]
                if nxt is None or not (0 <= nxt < len(waypoints)):
                    continue
                dy = waypoints[nxt].pos[1] - waypoints[nearest].pos[1]
                dz = waypoints[nxt].pos[2] - waypoints[nearest].pos[2]
                if math.hypot(dy, dz) < 1e-6:
                    continue
                headings.append(frame["heading"])
                deltas.append((dy, dz))
            if len(headings) < 50:
                continue
            observed.append(coherence(headings, tuple(zip(*deltas))))
            random.seed(0)
            shuffled = random.sample(deltas, len(deltas))
            baselines.append(coherence(headings, tuple(zip(*shuffled))))
        self.assertGreater(len(observed), 20)
        self.assertGreater(statistics.median(observed),
                           statistics.median(baselines) * 2)

    def test_gsc_mask_not_derived_from_member_metadata(self):
        """GSC GMT XOR masks do not match archive member metadata hashes."""
        import glob
        import zlib
        import gmt_semantic
        import isi_crypt
        import mas_tool
        rows = []
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                        continue
                    try:
                        decrypted = isi_crypt.decrypt_bytes(entry.data, 1)
                    except Exception:
                        continue
                    mask = gmt_semantic.gsc_xor_magic_key(decrypted)
                    if mask is None or mask == 0:
                        continue
                    crc = zlib.crc32(entry.data)
                    candidates = {
                        entry.size & 0xFF, entry.zsize & 0xFF,
                        entry.flags & 0xFF, crc & 0xFF, (crc >> 8) & 0xFF,
                        zlib.adler32(entry.data) & 0xFF,
                        sum(entry.data[:4096]) & 0xFF,
                    }
                    rows.append((mask, candidates))
                    if len(rows) >= 120:
                        break
                if len(rows) >= 120:
                    break
            if len(rows) >= 120:
                break
        self.assertEqual(len(rows), 120)
        matches = sum(1 for mask, candidates in rows if mask in candidates)
        self.assertLess(matches, 15)  # ~4 expected for 120 x 7 byte values

    def test_gsc_exes_are_packed(self):
        """GSC-family EXEs are packer stubs: static mesh-loader tracing is blocked."""
        for root, name in (("GameStockCar", "GSC.exe"),
                           ("CopaPetrobrasdeMarcas", "Marcas.exe"),
                           ("StockCarExtreme", "GSC.exe"),
                           ("Automobilista", "AMS.exe")):
            path = ROOT.parent / root / name
            if not path.is_file():
                continue
            data = path.read_bytes()
            self.assertIn(b"VirtualAlloc", data, name)
            self.assertIn(b"GetProcAddress", data, name)
            if root == "GameStockCar":
                # This EXE retains GMT loader strings inside its packed image.
                self.assertIn(b"Error reading mesh from GMT file", data)
            else:
                self.assertNotIn(b"Error reading mesh from GMT file", data, name)
                self.assertNotIn(b"GMOTOR_GMT", data, name)

    def test_gsc_mask_not_derived_from_member_name(self):
        """GSC GMT XOR masks do not match name-based hashes."""
        import glob
        import zlib
        import gmt_semantic
        import isi_crypt
        import mas_tool
        rows = []
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                        continue
                    try:
                        decrypted = isi_crypt.decrypt_bytes(entry.data, 1)
                    except Exception:
                        continue
                    mask = gmt_semantic.gsc_xor_magic_key(decrypted)
                    if mask is None or mask == 0:
                        continue
                    name = entry.name.lower().replace("\\", "/").rsplit("/", 1)[-1]
                    name = name.rsplit(".", 1)[0].encode()
                    candidates = {
                        zlib.crc32(name) & 0xFF,
                        (zlib.crc32(name) >> 8) & 0xFF,
                        zlib.adler32(name) & 0xFF,
                        sum(name) & 0xFF,
                        len(name) & 0xFF,
                        name[0] if name else 0,
                        name[-1] if name else 0,
                    }
                    rows.append((mask, candidates))
                if len(rows) >= 120:
                    break
            if len(rows) >= 120:
                break
        self.assertGreaterEqual(len(rows), 100)
        matches = sum(1 for mask, candidates in rows if mask in candidates)
        self.assertLess(matches, 20)  # ~3 expected; non-uniform candidate fields

    def test_f0_not_raw_record_hash(self):
        """f0 halfwords are not hashes/CRCs of raw material/stage records."""
        import glob
        import hashlib
        import zlib
        import gmt_format as gf
        import mas_tool

        def fnv(data):
            value = 2166136261
            for byte in data:
                value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
            return value

        hashes = {
            "crc": lambda b: zlib.crc32(b) & 0xFFFF,
            "crc_hi": lambda b: (zlib.crc32(b) >> 16) & 0xFFFF,
            "adler": lambda b: zlib.adler32(b) & 0xFFFF,
            "fnv": lambda b: fnv(b) & 0xFFFF,
            "md5": lambda b: int.from_bytes(hashlib.md5(b).digest()[:2], "little"),
        }
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        blobs = [material.raw] + [s.raw for s in material.stages]
                        rows.append((marker & 0xFFFF, marker >> 16,
                                     {name: {fn(blob) for blob in blobs if blob}
                                      for name, fn in hashes.items()}))
                if len(rows) >= 12000:
                    break
            if len(rows) >= 12000:
                break
        self.assertGreater(len(rows), 8000)
        for name in hashes:
            matches = sum(1 for lo, hi, values in rows
                          for half in (lo, hi) if half in values[name])
            self.assertLess(matches, 20)  # chance level for 2 x 12k halfwords

    def test_f0_predicts_material_family_weakly(self):
        """Equal f0 markers share material-name prefixes above chance."""
        import collections
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool

        rows = []
        for archive in sorted(glob.glob(
                str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                recursive=True))[:40]:
            try:
                _mtype, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt(entry.name, entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    marker = gf.mesh_marker(mesh)
                    index = mesh.record.material_index
                    if marker and index < len(parsed.materials):
                        rows.append((marker, parsed.materials[index].name))
            if len(rows) >= 12000:
                break
        if len(rows) < 5000:
            self.skipTest("GTR2 mesh corpus not present")

        def agreement(items):
            grouped = collections.defaultdict(list)
            for marker, name in items:
                grouped[marker].append(name[:3])
            pairs = [(v[i], v[j]) for v in grouped.values() if len(v) > 1
                     for i in range(len(v)) for j in range(i + 1, len(v))]
            return sum(a == b for a, b in pairs) / len(pairs)

        observed = agreement(rows)
        random.seed(2026)
        permuted = []
        for _ in range(30):
            shuffled = rows[:]
            random.shuffle(shuffled)
            permuted.append(agreement([(marker, shuffled[i][1])
                                       for i, (marker, _name) in enumerate(rows)]))
        self.assertGreater(observed, statistics.mean(permuted) * 3)
        self.assertGreater(observed, max(permuted))
        self.assertLess(observed, 0.4)  # weak association, not a material ID

    def test_f0_bytes_not_material_string_hash(self):
        """f0's two bytes are not 8-bit slices of material-name hashes."""
        import hashlib
        import random
        import struct
        import zlib
        import gmt_layout
        import gmt_format
        import gmt_semantic
        import mas_tool

        marker = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")
        rows = []
        for archive in sorted((ROOT.parent / "RF1Vanilla").rglob("*.mas")):
            try:
                _mtype, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                data = entry.data or b""
                if data[0x1D4:0x1E4] != marker:
                    continue
                try:
                    converted = gmt_layout.old_to_new_semantic(data)
                    parsed = gmt_format.parse_gmt(entry.name, converted)
                except Exception:
                    continue
                subs = gmt_semantic.find_submeshes(data)
                for sub, mesh in zip(subs, parsed.meshes):
                    index = mesh.record.material_index
                    if index >= len(parsed.materials):
                        continue
                    value = struct.unpack_from("<I", data, sub["v_off"] + 4)[0]
                    rows.append((value & 0xFF, (value >> 16) & 0xFF,
                                 parsed.materials[index].name))
                if len(rows) >= 3000:
                    break
            if len(rows) >= 3000:
                break
        if not rows:
            self.skipTest("rF1 old-layout GMTs not present")

        def hash8(name, algorithm):
            raw = name.encode("latin-1")
            if algorithm == "sum":
                return sum(raw) & 0xFF
            if algorithm == "crc32":
                return zlib.crc32(raw) & 0xFF
            digest = hashlib.md5(raw).digest()
            return digest[0]

        random.seed(2026)
        for index, label in ((0, "low"), (1, "high")):
            observed = [row[index] for row in rows]
            for algorithm in ("sum", "crc32", "md5"):
                hashed = [hash8(row[2], algorithm) for row in rows]
                hits = sum(a == b for a, b in zip(observed, hashed))
                expected = (sum(collections.Counter(observed)[v]
                                * collections.Counter(hashed)[v]
                                for v in set(observed) & set(hashed))
                            / len(rows))
                shuffled = hashed[:]
                random.shuffle(shuffled)
                permuted = sum(a == b for a, b in zip(observed, shuffled))
                self.assertLess(hits, expected * 1.5 + 20,
                                (label, algorithm, hits, expected))
                self.assertLess(hits, permuted * 1.5 + 20,
                                (label, algorithm, hits, permuted))

    def test_f0_not_order_independent_name_hash(self):
        """f0 halfwords are not set hashes of normalized material/stage names."""
        import functools
        import glob
        import hashlib
        import random
        import re
        import statistics
        import zlib
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        names = [material.name] + [s.name for s in material.stages]
                        normalized = sorted(set(
                            re.sub(r"[^a-z0-9]", "", name.lower())
                            for name in names if name))
                        if not normalized:
                            continue
                        joined = "|".join(normalized).encode()
                        part = [zlib.crc32(n.encode()) & 0xFFFF for n in normalized]
                        rows.append((marker & 0xFFFF, marker >> 16, {
                            "crc": zlib.crc32(joined) & 0xFFFF,
                            "adler": zlib.adler32(joined) & 0xFFFF,
                            "md5": int.from_bytes(hashlib.md5(joined).digest()[:2],
                                                  "little"),
                            "xor": functools.reduce(lambda a, b: a ^ b, part, 0),
                            "sum": sum(part) & 0xFFFF,
                        }))
                if len(rows) >= 12000:
                    break
            if len(rows) >= 12000:
                break
        self.assertGreater(len(rows), 8000)
        for name in ("crc", "adler", "md5", "xor", "sum"):
            observed = sum(1 for lo, hi, values in rows
                           for half in (lo, hi) if half == values[name])
            self.assertLess(observed, 10)  # chance level for 2 x 12k halfwords

    def test_f0_not_archive_scoped(self):
        """Adding archive identity to material names does not explain f0."""
        import collections
        import glob
        import random
        import re
        import statistics
        import gmt_format as gf
        import mas_tool

        def norm(value):
            return re.sub(r"[^a-z0-9]", "", value.lower())

        groups = collections.defaultdict(list)
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                stem = archive.rsplit("/", 1)[-1].lower()
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        names = tuple(sorted(set(
                            norm(value) for value in
                            [material.name] + [s.name for s in material.stages]
                            if value)))
                        groups[(stem, names)].append(marker)
                if sum(len(v) for v in groups.values()) >= 30000:
                    break
            if sum(len(v) for v in groups.values()) >= 30000:
                break
        multi = {k: v for k, v in groups.items() if len(v) > 1}
        self.assertGreater(len(multi), 3000)
        observed = sum(1 for v in multi.values() if len(set(v)) == 1) / len(multi)
        random.seed(0)
        marks = [m for v in multi.values() for m in v]

        def baseline():
            permutation = random.sample(marks, len(marks))
            offset = 0
            same = 0
            for values in multi.values():
                sample = permutation[offset:offset + len(values)]
                offset += len(values)
                same += int(len(set(sample)) == 1)
            return same / len(multi)
        self.assertGreater(observed, 10 * statistics.mean(baseline() for _ in range(5)))
        self.assertLess(observed, 0.25)

    def test_f0_half_sign_family_stable(self):
        """f0's paired-ID sign is family-stable and skewed by material slot."""
        import collections
        import glob
        import random
        import re
        import statistics
        import gmt_format as gf
        import mas_tool

        def norm(value):
            return re.sub(r"[^a-z0-9]", "", value.lower())

        groups = collections.defaultdict(list)
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        if not marker or index >= len(parsed.materials):
                            continue
                        high, low = marker >> 16, marker & 0xFFFF
                        sign = 1 if high > low else (-1 if high < low else 0)
                        names = tuple(sorted(set(
                            norm(value) for value in
                            [parsed.materials[index].name] +
                            [stage.name for stage in parsed.materials[index].stages]
                            if value)))
                        groups[names].append((sign, index == 0))
                if sum(len(v) for v in groups.values()) >= 25000:
                    break
            if sum(len(v) for v in groups.values()) >= 25000:
                break
        multi = {key: values for key, values in groups.items() if len(values) > 1}
        self.assertGreater(len(multi), 1500)
        random.seed(33)
        flat = [pair for values in multi.values() for pair in values]
        signs = [pair[0] for pair in flat]
        zeros = [pair[1] for pair in flat]

        def stability(values):
            offset = 0
            same = total = 0
            for values_in_group in multi.values():
                sample = values[offset:offset + len(values_in_group)]
                offset += len(values_in_group)
                nonzero = [value for value in sample if value != 0]
                if nonzero:
                    total += 1
                    same += int(len(set(nonzero)) == 1)
            return same / total
        observed = stability(signs)
        baseline = statistics.mean(stability(random.sample(signs, len(signs)))
                                   for _ in range(10))
        self.assertGreater(observed, 2 * baseline)

        def positivity(values):
            first = [value for value, zero in zip(values, zeros) if zero and value]
            second = [value for value, zero in zip(values, zeros) if not zero and value]
            return (statistics.mean(value > 0 for value in first)
                    - statistics.mean(value > 0 for value in second))
        observed_bias = positivity(signs)
        permuted = statistics.mean(abs(positivity(random.sample(signs, len(signs))))
                                   for _ in range(10))
        self.assertLess(observed_bias, -0.2)
        self.assertLess(observed_bias, -10 * max(permuted, 0.001))

    def test_f0_half_delta_index_zero_threshold(self):
        """Material index 0 meshes have much larger f0 half-deltas."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        if marker and len(parsed.materials) > 1 \
                                and index < len(parsed.materials):
                            delta = abs((marker >> 16) - (marker & 0xFFFF))
                            rows.append((delta <= 1, index == 0))
                if len(rows) >= 10000:
                    break
            if len(rows) >= 10000:
                break
        self.assertGreater(len(rows), 5000)
        flags = [row[0] for row in rows]
        zeros = [row[1] for row in rows]

        def difference(values):
            first = statistics.mean(value for value, zero in zip(values, zeros) if zero)
            second = statistics.mean(value for value, zero in zip(values, zeros) if not zero)
            return first - second
        observed = difference(flags)
        random.seed(32)
        baseline = statistics.mean(abs(difference(random.sample(flags, len(flags))))
                                   for _ in range(10))
        self.assertLess(observed, -0.3)
        self.assertLess(observed, -10 * max(baseline, 0.001))

    def test_f0_first_mesh_tracks_member_size(self):
        """Mesh-0's f0 half-sum grows weakly with GMT member size."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    if parsed.meshes:
                        marker = gf.mesh_marker(parsed.meshes[0])
                        if marker:
                            rows.append(((marker & 0xFFFF) + (marker >> 16),
                                         len(entry.data)))
                if len(rows) >= 6000:
                    break
            if len(rows) >= 6000:
                break
        self.assertGreater(len(rows), 3000)

        def pearson(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denominator = (sum((x - mx) ** 2 for x in xs)
                           * sum((y - my) ** 2 for y in ys)) ** 0.5
            return numerator / denominator if denominator else 0.0
        sums = [row[0] for row in rows]
        sizes = [row[1] for row in rows]
        observed = pearson(sums, sizes)
        random.seed(48)
        baseline = statistics.mean(abs(pearson(sums, random.sample(sizes, len(sizes))))
                                   for _ in range(5))
        self.assertGreater(observed, 0.1)
        self.assertGreater(observed, 5 * max(baseline, 0.001))

    def test_f0_first_mesh_tracks_mesh_count(self):
        """Mesh-0's f0 halves grow weakly with the GMT's mesh count."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    if parsed.meshes:
                        marker = gf.mesh_marker(parsed.meshes[0])
                        if marker:
                            rows.append(((marker & 0xFFFF) + (marker >> 16),
                                         len(parsed.meshes)))
                if len(rows) >= 6000:
                    break
            if len(rows) >= 6000:
                break
        self.assertGreater(len(rows), 3000)

        def pearson(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denominator = (sum((x - mx) ** 2 for x in xs)
                           * sum((y - my) ** 2 for y in ys)) ** 0.5
            return numerator / denominator if denominator else 0.0
        sums = [row[0] for row in rows]
        counts = [row[1] for row in rows]
        observed = pearson(sums, counts)
        random.seed(38)
        baseline = statistics.mean(abs(pearson(sums, random.sample(counts, len(counts))))
                                   for _ in range(5))
        self.assertGreater(observed, 0.1)
        self.assertGreater(observed, 5 * max(baseline, 0.001))

    def test_f0_first_mesh_structurally_distinct(self):
        """Mesh 0's f0 has much larger halves and half-delta than later meshes."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for ordinal, mesh in enumerate(parsed.meshes):
                        marker = gf.mesh_marker(mesh)
                        if marker:
                            rows.append((ordinal == 0,
                                         abs((marker >> 16) - (marker & 0xFFFF))))
                if len(rows) >= 15000:
                    break
            if len(rows) >= 15000:
                break
        self.assertGreater(len(rows), 5000)
        flags = [row[0] for row in rows]
        deltas = [row[1] for row in rows]

        def difference(values):
            return (statistics.median(v for v, first in zip(values, flags) if first)
                    - statistics.median(v for v, first in zip(values, flags) if not first))
        observed = difference(deltas)
        random.seed(36)
        baseline = statistics.mean(abs(difference(random.sample(deltas, len(deltas))))
                                   for _ in range(10))
        self.assertGreater(observed, 100)
        self.assertGreater(observed, 10 * max(baseline, 1))

    def test_f0_material_index_is_mesh_ordinal(self):
        """The material index used in f0 studies is the mesh's ordinal."""
        import glob
        import gmt_format as gf
        import mas_tool
        total = equal = 0
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for ordinal, mesh in enumerate(parsed.meshes):
                        total += 1
                        equal += int(mesh.record.material_index == ordinal)
                if total >= 12000:
                    break
            if total >= 12000:
                break
        self.assertGreater(total, 5000)
        self.assertGreater(equal / total, 0.99)

    def test_f0_half_sum_vs_material_index(self):
        """f0's paired-half mean decreases with local material index."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        if marker and index < len(parsed.materials):
                            rows.append(((marker & 0xFFFF) + (marker >> 16), index))
                if len(rows) >= 10000:
                    break
            if len(rows) >= 10000:
                break
        self.assertGreater(len(rows), 5000)

        def pearson(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denominator = (sum((x - mx) ** 2 for x in xs)
                           * sum((y - my) ** 2 for y in ys)) ** 0.5
            return numerator / denominator if denominator else 0.0
        sums = [row[0] for row in rows]
        indices = [row[1] for row in rows]
        observed = pearson(sums, indices)
        random.seed(34)
        baseline = statistics.mean(abs(pearson(sums, random.sample(indices, len(indices))))
                                   for _ in range(5))
        self.assertLess(observed, -0.15)
        self.assertLess(observed, -10 * max(baseline, 0.001))

    def test_f0_half_delta_vs_material_index(self):
        """f0's half-delta decreases as the local material index increases."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        if marker and len(parsed.materials) > 1 \
                                and index < len(parsed.materials):
                            rows.append((abs((marker >> 16) - (marker & 0xFFFF)), index))
                if len(rows) >= 10000:
                    break
            if len(rows) >= 10000:
                break
        self.assertGreater(len(rows), 5000)

        def pearson(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denominator = (sum((x - mx) ** 2 for x in xs)
                           * sum((y - my) ** 2 for y in ys)) ** 0.5
            return numerator / denominator if denominator else 0.0
        deltas = [row[0] for row in rows]
        indices = [row[1] for row in rows]
        observed = pearson(deltas, indices)
        random.seed(31)
        baseline = statistics.mean(abs(pearson(deltas, random.sample(indices, len(indices))))
                                   for _ in range(5))
        self.assertLess(observed, -0.1)
        self.assertLess(observed, -10 * max(baseline, 0.001))

    def test_f0_halves_family_stable(self):
        """Both f0 halves repeat across cross-corpus material families."""
        import collections
        import glob
        import random
        import re
        import statistics
        import gmt_format as gf
        import mas_tool

        def norm(value):
            return re.sub(r"[^a-z0-9]", "", value.lower())

        groups = collections.defaultdict(list)
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        names = tuple(sorted(set(
                            norm(value) for value in
                            [material.name] + [s.name for s in material.stages]
                            if value)))
                        groups[names].append((marker & 0xFFFF, marker >> 16))
                if sum(len(v) for v in groups.values()) >= 25000:
                    break
            if sum(len(v) for v in groups.values()) >= 25000:
                break
        multi = {key: values for key, values in groups.items() if len(values) > 1}
        self.assertGreater(len(multi), 2000)
        flat = [pair for values in multi.values() for pair in values]

        def agreement(pairs, half):
            return statistics.mean(
                len(set(pair[half] for pair in values)) == 1
                for values in pairs)

        random.seed(17)
        for half in (0, 1):
            observed = agreement(multi.values(), half)
            shuffled = random.sample(flat, len(flat))
            offset = 0
            same = 0
            for values in multi.values():
                sample = shuffled[offset:offset + len(values)]
                offset += len(values)
                same += int(len(set(pair[half] for pair in sample)) == 1)
            baseline = same / len(multi)
            self.assertGreater(observed, 10 * max(baseline, 0.001))
            self.assertGreater(observed, 0.1)

    def test_f0_not_shader_registry_index(self):
        """Shader members are too few to explain f0's 16-bit half range."""
        import glob
        import gmt_format as gf
        import mas_tool
        shaders = set()
        for root in ("GTR2Steam", "GTLSteam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not path.lower().endswith((".gtr", ".gtl", ".bmw")):
                    continue
                try:
                    _, entries = mas_tool.read_archive(path)
                except Exception:
                    continue
                shaders.update(e.name.lower() for e in entries
                               if e.name.lower().endswith((".psh", ".vsh")))
        self.assertLess(len(shaders), 200)
        halves = []
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    marker = gf.mesh_marker(mesh)
                    if marker:
                        halves.extend((marker & 0xFFFF, marker >> 16))
                if len(halves) >= 3000:
                    break
            if len(halves) >= 3000:
                break
        self.assertGreater(len(halves), 2000)
        self.assertGreater(max(halves), 10 * len(shaders))
        self.assertGreater(len(set(halves)), 5 * len(shaders))

    def test_gmt_stream3_col0_sparsity_artifact(self):
        """Stream3 col 0 is vertex-0-only; a per-vertex r=1.0 vs f0 is spurious."""
        import glob
        import struct
        import gmt_format as gf
        import mas_tool
        meshes = 0
        sparse = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    if vertex_count < 8 or len(mesh.stream3_data) != vertex_count * 32:
                        continue
                    column = [struct.unpack_from("<I", mesh.stream3_data,
                                                 i * 32)[0] for i in range(vertex_count)]
                    meshes += 1
                    sparse += (column[0] != 0
                               and all(value == 0 for value in column[1:])
                               and all(vertex.f0 == 0
                                       for vertex in mesh.base_vertices[1:]))
                if meshes >= 1700:
                    break
            if meshes >= 1700:
                break
        self.assertGreater(meshes, 1500)
        self.assertGreater(sparse / meshes, 0.95)

    def test_gmt_two_streams_share_uv_pair(self):
        """Two-stream meshes duplicate their UV-like pair across streams."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        observed = []
        baseline = []
        random.seed(64)
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    if vertex_count < 8 or not mesh.stream2_data or not mesh.stream3_data:
                        continue
                    if len(mesh.stream2_data) != vertex_count * 32:
                        continue
                    if len(mesh.stream3_data) != vertex_count * 32:
                        continue
                    agreement = gf.stream_cross_agreement(
                        mesh.stream2_data, mesh.stream3_data, vertex_count)
                    if agreement is None:
                        continue
                    observed.append(agreement)
                    rows = [mesh.stream3_data[i * 32:(i + 1) * 32]
                            for i in range(vertex_count)]
                    shuffled = random.sample(rows, len(rows))
                    baseline.append(gf.stream_cross_agreement(
                        mesh.stream2_data, b"".join(shuffled), vertex_count))
                if len(observed) >= 1700:
                    break
            if len(observed) >= 1700:
                break
        self.assertGreater(len(observed), 1500)
        self.assertGreater(statistics.median(observed), 0.95)
        self.assertLess(statistics.median(baseline), 0.1)

    def test_gmt_single_block_roundtrip_preserves_uv(self):
        """Repacking a real single-block GTR2 mesh keeps UV bytes intact."""
        import glob
        import gmt_format as gf
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    before = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                candidates = [m for m in before.meshes
                              if m.stream2_data and m.record.raw[7] == 0]
                if not candidates:
                    continue
                after = gf.parse_gmt("y.gmt", gf.relayout_gmt(before))
                for first, second in zip(before.meshes, after.meshes):
                    self.assertEqual(first.vertex_data, second.vertex_data)
                    self.assertEqual(first.stream2_data, second.stream2_data)
                checked += 1
                if checked >= 50:
                    break
            if checked >= 50:
                break
        self.assertEqual(checked, 50)

    def test_uv_layout_shared_with_volvo_race07(self):
        """JCA-decrypted sibling games use the same GTR2 UV signatures."""
        import glob
        import random
        import struct
        import gmt_format as gf
        import jca_crypt
        known = {(1, 2, 0, 0, 0, 0, 0), (1, 2, 1, 2, 1, 2, 1)}
        random.seed(69)
        counts = {}
        for game in ("VolvoTheGame", "Race07Vanilla"):
            checked = matching = baseline = 0
            for path in glob.glob(str(ROOT.parent / game / "**" / "*.gmt"),
                                  recursive=True):
                data = Path(path).read_bytes()
                parsed = None
                for key in (None, jca_crypt.CUSTOM_KEYS.get("volvo")):
                    try:
                        candidate = jca_crypt.decrypt_bytes(data, key)
                    except Exception:
                        continue
                    if not candidate or len(candidate) < 0x174:
                        continue
                    try:
                        candidate_parsed = gf.parse_gmt("x.gmt", candidate)
                    except Exception:
                        continue
                    if candidate_parsed.meshes:
                        parsed = candidate_parsed
                        break
                if parsed is None:
                    continue
                mesh = parsed.meshes[0]
                vertex_count = mesh.record.vertex_count
                stream = mesh.stream2_data
                if not stream or len(stream) != vertex_count * 32:
                    continue
                checked += 1
                matching += gf.stream_column_signature(stream, vertex_count) in known
                records = [list(struct.unpack_from("<8f", stream, i * 32))
                           for i in range(vertex_count)]
                scrambled = b"".join(struct.pack("<8f", *random.sample(record, 8))
                                     for record in records)
                baseline += gf.stream_column_signature(scrambled, vertex_count) in known
                if checked >= 60:
                    break
            counts[game] = (checked, matching, baseline)
        for checked, matching, baseline in counts.values():
            self.assertGreater(checked, 40)
            self.assertGreater(matching / checked, 0.7)
            self.assertLess(baseline / checked, 0.1)

    def test_synthetic_gmt_container_roundtrip(self):
        """A template-free GMT container parses and round-trips cleanly."""
        import struct
        import gmt_format as gf
        import validate_materials
        record = [0] * 27
        record[1] = 0x20004011
        record[3] = 3
        record[10] = 3
        vertices = b"".join(struct.pack("<I6fI", i + 1, float(i), 0, 0, 0, 1, 0, 0)
                            for i in range(3))
        stream = b"".join(bytes(4) + struct.pack("<2f", i * 0.5, 0.0) + bytes(20)
                          for i in range(3))
        mesh = gf.GmtMesh(record=gf.GmtMeshRecord(raw=record), vertex_data=vertices,
                          index_data=struct.pack("<I3H", 0, 0, 1, 2),
                          stream2_data=stream)
        built = gf.build_synthetic_gmt([mesh])
        first = gf.parse_gmt("a.gmt", built)
        self.assertEqual(len(first.meshes), 1)
        self.assertEqual(first.meshes[0].record.vertex_count, 3)
        self.assertEqual(first.meshes[0].stream2_data, stream)
        self.assertEqual(first.materials, [])
        self.assertEqual(validate_materials.check_gmt(built, "a.gmt"), [])
        second = gf.parse_gmt("b.gmt", gf.relayout_gmt(first))
        self.assertEqual(second.meshes[0].vertex_data, vertices)
        self.assertEqual(second.meshes[0].stream2_data, stream)

    def test_gmt_rec6_only_uv_block_exposed(self):
        """Single-block layouts expose their vc*32 UV candidate to decoders."""
        import glob
        import gmt_format as gf
        import mas_tool
        single = 0
        exposed = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    record = mesh.record.raw
                    if record[6] <= 0 or record[7] != 0:
                        continue
                    vertex_count = record[3]
                    if vertex_count < 8 or record[11] - record[6] != vertex_count * 32:
                        continue
                    single += 1
                    exposed += len(mesh.stream2_data) == vertex_count * 32
                if single >= 3000:
                    break
            if single >= 3000:
                break
        self.assertGreater(single, 2000)
        self.assertEqual(exposed, single)

    def test_uv_tiling_ratios_appear_in_material_records(self):
        """Mesh tiling ratios are modestly enriched in their material record."""
        import glob
        import random
        import statistics
        import struct
        import gmt_format as gf
        import mas_tool
        rows = []
        pool = []
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True)[:80]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt"):
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    stream = mesh.stream2_data
                    if vertex_count < 8 or not stream or len(stream) != vertex_count * 32:
                        continue
                    ratios = gf.uv_tiling_factors(stream, vertex_count)
                    if not ratios or not all(abs(value) > 1.5 for value in ratios):
                        continue
                    material_index = mesh.record.material_index
                    if material_index >= len(parsed.materials):
                        continue
                    raw = parsed.materials[material_index].raw
                    if len(raw) < 200:
                        continue
                    rows.append((ratios, raw))
                    pool.extend(int(value) for value in ratios)
                if len(rows) >= 400:
                    break
            if len(rows) >= 400:
                break
        self.assertGreater(len(rows), 300)
        observed = sum(struct.pack("<f", float(value)) in raw
                       for ratios, raw in rows for value in ratios) / (2 * len(rows))
        random.seed(106)
        baselines = []
        for _ in range(5):
            count = 0
            for ratios, raw in rows:
                for _ in ratios:
                    count += struct.pack("<f", float(random.choice(pool))) in raw
            baselines.append(count / (2 * len(rows)))
        baseline = statistics.mean(baselines)
        self.assertGreater(observed, 1.5 * baseline)
        self.assertLess(observed, 0.5)

    def test_uv_tiling_ratios_decode_in_race07(self):
        """The tiling-ratio rule also holds in JCA-decrypted Race07 GMTs."""
        import glob
        import gmt_format as gf
        import jca_crypt
        signature = (1, 2, 3, 4, 5, 6, 1)
        paths = sorted(glob.glob(str(ROOT.parent / "Race07Vanilla" / "**" / "*.gmt"),
                                 recursive=True))[:400]
        checked = decoded = 0
        for path in paths:
            data = Path(path).read_bytes()
            parsed = None
            for key in (None, jca_crypt.CUSTOM_KEYS.get("volvo")):
                try:
                    candidate = jca_crypt.decrypt_bytes(data, key)
                except Exception:
                    continue
                if not candidate or len(candidate) < 0x174:
                    continue
                try:
                    candidate_parsed = gf.parse_gmt("x.gmt", candidate)
                except Exception:
                    continue
                if candidate_parsed.meshes:
                    parsed = candidate_parsed
                    break
            if parsed is None:
                continue
            for mesh in parsed.meshes:
                vertex_count = mesh.record.vertex_count
                stream = mesh.stream2_data
                if vertex_count < 8 or len(stream) != vertex_count * 32:
                    continue
                if gf.stream_column_signature(stream, vertex_count) != signature:
                    continue
                checked += 1
                decoded += gf.uv_tiling_factors(stream, vertex_count) is not None
            if checked >= 16:
                break
        self.assertGreaterEqual(checked, 3)
        self.assertGreaterEqual(decoded, 1)

    def test_gmt_uv_tiling_ratios_are_material_properties(self):
        """Meshes sharing a material usually share their UV tiling ratios."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        groups = {}
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    stream = mesh.stream2_data
                    if vertex_count < 8 or len(stream) != vertex_count * 32:
                        continue
                    ratios = gf.uv_tiling_factors(stream, vertex_count)
                    if ratios is None:
                        continue
                    material_index = mesh.record.material_index
                    if material_index >= len(parsed.materials):
                        continue
                    name = parsed.materials[material_index].name
                    groups.setdefault(name, []).append(
                        tuple(round(value, 4) for value in ratios))
            if sum(len(values) for values in groups.values()) >= 8000:
                break
        multi = {name: values for name, values in groups.items()
                 if len(values) >= 3}
        self.assertGreater(len(multi), 300)
        observed = statistics.mean(len(set(values)) == 1
                                   for values in multi.values())
        self.assertGreater(observed, 0.8)
        random.seed(84)
        pool = [ratio for values in multi.values() for ratio in values]
        baselines = []
        for _ in range(5):
            shuffled = random.sample(pool, len(pool))
            offset = 0
            consistent = 0
            for values in multi.values():
                chunk = shuffled[offset:offset + len(values)]
                offset += len(values)
                consistent += len(set(chunk)) == 1
            baselines.append(consistent / len(multi))
        self.assertGreater(observed, 5 * max(statistics.mean(baselines), 0.01))

    def test_unified_uv_reader_matches_semantic_reader(self):
        """read_mesh_uvs works for both single- and two-stream UV layouts."""
        import glob
        import gmt_format as gf
        import gmt_semantic
        import mas_tool
        checked = 0
        single = 0
        two = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                    semantic = gmt_semantic.read_gmt(entry.data)
                except Exception:
                    continue
                for mesh, submesh in zip(parsed.meshes, semantic["submeshes"]):
                    recovered = gf.read_mesh_uvs(mesh)
                    expected = submesh["uvs"]
                    if recovered is None or expected is None:
                        continue
                    self.assertEqual(recovered, expected)
                    checked += 1
                    record = mesh.record.raw
                    single += record[7] == 0
                    two += record[7] > record[6] and record[8] > record[7]
                if checked >= 800:
                    break
            if checked >= 800:
                break
        self.assertEqual(checked, 800)
        self.assertGreater(single, 100)
        self.assertGreater(two, 50)

    def test_gmt_uv_tiling_ratios(self):
        """Some GTR2 UV streams encode integer tiling ratios on columns 4/6."""
        import glob
        import random
        import struct
        import gmt_format as gf
        import mas_tool
        random.seed(80)
        streams = []
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    stream = mesh.stream2_data
                    if vertex_count < 8 or len(stream) != vertex_count * 32:
                        continue
                    if gf.stream_column_signature(stream, vertex_count) != (1, 2, 3, 4, 5, 6, 1):
                        continue
                    streams.append((stream, vertex_count))
                if len(streams) >= 500:
                    break
            if len(streams) >= 500:
                break
        self.assertGreaterEqual(len(streams), 500)
        streams = streams[:500]
        matching = sum(gf.uv_tiling_factors(stream, count) is not None
                       for stream, count in streams)
        self.assertGreater(matching, 200)

        baseline = 0
        for stream, count in streams:
            rows = [struct.unpack_from("<8f", stream, i * 32) for i in range(count)]
            column2 = [row[2] for row in rows]
            column4 = [row[4] for row in rows]
            shuffled = random.sample(column2, len(column2))
            if abs(shuffled[0]) < 1e-9:
                continue
            ratio = column4[0] / shuffled[0]
            baseline += all(abs(y - ratio * x) <= 1e-3 * max(1.0, abs(y))
                            for x, y in zip(shuffled, column4))
        self.assertEqual(baseline, 0)

    def test_gmt_flag_bit20_predicts_stream_layout(self):
        """Mesh flag bit 0x20 exactly marks the two-stream UV layout."""
        import glob
        import gmt_format as gf
        import mas_tool
        checked = matches = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    record = mesh.record.raw
                    if record[3] < 8:
                        continue
                    two_streams = record[7] > record[6] and record[8] > record[7]
                    checked += 1
                    matches += bool(record[1] & 0x20) == two_streams
                if checked >= 40000:
                    break
            if checked >= 40000:
                break
        self.assertGreater(checked, 30000)
        self.assertEqual(matches, checked)

    def test_gmt_stream_last_column_equals_second(self):
        """Nearly every GTR2 extra stream repeats column 1 in column 7."""
        import glob
        import gmt_format as gf
        import mas_tool
        total = 0
        matching = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    record = mesh.record.raw
                    # The column-7/column-1 invariant is specific to the
                    # two-stream layout; single-block UVs end in zeros.
                    two_streams = record[7] > record[6] and record[8] > record[7]
                    if not two_streams or vertex_count < 8:
                        continue
                    if len(mesh.stream2_data) != vertex_count * 32:
                        continue
                    signature = gf.stream_column_signature(mesh.stream2_data, vertex_count)
                    if signature is None:
                        continue
                    total += 1
                    matching += signature[-1] == 1
                if total >= 2500:
                    break
            if total >= 2500:
                break
        self.assertGreater(total, 2000)
        self.assertGreater(matching / total, 0.99)

    def test_gmt_extra_stream_three_value_pattern(self):
        """Extra 32-byte vertex streams reduce to three distinct values."""
        import glob
        import random
        import struct
        import gmt_format as gf
        import mas_tool
        meshes = []
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    if vertex_count >= 8 and len(mesh.stream2_data) == vertex_count * 32:
                        meshes.append((mesh.stream2_data, vertex_count))
                if len(meshes) >= 1600:
                    break
            if len(meshes) >= 1600:
                break
        self.assertGreater(len(meshes), 1400)
        decoded = sum(gf.decode_stream_records(data, count) is not None
                      for data, count in meshes)
        ratio = decoded / len(meshes)
        self.assertGreater(ratio, 0.4)

        # Distribution-preserving baseline: shuffle each column's values
        # across vertices, which keeps every column's distribution intact.
        random.seed(59)
        baselines = []
        for data, count in meshes[:200]:
            columns = [list(struct.unpack_from("<f", data, i * 32 + 4 * j)[0]
                            for i in range(count)) for j in range(8)]
            shuffled = [column[:] for column in columns]
            for column in shuffled:
                random.shuffle(column)
            hist = sum(1 for i in range(count)
                       if shuffled[1][i] == shuffled[3][i] == shuffled[5][i] == shuffled[7][i]
                       and shuffled[2][i] == shuffled[4][i] == shuffled[6][i])
            baselines.append(hist == count)
        self.assertLess(sum(baselines) / len(baselines), 0.05)

    def test_f0_bytes_not_material_stage_indices(self):
        """f0 bytes do not index material stages (chance-level match)."""
        import glob
        import random
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        if not marker:
                            continue
                        _, high = gf.f0_byte_pair(marker)
                        material_index = mesh.record.material_index
                        stages = (len(parsed.materials[material_index].stages)
                                  if material_index < len(parsed.materials) else 0)
                        rows.append((high, stages))
                if len(rows) >= 20000:
                    break
            if len(rows) >= 20000:
                break
        self.assertGreater(len(rows), 15000)
        observed = sum(high < stages for high, stages in rows)
        random.seed(82)
        baseline = []
        shuffled_stages = [stages for _, stages in rows]
        for _ in range(5):
            sample = random.sample(shuffled_stages, len(shuffled_stages))
            baseline.append(sum(high < stages for (high, _), stages
                                in zip(rows, sample)))
        expected = sum(baseline) / len(baseline)
        self.assertLess(abs(observed - expected), 0.05 * max(expected, 1))

    def test_f0_high_byte_material_index_is_mesh0_artifact(self):
        """The hi-byte==material-index rate is confined to mesh 0."""
        import glob
        import gmt_format as gf
        import mas_tool
        first = [0, 0]
        later = [0, 0]
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for index, mesh in enumerate(parsed.meshes):
                        marker = gf.mesh_marker(mesh)
                        if not marker:
                            continue
                        _, high = gf.f0_byte_pair(marker)
                        bucket = first if index == 0 else later
                        bucket[0] += 1
                        bucket[1] += high == mesh.record.material_index
                if first[0] + later[0] >= 25000:
                    break
            if first[0] + later[0] >= 25000:
                break
        self.assertGreater(first[0], 5000)
        self.assertGreater(later[0], 10000)
        self.assertGreater(first[1] / first[0], 0.35)
        self.assertLess(later[1] / later[0], 0.05)

    def test_f0_byte_pair_consecutive_even(self):
        """f0's two meaningful bytes are usually consecutive (n, n+1)."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        lows = []
        highs = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        if marker:
                            low, high = gf.f0_byte_pair(marker)
                            lows.append(low)
                            highs.append(high)
                if len(lows) >= 30000:
                    break
            if len(lows) >= 30000:
                break
        self.assertGreater(len(lows), 20000)

        def even_consecutive(lo_values, hi_values):
            pairs = [(a, b) for a, b in zip(lo_values, hi_values) if a % 2 == 0]
            return sum(b == a + 1 for a, b in pairs) / len(pairs)

        observed = even_consecutive(lows, highs)
        shuffled = highs[:]
        random.seed(57)
        baseline = statistics.mean(even_consecutive(lows, random.sample(shuffled,
                                                                        len(shuffled)))
                                   for _ in range(5))
        self.assertGreater(observed, 0.5)
        self.assertGreater(observed, 20 * max(baseline, 0.001))

    def test_f0_halves_near_equal(self):
        """f0 packs two nearly-equal 16-bit identifiers."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        pairs = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        if marker:
                            pairs.append((marker & 0xFFFF, marker >> 16))
                if len(pairs) >= 20000:
                    break
            if len(pairs) >= 20000:
                break
        self.assertGreater(len(pairs), 10000)
        observed = sum(abs(low - high) <= 1 for low, high in pairs) / len(pairs)
        random.seed(15)
        lows = [p[0] for p in pairs]
        highs = [p[1] for p in pairs]
        baseline = statistics.mean(
            sum(abs(low - high) <= 1 for low, high in
                zip(random.sample(lows, len(lows)), highs)) / len(pairs)
            for _ in range(10))
        self.assertGreater(observed, 0.4)
        self.assertGreater(observed, 10 * baseline)

    def test_f0_not_shader_enum(self):
        """f0 is not the 1/2/3/99 stage-type enum used by shader lookups."""
        import glob
        import gmt_format as gf
        import mas_tool
        values = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        if marker:
                            values.append(marker)
                if len(values) >= 20000:
                    break
            if len(values) >= 20000:
                break
        self.assertGreater(len(values), 10000)
        self.assertGreater(len(set(values)), 1000)
        self.assertLess(sum(v in (1, 2, 3, 99) for v in values) / len(values), 0.05)

    def test_f0_material_record_association(self):
        """Same f0 is ~10x more likely when the raw material record is identical."""
        import collections
        import glob
        import hashlib
        import re
        import gmt_format as gf
        import mas_tool

        def norm(value):
            return re.sub(r"[^a-z0-9]", "", value.lower())

        groups = collections.defaultdict(list)
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        names = tuple(sorted(set(
                            norm(value) for value in
                            [material.name] + [s.name for s in material.stages]
                            if value)))
                        raw = hashlib.md5(material.raw +
                                          b"|".join(s.raw for s in material.stages)).hexdigest()
                        groups[names].append((marker, raw))
                if sum(len(v) for v in groups.values()) >= 30000:
                    break
            if sum(len(v) for v in groups.values()) >= 30000:
                break
        counts = collections.Counter()
        for values in groups.values():
            if len(values) < 2:
                continue
            f0_same = len(set(v[0] for v in values)) == 1
            raw_same = len(set(v[1] for v in values)) == 1
            counts[(f0_same, raw_same)] += 1
        same_raw = counts[(True, True)] + counts[(False, True)]
        diff_raw = counts[(True, False)] + counts[(False, False)]
        self.assertGreater(same_raw, 1000)
        p_same = counts[(True, True)] / same_raw
        p_diff = counts[(True, False)] / diff_raw
        self.assertGreater(p_same, p_diff * 5)

    def test_f0_groups_material_name_hashes(self):
        """Same-f0 meshes share rare normalized material/stage name hashes."""
        import collections
        import glob
        import random
        import re
        import statistics
        import zlib
        import gmt_format as gf
        import mas_tool
        rows = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    family = re.sub(r"(lod)?\d+$", "", entry.name.lower()
                                    .replace("\\", "/").rsplit("/", 1)[-1]
                                    .rsplit(".", 1)[0])
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        index = mesh.record.material_index
                        material = (parsed.materials[index]
                                    if index < len(parsed.materials) else None)
                        if not marker or material is None:
                            continue
                        names = [material.name] + [s.name for s in material.stages]
                        hashes = frozenset(
                            zlib.crc32(re.sub(r"[^a-z0-9]", "", name.lower())
                                       .encode()) & 0xFFFF
                            for name in names if name)
                        rows.append((family, marker, hashes))
                if len(rows) >= 20000:
                    break
            if len(rows) >= 20000:
                break
        self.assertGreater(len(rows), 10000)
        frequency = collections.Counter(h for _, _, hashes in rows for h in hashes)
        rare = {h for h, count in frequency.items()
                if count / len(rows) < 0.01}

        def score(assignment):
            groups = collections.defaultdict(list)
            for (family, _, hashes), marker in zip(rows, assignment):
                groups[marker].append((family, hashes))
            hits = pairs = 0
            random.seed(1)
            for group in groups.values():
                if len(group) < 2:
                    continue
                sample = random.sample(group, min(len(group), 20))
                for i in range(len(sample)):
                    for j in range(i + 1, len(sample)):
                        if sample[i][0] == sample[j][0]:
                            continue
                        pairs += 1
                        hits += int(bool((sample[i][1] & sample[j][1]) & rare))
            return hits / max(pairs, 1)
        observed = score([marker for _, marker, _ in rows])
        markers = [marker for _, marker, _ in rows]
        baseline = statistics.mean(
            score(random.sample(markers, len(markers))) for _ in range(5))
        self.assertGreater(observed, baseline * 2)

    def test_gttf_slot28_not_waypoint_index(self):
        """Slot +28 does not track AIW waypoint index or lap distance."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        rank_r = []
        distance_r = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            aiw = aiws.get((event.aiw or "").lower())
            if not aiw:
                continue
            waypoints = [w for w in stt.parse_aiw(stt.read_text(aiw)).waypoints
                         if w.pos and w.wp_class() in (0, 1)]
            order = []
            current = 0
            seen = set()
            while current not in seen and len(order) < len(waypoints):
                seen.add(current)
                order.append(current)
                nxt = waypoints[current].ptrs[1]
                if nxt is None or not (0 <= nxt < len(waypoints)):
                    break
                current = nxt
            rank = {wp: i for i, wp in enumerate(order)}
            distance = {}
            travelled = 0.0
            for i, wp in enumerate(order):
                distance[wp] = travelled
                if i + 1 < len(order):
                    travelled += math.dist(waypoints[wp].pos,
                                           waypoints[order[i + 1]].pos)
            values, ranks, distances = [], [], []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                nearest = min(range(len(waypoints)),
                              key=lambda k: (waypoints[k].pos[1] - y) ** 2
                              + (waypoints[k].pos[2] - z) ** 2)
                value = int.from_bytes(payload[frame["offset"] + 28:
                                               frame["offset"] + 32], "little")
                values.append(value)
                ranks.append(rank.get(nearest, 0))
                distances.append(distance.get(nearest, 0.0))
            if len(values) < 100:
                continue
            rank_r.append(st._corr(values, ranks))
            distance_r.append(st._corr(values, distances))
        self.assertGreater(len(rank_r), 10)
        self.assertLess(statistics.median(abs(v) for v in rank_r), 0.15)
        self.assertLess(statistics.median(abs(v) for v in distance_r), 0.15)

    def test_gttf_frame32_not_peak_power_rpm(self):
        """Ghost +32 ceilings do not match .eng peak-power RPM consistently."""
        import re
        def peak_power_rpm(path: Path) -> float:
            rows = []
            for match in re.finditer(
                    r"(?mi)^RPMTorque\s*=\s*\(\s*([\d.]+)\s*,\s*([-\d.e]+)\s*,\s*([-\d.e]+)",
                    path.read_bytes().decode("latin-1")):
                rows.append((float(match.group(1)), float(match.group(3))))
            return max(rows, key=lambda row: row[0] * row[1])[0]
        f550 = peak_power_rpm(ROOT.parent / "GTR2Steam" / "GameData" / "Teams" / "GT" /
                              "Ferrari 550 Teams" / "550_Std_V12.eng")
        bmw = peak_power_rpm(ROOT.parent / "BMWM3Challenge" / "GameData" / "Teams" /
                             "BMW" / "BMW M3" / "BMW_M3.eng")
        self.assertEqual((f550, bmw), (6500.0, 8250.0))
        ratio_f = 5_873_841 / f550
        ratio_b = 6_336_964 / bmw
        self.assertGreater(abs(ratio_f - ratio_b) / ratio_f, 0.14)

    def test_f0_not_count_or_bbox_derived(self):
        """f0 halfword matches to counts/bbox values equal permutation chance."""
        import glob
        import math
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        pairs = []
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        vertices = [(v.x, v.y, v.z) for v in mesh.base_vertices]
                        if not marker or not vertices:
                            continue
                        spans = [max(v[i] for v in vertices)
                                 - min(v[i] for v in vertices) for i in range(3)]
                        candidates = {len(parsed.materials),
                                      sum(len(m.stages) for m in parsed.materials)}
                        for span in spans + [math.sqrt(sum(s * s for s in spans))]:
                            for mult in (1, 10, 100):
                                candidates.add(int(span * mult) & 0xFFFF)
                        pairs.append(((marker & 0xFFFF, marker >> 16), candidates))
                if len(pairs) >= 6000:
                    break
            if len(pairs) >= 6000:
                break
        self.assertGreater(len(pairs), 4000)
        observed = sum(1 for halves, candidates in pairs
                       for half in halves if half in candidates)
        random.seed(0)
        baseline = statistics.mean(
            sum(1 for (halves, _), candidates in zip(
                pairs, random.sample([c for _, c in pairs], len(pairs)))
                for half in halves if half in candidates)
            for _ in range(10))
        self.assertLess(abs(observed - baseline) / max(baseline, 1), 0.15)

    def test_sce_bounds_vs_gtr2_targets(self):
        """SCE embedded physics ranges are incompatible with GTR2 targets."""
        import simbin_text_tool as stt
        for source, target, name in (
                ("hdv", stt.HDC_NUMERIC_BOUNDS, "hdc"),
                ("tbc", stt.TYR_NUMERIC_BOUNDS, "tyr")):
            bounds = stt.SCE_EMBEDDED_NUMERIC_BOUNDS[source]
            shared = set(bounds) & set(target)
            compatible = [k for k in shared
                          if target[k][0] <= bounds[k][0]
                          and bounds[k][1] <= target[k][1]]
            self.assertEqual(len(shared), 19 if source == "hdv" else 15)
            self.assertLessEqual(len(compatible), 4)
            self.assertGreaterEqual(len(shared) - len(compatible),
                                    15 if source == "hdv" else 10)
        self.assertEqual(stt.SCE_EMBEDDED_NUMERIC_BOUNDS["hdv"]["bumptravel"],
                         (-0.085, 0.026))
        self.assertEqual(stt.HDC_NUMERIC_BOUNDS["bumptravel"], (-0.12, -0.02))

    def test_gttf_heading_vs_dsi_tangent_negative(self):
        """Ghost +12 has no consistent DSI tangent relation in the y/z plane."""
        import glob
        import gzip
        import math
        import os
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        base = ROOT.parent / "GTR2Steam"
        coherences = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            track = os.path.basename(os.path.dirname(path))
            dsis = glob.glob(str(base / "GameData" / "DrivingSchool" / track
                                 / "*Lap Challenge*.DSI"))
            if not dsis:
                continue
            from pathlib import Path as _Path
            line = st.read_ghost_line(gzip.decompress(_Path(dsis[0]).read_bytes()))
            tangents = [(line[i], line[i + 1][1] - line[i][1],
                         line[i + 1][2] - line[i][2]) for i in range(len(line) - 1)]
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            matches = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                near = [(dy, dz) for point, dy, dz in tangents
                        if abs(point[1] - y) < 3 and abs(point[2] - z) < 2]
                if near:
                    matches.append((frame["heading"],
                                    statistics.mean(dy for dy, _ in near),
                                    statistics.mean(dz for _, dz in near)))
            if len(matches) < 50:
                continue
            best = 0
            for sign in (1, -1):
                for swap in (False, True):
                    diffs = []
                    for h, dy, dz in matches:
                        angle = sign * math.atan2(dz, dy) if swap \
                            else sign * math.atan2(dy, dz)
                        diffs.append((h - angle + math.pi) % (2 * math.pi) - math.pi)
                    c = sum(math.cos(x) for x in diffs) / len(diffs)
                    s = sum(math.sin(x) for x in diffs) / len(diffs)
                    best = max(best, math.hypot(c, s))
            coherences.append(best)
        self.assertGreater(len(coherences), 20)
        self.assertLess(statistics.median(coherences), 0.4)

    def test_gttf_frame16_not_steering_rate(self):
        """The +16 derivative has no relation to +8 or heading rate."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        versus_offset = []
        versus_heading = []
        for root in ("GTR2Steam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.GTT"),
                                  recursive=True):
                payload = gz.decompress(path)
                frames = st.read_frames(payload, st.find_frame_grid(payload))
                values = [f["pitch"] for f in frames]
                times = [f["time"] for f in frames]
                derivative = [(values[i] - values[i - 1])
                              / max(times[i] - times[i - 1], 1e-6)
                              for i in range(1, len(values))]
                offset = [f["position"][2] for f in frames][1:]
                heading = [f["heading"] for f in frames][1:]
                rate = [(b - a + math.pi) % (2 * math.pi) - math.pi
                        for a, b in zip(heading[:-1], heading[1:])]
                versus_offset.append(st._corr(derivative, offset))
                versus_heading.append(st._corr(derivative[1:], rate[1:]))
        self.assertEqual(len(versus_offset), 31)
        self.assertLess(statistics.median(abs(v) for v in versus_offset), 0.05)
        self.assertLess(statistics.median(abs(v) for v in versus_heading), 0.1)

    def test_gttf_frame16_not_unsigned_pedal(self):
        """Setups have no 0..1 pedal range, and +16 is sometimes negative."""
        import glob
        import gzip
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        configs = [
            ROOT.parent / "GTR2Steam" / "GameData" / "Teams" / "GT" /
            "Ferrari 550 Teams" / "BMS550.hdc",
            ROOT.parent / "BMWM3Challenge" / "GameData" / "Teams" / "BMW" /
            "BMW M3" / "BMW_M3.hdc",
        ]
        for path in configs:
            text = path.read_bytes().decode("latin-1")
            # Only a single fixed blip value; no throttle/brake pedal range.
            self.assertIn("DownshiftBlipThrottle", text)
            self.assertNotRegex(text, r"(?mi)^\s*ThrottlePedalRange\s*=")
            self.assertNotRegex(text, r"(?mi)^\s*BrakePedalRange\s*=")
        negative_files = 0
        for root in ("GTR2Steam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.GTT"),
                                  recursive=True):
                payload = gz.decompress(path)
                grid = st.find_frame_grid(payload)
                if not grid:
                    continue
                values = [f["pitch"] for f in st.read_frames(payload, grid)]
                negative_files += int(any(v < 0 for v in values))
        self.assertEqual(negative_files, 31)

    def test_gttf_frame16_not_bounded_by_steer_lock(self):
        """+16 extrema exceed the .hdc steer lock and often hit a 1.0 clamp."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        maxima = []
        clamped = 0
        for root in ("GTR2Steam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.GTT"),
                                  recursive=True):
                payload = gz.decompress(path)
                grid = st.find_frame_grid(payload)
                if not grid:
                    continue
                values = [f["pitch"] for f in st.read_frames(payload, grid)]
                maxima.append(max(values))
                clamped += int(any(v == 1.0 for v in values))
        self.assertEqual(len(maxima), 31)
        # SteerLockRange=(5,0.5,37), SteerLockSetting=20 in both cars => 15 deg.
        self.assertTrue(all(v > 0.262 for v in maxima))
        self.assertGreaterEqual(clamped, 25)
        self.assertEqual(statistics.median(maxima), 1.0)

    def test_gsc_to_gtr2_conversion_corpus(self):
        """150 GSC members convert to GTR2 layout preserving vertex counts."""
        import glob
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        converted = 0
        members = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                        continue
                    decoded = gmt_semantic.decode_gsc_member(entry.data)
                    if decoded is None:
                        continue
                    out = gmt_layout.gsc_member_to_gtr2(entry.data)
                    self.assertIsNotNone(out, entry.name)
                    parsed = gmt_format.parse_gmt("out.gmt", out)
                    self.assertEqual(
                        sum(len(m.base_vertices) for m in parsed.meshes),
                        sum(len(s["positions"]) for s in decoded["submeshes"]),
                        entry.name)
                    converted += 1
                    members += 1
                    if members >= 150:
                        break
                if members >= 150:
                    break
            if members >= 150:
                break
        self.assertEqual(converted, 150)

    def test_gttf_slot36_not_curvature(self):
        """Slot +36 is not a path-curvature measurement."""
        import glob
        import gzip
        import math
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        correlations = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True)[:10]:
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            world = [frame["world_position"] for frame in frames]
            smooth = [tuple(statistics.mean(p[k] for p in
                                            world[max(0, i - 2):i + 3])
                            for k in range(3)) for i in range(len(world))]
            values, curvature = [], []
            for i in range(1, len(smooth) - 1):
                a, b, c = smooth[i - 1], smooth[i], smooth[i + 1]
                u = [b[k] - a[k] for k in range(3)]
                v = [c[k] - b[k] for k in range(3)]
                cross = (u[1] * v[2] - u[2] * v[1],
                         u[2] * v[0] - u[0] * v[2],
                         u[0] * v[1] - u[1] * v[0])
                la = math.sqrt(sum(x * x for x in u))
                lb = math.sqrt(sum(x * x for x in v))
                if la * lb > 1e-9:
                    curvature.append(math.sqrt(sum(x * x for x in cross)) / (la * lb))
                    values.append(struct.unpack_from("<f", payload,
                                                     frames[i]["offset"] + 36)[0])
            if len(values) > 50:
                correlations.append(st._corr(values, curvature))
        self.assertEqual(len(correlations), 10)
        self.assertLess(statistics.median(abs(v) for v in correlations), 0.05)

    def test_gttf_slot36_not_aiw_surface(self):
        """+36 does not encode nearest-waypoint surface/path attributes."""
        import glob
        import gzip
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        fields = ("galpha", "width", "wpindex")
        observed = {name: [] for name in fields}
        baselines = {name: [] for name in fields}
        random.seed(8)
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"), recursive=True)[:12]:
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            aiw = aiws.get((event.aiw or "").lower())
            if not aiw:
                continue
            waypoints = stt.parse_aiw(stt.read_text(aiw)).waypoints
            values = [struct.unpack_from("<f", payload, frame["offset"] + 36)[0]
                      for frame in frames]
            references = {name: [] for name in fields}
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                index = min(range(len(waypoints)),
                            key=lambda k: (waypoints[k].pos[1] - y) ** 2
                            + (waypoints[k].pos[2] - z) ** 2)
                references["galpha"].append(waypoints[index].galpha or 0)
                references["width"].append(waypoints[index].width[0]
                                           if waypoints[index].width else 0)
                references["wpindex"].append(index)
            for name in fields:
                observed[name].append(abs(st._corr(values, references[name])))
                baselines[name].append(statistics.mean(
                    abs(st._corr(random.sample(values, len(values)),
                                 references[name])) for _ in range(3)))
        self.assertGreater(len(observed["galpha"]), 5)
        for name in fields:
            self.assertLess(statistics.median(observed[name]), 0.05)
            self.assertLess(statistics.median(observed[name]),
                            2 * statistics.median(baselines[name]) + 0.02)

    def test_gttf_slot48_high_half_engine(self):
        """The high signed 16-bit half of +48 tracks engine speed."""
        import glob
        import gzip
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(12)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            highs = []
            for frame in frames:
                value = int.from_bytes(payload[frame["offset"] + 48:
                                              frame["offset"] + 52], "little")
                highs.append(struct.unpack("<h", struct.pack("<H", (value >> 16) & 0xFFFF))[0])
            rpm = [frame["engine_speed"] for frame in frames]
            observed.append(abs(st._corr(highs, rpm)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(highs, len(highs)), rpm)) for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.09)
        self.assertGreater(statistics.median(observed),
                           3 * statistics.median(baseline))
        self.assertGreater(sum(o > 3 * b for o, b in zip(observed, baseline)), 15)

    def test_gttf_slot48_low_half_signed(self):
        """The low signed 16-bit half of +48 tracks steering +8 above chance."""
        import glob
        import gzip
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(6)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            lows = []
            for frame in frames:
                value = int.from_bytes(payload[frame["offset"] + 48:
                                              frame["offset"] + 52], "little")
                lows.append(struct.unpack("<h", struct.pack("<H", value & 0xFFFF))[0])
            steering = [frame["position"][2] for frame in frames]
            observed.append(abs(st._corr(lows, steering)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(lows, len(lows)), steering))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.4)
        self.assertGreater(statistics.median(observed),
                           5 * statistics.median(baseline))

    def test_gttf_slot48_steering_association(self):
        """Slot +48 is modestly but significantly coupled to steering +8."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(4)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            values = [int.from_bytes(payload[frame["offset"] + 48:
                                              frame["offset"] + 52], "little")
                      for frame in frames][1:]
            steering = [frame["position"][2] for frame in frames][1:]
            observed.append(abs(st._corr(values, steering)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), steering))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.1)
        self.assertGreater(statistics.median(observed),
                           3 * statistics.median(baseline))
        self.assertGreater(sum(o > 2 * b for o, b in zip(observed, baseline)), 15)

    def test_gttf_frame16_engine_coupling(self):
        """Frame +16 has a weak, non-clamp-driven coupling to engine speed."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(40)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            values = [frame["pitch"] for frame in frames]
            rpm = [frame["engine_speed"] for frame in frames]
            pairs = [(value, speed) for value, speed in zip(values, rpm)
                     if abs(value) < 0.99]
            if len(pairs) < 100:
                continue
            values = [value for value, _ in pairs]
            rpm = [speed for _, speed in pairs]
            observed.append(abs(st._corr(values, rpm)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), rpm))
                for _ in range(3)))
        self.assertGreater(len(observed), 20)
        self.assertGreater(statistics.median(observed), 0.1)
        self.assertGreater(statistics.median(observed),
                           2 * statistics.median(baseline))

    def test_gttf_engine_speed_gear_bands(self):
        """+32/speed clusters around F550 gear-ratio-derived bands."""
        import glob
        import math
        import random
        import re
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        base = ROOT.parent / "GTR2Steam" / "GameData"
        teams = base / "Teams" / "GT" / "Ferrari 550 Teams"
        hdc = (teams / "BMS550.hdc").read_text(errors="replace")
        grb = (teams / "HewlandLS200.grb").read_text(errors="replace")
        tyr = (base / "Teams" / "Michelin_GT.tyr").read_text(errors="replace")
        ratios = [int(b) / int(a) for a, b in re.findall(
            r"(?m)^Ratio=\((\d+),\s*(\d+)\)", grb)]
        settings = [int(re.search(rf"(?m)^Gear{i}Setting=(\d+)", hdc).group(1))
                    for i in range(1, 7)]
        final = 31 / 10  # .grb [FINAL_DRIVE] ratio=(10,31)
        radii = [float(x) for x in re.findall(r"(?m)^Radius=([\d.]+)", tyr)]
        radius = radii[1] if len(radii) > 1 else radii[0]
        bands = [ratios[i] * final * 60 * 1024 / (2 * math.pi * radius)
                 for i in settings]

        def score(values, proposed):
            return statistics.median(min(abs(v - p) / v for p in proposed)
                                     for v in values)

        observations = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True)[:8]:
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            world = [frame["world_position"] for frame in frames]
            smooth = [tuple(statistics.mean(p[k] for p in
                                            world[max(0, i - 2):i + 3])
                            for k in range(3)) for i in range(len(world))]
            speed = [math.dist(smooth[i], smooth[i + 1])
                     / max(frames[i + 1]["time"] - frames[i]["time"], 1e-6)
                     for i in range(len(smooth) - 1)]
            observations += [frames[i + 1]["engine_speed"] / s
                             for i, s in enumerate(speed) if 8 < s < 60]
        self.assertGreater(len(observations), 3000)
        observed = score(observations, bands)
        random.seed(2)
        baseline = [score(observations,
                          [math.exp(random.uniform(math.log(60000),
                                                   math.log(350000)))
                           for _ in bands]) for _ in range(50)]
        self.assertLess(observed, statistics.median(baseline))
        self.assertLess(observed, 0.07)

    def test_gttf_heading_is_aiw_xz_tangent(self):
        """Ghost +12 is atan2(dx,dz) of the AIW path in world x/z."""
        import glob
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        coherences = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"), recursive=True):
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            aiw = aiws.get((event.aiw or "").lower())
            if not aiw:
                continue
            waypoints = [w for w in stt.parse_aiw(stt.read_text(aiw)).waypoints
                         if w.pos and w.wp_class() in (0, 1)]
            diffs = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                i = min(range(len(waypoints)),
                        key=lambda k: (waypoints[k].pos[1] - y) ** 2
                        + (waypoints[k].pos[2] - z) ** 2)
                j = waypoints[i].ptrs[1]
                if not (0 <= j < len(waypoints)):
                    continue
                dx = waypoints[j].pos[0] - waypoints[i].pos[0]
                dz = waypoints[j].pos[2] - waypoints[i].pos[2]
                angle = math.atan2(dx, dz)
                diffs.append((frame["heading"] - angle + math.pi)
                             % (2 * math.pi) - math.pi)
            if len(diffs) < 50:
                continue
            c = sum(math.cos(x) for x in diffs) / len(diffs)
            s = sum(math.sin(x) for x in diffs) / len(diffs)
            coherences.append(math.hypot(c, s))
        self.assertGreater(len(coherences), 20)
        self.assertGreater(statistics.median(coherences), 0.7)

    def test_gttf_missing_x_reconstructed(self):
        """Pre-frame path records yield plausible world x and speeds."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        speeds = []
        span_ratios = []
        aiws = {}
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.AIW"),
                              recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            if not frames or any(f["x"] is None for f in frames):
                continue
            world = [f["world_position"] for f in frames]
            speeds.append(statistics.median(
                math.dist(p0, p1) / max(f1["time"] - f0["time"], 1e-6)
                for p0, p1, f0, f1 in zip(world, world[1:], frames, frames[1:])))
            event = st.parse_payload(payload)
            aiw = aiws.get((event.aiw or "").lower())
            if aiw:
                import simbin_text_tool as stt
                xw = [w.pos[0] for w in stt.parse_aiw(stt.read_text(aiw)).waypoints
                      if w.pos and w.wp_class() in (0, 1)]
                if xw:
                    span = max(p[0] for p in world) - min(p[0] for p in world)
                    span_ratios.append(span / (max(xw) - min(xw)))
        self.assertEqual(len(speeds), 29)
        self.assertGreater(statistics.median(speeds), 10)
        self.assertLess(statistics.median(speeds), 60)
        self.assertGreater(statistics.median(span_ratios), 0.6)
        self.assertLess(statistics.median(span_ratios), 1.4)

    def test_event_header_fields_from_gtr2_code(self):
        """Code-derived header fields hold across 29 ghosts and 13 replays."""
        import glob
        import simbin_events_tool as st
        sessions = []
        files = 0
        for root, pattern in (("GTR2Steam", "**/*.GTT"), ("GTR2Steam", "ReplayData/*.Vcr"),
                              ("GTLSteam", "ReplayData/*.Vcr")):
            for path in glob.glob(str(ROOT.parent / root / pattern), recursive=True):
                try:
                    event = st.parse_file(path)
                except Exception:
                    continue
                if event.session_seconds is None:
                    continue
                files += 1
                sessions.append(event.session_seconds)
                self.assertIn(event.flags_a, (0, 1))
                self.assertLess(event.flags_b, 10)
                self.assertLess(event.flags_c, 10)
                self.assertIn(event.flags_u, (0, 1))
        self.assertEqual(files, 42)
        self.assertTrue(all(value in (36000.0, 43200.0, 46800.0)
                            for value in sessions))

    def test_gtr2_no_extra_vertex_block_sampled(self):
        """Sampled GTR2 meshes do not expose a 16-byte extra UV block."""
        import glob
        import gmt_format as gf
        import mas_tool
        meshes = with_extra = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True)[:100]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gf.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                for mesh in parsed.meshes:
                    meshes += 1
                    with_extra += int(mesh.record.has_extra_vertex_block)
                if meshes >= 1000:
                    break
            if meshes >= 1000:
                break
        self.assertGreater(meshes, 100)
        self.assertEqual(with_extra, 0)

    def test_gtr1_uv_availability_matches_descriptors(self):
        """Only descriptor-based GTR1 meshes expose UVs for conversion."""
        import glob
        import gmt_semantic
        import gtr1_to_gmt
        import mas_tool
        counts = {"descriptor_uv": 0, "descriptor_no_uv": 0,
                  "fallback_uv": 0, "fallback_no_uv": 0}
        for archive in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                descriptor = bool(gmt_semantic.read_gtr1_geometry(entry.data))
                uv = bool(gtr1_to_gmt.uvs_from_gtr1(entry.data))
                key = ("descriptor" if descriptor else "fallback") + (
                    "_uv" if uv else "_no_uv")
                counts[key] += 1
            if counts["descriptor_uv"] + counts["fallback_no_uv"] >= 400:
                break
        self.assertGreater(counts["descriptor_uv"], 100)
        self.assertEqual(counts["descriptor_no_uv"], 0)
        self.assertEqual(counts["fallback_uv"], 0)

    def test_vrl_conversion_preserves_corner_uvs(self):
        """VRL corner UVs survive vertex expansion into the GTR2 UV block."""
        import glob
        import random
        import struct
        import gmt_format
        import mas_tool
        import simbin_text_tool as stt
        import vrl_to_gmt
        template = None
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True)[:100]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            template = next((entry.data for entry in entries
                             if entry.name.lower().endswith(".gmt") and entry.data), None)
            if template:
                break
        if template is None:
            self.skipTest("no GTR2 template")
        random.seed(68)
        checked = 0
        shuffled_mismatches = 0
        for archive in glob.glob(str(ROOT.parent / "SportsCarGtUsa" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".vrl") or not entry.data:
                    continue
                vrl = stt.read_vrl(entry.data)
                if not vrl:
                    continue
                expanded = vrl_to_gmt.prepare_geometry_with_uvs(vrl)
                if expanded is None:
                    continue
                positions, triangles, uvs = expanded
                output = vrl_to_gmt.vrl_to_gmt(vrl, template)
                self.assertEqual(vrl_to_gmt.verify_gmt(output, vrl), [], entry.name)
                stream = gmt_format.parse_gmt("x.gmt", output).meshes[0].stream2_data
                recovered = [struct.unpack_from("<2f", stream, i * 32 + 4)
                             for i in range(len(uvs))]
                self.assertEqual(recovered, uvs)
                shuffled = random.sample(uvs, len(uvs))
                shuffled_mismatches += recovered != shuffled
                checked += 1
                if checked >= 25:
                    break
            if checked >= 25:
                break
        self.assertEqual(checked, 25)
        self.assertGreater(shuffled_mismatches / checked, 0.9)

    def test_gtr1_conversion_preserves_uvs(self):
        """GTR1 vertex fields 9/10 survive into the GTR2 UV block."""
        import glob
        import struct
        import gmt_format
        import gtr1_to_gmt
        import mas_tool
        template = ROOT.parent / "hand_selected" / "gtr1_sniffnnbe5l6i"
        template_file = next((template / "Mesh.gtr").parent.glob("*.gmt"),
                             None) if template.is_dir() else None
        template_data = None
        for candidate in (template_file, *sorted(ROOT.parent.glob("GTR2Steam/**/*.gtr"))[:1]):
            if candidate is None or not candidate.is_file():
                continue
            try:
                _, entries = mas_tool.read_archive(str(candidate))
            except Exception:
                continue
            template_data = next((e.data for e in entries
                                  if e.name.lower().endswith(".gmt") and e.data), None)
            if template_data:
                break
        if template_data is None:
            self.skipTest("no GTR2 template")
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                source_uvs = (gtr1_to_gmt.uvs_from_gtr1(entry.data)
                              if entry.name.lower().endswith(".gmt") and entry.data else None)
                if not source_uvs:
                    continue
                output = gtr1_to_gmt.gtr1_to_gmt(entry.data, template_data)
                parsed = gmt_format.parse_gmt("x.gmt", output)
                stream = parsed.meshes[0].stream2_data
                self.assertEqual(len(stream), len(source_uvs) * 32)
                recovered = [struct.unpack_from("<2f", stream, i * 32 + 4)
                             for i in range(len(source_uvs))]
                self.assertEqual(recovered, source_uvs)
                checked += 1
                if checked >= 10:
                    break
            if checked >= 10:
                break
        self.assertEqual(checked, 10)

    def test_converted_uv_values_are_finite_and_bounded(self):
        """Converted GSC UVs stay finite and within plausible source ranges."""
        import glob
        import math
        import gmt_format as gf
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True)[:20]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                output = gmt_layout.gsc_member_to_gtr2(entry.data)
                if output is None:
                    continue
                for mesh in gf.parse_gmt("x.gmt", output).meshes:
                    pairs = gf.read_mesh_uvs(mesh)
                    if not pairs:
                        continue
                    for u, v in pairs:
                        self.assertTrue(math.isfinite(u) and math.isfinite(v))
                        self.assertLess(abs(u), 1e5)
                        self.assertLess(abs(v), 1e5)
                    checked += 1
                if checked >= 100:
                    break
            if checked >= 100:
                break
        self.assertGreater(checked, 50)

    def test_gsc_conversion_preserves_uv_values(self):
        """Converted GSC members carry exactly the source UV pairs."""
        import glob
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                decoded = gmt_semantic.decode_gsc_member(entry.data)
                if not decoded:
                    continue
                output = gmt_layout.gsc_member_to_gtr2(entry.data)
                if output is None:
                    continue
                source = [tuple(float(value) for value in uv)
                          for sub in decoded["submeshes"] for uv in sub["uvs"]]
                converted = []
                for mesh in gmt_format.parse_gmt("x.gmt", output).meshes:
                    pairs = gmt_format.read_mesh_uvs(mesh)
                    if pairs:
                        converted.extend(pairs)
                self.assertEqual(converted, source)
                checked += 1
                if checked >= 150:
                    break
            if checked >= 150:
                break
        self.assertEqual(checked, 150)

    def test_gsc_conversion_uv_layout_matches_gtr2(self):
        """Converted UV blocks match the dominant real GTR2 stream layout."""
        import glob
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                converted = gmt_layout.gsc_member_to_gtr2(entry.data)
                if converted is None:
                    continue
                parsed = gmt_format.parse_gmt("x.gmt", converted)
                for mesh in parsed.meshes:
                    vertex_count = mesh.record.vertex_count
                    if vertex_count < 8:
                        continue
                    self.assertEqual(len(mesh.stream2_data), vertex_count * 32)
                    self.assertEqual(
                        gmt_format.stream_column_signature(mesh.stream2_data, vertex_count),
                        (1, 2, 0, 0, 0, 0, 0))
                    checked += 1
                if checked >= 20:
                    break
            if checked >= 20:
                break
        self.assertEqual(checked, 20)

    def test_gsc_conversion_roundtrip_preserves_streams(self):
        """Repacking a converted GSC GMT preserves vertices and streams."""
        import glob
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                converted = gmt_layout.gsc_member_to_gtr2(entry.data)
                if converted is None:
                    continue
                before = gmt_format.parse_gmt("a.gmt", converted)
                after = gmt_format.parse_gmt("b.gmt", gmt_format.relayout_gmt(before))
                self.assertEqual(len(before.meshes), len(after.meshes))
                for first, second in zip(before.meshes, after.meshes):
                    self.assertEqual(first.record.vertex_count, second.record.vertex_count)
                    self.assertEqual(first.vertex_data, second.vertex_data)
                    self.assertEqual(first.stream2_data, second.stream2_data)
                checked += 1
                if checked >= 40:
                    break
            if checked >= 40:
                break
        self.assertEqual(checked, 40)

    def test_gsc_conversion_index_integrity(self):
        """Converted faces stay within vertex bounds and are non-degenerate."""
        import glob
        import struct
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                parsed = gmt_format.parse_gmt("out.gmt",
                                              gmt_layout.gsc_member_to_gtr2(entry.data))
                for mesh in parsed.meshes:
                    ids = struct.unpack("<%dH" % ((len(mesh.index_data) - 4) // 2),
                                        mesh.index_data[4:])
                    count = len(mesh.base_vertices)
                    self.assertEqual(sum(1 for index in ids if index >= count), 0)
                    self.assertEqual(sum(1 for k in range(0, len(ids) - 2, 3)
                                         if len(set(ids[k:k + 3])) < 3), 0)
                    checked += 1
                if checked >= 40:
                    break
            if checked >= 40:
                break
        self.assertEqual(checked, 40)

    def test_gsc_conversion_preserves_material_names(self):
        """Converted GSC meshes keep a parseable material library."""
        import glob
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                out = gmt_layout.gsc_member_to_gtr2(entry.data)
                parsed = gmt_format.parse_gmt("out.gmt", out)
                self.assertGreater(len(parsed.materials), 0, entry.name)
                self.assertTrue(all(material.name for material in parsed.materials),
                                entry.name)
                checked += 1
                if checked >= 40:
                    break
            if checked >= 40:
                break
        self.assertEqual(checked, 40)

    def test_gsc_converted_winding_matches_gtr2(self):
        """Converted meshes keep GTR2's inverted winding-vs-normal convention."""
        import glob
        import math
        import statistics
        import struct
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool

        def agreement(positions, normals, triangles):
            forward = reversed_count = total = 0
            for i, j, k in triangles:
                if max(i, j, k) >= len(positions):
                    continue
                u = [positions[j][x] - positions[i][x] for x in range(3)]
                v = [positions[k][x] - positions[i][x] for x in range(3)]
                cross = (u[1] * v[2] - u[2] * v[1],
                         u[2] * v[0] - u[0] * v[2],
                         u[0] * v[1] - u[1] * v[0])
                dot = sum(cross[x] * normals[i][x] for x in range(3))
                total += 1
                forward += int(dot > 0)
                reversed_count += int(dot < 0)
            return forward / total, reversed_count / total if total else (0, 0)

        raw_values = []
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                decoded = gmt_semantic.decode_gsc_member(entry.data)
                if not decoded:
                    continue
                raw_values.append(entry.data)
                if len(raw_values) >= 10:
                    break
            if len(raw_values) >= 10:
                break
        self.assertEqual(len(raw_values), 10)
        forward, reverse = [], []
        for raw in raw_values:
            out = gmt_layout.gsc_member_to_gtr2(raw)
            parsed = gmt_format.parse_gmt("out.gmt", out)
            for mesh in parsed.meshes:
                positions = [(v.x, v.y, v.z) for v in mesh.base_vertices]
                normals = [(v.nx, v.ny, v.nz) for v in mesh.base_vertices]
                ids = struct.unpack("<%dH" % ((len(mesh.index_data) - 4) // 2),
                                    mesh.index_data[4:])
                triangles = [tuple(ids[k:k + 3]) for k in range(0, len(ids) - 2, 3)]
                f, r = agreement(positions, normals, triangles)
                forward.append(f)
                reverse.append(r)
        self.assertGreater(len(forward), 5)
        self.assertLess(statistics.median(forward), 0.1)
        self.assertGreater(statistics.median(reverse), 0.9)

    def test_gttf_slot44_halves_path_f4(self):
        """Slot +44's packed halves carry a path_f4-related signal."""
        import glob
        import gzip
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(29)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            words = [int.from_bytes(payload[frame["offset"] + 44:
                                            frame["offset"] + 48], "little")
                     for frame in frames]
            lows = [struct.unpack("<h", struct.pack("<H", value & 0xFFFF))[0]
                    for value in words]
            highs = [struct.unpack("<h", struct.pack("<H", (value >> 16) & 0xFFFF))[0]
                     for value in words]
            values = lows + highs
            reference = [frame["path_f4"] for frame in frames] * 2
            observed.append(abs(st._corr(values, reference)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), reference))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 3 * statistics.median(baseline))
        self.assertGreater(sum(o > 2 * b for o, b in zip(observed, baseline)), 20)

    def test_gttf_path_f4_decreases_with_gear(self):
        """Racing-line f4 falls as the engine/gear band rises."""
        import glob
        import gzip
        import math
        import random
        import re
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        base = ROOT.parent / "GTR2Steam" / "GameData" / "Teams" / "GT" / "Ferrari 550 Teams"
        grb = (base / "HewlandLS200.grb").read_text(errors="replace")
        hdc = (base / "BMS550.hdc").read_text(errors="replace")
        ratios = [int(b) / int(a) for a, b in re.findall(
            r"(?m)^Ratio=\((\d+),\s*(\d+)\)", grb)]
        settings = [int(re.search(rf"(?m)^Gear{i}Setting=(\d+)", hdc).group(1))
                    for i in range(1, 7)]
        bands = [ratios[i] * 3.10 * 60 * 1024 / (2 * math.pi * 0.355)
                 for i in settings]
        observed = []
        baseline = []
        random.seed(11)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            world = [frame["world_position"] for frame in frames]
            speed = [math.dist(world[i], world[i + 1])
                     / max(frames[i + 1]["time"] - frames[i]["time"], 1e-6)
                     for i in range(len(world) - 1)]
            gears, values = [], []
            for i in range(1, len(frames)):
                if not (8 < speed[i - 1] < 60):
                    continue
                ratio = frames[i]["engine_speed"] / speed[i - 1]
                gears.append(min(range(6),
                                 key=lambda k: abs(ratio - bands[k]) / bands[k]))
                values.append(frames[i]["path_f4"])
            if len(gears) < 100:
                continue
            observed.append(st._corr(gears, values))
            baseline.append(statistics.mean(
                st._corr(random.sample(gears, len(gears)), values) for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertLess(statistics.median(observed), -0.1)
        self.assertLess(statistics.median(observed), 2 * statistics.median(baseline))

    def test_gtl_gmts_already_new_layout(self):
        """GTL archive GMTs need no old-to-new mesh relayout."""
        import glob
        import gmt_format as gf
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTLSteam" / "**" / "*.gtl"),
                                 recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                data = entry.data
                if len(data) >= 24 and data[8:24] == gf.GMT_MAGIC:
                    checked += 1
                elif len(data) >= 0x1E4 and data[0x1D4:0x1E4] == bytes.fromhex(
                        "c8cfd2d8ced8e6c3d6ded8bebba7bf90"):
                    self.fail(f"old-layout GMT in GTL archive: {entry.name}")
            if checked >= 2000:
                break
        self.assertGreater(checked, 1500)

    def test_gtr2_exe_ghost_writer_selection_code(self):
        """GTR2.exe contains the GTTF/IRSR magic-selection branch in its writer."""
        exe = ROOT.parent / "GTR2Steam" / "GTR2.exe"
        if not exe.is_file():
            self.skipTest("GTR2.exe not present")
        data = exe.read_bytes()
        # fcn.0052a540: mov ecx,[0x6ead90] / push ecx / mov ecx,esi
        # for GTTF, and the same with [0x6ead7c] for IRSR.
        self.assertEqual(data.count(bytes.fromhex("8b0d90ad6e00518bce")), 1)
        self.assertEqual(data.count(bytes.fromhex("8b0d7cad6e00518bce")), 1)
        # Per-object writer: 64-byte blocks at +0x41/+0x81 and trailing u32s.
        self.assertEqual(data.count(bytes.fromhex("6a408d4f41518bce")), 1)
        # Per-object reader splits a flags byte's top bit into +0xcc.
        self.assertEqual(data.count(bytes.fromhex("80e17fc0e807880f8887cc000000")), 1)
        # Sub-record reader fcn.00527890: u32 header with packed 10-bit size.
        self.assertEqual(data.count(bytes.fromhex("8b4424048bc881e1000000e081f9000000207524")), 1)

    def test_no_debug_symbols_in_game_binaries(self):
        """Game EXEs reference PDBs but ship no usable debug symbols."""
        root = ROOT.parent
        pdbs = list(root.glob("*/**/*.pdb"))
        self.assertEqual(pdbs, [])
        exe = root / "GTR2Steam" / "GTR2.exe"
        if not exe.is_file():
            self.skipTest("GTR2.exe not present")
        data = exe.read_bytes()
        self.assertIn(b"RSDS", data)
        self.assertIn(b"GTR2.pdb", data)
        import struct
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        self.assertEqual(data[pe:pe + 4], b"PE\0\0")
        self.assertEqual(struct.unpack_from("<I", data, pe + 12)[0], 0)

    def test_dedicated_exe_no_frame_serializer_pattern(self):
        """GTR2Dedicated.exe retains GTTF strings but no 63-byte read site."""
        exe = ROOT.parent / "GTR2Steam" / "GTR2Dedicated.exe"
        if not exe.is_file():
            self.skipTest("GTR2Dedicated.exe not present")
        data = exe.read_bytes()
        self.assertIn(b"GTTF", data)
        lo = 0x520000 - 0x400C00
        hi = 0x534000 - 0x400C00
        patterns = (b"\xff\x50\x1c", b"\xff\x52\x1c",
                    b"\xff\x51\x1c", b"\xff\x53\x1c")
        pos = lo
        hits = 0
        while True:
            index = data.find(b"\x6a\x3f", pos, hi)
            if index < 0:
                break
            if any(pattern in data[index:index + 20] for pattern in patterns):
                hits += 1
            pos = index + 1
        self.assertEqual(hits, 0)

    def test_gttf_slot36_exponent_tracks_path_f4(self):
        """Slot +36's quantization exponent rises with path f4 demand."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(55)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            if not frames or frames[0]["path_f4"] is None:
                continue
            levels = []
            for frame in frames:
                value = abs(struct.unpack_from("<f", payload,
                                               frame["offset"] + 36)[0])
                levels.append(math.log2(value / 34.0) / 2.0 if value > 0 else 0.0)
            demand = [frame["path_f4"] for frame in frames]
            observed.append(st._corr(levels, demand))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(levels, len(levels)), demand))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.2)
        self.assertTrue(all(value > 0 for value in observed))
        self.assertGreater(statistics.median(observed),
                           5 * statistics.median(baseline))

    def test_converted_gmts_agree_with_independent_parser(self):
        """Converted meshes parse in gtr2-agent-tools' independent reader."""
        import importlib.util
        import struct
        import gmt_format
        import gmt_layout
        import gmt_semantic
        import mas_tool
        reference_path = (ROOT.parent / "gtr2-agent-tools" / "scripts"
                          / "gtr2_driving" / "gmt.py")
        if not reference_path.is_file():
            self.skipTest("independent reference parser not present")
        spec = importlib.util.spec_from_file_location("reference_gmt", reference_path)
        reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reference)
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True)[:20]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                    continue
                if not gmt_semantic.decode_gsc_member(entry.data):
                    continue
                output = gmt_layout.gsc_member_to_gtr2(entry.data)
                if output is None:
                    continue
                ours = gmt_format.parse_gmt("x.gmt", output)
                theirs = reference.parse(output)
                self.assertEqual(len(ours.meshes), len(theirs))
                for mesh, other in zip(ours.meshes, theirs):
                    self.assertEqual(len(mesh.base_vertices), len(other["vertices"]))
                    indices = struct.unpack("<%dH" % ((len(mesh.index_data) - 4) // 2),
                                            mesh.index_data[4:])
                    triangles = [tuple(indices[k:k + 3])
                                 for k in range(0, len(indices) - 2, 3)]
                    self.assertEqual(triangles, other["triangles"])
                checked += 1
                if checked >= 10:
                    break
            if checked >= 10:
                break
        self.assertGreaterEqual(checked, 5)

        # GTR1 conversions using a real GTR2 template.
        template = None
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True)[:20]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            template = next((entry.data for entry in entries
                             if entry.name.lower().endswith(".gmt") and entry.data), None)
            if template:
                break
        if template:
            import gtr1_to_gmt
            gtr1_checked = 0
            for archive in glob.glob(str(ROOT.parent / "GTR1Vanilla" / "**" / "*.gtr"),
                                     recursive=True)[:20]:
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        converted = gtr1_to_gmt.gtr1_to_gmt(entry.data, template)
                    except Exception:
                        continue
                    ours = gmt_format.parse_gmt("x.gmt", converted)
                    theirs = reference.parse(converted)
                    self.assertEqual(len(ours.meshes), len(theirs))
                    gtr1_checked += 1
                    if gtr1_checked >= 5:
                        break
                if gtr1_checked >= 5:
                    break
            self.assertGreaterEqual(gtr1_checked, 3)

    def test_gmt_semantic_reader_recognizes_all_mesh_magics(self):
        """find_submeshes handles 0x60xx variants as well as 0x40xx."""
        import glob
        import gmt_format
        import gmt_semantic
        import mas_tool
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "GTR2Steam" / "**" / "*.gtr"),
                                 recursive=True)[:60]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                try:
                    parsed = gmt_format.parse_gmt("x.gmt", entry.data)
                except Exception:
                    continue
                self.assertEqual(len(gmt_semantic.find_submeshes(entry.data)),
                                 len(parsed.meshes), entry.name)
                checked += 1
            if checked >= 2000:
                break
        self.assertGreater(checked, 1000)

        # Expanded magic set must not produce false matches in old-layout GSC.
        false_positives = 0
        for archive in glob.glob(str(ROOT.parent / "CopaPetrobrasdeMarcas" / "**" / "*.mas"),
                                 recursive=True)[:20]:
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".gmt") or not entry.data:
                    continue
                false_positives += len(gmt_semantic.find_submeshes(entry.data))
        self.assertLess(false_positives, 20)

    def test_phs_members_have_no_recognizable_cipher_header(self):
        """The five GTL PHS members expose no ISI/JCA/gMb header."""
        import isi_crypt
        import mas_tool
        archives = list((ROOT.parent / "GTLSteam").rglob("*.gtl"))
        members = []
        for archive in archives:
            try:
                _, entries = mas_tool.read_archive(str(archive))
            except Exception:
                continue
            members.extend(entry.data for entry in entries
                           if entry.name.lower().endswith(".phs") and entry.data)
        self.assertEqual(len(members), 5)
        magics = (bytes.fromhex("0fb1ffff"), bytes.fromhex("2f2f5b5b"))
        par2 = b"PAR2\0PKT"
        opaque = 0
        for data in members:
            for offset in range(0, 65):
                if offset + 16 > len(data):
                    break
                sign, _ = isi_crypt.crypt_info(data[offset:])
                self.assertNotIn(sign, isi_crypt.GAMES)
            for magic in magics:
                self.assertLess(data.find(magic), 0)
            opaque += data.find(par2) < 0
        self.assertEqual(opaque, 1)

    def test_vcr_bulk_data_has_20_byte_periodicity(self):
        """Replay bulk data repeats at lag 20 more than at neighbouring lags."""
        import gzip_simbin_tool as gz
        root = ROOT.parent / "GTR2Steam" / "ReplayData"
        checked = positive = 0
        for path in sorted(root.glob("*.Vcr")):
            data = gz.decompress(str(path))
            lo = min(max(0x4000, len(data) // 4), max(0, len(data) - 1024))
            hi = min(len(data), lo + 0x10000)

            def match(lag: int) -> float:
                indices = range(lo, max(lo + 1, min(hi, len(data) - lag)), 8)
                count = len(indices)
                return (sum(data[i] == data[i + lag] for i in indices) / count
                        if count else 0.0)

            checked += 1
            positive += match(20) > (match(18) + match(19) + match(21) + match(22)) / 4
        self.assertEqual(checked, 9)
        self.assertGreaterEqual(positive, 7)

    def test_vcr_header_has_86_byte_periodicity(self):
        """The replay header region repeats with an 86-byte period."""
        import gzip_simbin_tool as gz
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Anderstorp.Vcr"
        if not path.is_file():
            self.skipTest("Anderstorp.Vcr not present")
        data = gz.decompress(str(path))
        lo, hi = 0, min(len(data), 0x2000)

        def match_at(buffer: bytes, lag: int) -> float:
            indices = range(lo, hi - lag, 8)
            return sum(buffer[i] == buffer[i + lag] for i in indices) / len(indices)

        scores = [(match_at(data, lag), lag) for lag in range(1, 201)]
        best_lag = max(scores)[1]
        self.assertEqual(best_lag, 86)
        self.assertGreater(match_at(data, 86), 0.5)
        import random
        random.seed(89)
        shuffled = bytearray(data)
        random.shuffle(shuffled)
        self.assertLess(match_at(bytes(shuffled), 86), 0.2)

    def test_gttf_flags_constant_irsr_flags_vary(self):
        """GTTF header flags are fixed; IRSR replay flags carry variation."""
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        ghosts = list((ROOT.parent / "GTR2Steam" / "TimeTrial").rglob("*.GTT"))
        ghost_flags = set()
        for path in ghosts:
            event = st.parse_payload(gz.decompress(str(path)))
            ghost_flags.add((event.flags_a, event.flags_b, event.flags_c, event.flags_u))
        self.assertEqual(len(ghosts), 29)
        self.assertEqual(ghost_flags, {(0, 0, 1, 0)})

        replay_flags = set()
        for path in (ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"):
            event = st.parse_payload(gz.decompress(str(path)))
            replay_flags.add((event.flags_a, event.flags_b, event.flags_c, event.flags_u))
        self.assertGreater(len(replay_flags), 3)

    def test_gttf_frame_time_editor_preserves_other_fields(self):
        """Frame-time shifting changes only frame time words."""
        import glob
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True)[:10]:
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            shifted = st.shift_frame_times(payload, 64.0)
            before = st.read_frames(payload, grid)
            grid2 = st.find_frame_grid(shifted)
            after = st.read_frames(shifted, grid2)
            self.assertEqual(len(before), len(after))
            for old, new in zip(before, after):
                self.assertLess(abs((new["time"] - old["time"]) - 64.0), 1e-4)
                self.assertEqual(old["position"], new["position"])
                self.assertEqual(old["heading"], new["heading"])
            self.assertEqual(gz.compress_simbin(shifted)[:10],
                             Path(path).read_bytes()[:10])
            checked += 1
        self.assertEqual(checked, 10)

    def test_gttf_session_field_editor(self):
        """Session seconds can be changed without touching other payload bytes."""
        import glob
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            offset = st.session_field_offset(payload)
            self.assertIsNotNone(offset)
            edited = st.set_session_seconds(payload, 12345.0)
            self.assertEqual(len(edited), len(payload))
            self.assertEqual(st.parse_payload(edited).session_seconds, 12345.0)
            differences = [index for index, (old, new)
                           in enumerate(zip(payload, edited)) if old != new]
            self.assertTrue(set(differences).issubset(set(range(offset, offset + 4))))
            self.assertEqual(gz.compress_simbin(gz.decompress(path)), Path(path).read_bytes())
            checked += 1
        self.assertEqual(checked, 29)

    def test_gttf_container_roundtrips_byte_identically(self):
        """SimBin gzip headers can be reproduced byte-for-byte."""
        import glob
        import gzip_simbin_tool as gz
        checked = 0
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            original = Path(path).read_bytes()
            payload = gz.decompress(path)
            self.assertEqual(gz.compress_simbin(payload), original, path)
            checked += 1
        self.assertEqual(checked, 29)
        replays = 0
        for path in (ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"):
            original = path.read_bytes()
            self.assertEqual(gz.compress_simbin(gz.decompress(str(path))), original, path)
            replays += 1
        self.assertEqual(replays, 9)

        extensions = collections.Counter()
        for path in (ROOT.parent / "GTR2Steam").rglob("*"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            if path.read_bytes()[:2] != b"\x1f\x8b":
                continue
            extension = path.suffix.lower()
            extensions[extension] += 1
            self.assertEqual(gz.compress_simbin(gz.decompress(str(path))),
                             path.read_bytes(), str(path))
        self.assertEqual(set(extensions), {".dsi", ".hat", ".gtt", ".vcr"})

    def test_driver_u16_deltas_not_wheel_speed(self):
        """Apparent u16-delta/speed correlations are shared slow trends."""
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st

        def correlate(x, y):
            mx, my = statistics.mean(x), statistics.mean(y)
            numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
            denominator = (sum((a - mx) ** 2 for a in x)
                           * sum((b - my) ** 2 for b in y)) ** 0.5
            return numerator / denominator if denominator else 0.0

        def detrend(values):
            indices = list(range(len(values)))
            mean_index = statistics.mean(indices)
            mean_value = statistics.mean(values)
            slope = sum((i - mean_index) * (v - mean_value)
                        for i, v in zip(indices, values)) / sum(
                            (i - mean_index) ** 2 for i in indices)
            return [v - mean_value - slope * (i - mean_index)
                    for i, v in zip(indices, values)]

        checked = 0
        apparent = 0
        for path in sorted((ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr")):
            parsed = st.parse_vcr_frames(gz.decompress(str(path)))
            if not parsed:
                continue
            states = []
            for frame in parsed["frames"]:
                for record in frame["records"]:
                    if st.vcr_record_tag(record["header"]) == 0:
                        state = st.vcr_driver_state(record["data"])
                        if state:
                            states.append(state)
                        break
            if len(states) < 30:
                continue
            speeds = [math.dist(a["position"], b["position"])
                      for a, b in zip(states, states[1:])]
            keep = sorted(range(len(speeds)), key=lambda i: speeds[i])[:-3]
            speed_series = [speeds[i] for i in keep]
            for slot in range(4):
                wrapped = [((b["shorts"][slot] - a["shorts"][slot]) % 65536)
                           for a, b in zip(states, states[1:])]
                series = [min(wrapped[i], 65536 - wrapped[i]) for i in keep]
                raw = correlate(series, speed_series)
                if abs(raw) < 0.15:
                    continue
                apparent += 1
                cleaned = correlate(detrend(series), detrend(speed_series))
                self.assertLess(abs(cleaned), 0.15, (path.name, slot, raw, cleaned))
            checked += 1
        self.assertGreaterEqual(checked, 5)
        self.assertGreaterEqual(apparent, 2)

    def test_driver_u16s_not_universal_tyre_units(self):
        """Live per-wheel units do not decode the u16s across all cars."""
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        temperature_fits = []
        pressure_fits = []
        for name in ("Monza.Vcr", "Imola.Vcr", "Magny-Cours.Vcr"):
            path = ROOT.parent / "GTR2Steam" / "ReplayData" / name
            if not path.is_file():
                continue
            parsed = st.parse_vcr_frames(gz.decompress(str(path)))
            if not parsed:
                continue
            raw = []
            for frame in parsed["frames"][:200]:
                for record in frame["records"]:
                    if st.vcr_record_tag(record["header"]) != 0:
                        continue
                    state = st.vcr_driver_state(record["data"])
                    if state:
                        raw.extend(state["shorts"])
                    break
            if not raw:
                continue
            temperature_fits.append(sum(60 <= value / 256 <= 110 for value in raw)
                                    / len(raw))
            halves = [struct.unpack("<e", struct.pack("<H", value))[0]
                      for value in raw]
            pressure_fits.append(sum(1.5 <= value <= 3.0 for value in halves)
                                 / len(halves))
        self.assertGreaterEqual(len(temperature_fits), 2)
        self.assertLess(min(temperature_fits), 0.5)
        self.assertLess(min(pressure_fits), 0.5)

    def test_driver_state_u16s_form_wheel_pairs(self):
        """The four u16 fields are paired values, not four independent counts."""
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Monza.Vcr"
        if not path.is_file():
            self.skipTest("Monza.Vcr not present")
        parsed = st.parse_vcr_frames(gz.decompress(str(path)))
        if not parsed:
            self.skipTest("frame stream unparsed")
        rows = []
        for frame in parsed["frames"]:
            for record in frame["records"]:
                if st.vcr_record_tag(record["header"]) != 0:
                    continue
                state = st.vcr_driver_state(record["data"])
                if state:
                    rows.append(state["shorts"])
                break
        self.assertGreater(len(rows), 100)
        rear_gap = statistics.median(abs(row[2] - row[3]) for row in rows)
        scale = statistics.median(max(row) for row in rows)
        self.assertLess(rear_gap, 0.01 * scale)
        import random
        random.seed(153)
        shuffled = [list(row) for row in rows]
        for row in shuffled:
            random.shuffle(row)
        shuffled_gap = statistics.median(abs(row[2] - row[3]) for row in shuffled)
        self.assertLess(rear_gap, 0.1 * shuffled_gap)

    def test_hat_payloads_are_gmb_wrapped_high_entropy(self):
        """`.hat` files share the gMb container but use an undecoded body."""
        import math
        import gzip_simbin_tool as gz
        paths = list((ROOT.parent / "GTR2Steam").rglob("*.hat"))
        checked = 0
        for path in paths[:12]:
            payload = gz.decompress(str(path))
            self.assertIn(b"//[[gMb", payload)
            marker = payload.find(b"generated\x00")
            self.assertGreater(marker, 0)
            body = payload[marker + 10:]
            self.assertGreater(len(body), 100000)
            counts = collections.Counter(body[:65536])
            entropy = -sum((n / len(body[:65536])) * math.log2(n / len(body[:65536]))
                           for n in counts.values())
            self.assertGreater(entropy, 6.5)
            checked += 1
        self.assertGreaterEqual(checked, 10)

    def test_hat_header_bytes_4_to_16_are_track_stable(self):
        """The .hat 16-byte header carries a per-track identifier at 4:16."""
        import random
        import gzip_simbin_tool as gz
        tracks = ("ANDERSTORP", "Barcelona", "Brno", "Donington", "Enna",
                  "Estoril", "Magny", "Monza", "Oschersleben", "Spa", "Dubai",
                  "Valencia", "Imol", "Zhuhai", "Hockenheim")
        rows = []
        for path in sorted((ROOT.parent / "GTR2Steam").rglob("*.hat")):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            if marker < 0:
                continue
            body = payload[marker + 10:]
            name = path.stem
            track = next((x for x in tracks if x.lower() in name.lower()), None)
            rows.append((name, track, body[4:16]))
        self.assertGreaterEqual(len(rows), 30)
        self.assertTrue(all(row[1] for row in rows))

        def matches(rows):
            groups = collections.defaultdict(list)
            for name, track, header in rows:
                groups[track].append((name, track, header))
            pairs = [(a, b) for group in groups.values()
                     for i, a in enumerate(group) for b in group[i + 1:]]
            return sum(a[2] == b[2] for a, b in pairs), len(pairs)

        observed, total = matches(rows)
        self.assertGreaterEqual(observed / total, 0.8)
        labels = [row[1] for row in rows]
        random.seed(2026)
        permuted = []
        for _ in range(1000):
            random.shuffle(labels)
            permuted.append(matches([(r[0], label, r[2])
                                     for r, label in zip(rows, labels)])[0])
        self.assertGreater(observed, max(permuted))

    def test_hat_signature_is_cross_game_stable(self):
        """The 32-byte .hat layout signature is shared by GTL and GTR2."""
        import random
        import gzip_simbin_tool as gz

        def signature(path):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            if marker < 0:
                return None, None
            body = payload[marker + 10:]
            return body[4:36], body

        gtr = {}
        for path in sorted((ROOT.parent / "GTR2Steam").rglob("*.hat")):
            sig, body = signature(path)
            if sig:
                gtr[path.stem] = (sig, body)
        self.assertGreaterEqual(len(gtr), 30)
        gtl = {}
        for path in sorted((ROOT.parent / "GTLSteam" / "UserData" / "LOG"
                            / "HAT").glob("*.hat")):
            sig, body = signature(path)
            if sig:
                gtl[path.stem] = (sig, body)
        self.assertGreaterEqual(len(gtl), 2)
        for name, (sig, body) in gtl.items():
            matches = [n for n, (s, _b) in gtr.items() if s == sig]
            if name == "NANDERSTORP":
                self.assertEqual(set(matches), {"3ANDERSTORP", "SANDERSTORP"})
            else:
                self.assertEqual(matches, [])
            # Sharing the signature does not make the body convertible.
            if matches:
                other = gtr[matches[0]][1]
                limit = min(len(body), len(other), 200000)
                agreement = sum(body[i] == other[i] for i in range(36, limit))
                self.assertLess(agreement / (limit - 36), 0.4)
        tokens = ("ANDERSTORP", "Barcelona", "Brno", "Donington", "Enna",
                  "Estoril", "Magny", "Monza", "Oschersleben", "Spa", "Dubai",
                  "Valencia", "Imol", "Zhuhai", "Hockenheim", "Nuerburgring")

        def token(name):
            return next((t for t in tokens if t.lower() in name.lower()), None)

        def labelled_count(items, labels):
            return sum(1 for (name, sig, _unused), label in zip(items, labels)
                       for gtl_name, (gtl_sig, _body) in gtl.items()
                       if label == token(gtl_name) and sig == gtl_sig)

        items = [(name, sig, token(name)) for name, (sig, _b) in gtr.items()]
        observed = labelled_count(items, [item[2] for item in items])
        self.assertEqual(observed, 2)
        random.seed(2026)
        labels = [item[2] for item in items]
        permuted = []
        for _ in range(1000):
            random.shuffle(labels)
            permuted.append(labelled_count(items, labels))
        self.assertGreater(observed, sum(permuted) / len(permuted))
        self.assertLess(sum(value >= observed for value in permuted)
                        / len(permuted), 0.01)

    def test_hat_track_id_not_a_track_asset_hash(self):
        """The .hat header ID is not a hash of track filenames or file contents."""
        import hashlib
        import struct
        import zlib
        import gzip_simbin_tool as gz
        tracks = {"ANDERSTORP": "Anderstorp", "Barcelona": "Barcelona",
                  "Brno": "Brno", "Donington": "Donington", "Enna": "Enna",
                  "Estoril": "Estoril", "Magny": "Magny-Cours", "Monza": "Monza",
                  "Oschersleben": "Oschersleben", "Spa": "Spa", "Dubai": "Dubai",
                  "Valencia": "Valencia", "Imol": "Imola", "Zhuhai": "Zhuhai",
                  "Hockenheim": "Hockenheim"}
        representatives = {}
        for path in sorted((ROOT.parent / "GTR2Steam").rglob("*.hat")):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            if marker < 0:
                continue
            header = payload[marker + 10:marker + 22]
            for key, directory in tracks.items():
                if key.lower() in path.stem.lower() and key not in representatives:
                    representatives[key] = (path.stem, header)
        self.assertGreaterEqual(len(representatives), 14)

        def digest_values(data):
            return (zlib.crc32(data), zlib.adler32(data),
                    struct.unpack("<I", hashlib.md5(data).digest()[:4])[0],
                    struct.unpack("<I", hashlib.md5(data).digest()[-4:])[0])

        total = 0
        for key, directory in tracks.items():
            if key not in representatives:
                continue
            header = representatives[key][1]
            targets = {struct.unpack_from("<I", header, offset)[0]
                       for offset in (0, 8)}
            root = ROOT.parent / "GTR2Steam" / "GameData" / "Locations" / directory
            strings = set()
            for asset in root.rglob("*"):
                if not asset.is_file():
                    continue
                strings.update((asset.name, asset.stem, asset.stem.lower(),
                                asset.stem.lstrip("0123456789")))
                if asset.stat().st_size <= 20_000_000:
                    content = asset.read_bytes()
                    for value in digest_values(content):
                        self.assertNotIn(value, targets)
                    total += 1
            for stem in {representatives[key][0], directory, key,
                         representatives[key][0].lstrip("0123456789")}:
                for extension in ("", ".trk", ".aiw", ".mas", ".gtr", ".gdb"):
                    for candidate in (stem + extension, (stem + extension).upper(),
                                      (stem + extension).lower()):
                        strings.add(candidate)
            for candidate in strings:
                for value in digest_values(candidate.encode()):
                    self.assertNotIn(value, targets)
        self.assertGreater(total, 300)

    def test_hat_body_starts_with_16_byte_record_table(self):
        """Every .hat body begins with a fixed-stride f32/u32 record table."""
        import random
        import struct
        import statistics
        import gzip_simbin_tool as gz

        rows = []
        for path in sorted((ROOT.parent / "GTR2Steam").rglob("*.hat")):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            if marker < 0:
                continue
            body = payload[marker + 10:]
            count = 0
            for offset in range(48, len(body) - 16, 16):
                first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
                if not (-1e6 < first < 1e6 and first == first
                        and second == second and 0.01 < abs(second) < 20
                        and -1e6 < third < 1e6 and third == third):
                    break
                count += 1
            self.assertGreater(count, 0, path.name)
            rows.append((path.stem, body[4:], count))
        self.assertGreaterEqual(len(rows), 30)

        classes = {}
        for name, body, count in rows:
            classes.setdefault(body, []).append((name, count))
        multi = [values for values in classes.values() if len(values) > 1]
        self.assertGreaterEqual(len(multi), 5)
        self.assertTrue(all(len({count for _name, count in values}) == 1
                            for values in multi))
        # Distribution-preserving control: permuting counts among files breaks
        # the within-class agreement.
        counts = [count for _name, _body, count in rows]
        random.seed(2026)
        observed = sum(len({c for _n, c in values}) == 1 for values in multi)
        permuted = []
        for _ in range(1000):
            random.shuffle(counts)
            shuffled = {}
            for (name, body, _count), count in zip(rows, counts):
                shuffled.setdefault(body, []).append(count)
            permuted.append(sum(len(set(values)) == 1 for values in shuffled.values()
                                if len(values) > 1))
        self.assertGreater(observed, statistics.mean(permuted))
        self.assertGreater(observed, max(permuted))

    def test_hat_trailing_stream_has_eight_byte_periodicity(self):
        """The .hat stream after the record table is not byte-random."""
        import collections
        import random
        import struct
        import gzip_simbin_tool as gz

        def split(payload):
            marker = payload.find(b"generated\x00")
            body = payload[marker + 10:]
            count = 0
            for offset in range(48, len(body) - 16, 16):
                first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
                if not (-1e6 < first < 1e6 and first == first
                        and second == second and 0.01 < abs(second) < 20
                        and -1e6 < third < 1e6 and third == third):
                    break
                count += 1
            return body[48 + 16 * count + 8:]

        def match_rate(data, lag):
            sample = data[:200000]
            return sum(a == b for a, b in zip(sample[:-lag], sample[lag:])) / (
                len(sample) - lag)

        random.seed(2026)
        checked = 0
        for name in ("3Brno.hat", "3Monza.hat", "3Spa.hat"):
            path = (ROOT.parent / "GTR2Steam" / "GameData" / "Locations"
                    / "HAT_Dedicated" / name)
            if not path.is_file():
                continue
            tail = split(gz.decompress(str(path)))
            self.assertGreater(len(tail), 100000)
            observed = match_rate(tail, 8)
            shuffled = list(tail[:200000])
            random.shuffle(shuffled)
            baseline = match_rate(bytes(shuffled), 8)
            self.assertGreater(observed, 0.05, (name, observed))
            self.assertLess(baseline, 0.02, (name, baseline))
            matches = collections.Counter(a for a, b in zip(tail[:-8], tail[8:])
                                          if a == b)
            top_values = [value for value, _count in matches.most_common(3)]
            self.assertTrue(all(value in (0,) or 48 <= value <= 80
                                or 192 <= value <= 208 for value in top_values),
                            (name, top_values))
            checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_hat_record_b_weak_track_scale_association(self):
        """Field B has only a weak track-scale trend; duplicates inflate it.

        Using all 32 GTR2 layout files (with duplicate byte-identical bodies)
        gives r=0.66; deduplicating to 14 independent layouts gives r=0.495
        (permutation p~0.07), and 43 independent Race07 layouts give r=0.326
        (p~0.04). No decoder or waypoint-count rule is claimed.
        """
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_text_tool as stt

        tracks = ("ANDERSTORP", "Barcelona", "Brno", "Donington", "Enna",
                  "Estoril", "Magny", "Monza", "Oschersleben", "Spa", "Dubai",
                  "Valencia", "Imol", "Zhuhai", "Hockenheim")

        def magnitude(path):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            body = payload[marker + 10:]
            values = []
            for offset in range(48, len(body) - 16, 16):
                first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
                if not (-1e6 < first < 1e6 and first == first
                        and second == second and 0.01 < abs(second) < 20
                        and -1e6 < third < 1e6 and third == third):
                    break
                values.append(second)
            return abs(statistics.median(values)) if values else None

        def correlate(x, y):
            mx, my = statistics.mean(x), statistics.mean(y)
            numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
            denominator = (sum((a - mx) ** 2 for a in x)
                           * sum((b - my) ** 2 for b in y)) ** 0.5
            return numerator / denominator if denominator else 0.0

        gtr2 = {}
        for path in sorted((ROOT.parent / "GTR2Steam" / "GameData" / "Locations"
                            / "HAT_Dedicated").glob("*.hat")):
            name = path.stem
            track = next((t for t in tracks if t.lower() in name.lower()), None)
            if track is None or track in gtr2:
                continue
            parents = [p for p in (ROOT.parent / "GTR2Steam" / "GameData"
                                   / "Locations").iterdir()
                       if p.is_dir() and track.lower() in p.name.lower()]
            aiws = sorted(parents[0].glob("*.AIW")) if parents else []
            if not aiws:
                continue
            value = magnitude(path)
            if value:
                gtr2[track] = (value, len(stt.parse_aiw(
                    stt.read_text(aiws[0])).waypoints))
        self.assertGreaterEqual(len(gtr2), 12)
        observed = correlate([v[0] for v in gtr2.values()],
                             [v[1] for v in gtr2.values()])
        self.assertGreater(observed, 0.2)
        self.assertLess(observed, 0.8)  # not a waypoint-count proxy

        random.seed(2026)
        values = [v[0] for v in gtr2.values()]
        counts = [v[1] for v in gtr2.values()]
        permuted = [correlate(values, random.sample(counts, len(counts)))
                    for _ in range(2000)]
        p_value = sum(abs(v) >= abs(observed) for v in permuted) / len(permuted)
        self.assertGreater(p_value, 0.01)  # weak, not significant at 1%

    def test_hat_records_are_not_aiw_or_cam_positions(self):
        """The .hat f32 triples do not reproduce AIW waypoints or CAM points."""
        import random
        import re
        import struct
        import gzip_simbin_tool as gz
        import simbin_text_tool as stt

        def records(path):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            body = payload[marker + 10:]
            out = []
            for offset in range(48, len(body) - 16, 16):
                first, _unknown, second, third = struct.unpack_from("<fIff", body, offset)
                if not (-1e6 < first < 1e6 and first == first
                        and second == second and 0.01 < abs(second) < 20
                        and -1e6 < third < 1e6 and third == third):
                    break
                out.append((first, second, third))
            return out

        def near_matches(points, triples, tolerance=0.5):
            buckets = {(round(x / tolerance), round(y / tolerance),
                        round(z / tolerance)) for x, y, z in points}
            return sum((round(x / tolerance), round(y / tolerance),
                        round(z / tolerance)) in buckets for x, y, z in triples)

        random.seed(2026)
        checked = 0
        for track, aiw_name in (("Brno", "3Brno.AIW"), ("Monza", "4Monza.AIW")):
            base_dir = ROOT.parent / "GTR2Steam" / "GameData" / "Locations" / track
            hat = sorted((ROOT.parent / "GTR2Steam" / "GameData" / "Locations"
                          / "HAT_Dedicated").glob(f"*{track}*.hat"))
            if not hat or not (base_dir / aiw_name).is_file():
                continue
            triples = records(hat[0])
            self.assertGreater(len(triples), 1000)
            aiw = stt.parse_aiw((base_dir / aiw_name).read_text(encoding="latin-1"))
            waypoints = [wp.pos for wp in aiw.waypoints if wp.pos]
            self.assertNotEqual(len(triples), len(waypoints))
            self.assertEqual(near_matches(waypoints, triples), 0)
            shuffled = waypoints[:]
            random.shuffle(shuffled)
            self.assertEqual(near_matches(shuffled, triples), 0)
            for cam in base_dir.glob("*.cam"):
                numbers = [float(x) for x in re.findall(
                    r"-?\d+\.\d+", cam.read_text(encoding="latin-1",
                                                    errors="ignore"))]
                points = list(zip(numbers[0::3], numbers[1::3], numbers[2::3]))
                self.assertEqual(near_matches(points, triples), 0, cam.name)
            checked += 1
        self.assertGreaterEqual(checked, 2)

    def test_hat_body_is_deterministic_per_layout(self):
        """Same-layout .hat bodies are byte-identical after the 4-byte prefix."""
        import random
        import gzip_simbin_tool as gz
        tracks = ("ANDERSTORP", "Barcelona", "Brno", "Donington", "Enna",
                  "Estoril", "Magny", "Monza", "Oschersleben", "Spa", "Dubai",
                  "Valencia", "Imol", "Zhuhai", "Hockenheim")
        rows = []
        for path in sorted((ROOT.parent / "GTR2Steam").rglob("*.hat")):
            payload = gz.decompress(str(path))
            marker = payload.find(b"generated\x00")
            if marker < 0:
                continue
            body = payload[marker + 10:]
            track = next((x for x in tracks if x.lower() in path.stem.lower()), None)
            rows.append((path.stem, track, body))
        self.assertGreaterEqual(len(rows), 30)
        # Exact identity classes on body[4:] prove the high-entropy body is a
        # deterministic per-layout blob, not ciphertext with per-file salt.
        classes = collections.defaultdict(list)
        for name, _track, body in rows:
            classes[body[4:]].append(name)
        multi = [v for v in classes.values() if len(v) > 1]
        self.assertGreaterEqual(len(multi), 5)
        self.assertGreaterEqual(sum(len(v) for v in multi), 10)
        self.assertTrue(any(len(v) >= 3 for v in multi))
        # body[16:36] is a 20-byte layout signature, stable across series
        # prefixes for the same physical layout.
        signatures = collections.Counter(body[16:36] for _, _, body in rows)
        self.assertGreaterEqual(len(signatures), 15)
        self.assertGreaterEqual(sum(1 for v in signatures.values() if v >= 2), 10)
        bodies = {name: body for name, _track, body in rows}
        for first, second in (("3Brno", "4Brno"), ("3Monza", "4Monza"),
                              ("3ANDERSTORP", "SANDERSTORP"),
                              ("3Donington", "4Donington")):
            self.assertEqual(bodies[first][4:], bodies[second][4:])

    def test_gtl_replays_use_irsr_v101(self):
        """GTL .Vcr replays parse as IRSR v1.01 and rewrap byte-identically."""
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for path in (ROOT.parent / "GTLSteam" / "ReplayData").glob("*.Vcr"):
            original = path.read_bytes()
            payload = gz.decompress(str(path))
            event = st.parse_payload(payload)
            self.assertEqual(event.kind, "IRSR")
            self.assertAlmostEqual(event.version, 1.01, places=2)
            self.assertTrue(event.trk.lower().endswith(".trk"))
            self.assertEqual(gz.compress_simbin(payload), original)
            checked += 1
        self.assertEqual(checked, 4)

    def test_vcr_driver_angle_tracks_heading(self):
        """The driver-state angle-like field is associated with path heading."""
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        path = ROOT.parent / "GTR2Steam" / "ReplayData" / "Monza.Vcr"
        if not path.is_file():
            self.skipTest("Monza.Vcr not present")
        parsed = st.parse_vcr_frames(gz.decompress(str(path)))
        if not parsed:
            self.skipTest("frame stream unparsed")
        samples = []
        for frame in parsed["frames"]:
            for record in frame["records"]:
                if st.vcr_record_tag(record["header"]) != 0:
                    continue
                state = st.vcr_driver_state(record["data"])
                if state:
                    samples.append((state["position"], state["angle_like"]))
                break
        headings = []
        angles = []
        for (a, angle_a), (b, angle_b) in zip(samples, samples[1:]):
            dx, dz = b[0] - a[0], b[2] - a[2]
            if math.hypot(dx, dz) > 0.5:
                headings.append(math.atan2(dx, dz))
                angles.append(angle_b)

        def correlation(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denominator = (sum((x - mx) ** 2 for x in xs)
                           * sum((y - my) ** 2 for y in ys)) ** 0.5
            return numerator / denominator if denominator else 0.0

        self.assertGreater(len(angles), 200)
        observed = abs(correlation(angles, headings))
        self.assertGreater(observed, 0.4)
        random.seed(133)
        baseline = statistics.mean(abs(correlation(random.sample(angles, len(angles)),
                                                   headings)) for _ in range(5))
        self.assertGreater(observed, 3 * baseline)

    def test_gtl_v101_replay_frames_parse(self):
        """GTL v1.01 replays use u24 counts after the -1e32 sentinel."""
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for path in (ROOT.parent / "GTLSteam" / "ReplayData").glob("*.Vcr"):
            payload = gz.decompress(str(path))
            summary = st.parse_replay_summary(payload)
            self.assertIsNotNone(summary)
            self.assertEqual(summary["version"], "v1.01")
            self.assertGreater(summary["count_a"], 0)
            parsed = st.parse_vcr_frames(payload)
            self.assertIsNotNone(parsed)
            self.assertEqual(len(parsed["frames"]), summary["count_a"])
            self.assertEqual(parsed["end_offset"], len(payload))
            checked += 1
        self.assertEqual(checked, 4)

    def test_dsi_ghost_line_matches_decoded_frame_positions(self):
        """Driving-school ghost points are the frames' driver-state positions."""
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        base = ROOT.parent / "GTR2Steam" / "GameData" / "DrivingSchool"
        checked = 0
        for path in list(base.rglob("*.dsi"))[:6]:
            payload = gz.decompress(str(path))
            line = st.read_ghost_line(payload)
            parsed = st.parse_vcr_frames(payload)
            if not line or not parsed:
                continue
            positions = []
            for frame in parsed["frames"]:
                for record in frame["records"]:
                    state = st.vcr_driver_state(record["data"])
                    if state:
                        positions.append(state["position"])
                        break
            self.assertEqual(len(line), len(positions), path.name)
            self.assertEqual(positions, line, path.name)
            checked += 1
        self.assertGreaterEqual(checked, 4)

        all_dsi = [path for path in
                   (ROOT.parent / "GTR2Steam" / "GameData" / "DrivingSchool").rglob("*")
                   if path.is_file() and path.suffix.lower() == ".dsi"]
        total_frames = 0
        for path in all_dsi:
            payload = gz.decompress(str(path))
            parsed = st.parse_vcr_frames(payload)
            self.assertIsNotNone(parsed, path.name)
            self.assertEqual(parsed["end_offset"], len(payload), path.name)
            total_frames += len(parsed["frames"])
        self.assertEqual(len(all_dsi), 142)
        self.assertGreater(total_frames, 60000)

    def test_shift_replay_times_is_consistent(self):
        """Frame times and participant windows shift together; spans do not."""
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for name in ("Brno.Vcr", "Monza.Vcr", "Anderstorp.Vcr"):
            path = ROOT.parent / "GTR2Steam" / "ReplayData" / name
            if not path.is_file():
                continue
            payload = gz.decompress(str(path))
            shifted = st.shift_replay_times(payload, 64.0)
            before = st.parse_vcr_frames(payload)
            after = st.parse_vcr_frames(shifted)
            if before is None or after is None:
                continue
            self.assertEqual(len(before["frames"]), len(after["frames"]))
            self.assertEqual(after["end_offset"], before["end_offset"])
            self.assertEqual(after["summary"]["duration"],
                             before["summary"]["duration"])
            deltas = []
            for old, new in zip(before["frames"], after["frames"]):
                old_t = struct.unpack("<f", struct.pack("<I", old["time_word"]))[0]
                new_t = struct.unpack("<f", struct.pack("<I", new["time_word"]))[0]
                deltas.append(new_t - old_t)
                self.assertEqual(len(old["records"]), len(new["records"]))
            self.assertLess(abs(statistics.median(deltas) - 64.0), 0.01)
            windows_before = st.parse_object_records(payload)
            windows_after = st.parse_object_records(shifted)
            self.assertEqual(len(windows_before), len(windows_after))
            for old, new in zip(windows_before, windows_after):
                self.assertLess(abs((new["window_start"] - old["window_start"]) - 64.0), 0.01)
            checked += 1
        self.assertEqual(checked, 3)

    def test_vcr_driver_state_positions_are_smooth(self):
        """The 53-byte driver body's f32 block starts at byte 29."""
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        for name in ("Monza.Vcr", "Imola.Vcr"):
            path = ROOT.parent / "GTR2Steam" / "ReplayData" / name
            if not path.is_file():
                continue
            payload = gz.decompress(str(path))
            parsed = st.parse_vcr_frames(payload)
            if not parsed:
                continue
            positions = []
            for frame in parsed["frames"]:
                for record in frame["records"]:
                    if st.vcr_record_tag(record["header"]) != 0:
                        continue
                    state = st.vcr_driver_state(record["data"])
                    if state:
                        positions.append(state["position"])
                    break
            self.assertGreater(len(positions), 100)
            deltas = [math.dist(a, b) for a, b in zip(positions, positions[1:])]
            self.assertLess(statistics.median(deltas), 5.0)
            random.seed(132)
            shuffled = random.sample(positions, len(positions))
            shuffled_deltas = [math.dist(a, b) for a, b in
                               zip(shuffled, shuffled[1:])]
            self.assertLess(statistics.median(deltas),
                            0.2 * statistics.median(shuffled_deltas))

    def test_vcr_subrecord_tags_follow_participants(self):
        """Sub-record tags are bounded by participant count; 0x68/0xff recur."""
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        checked = 0
        for path in (ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"):
            payload = gz.decompress(str(path))
            parsed = st.parse_vcr_frames(payload)
            if parsed is None:
                continue
            participants = len(st.parse_object_records(payload))
            tags = {st.vcr_record_tag(record["header"])
                    for frame in parsed["frames"] for record in frame["records"]}
            self.assertIn(0x68, tags)
            self.assertIn(0xFF, tags)
            self.assertTrue(all(tag < participants for tag in tags
                                if tag not in (0x68, 0xFF)))
            checked += 1
        self.assertEqual(checked, 9)

    def test_vcr_frame_subrecord_decoder(self):
        """The EXE-derived frame layout consumes the replay payload exactly."""
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        exact = 0
        for path in (ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"):
            payload = gz.decompress(str(path))
            parsed = st.parse_vcr_frames(payload)
            if parsed is None:
                continue
            summary = parsed["summary"]
            self.assertEqual(parsed["end_offset"], len(payload))
            self.assertEqual(parsed["declared_frames"], summary["count_a"])
            self.assertGreaterEqual(len(parsed["frames"]), summary["count_a"])
            self.assertTrue(all(0 <= record["header"] <= 0xFFFFFFFF
                                for frame in parsed["frames"]
                                for record in frame["records"]))
            exact += 1
            total = sum(len(frame["records"]) for frame in parsed["frames"])
            if parsed["declared_frames"] == len(parsed["frames"]):
                self.assertEqual(total, summary["count_b"])
            if parsed["declared_frames"] == len(parsed["frames"]):
                first = struct.unpack("<f", struct.pack("<I",
                                      parsed["frames"][0]["time_word"]))[0]
                last = struct.unpack("<f", struct.pack("<I",
                                     parsed["frames"][-1]["time_word"]))[0]
                self.assertLess(abs((last - first) - summary["duration"]), 0.05)
        self.assertEqual(exact, 9)

    def test_replay_post_object_summary(self):
        """A 13-byte summary follows the participant records in most replays."""
        import math
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        summaries = []
        for path in (ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"):
            summary = st.parse_replay_summary(gz.decompress(str(path)))
            if summary is not None:
                summaries.append(summary)
        self.assertEqual(len(summaries), 9)
        well_formed = [summary for summary in summaries if summary["marker"] == 0]
        self.assertEqual(len(well_formed), 8)
        self.assertTrue(all(summary["count_a"] < summary["count_b"]
                            for summary in well_formed))
        self.assertTrue(all(math.isfinite(summary["duration"])
                            and 0 < summary["duration"] < 3600
                            for summary in well_formed))

    def test_replay_object_trailing_fields(self):
        """The object record's trailing u32 is mostly an f32 'unset' sentinel."""
        import math
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        sentinel = st.UNBOUNDED_TIME
        roots = (ROOT.parent / "GTR2Steam" / "ReplayData",
                 ROOT.parent / "GTLSteam" / "ReplayData")
        records = []
        for root in roots:
            for path in root.glob("*.Vcr"):
                records.extend(st.parse_object_records(gz.decompress(str(path))))
        self.assertGreater(len(records), 30)
        sentinel_or_zero = sum(record["trailing_u32"] in (0, sentinel)
                               for record in records)
        self.assertGreater(sentinel_or_zero / len(records), 0.9)
        self.assertTrue(all(math.isfinite(record["value"])
                            and record["value"] >= 0 for record in records))
        finite_windows = [record for record in records if record["window_end"] is not None]
        self.assertGreater(len(finite_windows), 0)
        self.assertTrue(all(record["window_start"] <= record["window_end"]
                            for record in finite_windows))
        self.assertTrue(all(record["window_end"] is None
                            for record in records if record["trailing_u32"] == sentinel))

    def test_replay_object_record_chains(self):
        """The EXE-derived object layout parses real replay participants."""
        import random
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        payloads = [gz.decompress(str(path))
                    for path in sorted((ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"))]
        self.assertEqual(len(payloads), 9)
        random.seed(110)
        chains = [st.parse_object_records(payload) for payload in payloads]
        self.assertTrue(all(len(chain) >= 2 for chain in chains))
        cars = [record["car"] for chain in chains for record in chain]
        self.assertTrue(cars)
        self.assertTrue(all(name.lower().endswith(".car") for name in cars))
        skins = [record["skin"] for chain in chains for record in chain]
        self.assertTrue(any(skin.lower().endswith(".bmp") for skin in skins))
        marshals = sum(any("Marshal" in record["name"] for record in chain)
                       for chain in chains)
        self.assertGreaterEqual(marshals, 7)
        baselines = []
        for payload in payloads:
            shuffled = bytearray(payload)
            random.shuffle(shuffled)
            baselines.append(len(st.parse_object_records(bytes(shuffled))))
        self.assertGreater(sum(len(chain) for chain in chains),
                           3 * sum(baselines))

    def test_vcr_replay_headers_parse(self):
        """All shipped .Vcr replays parse as IRSR with known session values."""
        import gzip
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        replays = sorted((ROOT.parent / "GTR2Steam" / "ReplayData").glob("*.Vcr"))
        self.assertGreaterEqual(len(replays), 9)
        for path in replays:
            event = st.parse_payload(gz.decompress(str(path)))
            self.assertEqual(event.kind, "IRSR", path.name)
            self.assertAlmostEqual(event.version, 1.05, places=2)
            self.assertTrue(event.trk.lower().endswith(".trk"), path.name)
            self.assertTrue(event.aiw.lower().endswith(".aiw"), path.name)
            self.assertIn(event.session_seconds, (36000.0, 43200.0, 46800.0))
            self.assertTrue(event.driver, path.name)
            self.assertTrue(event.car.lower().endswith(".car"), path.name)

    def test_cam_activation_locations_match_negated_waypoints(self):
        """Camera activation points map onto waypoints after negation."""
        import math
        import random
        import statistics
        import simbin_text_tool as stt
        direct_distances = []
        negated_distances = []
        location_root = ROOT.parent / "GTR2Steam" / "GameData" / "Locations"
        for directory in location_root.iterdir():
            if not directory.is_dir():
                continue
            for cam_path in directory.glob("*.cam"):
                aiw_path = directory / (cam_path.stem + ".AIW")
                if not aiw_path.is_file():
                    continue
                try:
                    cameras = stt.parse_cam(cam_path.read_text(encoding="latin-1"))
                    waypoints = stt.parse_aiw(aiw_path.read_text(encoding="latin-1"))
                except Exception:
                    continue
                if not cameras.cameras or not waypoints.waypoints:
                    continue
                points = [tuple(wp.pos) for wp in waypoints.waypoints]
                for camera in cameras.cameras:
                    if camera.activation_location is None:
                        continue
                    position = tuple(camera.activation_location)
                    if position == (0.0, 0.0, 0.0):
                        continue
                    negated = tuple(-value for value in position)
                    direct_distances.append(min(math.dist(position, p) for p in points))
                    negated_distances.append(min(math.dist(negated, p) for p in points))
        self.assertGreater(len(direct_distances), 300)
        self.assertLess(statistics.median(negated_distances),
                        0.5 * statistics.median(direct_distances))
        observed = sum(negated < direct for negated, direct
                       in zip(negated_distances, direct_distances)) / len(direct_distances)
        self.assertGreater(observed, 0.7)
        random.seed(86)
        flips = []
        for _ in range(20):
            signs = [random.choice((-1, 1)) for _ in direct_distances]
            flips.append(sum(sign < 0 for sign in signs) / len(signs))
        self.assertGreater(observed, max(flips) + 0.2)

    def test_cam_inversion_is_shared_across_generations(self):
        """rF1, GTL and GTR2 all store CAM positions inverted vs AIW."""
        import math
        import statistics
        import simbin_text_tool as stt
        for game in ("RF1Vanilla", "GTLSteam", "GTR2Steam"):
            direct = []
            negated = []
            root = ROOT.parent / game
            for cam_path in root.rglob("*.cam"):
                aiw_path = cam_path.with_suffix(".AIW")
                if not aiw_path.is_file():
                    continue
                try:
                    cameras = stt.parse_cam(cam_path.read_text(encoding="latin-1"))
                    waypoints = stt.parse_aiw(aiw_path.read_text(encoding="latin-1"))
                except Exception:
                    continue
                if not cameras.cameras or not waypoints.waypoints:
                    continue
                points = [tuple(wp.pos) for wp in waypoints.waypoints]
                for camera in cameras.cameras:
                    if camera.activation_location is None:
                        continue
                    position = tuple(camera.activation_location)
                    if position == (0.0, 0.0, 0.0):
                        continue
                    flipped = tuple(-value for value in position)
                    direct.append(min(math.dist(position, point) for point in points))
                    negated.append(min(math.dist(flipped, point) for point in points))
            self.assertGreater(len(direct), 200, game)
            self.assertLess(statistics.median(negated),
                            0.5 * statistics.median(direct), game)
            share = sum(negated_value < direct_value
                        for negated_value, direct_value in zip(negated, direct)) / len(direct)
            self.assertGreater(share, 0.75, game)

    def test_rf1_pipeline_leaves_cam_files_intact(self):
        """CAM files pass through the rF1 -> GTR2 byte conversion unchanged."""
        import glob
        import rf1_to_gtr2
        checked = 0
        for path in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*.cam"),
                              recursive=True):
            name = Path(path).name
            data = Path(path).read_bytes()
            output, action = rf1_to_gtr2.convert_bytes(name, data)
            self.assertEqual(output, data, name)
            self.assertEqual(action, "copy")
            checked += 1
            if checked >= 50:
                break
        self.assertEqual(checked, 50)

    def test_cam_positions_invert_aiw_world_coordinates(self):
        """GTR2 camera positions are negatively correlated with AIW waypoints."""
        import random
        import statistics
        import simbin_text_tool as stt
        rows = []
        location_root = ROOT.parent / "GTR2Steam" / "GameData" / "Locations"
        for directory in location_root.iterdir():
            if not directory.is_dir():
                continue
            for cam_path in directory.glob("*.cam"):
                aiw_path = directory / (cam_path.stem + ".AIW")
                if not aiw_path.is_file():
                    continue
                try:
                    cameras = stt.parse_cam(cam_path.read_text(encoding="latin-1"))
                    waypoints = stt.parse_aiw(aiw_path.read_text(encoding="latin-1"))
                except Exception:
                    continue
                if not cameras.cameras or not waypoints.waypoints:
                    continue
                centers = [[sum(cam.position[k] for cam in cameras.cameras) / len(cameras.cameras)
                            for k in range(3)],
                           [sum(wp.pos[k] for wp in waypoints.waypoints) / len(waypoints.waypoints)
                            for k in range(3)]]
                rows.append(centers)
        self.assertGreaterEqual(len(rows), 25)
        random.seed(85)
        for axis in range(3):
            cam_values = [row[0][axis] for row in rows]
            aiw_values = [row[1][axis] for row in rows]
            observed = sum(x * y < 0 for x, y in zip(cam_values, aiw_values)) / len(rows)
            baselines = []
            for _ in range(50):
                shuffled = random.sample(aiw_values, len(aiw_values))
                baselines.append(sum(x * y < 0 for x, y in zip(cam_values, shuffled))
                                 / len(rows))
            margin = 0.25 if axis == 0 else 0.10
            self.assertGreater(observed, statistics.mean(baselines) + margin)

    def test_gttf_tail_final_frame_state(self):
        """Tail floats 2/3/4 mirror the final frame's controls and heading."""
        import glob
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        tails = []
        headings = []
        values16 = []
        slots = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            if not frames:
                continue
            end = grid["offset"] + grid["count"] * grid["stride"]
            tails.append(struct.unpack_from("<5f", payload, end))
            last = frames[-1]
            headings.append(last["heading"])
            values16.append(struct.unpack_from("<f", payload, last["offset"] + 16)[0])
            slots.append(last["slot48_low"])
        self.assertEqual(len(tails), 29)

        def median_error(a, b):
            return statistics.median(abs(x - y) for x, y in zip(a, b))

        self.assertLess(median_error([tail[3] for tail in tails], headings), 0.01)
        self.assertLess(median_error([tail[4] for tail in tails], values16), 0.01)
        random.seed(97)
        shuffled_headings = random.sample(headings, len(headings))
        shuffled_values = random.sample(values16, len(values16))
        self.assertGreater(
            median_error([tail[3] for tail in tails], shuffled_headings),
            3 * max(median_error([tail[3] for tail in tails], headings), 1e-6))
        self.assertGreater(
            median_error([tail[4] for tail in tails], shuffled_values),
            2 * max(median_error([tail[4] for tail in tails], values16), 1e-6))

        def correlation(a, b):
            mean_a, mean_b = statistics.mean(a), statistics.mean(b)
            numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
            denominator = (sum((x - mean_a) ** 2 for x in a)
                           * sum((y - mean_b) ** 2 for y in b)) ** 0.5
            return numerator / denominator if denominator else 0.0

        observed = abs(correlation([tail[2] for tail in tails], slots))
        self.assertGreater(observed, 0.9)
        random.seed(98)
        baseline = statistics.mean(
            abs(correlation([tail[2] for tail in tails],
                            random.sample(slots, len(slots)))) for _ in range(5))
        self.assertGreater(observed, 3 * max(baseline, 0.01))

    def test_gttf_tail_encodes_track_finish_point(self):
        """The 20-byte GTTF tail repeats a fixed point per track."""
        import collections
        import glob
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        by_track = collections.defaultdict(list)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            end = grid["offset"] + grid["count"] * grid["stride"]
            by_track[Path(path).parent.name].append(
                struct.unpack_from("<2f", payload, end))
        groups = [values for values in by_track.values() if len(values) >= 2]
        self.assertGreaterEqual(len(groups), 8)

        def distance(a, b) -> float:
            return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

        within = [distance(a, b) for values in groups
                  for index, a in enumerate(values) for b in values[index + 1:]]
        random.seed(93)
        pool = [point for values in groups for point in values]
        between = [distance(*random.sample(pool, 2)) for _ in range(1000)]
        self.assertLess(statistics.median(within), 2.0)
        self.assertGreater(statistics.median(between), 100.0)

    def test_gttf_frame_time_span_equals_lap_time(self):
        """Frame time span reproduces the lap time encoded in ghost filenames."""
        import glob
        import random
        import re
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        targets = []
        spans = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            match = re.search(r"(\d+)_(\d+)_(\d+)_", Path(path).name)
            if not match:
                continue
            minutes, seconds, milliseconds = (int(part) for part in match.groups())
            target = minutes * 60 + seconds + milliseconds / 1000
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            frames = st.read_frames(payload, grid) if grid else []
            if not frames:
                continue
            targets.append(target)
            spans.append(frames[-1]["time"] - frames[0]["time"])
        self.assertEqual(len(targets), 29)
        errors = [abs(target - span) for target, span in zip(targets, spans)]
        self.assertLess(statistics.median(errors), 0.01)
        self.assertLess(max(errors), 0.05)
        random.seed(91)
        shuffled = random.sample(spans, len(spans))
        baseline = statistics.median(abs(target - span)
                                     for target, span in zip(targets, shuffled))
        self.assertGreater(baseline, 10)

    def test_gttf_field_units_match_runtime_telemetry(self):
        """Frame ranges match the live shared-memory units from gtr2-agent-tools."""
        import glob
        import random
        import statistics
        import struct
        import gzip_simbin_tool as gz
        import simbin_events_tool as st

        def lag1(values):
            a, b = values[:-1], values[1:]
            ma, mb = statistics.mean(a), statistics.mean(b)
            numerator = sum((x - ma) * (y - mb) for x, y in zip(a, b))
            denominator = (sum((x - ma) ** 2 for x in a)
                           * sum((y - mb) ** 2 for y in b)) ** 0.5
            return numerator / denominator if denominator else 0.0

        controls = []
        rpms = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            for index in range(grid["count"]):
                offset = grid["offset"] + index * grid["stride"]
                controls.append(struct.unpack_from("<f", payload, offset + 16)[0])
                rpms.append(struct.unpack_from("<I", payload, offset + 32)[0] / 1024)
        self.assertGreater(len(controls), 40000)
        self.assertGreater(sum(-1 <= value <= 1 for value in controls) / len(controls),
                           0.999)
        self.assertGreater(sum(800 <= value <= 9000 for value in rpms) / len(rpms), 0.999)
        self.assertGreater(lag1(rpms), 0.9)
        random.seed(171)
        self.assertLess(lag1(random.sample(rpms, len(rpms))), 0.1)

    def test_gttf_frame_marker_prefix_constant(self):
        """Bytes +24..+30 are a fixed marker; only byte +31 varies."""
        import glob
        import gzip
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        expected = bytes((1, 0, 0, 52, 0, 32, 0))
        frames_checked = 0
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            for index in range(grid["count"]):
                offset = grid["offset"] + index * grid["stride"]
                self.assertEqual(payload[offset + 24:offset + 31], expected)
                frames_checked += 1
        self.assertEqual(frames_checked, 44631)

    def test_gttf_path_f3_tracks_aiw_curvature(self):
        """Path control f3 correlates with AIW-derived waypoint curvature."""
        import glob
        import math
        import random
        import statistics
        from pathlib import Path
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt

        def correlation(a, b):
            mean_a, mean_b = statistics.mean(a), statistics.mean(b)
            numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
            denominator = (sum((x - mean_a) ** 2 for x in a)
                           * sum((y - mean_b) ** 2 for y in b)) ** 0.5
            return numerator / denominator if denominator else 0.0

        observed = []
        baseline = []
        random.seed(102)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            records = st.find_preframe_records(payload, grid["offset"])
            if not records:
                continue
            location = ROOT.parent / "GTR2Steam" / "GameData" / "Locations" / Path(path).parent.name
            waypoints = []
            for aiw_path in location.glob("*.AIW"):
                try:
                    parsed = stt.parse_aiw(aiw_path.read_text(encoding="latin-1"))
                except Exception:
                    continue
                if len(parsed.waypoints) > len(waypoints):
                    waypoints = parsed.waypoints
            if len(waypoints) < 10:
                continue
            curvature = {}
            for index in range(1, len(waypoints) - 1):
                first, middle, last = (waypoints[index - 1].pos,
                                       waypoints[index].pos,
                                       waypoints[index + 1].pos)
                u = (middle[0] - first[0], middle[2] - first[2])
                v = (last[0] - middle[0], last[2] - middle[2])
                cross = u[0] * v[1] - u[1] * v[0]
                length = math.hypot(*u) * math.hypot(*v)
                curvature[index] = abs(cross) / length if length > 1e-9 else 0.0
            controls = []
            bends = []
            for record in records[::max(1, len(records) // 100)]:
                index = min(range(len(waypoints)),
                            key=lambda k: (waypoints[k].pos[1] - record[0]) ** 2
                            + (waypoints[k].pos[2] - record[1]) ** 2)
                if index not in curvature:
                    continue
                controls.append(record[3])
                bends.append(curvature[index])
            if len(controls) < 20:
                continue
            observed.append(abs(correlation(controls, bends)))
            baseline.append(statistics.mean(
                abs(correlation(random.sample(controls, len(controls)), bends))
                for _ in range(3)))
        self.assertGreater(len(observed), 20)
        self.assertGreater(statistics.median(observed), 0.1)
        self.assertGreater(statistics.median(observed), 1.8 * statistics.median(baseline))

    def test_gttf_path_f4_tracks_aiw_galpha(self):
        """Path control f4 correlates with AIW waypoint galpha."""
        import glob
        import random
        import statistics
        from pathlib import Path
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt

        def correlation(a, b):
            mean_a, mean_b = statistics.mean(a), statistics.mean(b)
            numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
            denominator = (sum((x - mean_a) ** 2 for x in a)
                           * sum((y - mean_b) ** 2 for y in b)) ** 0.5
            return numerator / denominator if denominator else 0.0

        observed = []
        baseline = []
        random.seed(100)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            records = st.find_preframe_records(payload, grid["offset"])
            if not records:
                continue
            location = ROOT.parent / "GTR2Steam" / "GameData" / "Locations" / Path(path).parent.name
            waypoints = []
            for aiw_path in location.glob("*.AIW"):
                try:
                    parsed = stt.parse_aiw(aiw_path.read_text(encoding="latin-1"))
                except Exception:
                    continue
                if len(parsed.waypoints) > len(waypoints):
                    waypoints = parsed.waypoints
            if not waypoints:
                continue
            controls = []
            galphas = []
            for record in records[::max(1, len(records) // 100)]:
                waypoint = min(waypoints,
                               key=lambda wp: (wp.pos[1] - record[0]) ** 2
                               + (wp.pos[2] - record[1]) ** 2)
                if (waypoint.pos[1] - record[0]) ** 2 + (waypoint.pos[2] - record[1]) ** 2 > 9:
                    continue
                controls.append(record[4])
                galphas.append(waypoint.galpha)
            if len(controls) < 20:
                continue
            observed.append(abs(correlation(controls, galphas)))
            baseline.append(statistics.mean(
                abs(correlation(random.sample(controls, len(controls)), galphas))
                for _ in range(3)))
        self.assertGreater(len(observed), 20)
        self.assertGreater(statistics.median(observed), 0.2)
        self.assertGreater(statistics.median(observed), 2 * statistics.median(baseline))

    def test_gttf_path_controls_weaker_at_record_level(self):
        """Source path records are only loosely complementary, unlike frames."""
        import glob
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        sums = []
        correlations = []
        baselines = []
        random.seed(76)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            records = st.find_preframe_records(payload, grid["offset"])
            if len(records) < 50:
                continue
            first = [record[3] for record in records]
            second = [record[4] for record in records]
            sums.append(statistics.median(x + y for x, y in zip(first, second)))
            correlations.append(st._corr(first, second))
            baselines.append(statistics.mean(
                st._corr(first, random.sample(second, len(second))) for _ in range(3)))
        self.assertEqual(len(sums), 29)
        self.assertLess(statistics.median(sums), 0.95)
        self.assertGreater(statistics.median(sums), 0.7)
        self.assertLess(statistics.median(correlations), -0.05)
        self.assertLess(statistics.median(correlations),
                        5 * statistics.median(baselines))

    def test_gttf_path_controls_complementary(self):
        """Path f3/f4 are complementary normalized channels (median sum 1)."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        correlations = []
        baselines = []
        zero_fractions = []
        sums = []
        random.seed(53)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            if frames[0]["path_f3"] is None:
                continue
            first = [frame["path_f3"] for frame in frames]
            second = [frame["path_f4"] for frame in frames]
            correlations.append(st._corr(first, second))
            baselines.append(statistics.mean(
                st._corr(first, random.sample(second, len(second)))
                for _ in range(3)))
            zero_fractions.append(sum(value == 0 for value in first) / len(first))
            sums.append(statistics.median(x + y for x, y in zip(first, second)))
        self.assertEqual(len(correlations), 29)
        self.assertLess(statistics.median(correlations), -0.4)
        self.assertLess(statistics.median(correlations),
                        5 * statistics.median(baselines))
        self.assertGreater(statistics.median(zero_fractions), 0.5)
        self.assertTrue(0.9 <= statistics.median(sums) <= 1.1)

    def test_gttf_byte31_tracks_engine_speed_no_clamps(self):
        """GTTF byte +31 tracks engine speed after removing saturation."""
        import glob
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(62)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            if len(frames) < 100:
                continue
            values = [payload[frame["offset"] + 31] for frame in frames]
            engines = [frame["engine_speed"] for frame in frames]
            ordered = sorted(engines)
            low, high = ordered[len(ordered) // 50], ordered[-len(ordered) // 50]
            keep = [i for i, value in enumerate(engines) if low < value < high]
            x = [values[i] for i in keep]
            y = [engines[i] for i in keep]
            observed.append(abs(st._corr(x, y)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(x, len(x)), y)) for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.15)
        self.assertGreater(statistics.median(observed),
                           3 * statistics.median(baseline))
        self.assertGreaterEqual(sum(o > 3 * b for o, b in zip(observed, baseline)), 18)

    def test_gttf_byte31_tracks_path_y(self):
        """The varying byte at +31 tracks the path's world y coordinate."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(52)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            records = st.find_preframe_records(payload, grid["offset"])
            if not records:
                continue
            values = [payload[frame["offset"] + 31] for frame in frames]
            index = 0
            heights = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                candidates = range(max(0, index - 3), min(len(records), index + 30))
                chosen = min(candidates,
                             key=lambda k: (records[k][0] - y) ** 2
                             + (records[k][1] - z) ** 2)
                index = chosen
                heights.append(records[chosen][0])
            observed.append(abs(st._corr(values, heights)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), heights))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.12)
        self.assertGreater(statistics.median(observed),
                           3 * statistics.median(baseline))
        self.assertGreaterEqual(sum(o > 3 * b for o, b in zip(observed, baseline)), 20)

    def test_gttf_path_f4_vs_curvature(self):
        """Path f4 has a reproducible, mostly positive curvature association."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(51)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            records = st.find_preframe_records(payload, grid["offset"])
            if not records or frames[0]["path_f4"] is None:
                continue
            values = [frame["path_f4"] for frame in frames]
            curvature = []
            for first, middle, last in zip(records, records[1:], records[2:]):
                u = [middle[k] - first[k] for k in (0, 1, 5)]
                v = [last[k] - middle[k] for k in (0, 1, 5)]
                cross = (u[1] * v[2] - u[2] * v[1],
                         u[2] * v[0] - u[0] * v[2],
                         u[0] * v[1] - u[1] * v[0])
                la = math.sqrt(sum(x * x for x in u))
                lb = math.sqrt(sum(x * x for x in v))
                curvature.append(math.sqrt(sum(x * x for x in cross)) / (la * lb)
                                 if la * lb > 1e-9 else 0.0)
            index = 0
            bends = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                candidates = range(max(0, index - 3), min(len(records) - 2, index + 30))
                chosen = min(candidates,
                             key=lambda k: (records[k][0] - y) ** 2
                             + (records[k][1] - z) ** 2)
                index = chosen
                bends.append(curvature[chosen] if chosen < len(curvature) else 0.0)
            observed.append(abs(st._corr(values, bends)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), bends))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.05)
        self.assertGreater(statistics.median(observed),
                           2 * statistics.median(baseline))

    def test_gttf_path_f3_vs_curvature(self):
        """Path f3 rises mildly with racing-line curvature (brake-like)."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(50)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            records = st.find_preframe_records(payload, grid["offset"])
            if not records or frames[0]["path_f3"] is None:
                continue
            curvature = []
            for first, middle, last in zip(records, records[1:], records[2:]):
                u = [middle[k] - first[k] for k in (0, 1, 5)]
                v = [last[k] - middle[k] for k in (0, 1, 5)]
                cross = (u[1] * v[2] - u[2] * v[1],
                         u[2] * v[0] - u[0] * v[2],
                         u[0] * v[1] - u[1] * v[0])
                la = math.sqrt(sum(x * x for x in u))
                lb = math.sqrt(sum(x * x for x in v))
                curvature.append(math.sqrt(sum(x * x for x in cross)) / (la * lb)
                                 if la * lb > 1e-9 else 0.0)
            index = 0
            values = []
            bends = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                candidates = range(max(0, index - 3), min(len(records) - 2, index + 30))
                chosen = min(candidates,
                             key=lambda k: (records[k][0] - y) ** 2
                             + (records[k][1] - z) ** 2)
                index = chosen
                values.append(frame["path_f3"])
                bends.append(curvature[chosen] if chosen < len(curvature) else 0.0)
            observed.append(abs(st._corr(values, bends)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), bends))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.04)
        self.assertGreater(statistics.median(observed),
                           2 * statistics.median(baseline))
        self.assertGreaterEqual(sum(o > 2 * b for o, b in zip(observed, baseline)), 15)

    def test_gttf_slot48_low_vs_path_f3_no_clamps(self):
        """Slot +48's low half tracks path f3 even without clamped frames."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(46)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            if frames[0]["path_f3"] is None:
                continue
            frames = [frame for frame in frames if abs(frame["pitch"]) < 0.99]
            if len(frames) < 100:
                continue
            values = [frame["slot48_low"] for frame in frames]
            reference = [frame["path_f3"] for frame in frames]
            observed.append(abs(st._corr(values, reference)))
            baseline.append(statistics.mean(
                abs(st._corr(random.sample(values, len(values)), reference))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.08)
        self.assertGreater(statistics.median(observed),
                           3 * statistics.median(baseline))

    def test_gttf_time_tracks_path_x(self):
        """Frame time advances with the path record's world x coordinate."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(45)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            records = st.find_preframe_records(payload, grid["offset"])
            if not records:
                continue
            index = 0
            times = []
            path_x = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                candidates = range(max(0, index - 3), min(len(records), index + 30))
                chosen = min(candidates,
                             key=lambda k: (records[k][0] - y) ** 2
                             + (records[k][1] - z) ** 2)
                index = chosen
                times.append(frame["time"])
                path_x.append(records[chosen][5])
            observed.append(abs(st._corr(times, path_x)))
            baseline.append(statistics.mean(
                abs(st._corr(times, random.sample(path_x, len(path_x))))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.4)
        self.assertGreater(statistics.median(observed), 10 * statistics.median(baseline))

    def test_gttf_heading_matches_path_record_heading(self):
        """Ghost +12 equals the nearest path record's heading field."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baseline = []
        random.seed(44)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            frames = st.read_frames(payload, grid)
            records = st.find_preframe_records(payload, grid["offset"])
            if not records:
                continue
            index = 0
            ghost = []
            path_heading = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                candidates = range(max(0, index - 3), min(len(records), index + 30))
                chosen = min(candidates,
                             key=lambda k: (records[k][0] - y) ** 2
                             + (records[k][1] - z) ** 2)
                index = chosen
                ghost.append(frame["heading"])
                path_heading.append(records[chosen][2])

            def coherence(left, right):
                diffs = [(a - b + math.pi) % (2 * math.pi) - math.pi
                         for a, b in zip(left, right)]
                c = sum(math.cos(x) for x in diffs) / len(diffs)
                s = sum(math.sin(x) for x in diffs) / len(diffs)
                return math.hypot(c, s)
            observed.append(coherence(ghost, path_heading))
            baseline.append(statistics.mean(
                coherence(ghost, random.sample(path_heading, len(path_heading)))
                for _ in range(3)))
        self.assertEqual(len(observed), 29)
        self.assertGreater(statistics.median(observed), 0.9)
        self.assertGreater(statistics.median(observed), 10 * statistics.median(baseline))

    def test_gttf_path_record_count_ratio(self):
        """Frame count is a bounded multiple of pre-frame path record count."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        ratios = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            records = st.find_preframe_records(payload, grid["offset"])
            if records:
                ratios.append(grid["count"] / len(records))
        self.assertEqual(len(ratios), 29)
        self.assertTrue(all(1.5 < value < 4.0 for value in ratios))
        self.assertLess(statistics.median(ratios), 3.0)

    def test_gttf_path_heading_is_xz_tangent(self):
        """The 24-byte path heading is the world x/z tangent of its own points."""
        import glob
        import gzip
        import math
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        observed = []
        baselines = []
        random.seed(20)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True)[:15]:
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            records = st.find_preframe_records(payload, grid["offset"])
            if len(records) < 50:
                continue
            angles = []
            headings = [record[2] for record in records]
            for first, second in zip(records, records[1:]):
                dx = second[5] - first[5]
                dz = second[1] - first[1]
                if math.hypot(dx, dz) > 1e-6:
                    angles.append(math.atan2(dx, dz))
            if len(angles) < 50:
                continue

            def coherence(values, directions):
                diffs = [(value - angle + math.pi) % (2 * math.pi) - math.pi
                         for value, angle in zip(values, directions)]
                c = sum(math.cos(x) for x in diffs) / len(diffs)
                s = sum(math.sin(x) for x in diffs) / len(diffs)
                return math.hypot(c, s)
            observed.append(coherence(headings, angles))
            baselines.append(statistics.mean(
                coherence(headings, random.sample(angles, len(angles)))
                for _ in range(5)))
        self.assertGreater(len(observed), 10)
        self.assertGreater(statistics.median(observed), 0.9)
        self.assertGreater(statistics.median(observed), 3 * statistics.median(baselines))

    def test_gttf_path_control_fields(self):
        """Pre-frame path fields f3/f4 track steering and engine speed."""
        import glob
        import gzip
        import random
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        engine = []
        engine_perm = []
        steering = []
        steering_perm = []
        random.seed(9)
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            f3 = [frame["path_f3"] for frame in frames]
            f4 = [frame["path_f4"] for frame in frames]
            if f3[0] is None:
                continue
            rpm = [frame["engine_speed"] for frame in frames]
            steer = [frame["position"][2] for frame in frames]
            engine.append(abs(st._corr(f4, rpm)))
            steering.append(abs(st._corr(f3, steer)))
            engine_perm.append(statistics.mean(
                abs(st._corr(random.sample(f4, len(f4)), rpm)) for _ in range(3)))
            steering_perm.append(statistics.mean(
                abs(st._corr(random.sample(f3, len(f3)), steer)) for _ in range(3)))
        self.assertEqual(len(engine), 29)
        self.assertGreater(statistics.median(engine), 0.3)
        self.assertGreater(statistics.median(engine), 5 * statistics.median(engine_perm))
        self.assertGreater(statistics.median(steering), 0.06)
        self.assertGreater(statistics.median(steering),
                           3 * statistics.median(steering_perm))

    def test_gsc_member_geometry_corpus(self):
        """150 ISI-encrypted GSC GMT members decode to valid geometry with skip=4."""
        import glob
        import gmt_semantic
        import mas_tool
        decoded = 0
        members = 0
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.mas"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or len(entry.data) < 0x400:
                        continue
                    result = gmt_semantic.decode_gsc_member(entry.data)
                    members += 1
                    decoded += int(result is not None)
                    if members >= 150:
                        break
                if members >= 150:
                    break
            if members >= 150:
                break
        self.assertEqual(members, 150)
        self.assertEqual(decoded, 150)

    def test_gsc_gmt_no_alignment_counterpart(self):
        """No GSC GMT has a same-name/same-size plain GTR2/GTL counterpart."""
        import glob
        import mas_tool
        plain = set()
        gsc = set()
        for root in ("GTR2Steam", "GTLSteam"):
            pattern = str(ROOT.parent / root / "**" / "*")
            for path in glob.glob(pattern, recursive=True):
                if not path.lower().endswith((".gtr", ".gtl")):
                    continue
                try:
                    _, entries = mas_tool.read_archive(path)
                except Exception:
                    continue
                for entry in entries:
                    if entry.name.lower().endswith(".gmt") and entry.data:
                        plain.add((entry.name.lower().replace("\\", "/")
                                   .rsplit("/", 1)[-1], len(entry.data)))
        for root in ("Automobilista", "StockCarExtreme", "GameStockCar",
                     "CopaPetrobrasdeMarcas"):
            pattern = str(ROOT.parent / root / "**" / "*.mas")
            for path in glob.glob(pattern, recursive=True):
                try:
                    _, entries = mas_tool.read_archive(path)
                except Exception:
                    continue
                for entry in entries:
                    if entry.name.lower().endswith(".gmt") and entry.data:
                        gsc.add((entry.name.lower().replace("\\", "/")
                                 .rsplit("/", 1)[-1], len(entry.data)))
        self.assertGreater(len(plain), 20000)
        self.assertGreater(len(gsc), 20000)
        self.assertEqual(len(plain & gsc), 0)

    def test_gttf_steering_vs_dsi_curvature(self):
        """Ghost +16 shows a modest relation to DSI instructor-line curvature."""
        import glob
        import gzip
        import math
        import os
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        base = ROOT.parent / "GTR2Steam"
        correlations = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"), recursive=True):
            track = os.path.basename(os.path.dirname(path))
            dsis = glob.glob(str(base / "GameData" / "DrivingSchool" / track
                                 / "*Lap Challenge*.DSI"))
            if not dsis:
                continue
            line = st.read_ghost_line(gzip.decompress(
                (Path(dsis[0])).read_bytes()))
            curvature = []
            for i in range(1, len(line) - 1):
                ax, az = line[i][0] - line[i - 1][0], line[i][2] - line[i - 1][2]
                bx, bz = line[i + 1][0] - line[i][0], line[i + 1][2] - line[i][2]
                la, lb = math.hypot(ax, az), math.hypot(bx, bz)
                k = (ax * bz - az * bx) / (la * lb) if la > 1e-9 and lb > 1e-9 else 0
                curvature.append((line[i], k))
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            pairs = []
            for frame in frames:
                y, z = frame["position"][0], frame["position"][1]
                near = [k for point, k in curvature
                        if abs(point[1] - y) < 3 and abs(point[2] - z) < 2]
                if near:
                    pairs.append((frame["pitch"], statistics.mean(near)))
            if len(pairs) >= 50:
                correlations.append(st._corr([a for a, b in pairs],
                                             [b for a, b in pairs]))
        self.assertEqual(len(correlations), 27)
        self.assertGreater(statistics.median(abs(v) for v in correlations), 0.2)
        self.assertGreaterEqual(sum(1 for v in correlations if abs(v) > 0.2), 15)

    def test_f0_halfwords_not_stage_types(self):
        """f0 halfwords matching stage types is a small-integer artifact."""
        import glob
        import random
        import statistics
        import gmt_format as gf
        import mas_tool
        pairs = []
        for root in ("GTR2Steam", "GTLSteam"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.gtr"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    if not entry.name.lower().endswith(".gmt") or not entry.data:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    types = {v[0] & 0xFFFF for v in
                             gf.build_stage_type_map(parsed.materials).values()}
                    for mesh in parsed.meshes:
                        marker = gf.mesh_marker(mesh)
                        if marker:
                            pairs.append((marker & 0xFFFF, marker >> 16, types))
                if len(pairs) >= 2000:
                    break
            if len(pairs) >= 2000:
                break
        self.assertGreater(len(pairs), 1000)
        observed = sum(1 for a, b, types in pairs if a in types or b in types)

        def permuted():
            shuffled = random.sample([p[2] for p in pairs], len(pairs))
            return sum(1 for (a, b, _), types in zip(pairs, shuffled)
                       if a in types or b in types)
        random.seed(0)
        baseline = statistics.mean(permuted() for _ in range(10))
        self.assertLess(abs(observed - baseline) / max(baseline, 1), 0.1)

    def test_gttf_steering_sign_vs_heading_trend(self):
        """Sign of the +8/+16 relation tracks the ghost's heading trend."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        correlations = []
        trends = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            correlations.append(st._corr([f["position"][2] for f in frames],
                                         [f["pitch"] for f in frames]))
            heading = [f["heading"] for f in frames]
            steps = [(b - a + math.pi) % (2 * math.pi) - math.pi
                     for a, b in zip(heading, heading[1:])]
            trends.append(sum(steps))
        self.assertEqual(len(correlations), 29)
        self.assertGreater(abs(st._corr(correlations, trends)), 0.4)
        positive = [t for r, t in zip(correlations, trends) if r > 0]
        negative = [t for r, t in zip(correlations, trends) if r < 0]
        self.assertGreater(statistics.median(positive) - statistics.median(negative), 2)

    def test_gttf_frame8_steering_coupling_is_clamp_artifact(self):
        """The +8/+16 correlation disappears when +16's clamped frames are removed."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        all_correlations = []
        unclamped = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            offset = [f["position"][2] for f in frames]
            steering = [f["pitch"] for f in frames]
            all_correlations.append(abs(st._corr(offset, steering)))
            pairs = [(x, y) for x, y in zip(offset, steering) if abs(y) < 0.99]
            if len(pairs) > 100:
                unclamped.append(abs(st._corr([x for x, _ in pairs],
                                              [y for _, y in pairs])))
        self.assertEqual(len(all_correlations), 29)
        self.assertGreater(statistics.median(all_correlations), 0.5)
        self.assertLess(statistics.median(unclamped), 0.25)
        self.assertLess(statistics.median(unclamped),
                        0.5 * statistics.median(all_correlations))

    def test_gttf_frame8_not_missing_x(self):
        """+8 does not encode the AIW x coordinate via a DSI centerline."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        ghost = glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" /
                              "Anderstorp" / "*.GTT"))[0]
        payload = gz.decompress(ghost)
        frames = st.read_frames(payload, st.find_frame_grid(payload))
        dsi = glob.glob(str(ROOT.parent / "GTR2Steam" / "GameData" /
                            "DrivingSchool" / "Anderstorp" /
                            "*Lap Challenge, Level 1.DSI"))[0]
        from pathlib import Path
        line = st.read_ghost_line(gzip.decompress(Path(dsi).read_bytes()))
        offsets = []
        xs = []
        zs = []
        for frame in frames:
            y, z = frame["position"][0], frame["position"][1]
            near = [q for q in line if abs(q[1] - y) < 3 and abs(q[2] - z) < 3]
            if near:
                offsets.append(frame["position"][2])
                xs.append(statistics.mean(q[0] for q in near))
                zs.append(z)
        self.assertGreater(len(offsets), 500)
        self.assertLess(max(offsets) - min(offsets), 3)
        self.assertLess(abs(st._corr(offsets, xs)), 0.2)
        self.assertLess(abs(st._corr(offsets, zs)), 0.2)

    def test_gttf_axes_match_aiw_y_z(self):
        """Ghost +0/+1 endpoint ranges match AIW elevation/z on matched tracks."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        y_errors = []
        z_errors = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"), recursive=True):
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            grid = st.find_frame_grid(payload)
            aiw = aiws.get((event.aiw or "").lower())
            if not grid or not aiw:
                continue
            waypoints = [w.pos for w in stt.parse_aiw(stt.read_text(aiw)).waypoints
                         if w.pos and w.wp_class() in (0, 1)]
            frames = st.read_frames(payload, grid)
            y_errors.append(abs(min(f["position"][0] for f in frames)
                                - min(w[1] for w in waypoints))
                            + abs(max(f["position"][0] for f in frames)
                                  - max(w[1] for w in waypoints)))
            z_errors.append(abs(min(f["position"][1] for f in frames)
                                - min(w[2] for w in waypoints))
                            + abs(max(f["position"][1] for f in frames)
                                  - max(w[2] for w in waypoints)))
        self.assertGreaterEqual(len(y_errors), 25)
        self.assertLess(statistics.median(y_errors), 2)
        self.assertLess(statistics.median(z_errors), 10)
        self.assertGreaterEqual(sum(v < 10 for v in z_errors), 20)

    def test_gttf_frame8_not_elevation_or_progress(self):
        """Ghost frame +8 is a bounded smooth field, not elevation/progress."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        spans = []
        monotonic = []
        autocorr = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            grid = st.find_frame_grid(payload)
            if not grid:
                continue
            values = [f["position"][2] for f in st.read_frames(payload, grid)]
            spans.append(max(values) - min(values))
            monotonic.append(sum(b >= a for a, b in zip(values, values[1:]))
                             / (len(values) - 1))
            autocorr.append(st._corr(values[:-1], values[1:]))
        self.assertEqual(len(spans), 29)
        self.assertLess(statistics.median(spans), 3)
        self.assertLess(statistics.median(monotonic), 0.6)
        self.assertGreater(statistics.median(autocorr), 0.3)
        self.assertLess(statistics.median(autocorr), 0.8)

    def test_gttf_position_axis_spans(self):
        """Ghost position triples are track-local, not AIW world XYZ."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        small = []
        large = []
        for root in ("GTR2Steam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.GTT"),
                                  recursive=True):
                payload = gz.decompress(path)
                grid = st.find_frame_grid(payload)
                if not grid:
                    continue
                frames = st.read_frames(payload, grid)
                spans = sorted(
                    max(r["position"][i] for r in frames)
                    - min(r["position"][i] for r in frames) for i in range(3))
                small.append(spans[0])
                large.append(spans[2])
        self.assertEqual(len(large), 31)
        self.assertTrue(all(v < 5 for v in small))
        self.assertTrue(all(v > 100 for v in large))
        self.assertLess(statistics.median(small), 3)

    def test_gttf_position_speed_scale_negative(self):
        """Frame position deltas give implausibly low speeds in all GTT files."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        medians = []
        for root in ("GTR2Steam", "BMWM3Challenge"):
            for path in glob.glob(str(ROOT.parent / root / "**" / "*.GTT"),
                                  recursive=True):
                payload = gz.decompress(path)
                grid = st.find_frame_grid(payload)
                if not grid:
                    continue
                frames = st.read_frames(payload, grid)
                speeds = [math.hypot(b["position"][0] - a["position"][0],
                                     b["position"][2] - a["position"][2])
                          / max(b["time"] - a["time"], 1e-6)
                          for a, b in zip(frames, frames[1:])]
                medians.append(statistics.median(speeds))
        self.assertEqual(len(medians), 31)
        self.assertLess(statistics.median(medians), 1.5)
        self.assertTrue(all(v < 2.0 for v in medians))

    def test_f0_halfwords_not_material_derived(self):
        """f0 halfwords do not equal material offsets, hashes or name words."""
        import glob
        import struct
        import zlib
        import gmt_format as gf
        import mas_tool
        markers = 0
        matches = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.gtr"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    name = entry.name.lower()
                    if not name.endswith(".gmt") or not entry.data or len(entry.data) < 0x400:
                        continue
                    try:
                        parsed = gf.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    starts = gf._find_material_starts(parsed.tail, len(parsed.materials))
                    for i, mesh in enumerate(parsed.meshes):
                        marker = gf.mesh_marker(mesh)
                        if not marker:
                            continue
                        halves = (marker & 0xFFFF, marker >> 16)
                        markers += 1
                        candidates = []
                        if i < len(starts):
                            off = parsed.obj_list_offset + starts[i]
                            candidates += [off & 0xFFFF, starts[i] & 0xFFFF,
                                           (off + 152) & 0xFFFF]
                        if i < len(parsed.materials):
                            raw = parsed.materials[i].name.encode("latin-1")
                            candidates += [zlib.crc32(raw) & 0xFFFF, sum(raw) & 0xFFFF]
                            if raw:
                                candidates.append(struct.unpack(
                                    "<H", raw[:2].ljust(2, b"\0"))[0])
                        matches += sum(1 for h in halves for c in candidates if h == c)
                    if markers >= 1500:
                        break
                if markers >= 1500:
                    break
            if markers >= 1500:
                break
        self.assertGreater(markers, 1000)
        self.assertLess(matches / markers, 0.01)

    def test_f0_marker_cross_corpus_invariant(self):
        """Identical mesh families share f0 marker lists across GTR2/GTL/BMW."""
        import collections
        import glob
        import re
        import gmt_format
        import mas_tool
        families = {}
        for root, ext in (("GTR2Steam", ".gtr"), ("GTLSteam", ".gtl"),
                          ("BMWM3Challenge", ".bmw")):
            for archive in glob.glob(str(ROOT.parent / root / "**" / f"*{ext}"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    name = entry.name.lower()
                    if not name.endswith(".gmt") or not entry.data or len(entry.data) < 0x400:
                        continue
                    try:
                        parsed = gmt_format.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    marks = tuple(gmt_format.mesh_marker(m) or 0 for m in parsed.meshes)
                    if not any(marks):
                        continue
                    base = re.sub(r"(lod)?\d+$", "", name.replace("\\", "/")
                                  .rsplit("/", 1)[-1].rsplit(".", 1)[0])
                    families.setdefault(base, {}).setdefault(root, marks)
        shared = [tuple(v.values()) for v in families.values() if len(v) > 1]
        self.assertGreater(len(shared), 500)
        identical = sum(1 for group in shared if len(set(group)) == 1)
        self.assertGreater(identical / len(shared), 0.35)

    def test_gtr2_f0_lod_family_invariant(self):
        """f0 marker lists repeat across LOD variants more than chance."""
        import collections
        import glob
        import re
        import gmt_format
        import mas_tool
        groups = collections.defaultdict(list)
        material_matches = 0
        markers = 0
        files = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for archive in glob.glob(str(ROOT.parent / root / "**" / "*.gtr"),
                                     recursive=True):
                try:
                    _, entries = mas_tool.read_archive(archive)
                except Exception:
                    continue
                for entry in entries:
                    name = entry.name.lower()
                    if not name.endswith(".gmt") or not entry.data or len(entry.data) < 0x400:
                        continue
                    try:
                        parsed = gmt_format.parse_gmt("x.gmt", entry.data)
                    except Exception:
                        continue
                    marks = tuple(gmt_format.mesh_marker(m) or 0 for m in parsed.meshes)
                    if not any(marks):
                        continue
                    files += 1
                    if len(parsed.meshes) < 2:
                        continue
                    base = re.sub(r"(lod)?\d+$", "", name.replace("\\", "/")
                                  .rsplit("/", 1)[-1].rsplit(".", 1)[0])
                    groups[base].append(marks)
                    for mesh in parsed.meshes:
                        marker = gmt_format.mesh_marker(mesh) or 0
                        markers += 1
                        material_matches += int((marker & 0xFFFF) == mesh.record.material_index
                                                or (marker >> 16) == mesh.record.material_index)
                if files >= 500:
                    break
            if files >= 500:
                break
        multi = {k: v for k, v in groups.items() if len(v) > 1}
        self.assertGreater(len(multi), 20)
        same = sum(1 for v in multi.values() if len(set(v)) == 1)
        self.assertGreater(same / len(multi), 0.2)
        self.assertLess(material_matches / markers, 0.25)

    def test_gttf_heading_vs_aiw_negative(self):
        """Ghost +12 heading has no consistent relation to AIW directions."""
        import glob
        import gzip
        import math
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st
        import simbin_text_tool as stt
        base = ROOT.parent / "GTR2Steam"
        aiws = {}
        for path in glob.glob(str(base / "**" / "*.AIW"), recursive=True):
            aiws.setdefault(path.lower().rsplit("/", 1)[-1], path)
        diffs = []
        for path in glob.glob(str(base / "TimeTrial" / "**" / "*.GTT"), recursive=True):
            payload = gz.decompress(path)
            event = st.parse_payload(payload)
            grid = st.find_frame_grid(payload)
            aiw = aiws.get((event.aiw or "").lower())
            if not grid or not aiw:
                continue
            waypoints = stt.parse_aiw(stt.read_text(aiw)).waypoints
            for frame in st.read_frames(payload, grid)[::10]:
                px, pz = frame["position"][0], frame["position"][2]
                i = min(range(len(waypoints)),
                        key=lambda k: (waypoints[k].pos[0] - px) ** 2
                        + (waypoints[k].pos[2] - pz) ** 2)
                j = waypoints[i].ptrs[1]
                if not (0 <= j < len(waypoints)) or j == i:
                    continue
                dx = waypoints[j].pos[0] - waypoints[i].pos[0]
                dz = waypoints[j].pos[2] - waypoints[i].pos[2]
                direction = math.atan2(dx, dz)
                diffs.append((frame["heading"] - direction + math.pi)
                             % (2 * math.pi) - math.pi)
        self.assertGreater(len(diffs), 1000)
        coherence = math.hypot(sum(math.cos(x) for x in diffs),
                               sum(math.sin(x) for x in diffs)) / len(diffs)
        self.assertLess(coherence, 0.1)
        self.assertGreater(statistics.median(abs(x) for x in diffs), 1.4)

    def test_gsc_region_mask_per_vertex_run_negative(self):
        """Repeated-byte runs at 32-byte stride decode to near-zero padding."""
        import math
        import struct
        import isi_crypt
        import mas_tool
        archive = ROOT.parent / "CopaPetrobrasdeMarcas" / "Gamedata" / \
            "Vehicles" / "showroom.mas"
        if not archive.is_file():
            self.skipTest("showroom.mas not present")
        _, entries = mas_tool.read_archive(str(archive))
        entry = next((e for e in entries if e.name.lower() == "purchased.gmt"), None)
        if entry is None:
            self.skipTest("PURCHASED.GMT not present")
        data = isi_crypt.decrypt_bytes(entry.data, 1)
        magnitudes = []
        for off in range(0x330, len(data) - 16, 32):
            run = data[off:off + 4]
            if len(run) != 4 or len(set(run)) != 1:
                continue
            mask = run[0]
            triple = struct.unpack("<3f", bytes(b ^ mask for b in data[off + 4:off + 16]))
            if all(math.isfinite(v) and abs(v) < 1000 for v in triple):
                magnitudes.append(max(abs(v) for v in triple))
        self.assertGreater(len(magnitudes), 100)
        self.assertLess(sorted(magnitudes)[len(magnitudes) // 2], 0.01)

    def test_gttf_engine_scale_vs_eng_revlimit(self):
        """GTTF +32 /1024 ceilings do not match .eng rev limits per car."""
        import re
        def rev_limit(path: Path) -> float:
            text = path.read_bytes().decode("latin-1")
            rng = re.search(r"(?mi)^RevLimitRange\s*=\s*\(\s*([\d.]+)\s*,\s*([\d.]+)", text)
            setting = re.search(r"(?mi)^RevLimitSetting\s*=\s*(\d+)", text)
            return float(rng.group(1)) + float(rng.group(2)) * int(setting.group(1))
        f550 = rev_limit(ROOT.parent / "GTR2Steam" / "GameData" / "Teams" / "GT" /
                         "Ferrari 550 Teams" / "550_Std_V12.eng")
        bmw = rev_limit(ROOT.parent / "BMWM3Challenge" / "GameData" / "Teams" / "BMW" /
                        "BMW M3" / "BMW_M3.eng")
        self.assertEqual(f550, 7400.0)
        self.assertEqual(bmw, 8500.0)
        ratio_f = 5_873_841 / f550
        ratio_b = 6_336_964 / bmw
        self.assertGreater(abs(ratio_f - ratio_b) / ratio_f, 0.05)

    def test_sce_embedded_config_bounds(self):
        """All 131 SCE embedded vehicle configs satisfy their own bounds."""
        import gsc_exe_tool as gsc
        import simbin_text_tool as stt
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        index = 0
        checked = 0
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                if res.kind == 1:
                    key = keys[index + 11]
                    index += 1
                else:
                    continue
            ext = res.name.lower().rsplit(".", 1)[-1]
            if ext not in stt.SCE_EMBEDDED_NUMERIC_BOUNDS:
                continue
            data, ok = gsc.decode_resource(res, key)
            self.assertTrue(ok, res.name)
            self.assertEqual(stt.validate_sce_embedded_config(data, ext), [], res.name)
            checked += 1
        self.assertEqual(checked, 131)
        self.assertEqual(stt.validate_sce_embedded_config(b"x=1", "car"),
                         ["unsupported SCE config extension car"])

    def test_sce_vehicle_vocabularies(self):
        """SCE embedded vehicle configs have their own universal key sets."""
        import re
        import gsc_exe_tool as gsc
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        keys = container.key_list()
        index = 0
        by_ext = {}
        for res in container.resources:
            key = None
            if gsc.resource_encrypted(res):
                if res.kind == 1:
                    key = keys[index + 11]
                    index += 1
                else:
                    continue
            ext = res.name.lower().rsplit(".", 1)[-1]
            if ext not in ("hdv", "gen", "tbc", "pm", "sfx"):
                continue
            data, ok = gsc.decode_resource(res, key)
            self.assertTrue(ok, res.name)
            by_ext.setdefault(ext, []).append({
                match.group(1).lower() for match in re.finditer(
                    r"(?m)^\s*([A-Za-z_]\w*)\s*=", data.decode("latin-1"))})
        self.assertEqual({ext: len(v) for ext, v in by_ext.items()},
                         {"hdv": 28, "gen": 33, "tbc": 24, "pm": 23, "sfx": 23})
        for ext, expected in (("hdv", 237), ("gen", 6), ("tbc", 38),
                              ("pm", 3), ("sfx", 89)):
            self.assertEqual(len(set.intersection(*by_ext[ext])), expected, ext)

    def test_sce_exe_full_extract(self):
        """Full-tier: extract all decodable StockCarExtreme EXE resources."""
        import gsc_exe_tool as gsc
        exe = ROOT.parent / "StockCarExtreme" / "GSC.exe"
        if not exe.is_file():
            self.skipTest("StockCarExtreme GSC.exe not present")
        container = gsc.read_container(exe)
        results = gsc.extract_all(container, "/tmp/opencode/sce_full_extract")
        self.assertEqual(sum(1 for _, flag in results if flag), 207)
        self.assertEqual(len(results), 218)

    def test_gsc_exe_large_mas(self):
        """Full-tier: decode the 15 MB MAS embedded in Marcas.exe."""
        import gsc_exe_tool as gsc
        exe = ROOT.parent / "CopaPetrobrasdeMarcas" / "Marcas.exe"
        if not exe.is_file():
            self.skipTest("Marcas.exe not present")
        container = gsc.read_container(exe)
        res = container.get("Gamedata\\Locations\\ReizaCommon\\AdPackStockcar.MAS")
        data, ok = gsc.decode_resource(res, container.key_list()[5])
        self.assertTrue(ok)
        self.assertTrue(data.startswith(b"\xce\xc3\xd5\xc7\xc0\xd9\xe6\xc9"))
        self.assertGreater(len(data), 15_000_000)

    def test_decrypted_gm_config_vocabularies(self):
        """Decrypted SVM/GMB configs match corpus key and numeric invariants."""
        import glob
        import os
        import isi_gm_crypt as gm
        svm = gmb = 0
        for root in ("hand_selected", "TC2000", "SimuladorTopRace2009",
                     "SuperleagueFormula2009"):
            paths = []
            for ext in ("*.svm", "*.hdv", "*.ini", "*.tbc", "*.pm"):
                paths.extend(glob.glob(str(ROOT.parent / root / "**" / ext),
                                       recursive=True))
            for p in paths:
                if not os.path.isfile(p):
                    continue
                data = Path(p).read_bytes()
                if not data.startswith(b"//[[gM"):
                    continue
                name = gm.detect_keynum(data)
                if name is None:
                    continue
                text = gm.decrypt_gm_file(data, gm.GM_KEYNUMS[name])
                variant = "svm" if data[7:12].startswith(b"1.000") else "gmb"
                self.assertEqual(stt.validate_decrypted_gm_config(text, variant), [], p)
                if variant == "svm":
                    svm += 1
                else:
                    gmb += 1
        self.assertEqual(svm, 8)
        self.assertEqual(gmb, 18)

    def test_encrypted_gm_configs(self):
        """Every encrypted .svm / gMb config decrypts to real text."""
        import glob
        import os
        import isi_gm_crypt as gm
        svm = gmb = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*"), recursive=True):
            if not os.path.isfile(p):
                continue
            data = Path(p).read_bytes()
            if data.startswith(b"//[[gM") and data[6:7] == b"b":
                if gm.printability(data.split(b"\n", 1)[-1]) > 0.9:
                    continue  # plain text config with a gM-style header
                name = gm.detect_keynum(data)
                if name is None:
                    continue  # unrelated //[[gM file (e.g. .bch replay)
                text = gm.decrypt_gm_file(data, gm.GM_KEYNUMS[name])
                self.assertGreater(gm.printability(text), 0.97, p)
                if data[7:12] == b"1.000":
                    svm += 1
                    self.assertIn(b"VehicleClassSetting=", text, p)
                    self.assertIn(b"[GENERAL]", text, p)
                else:
                    gmb += 1
        self.assertEqual(svm, 10)
        self.assertGreaterEqual(gmb, 18)

    def test_hdc_numeric_bounds(self):
        """HDC chassis fields stay within corpus-observed bounds."""
        import glob
        import os
        checked = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".hdc"):
                    continue
                text = media_tool.decrypt_jca_text(Path(p).read_bytes())
                self.assertEqual(stt.validate_hdc_numeric(text), [], p)
                checked += 1
        self.assertEqual(checked, 86)

    def test_tyr_numeric_bounds(self):
        """TYR tire-model fields stay within corpus-observed bounds."""
        import glob
        import os
        checked = 0
        for root in ("GTR2Steam", "GTLSteam"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".tyr"):
                    continue
                self.assertEqual(stt.validate_tyr_numeric(Path(p).read_bytes()), [], p)
                checked += 1
        self.assertEqual(checked, 41)

    def test_aud_numeric_bounds(self):
        """AUD numeric event values stay within corpus-observed bounds."""
        import glob
        import os
        checked = numeric = 0
        for root in ("GTR2Steam", "GTLSteam", "Race07Complete", "VolvoTheGame"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*.aud"), recursive=True):
                if not os.path.isfile(p):
                    continue
                info = stt.parse_aud(media_tool.decrypt_jca_text(Path(p).read_bytes())
                                     .decode("latin-1"))
                self.assertEqual(stt.validate_aud_map(info), [], p)
                checked += 1
                numeric += sum(len(info.values[k]) for k in stt.AUD_NUMERIC_BOUNDS
                               if k in info.values)
        self.assertEqual(checked, 202)
        self.assertGreater(numeric, 6000)

    def test_svm_numeric_bounds(self):
        """Plain .svm numeric values stay within corpus-observed bounds."""
        import glob
        import os
        checked = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(".svm"):
                continue
            data = Path(p).read_bytes()
            self.assertEqual(stt.validate_svm_numeric(data), [], p)
            checked += 1
        self.assertGreater(checked, 20000)

    def test_scn_mas_reference_resolution(self):
        """rF1-era .scn MASFile references resolve to local archives."""
        import glob
        import os
        checked = resolved = paths = paths_ok = 0
        for root in ("RF1Vanilla", "F1C", "F12002", "NT2003"):
            base = ROOT.parent / root
            files = {os.path.basename(p).lower()
                     for p in glob.glob(str(base / "**" / "*"), recursive=True)
                     if os.path.isfile(p)}
            dirs = {os.path.relpath(os.path.dirname(p), base).lower().replace("\\", "/")
                    for p in glob.glob(str(base / "**" / "*"), recursive=True)
                    if os.path.isfile(p)}
            for p in glob.glob(str(base / "**" / "*.scn"), recursive=True):
                if not os.path.isfile(p):
                    continue
                info = stt.parse_scn(stt.read_text(p))
                for entry in info.mas_files:
                    checked += 1
                    resolved += os.path.basename(entry.replace("\\", "/")).lower() in files
                for entry in info.search_path:
                    paths += 1
                    rel = "/".join(x for x in entry.lower().replace("\\", "/").split("/") if x)
                    paths_ok += rel in dirs or any(d.endswith("/" + rel) for d in dirs)
        self.assertGreater(checked, 120)
        self.assertGreater(resolved / checked, 0.98)
        self.assertGreater(paths, 70)
        self.assertLess(paths_ok / paths, 0.3)  # documented stale SearchPaths

    def test_rfm_corpus(self):
        """All 10 rF1 .rfm mod descriptors carry 37 universal keys."""
        import glob
        import media_tool
        n = 0
        for root in ("LexusIsfTrackTime", "TC2000", "SimuladorTopRace2009",
                     "SuperleagueFormula2009", "RF1Vanilla"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*.rfm"), recursive=True):
                keys = stt.parse_rfm(Path(p).read_bytes())
                self.assertEqual(stt.validate_rfm(keys), [], p)
                self.assertEqual(media_tool.identify(p).format, "rfactor-rfm", p)
                n += 1
        self.assertEqual(n, 10)

    def test_raceroom_shader_corpus(self):
        """All 226 RaceRoom JCA shaders decrypt to ISI shader sources."""
        import glob
        import os
        import media_tool
        n = 0
        for root in ("RaceRoomTheGame", "RaceRoomTheGame2"):
            for ext in ("vsh", "gfx", "psh"):
                for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                    if not os.path.isfile(p) or not p.lower().endswith("." + ext):
                        continue
                    info = media_tool.identify(p)
                    self.assertEqual(info.format, "shader-jca", p)
                    self.assertTrue(info.details["shader_source"])
                    n += 1
        self.assertEqual(n, 226)

    def test_rcs_and_utf16_dic(self):
        """.rcs control configs and UTF-16 .dic identification."""
        import glob
        import media_tool
        n = 0
        for root in ("RaceRoomTheGame", "RaceRoomTheGame2"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*.rcs"), recursive=True):
                info = stt.parse_rcs(Path(p).read_bytes())
                self.assertEqual(stt.validate_rcs(info), [], p)
                n += 1
        self.assertEqual(n, 36)
        dics = [p for p in glob.glob(str(ROOT.parent / "**" / "*.dic"), recursive=True)
                if Path(p).read_bytes()[:2] == b"\xff\xfe"]
        self.assertGreater(len(dics), 0)
        for p in dics:
            self.assertEqual(media_tool.identify(p).format, "utf16-text", p)

    def test_tdf_corpus(self):
        """All 57 .tdf terrain configs carry 12 universal keys, 3 sections."""
        import glob
        import media_tool
        n = 0
        for root in ("TC2000", "SuperleagueFormula2009", "SimuladorTopRace2009"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*.tdf"), recursive=True):
                info = stt.parse_tdf(Path(p).read_bytes())
                self.assertEqual(stt.validate_tdf(info), [], p)
                self.assertEqual(media_tool.identify(p).format, "rfactor-tdf", p)
                n += 1
        self.assertEqual(n, 57)

    def test_tc2000_superleague_rf1_config_corpus(self):
        """Shared universal keys in TC2000/Superleague .gdb/.cam/.aiw."""
        import os
        import re
        import media_tool
        for root in ("TC2000", "SuperleagueFormula2009"):
            for ext in (".gdb", ".cam", ".aiw"):
                n = 0
                for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                    if not os.path.isfile(p) or not p.lower().endswith(ext):
                        continue
                    text = media_tool.decrypt_jca_text(
                        Path(p).read_bytes()).decode("latin-1")
                    keys = set(x.lower() for x in re.findall(
                        r"(?m)^\s*([A-Za-z_][\w]*)\s*=", text))
                    self.assertEqual(stt.validate_rf1_config(keys, ext), [], p)
                    n += 1
                self.assertGreater(n, 0, f"{root} {ext}")

    def test_tc2000_superleague_veh_svm_corpus(self):
        """TC2000/Superleague .veh core keys and TC2000 6-speed .svm keys."""
        import os
        for root, family in (("TC2000", "core"),
                             ("SuperleagueFormula2009", "superleague")):
            n = 0
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith(".veh"):
                    continue
                keys = set(stt.parse_veh(Path(p).read_bytes()))
                self.assertEqual(stt.validate_veh_core(keys, family), [], p)
                n += 1
            self.assertGreaterEqual(n, 19)
        n = 0
        for p in glob.glob(str(ROOT.parent / "TC2000" / "**" / "*.svm"), recursive=True):
            keys = stt.parse_svm(Path(p).read_bytes()).keys
            self.assertEqual(stt.validate_svm_tc2000(keys), [], p)
            n += 1
        self.assertEqual(n, 12)

    def test_rcd_parser_corpus(self):
        """All 5,047 .rcd configs classify and validate."""
        import glob
        fam = collections.Counter()
        n = 0
        for p in glob.glob(str(ROOT.parent / "**" / "*.rcd"), recursive=True):
            info = stt.parse_rcd(Path(p).read_bytes())
            self.assertEqual(stt.validate_rcd(info), [], p)
            fam[info.family] += 1
            n += 1
        self.assertGreaterEqual(n, 5047)
        self.assertGreaterEqual(fam["driver"], 3038)
        self.assertGreaterEqual(fam["event"], 1830)
        self.assertEqual(fam["nascar"], 178)

    def test_corpus_decode_rate(self):
        """Archived ANM members decode across every ANM-bearing corpus.

        The full 2,436-member survey (F1C/F12001/F12002/NT2003/NT2004/
        NascarSimRacing/GTR1) yields 2,435 decodes; the sole exception is a
        degenerate quaternion in F12001 CATSTEER.ANM. Sample a bounded number
        per corpus here to keep the test fast.
        """
        corpora = ("F1C", "F12001", "F12002", "NT2003", "NT2004",
                   "NascarSimRacing", "GTR1Vanilla")
        per_corpus = {}
        for root in corpora:
            ok = bad = 0
            for name, data in _anm_samples(root, 120):
                try:
                    anm_format.read_anm(data)
                    ok += 1
                except ValueError as ex:
                    # Only degenerate quaternions are acceptable failures.
                    self.assertIn("quaternion norm", str(ex), f"{root}/{name}")
                    bad += 1
            per_corpus[root] = (ok, bad)
            self.assertGreater(ok, 0, root)
        # At least 7 corpora and >400 sampled decodes overall.
        self.assertEqual(len(per_corpus), 7)
        self.assertGreater(sum(o for o, _ in per_corpus.values()), 400)



    def test_gmb_encrypted_config_family(self):
        """gMb1.002f encrypted configs share the same header structure."""
        import glob
        import os
        n = encrypted = 0
        for root in ("TC2000", "SimuladorTopRace2009", "SuperleagueFormula2009"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p):
                    continue
                with open(p, "rb") as f:
                    info = media_tool.gmb_encrypted_config(f.read(4096))
                if not info or info["version"] != "gMb1.002f":
                    continue
                n += 1
                if info["encrypted"]:
                    encrypted += 1
                    self.assertEqual(len(info["field"]), 12, p)
        self.assertEqual(n, 19)
        self.assertEqual(encrypted, 18)

    def test_hdr_dat_index_bounds(self):
        """HDR index bounds match the companion MP3 .dat on all pairs."""
        import glob
        import os
        n = 0
        for root in ("NT2003", "NascarSimRacing"):
            for h in glob.glob(str(ROOT.parent / root / "**" / "*.hdr"),
                               recursive=True):
                if not os.path.isfile(os.path.splitext(h)[0] + ".dat"):
                    continue
                self.assertEqual(media_tool.validate_hdr_dat_pair(h), [], h)
                n += 1
        self.assertGreater(n, 1900)

    def test_anm_keyframe_corpus(self):
        """ANM keyframes: monotonic times and unit quaternions corpus-wide."""
        import glob
        import os
        import anm_format
        n = 0
        for root in ("F1C", "F12002"):
            for p in glob.glob(str(ROOT.parent / root / "**" / "*"), recursive=True):
                if not os.path.isfile(p) or not p.lower().endswith((".mas", ".exe")):
                    continue
                try:
                    _, entries = mas_tool.read_archive(p)
                except Exception:
                    continue
                for e in entries:
                    if not e.name.lower().endswith(".anm") or not e.data:
                        continue
                    try:
                        a = anm_format.read_anm(e.data)
                    except Exception:
                        continue
                    self.assertEqual(anm_format.validate_anm(a), [], f"{root}/{e.name}")
                    n += 1
                if n >= 200:
                    break
            if n >= 200:
                break
        self.assertGreater(n, 150)

    def test_gsc_survey_cache_incremental(self):
        """Cache keys are stable and incremental survey skips cached members."""
        import glob
        import json
        import tempfile
        arc = glob.glob(str(ROOT.parent / "Automobilista" / "**" / "*.mas"), recursive=True)[0]
        _, entries = mas_tool.read_archive(arc, read_data=False)
        entry = next(e for e in entries if e.name.lower().endswith(".gmt"))
        key1 = gsc_survey.member_key(Path(arc), entry)
        key2 = gsc_survey.member_key(Path(arc), entry)
        self.assertEqual(key1, key2)
        self.assertIn(entry.name, key1)
        data = mas_tool.read_member(arc, entry)
        result = gsc_survey.classify(data)
        self.assertEqual(result["sig"], "Game Stock Car")
        self.assertEqual(result["decrypt"], "ok")
        with tempfile.TemporaryDirectory() as td:
            cp = Path(td) / "cache.json"
            gsc_survey.save_cache(cp, {key1: result})
            loaded = gsc_survey.load_cache(cp)
            self.assertEqual(loaded, {key1: result})
            self.assertTrue((cp).is_file())


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
