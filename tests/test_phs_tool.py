"""Tests for the GTL PHS PAR2-style container scanner."""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mas_tool  # noqa: E402
import phs_tool  # noqa: E402


def _phs_members():
    out = []
    for archive in glob.glob(str(ROOT.parent / "GTLSteam" / "**" / "*"), recursive=True):
        if not os.path.isfile(archive) or Path(archive).suffix.lower() not in (".gtl", ".gtr", ".mas"):
            continue
        try:
            _, entries = mas_tool.read_archive(archive)
        except Exception:
            continue
        for entry in entries:
            if entry.name.lower().endswith(".phs"):
                out.append((entry.name, entry.data))
    return out


class PhsToolTest(unittest.TestCase):
    def test_five_members_and_packet_chain(self):
        members = _phs_members()
        if not members:
            self.skipTest("GTL PHS members not present")
        self.assertEqual(len(members), 5)
        for name, data in members:
            packets = phs_tool.find_packets(data)
            for packet in packets:
                self.assertEqual(packet["length"] % 1, 0)
                self.assertGreater(packet["length"], 64)
                self.assertLessEqual(packet["offset"] + packet["length"], len(data))
                self.assertIn(packet["type"], ("Main", "FileDesc", "RecvSlic"))
        self.assertGreater(sum(len(phs_tool.find_packets(d)) for _, d in members), 0)

    def test_main_packet_metadata(self):
        for name, data in _phs_members():
            if name.lower() not in ("cars.phs", "ai.phs", "tracks.phs"):
                continue
            report = phs_tool.scan(data)
            self.assertTrue(report["main"])
            main = report["main"][0]
            self.assertEqual(main["slice_size"], 384000)
            self.assertEqual(main["file_count"], 1)
            self.assertEqual(main["file_ids"],
                             ["2f1fc214fdfa91110008fa2a52a622d1"])

    def test_filedesc_names_update_executable(self):
        for name, data in _phs_members():
            if name.lower() != "drivers.phs":
                continue
            report = phs_tool.scan(data)
            self.assertTrue(report["filedesc"])
            desc = report["filedesc"][0]
            self.assertEqual(desc["filename"], "GTL_Update_0901.exe")
            self.assertEqual(desc["file_id"], "2f1fc214fdfa91110008fa2a52a622d1")


if __name__ == "__main__":
    unittest.main()
