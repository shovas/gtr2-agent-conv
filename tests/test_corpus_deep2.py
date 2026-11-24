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
