"""Observations from the NASCAR Thunder 2003 (ISI, 2002) corpus (../NT2003).

Early ISI title using MAS type 3 and CUBE MTS, like F1 2002 and NT2004.
"""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402

NT = ROOT.parent / "NT2003"
MTS_MAGIC = b"CUBE_MTS_4.10\x00\x00\x00"


def _files(ext):
    if not NT.is_dir():
        return []
    return [Path(p) for p in glob.glob(str(NT / "**" / "*"), recursive=True)
            if os.path.isfile(p) and Path(p).suffix.lower() == "." + ext]


class NascarThunder2003Test(unittest.TestCase):
    def test_type3_archives_and_mts(self):
        arcs = _files("mas")
        if not arcs:
            self.skipTest("NT2003 corpus not present")
        self.assertEqual(len(arcs), 179)
        total = standard = 0
        for arc in arcs:
            self.assertEqual(mas_tool.read_signature(arc), mas_tool.MAS_TYPE3, arc)
            mtype, entries = mas_tool.read_archive(arc)
            self.assertEqual(mtype, 3, arc)
            total += len(entries)
            for e in entries:
                if e.name.lower().endswith(".mts"):
                    standard += (e.data or b"")[:16] == MTS_MAGIC
        self.assertEqual(total, 19006)
        self.assertEqual(standard, 10206)

    def test_audio_and_vehicle_formats(self):
        if not NT.is_dir():
            self.skipTest("NT2003 corpus not present")
        hdr, dat, veh, hdv = (_files(x) for x in ("hdr", "dat", "veh", "hdv"))
        self.assertEqual((len(hdr), len(dat), len(veh), len(hdv)), (476, 476, 70, 70))
        self.assertTrue(all(p.read_bytes().startswith(b"\r\nHDVehi") for p in veh))
        self.assertTrue(all(p.read_bytes().startswith(b"\r\n//") for p in hdv))
        # .dat audio starts with an MPEG audio frame sync (0xfff3/0xfffb).
        self.assertTrue(all(p.read_bytes()[:2] in (b"\xff\xf3", b"\xff\xfb") for p in dat))


if __name__ == "__main__":
    unittest.main()
