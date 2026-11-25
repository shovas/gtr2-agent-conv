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

    def test_gttf_frame8_tracks_steering(self):
        """+8 and the decoded steering field +16 are strongly related."""
        import glob
        import gzip
        import statistics
        import gzip_simbin_tool as gz
        import simbin_events_tool as st

        def resid(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            den = sum((x - mx) ** 2 for x in xs)
            if den == 0:
                return [y - my for y in ys]
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
            return [y - my - slope * (x - mx) for x, y in zip(xs, ys)]

        correlations = []
        for path in glob.glob(str(ROOT.parent / "GTR2Steam" / "TimeTrial" / "**" / "*.GTT"),
                              recursive=True):
            payload = gz.decompress(path)
            frames = st.read_frames(payload, st.find_frame_grid(payload))
            offset = [f["position"][2] for f in frames]
            steering = [f["pitch"] for f in frames]
            z = [f["position"][1] for f in frames]
            speed = [0] + [abs(z[i] - z[i - 1]) for i in range(1, len(z))]
            detrended_offset = resid(z, resid(speed, offset))
            detrended_steering = resid(z, resid(speed, steering))
            correlations.append(st._corr(detrended_offset, detrended_steering))
        self.assertEqual(len(correlations), 29)
        self.assertGreater(statistics.median(abs(v) for v in correlations), 0.5)
        self.assertGreaterEqual(sum(1 for v in correlations if abs(v) > 0.3), 20)

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
