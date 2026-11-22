"""Tests for the GTL PHS structural scanner."""
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
    def test_packets_and_plaintext(self):
        members = _phs_members()
        if not members:
            self.skipTest("GTL PHS members not present")
        self.assertEqual(len(members), 5)
        found_packets = 0
        found_labels = 0
        for name, data in members:
            report = phs_tool.scan(data)
            found_packets += len(report["packets"])
            texts = [text for _, text in report["strings"]]
            if any("PAR 2.0" in t for t in texts):
                found_labels += 1
        self.assertGreater(found_packets, 0)
        self.assertGreater(found_labels, 0)

    def test_packet_fields(self):
        data = None
        for name, d in _phs_members():
            if name.lower() == "cars.phs":
                data = d
                break
        if data is None:
            self.skipTest("CARS.PHS not present")
        packets = phs_tool.find_packets(data)
        self.assertTrue(packets)
        self.assertEqual(packets[0]["type_hash"][:16], "7a8c71fbc5752bf9")
        self.assertGreater(packets[0]["length"], 64)


if __name__ == "__main__":
    unittest.main()
