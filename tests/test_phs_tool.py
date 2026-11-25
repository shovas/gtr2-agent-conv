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


class PhsRecoveryCoverageTest(unittest.TestCase):
    """How much PAR2 recovery data exists for GTL_Update_0901.exe?"""

    def test_recv_slice_coverage(self):
        import glob
        import math
        import mas_tool
        import phs_tool
        slices = []
        slice_size = None
        for path in glob.glob(str(Path(__file__).resolve().parents[1].parent
                                 / "GTLSteam" / "**" / "*.gtl"), recursive=True):
            try:
                _, entries = mas_tool.read_archive(path)
            except Exception:
                continue
            for entry in entries:
                if not entry.name.lower().endswith(".phs"):
                    continue
                for packet in phs_tool.find_packets(entry.data):
                    if packet["type"] == "Main":
                        main = phs_tool.parse_main(packet["body"])
                        if main:
                            slice_size = main["slice_size"]
                    if packet["type"].startswith("RecvSlic"):
                        exponent = int.from_bytes(packet["body"][:4], "little")
                        slices.append((entry.name, exponent, len(packet["body"])))
        self.assertEqual(slice_size, 384000)
        self.assertEqual(sorted(x[1] for x in slices), [53, 58, 59])
        total = sum(x[2] for x in slices)
        self.assertEqual(total, 3 * 384004)
        # The 61 MB GTL 1.1 updater implies ~160 source slices; three PAR2
        # slices (1.9%) cannot reconstruct it, and exponents 0..52 are absent.
        needed = math.ceil(61_334_805 / slice_size)
        self.assertGreater(needed, 150)
        self.assertLess(len(slices) / needed, 0.05)


class PhsRuntimeConsumerTest(unittest.TestCase):
    """No shipped GTL/GTR2 binary appears to reference a .PHS file."""

    def test_no_binary_references_phs(self):
        import glob
        roots = [Path(__file__).resolve().parents[1].parent / "GTLSteam",
                 Path(__file__).resolve().parents[1].parent / "GTR2Steam"]
        binaries = []
        for root in roots:
            binaries.extend(glob.glob(str(root / "**" / "*.exe"), recursive=True))
            binaries.extend(glob.glob(str(root / "**" / "*.dll"), recursive=True))
        self.assertGreater(len(binaries), 20)
        patterns = (b".PHS", b".phs", b"PHS\0", b"P\x00H\x00S\x00",
                    b"PHYSICS", b"p\x00h\x00y\x00s\x00i\x00c\x00s\x00")
        for path in binaries:
            data = Path(path).read_bytes()
            for pattern in patterns:
                self.assertNotIn(pattern, data, f"{path}: {pattern!r}")


if __name__ == "__main__":
    unittest.main()
