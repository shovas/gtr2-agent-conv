"""Tests for offline GMT conversion validation."""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gmt_layout  # noqa: E402
import mas_tool  # noqa: E402
import validate_conversion as vc  # noqa: E402

OLD_MAGIC = bytes.fromhex("c8cfd2d8ced8e6c3d6ded8bebba8bf90")


def _old_gmts(limit=10):
    for archive in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*.mas"), recursive=True):
        try:
            _, entries = mas_tool.read_archive(archive)
        except Exception:
            continue
        for entry in entries:
            data = entry.data or b""
            if data[0x1d4:0x1e4] != OLD_MAGIC:
                continue
            yield data
            limit -= 1
            if limit <= 0:
                return


class ValidateConversionTest(unittest.TestCase):
    def test_semantic_conversion_passes_offline_validation(self):
        checked = 0
        for data in _old_gmts(10):
            converted = gmt_layout.old_to_new_semantic(data)
            report = vc.validate(data, converted)
            self.assertTrue(report["pass"], report)
            self.assertTrue(report["positions_equal"])
            self.assertTrue(report["uvs_equal"])
            self.assertTrue(report["faces_equal"])
            self.assertTrue(report["independent_cross_check"])
            self.assertTrue(report["material_tail_equal"])
            self.assertTrue(report["f0_equal"])
            self.assertFalse(report["gsc_source"])
            self.assertTrue(report["material_tail_checked"])
            self.assertTrue(report["f0_checked"])
            checked += 1
        if not checked:
            self.skipTest("old-layout GMTs not present")
        self.assertEqual(checked, 10)

    def test_gsc_source_validation(self):
        """Encrypted GSC members validate geometry with N/A raw checks."""
        import struct
        import gmt_semantic
        import gmt_layout
        import mas_tool

        # Deterministic known-good sample keeps this test in the quick tier.
        archive = (ROOT.parent / "CopaPetrobrasdeMarcas" / "Gamedata"
                   / "Scripts" / "pits.mas")
        if not archive.is_file():
            self.skipTest("GSC sample archive not present")
        try:
            _mtype, entries = mas_tool.read_archive(archive)
        except Exception:
            self.skipTest("GSC sample archive unreadable")
        for entry in entries:
            if entry.name.upper() != "STARTBOX.GMT":
                continue
            data = entry.data or b""
            try:
                decoded = gmt_semantic.decode_gsc_member(data)
            except Exception:
                decoded = None
            if not decoded or not decoded.get("submeshes"):
                continue
            try:
                converted = gmt_layout.gsc_member_to_gtr2(data)
            except Exception:
                continue
            report = vc.validate(data, converted)
            self.assertTrue(report["pass"], report)
            self.assertTrue(report["gsc_source"])
            self.assertFalse(report["material_tail_checked"])
            self.assertFalse(report["f0_checked"])
            self.assertTrue(report["positions_equal"])
            self.assertTrue(report["uvs_equal"])
            self.assertTrue(report["faces_equal"])
            self.assertTrue(report["independent_cross_check"])

            subs = gmt_semantic.find_submeshes(converted)
            self.assertTrue(subs)
            bad = bytearray(converted)
            offset = subs[0]["i_off"] + 4
            value = struct.unpack_from("<H", bad, offset)[0]
            struct.pack_into("<H", bad, offset, value + 1)
            report = vc.validate(data, bytes(bad))
            self.assertFalse(report["faces_equal"], report)
            self.assertFalse(report["pass"], report)
            return
        self.skipTest("decodable GSC member not present")

    def test_f0_corruption_is_detected(self):
        """The validator rejects a converted GMT whose f0 marker was altered."""
        import gmt_semantic
        import struct
        for data in _old_gmts(10):
            converted = gmt_layout.old_to_new_semantic(data)
            self.assertTrue(vc.validate(data, converted)["f0_equal"])
            subs = gmt_semantic.find_submeshes(converted)
            if not subs:
                continue
            corrupted = bytearray(converted)
            off = subs[0]["v_off"] + 4
            value = struct.unpack_from("<I", corrupted, off)[0]
            struct.pack_into("<I", corrupted, off, value ^ 0x01010101)
            report = vc.validate(data, bytes(corrupted))
            self.assertFalse(report["f0_equal"], report)
            self.assertFalse(report["pass"], report)
            return
        self.skipTest("old-layout GMTs not present")

    def test_metamorphic_position_perturbation(self):
        import struct
        import gmt_semantic
        for data in _old_gmts(10):
            subs = gmt_semantic.find_submeshes(data)
            if not subs:
                continue
            before = gmt_semantic.read_gmt(data)["submeshes"][0]["positions"]
            modified = bytearray(data)
            pos = subs[0]["v_off"] + 4
            x = struct.unpack_from("<f", modified, pos)[0]
            struct.pack_into("<f", modified, pos, x + 1.0)
            after = gmt_semantic.read_gmt(gmt_layout.old_to_new_semantic(bytes(modified)))["submeshes"][0]["positions"]
            changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
            self.assertEqual(changed, [0])
            self.assertAlmostEqual(after[0][0] - before[0][0], 1.0, places=3)
            return
        self.skipTest("old-layout GMTs not present")

    def test_independent_reader_agrees_with_gmt_semantic(self):
        data = next(_old_gmts(1), None)
        if data is None:
            self.skipTest("old-layout GMTs not present")
        converted = gmt_layout.old_to_new_semantic(data)
        ref = vc.gmt_semantic.read_gmt(converted)["submeshes"][0]
        indep = vc.independent_read(converted, "gtr2")["submeshes"][0]
        self.assertEqual(indep["positions"], ref["positions"])
        self.assertEqual(indep["uvs"], ref["uvs"])


    def test_independent_cross_check_covers_all_submeshes(self):
        """The schema-only reader compares every submesh, including triangles."""
        import struct
        import gmt_semantic
        import gmt_layout
        for data in _old_gmts(60):
            converted = gmt_layout.old_to_new_semantic(data)
            subs = gmt_semantic.find_submeshes(converted)
            if len(subs) < 2:
                continue
            read = vc.independent_read(converted, "gtr2")["submeshes"]
            self.assertEqual(len(read), len(subs))
            self.assertTrue(vc.validate(data, converted)["independent_cross_check"])
            # Corrupt one triangle index in the *second* submesh only.
            corrupted = bytearray(converted)
            off = subs[1]["i_off"] + 4
            value = struct.unpack_from("<H", corrupted, off)[0]
            struct.pack_into("<H", corrupted, off, value + 1)
            report = vc.validate(data, bytes(corrupted))
            self.assertFalse(report["independent_cross_check"], report)
            self.assertFalse(report["pass"], report)
            return
        self.skipTest("multi-submesh old-layout GMTs not present")

    def test_nan_aware_float_comparison(self):
        self.assertTrue(vc._float_lists_equal([(float("nan"), 1.0)],
                                              [(float("nan"), 1.0)]))
        self.assertFalse(vc._float_lists_equal([(float("nan"), 1.0)],
                                               [(0.0, 1.0)]))
        # STANDS01.GMT carries NaN UVs that are preserved byte-for-byte.
        for archive in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*.mas"), recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                if entry.name.upper() != "STANDS01.GMT":
                    continue
                data = entry.data or b""
                if data[0x1d4:0x1e4] != OLD_MAGIC:
                    continue
                report = vc.validate(data, gmt_layout.old_to_new_semantic(data))
                self.assertTrue(report["uvs_equal"], report)
                return
        self.skipTest("STANDS01.GMT not present")

    def test_multi_object_semantic_geometry_validation(self):
        """Multi-object rF1 GMTs convert losslessly via the semantic bridge."""
        import struct
        checked = 0
        for archive in glob.glob(str(ROOT.parent / "RF1Vanilla" / "**" / "*.mas"), recursive=True):
            try:
                _, entries = mas_tool.read_archive(archive)
            except Exception:
                continue
            for entry in entries:
                data = entry.data or b""
                if data[0x1d4:0x1e4] != OLD_MAGIC:
                    continue
                if struct.unpack_from("<I", data, 0x174)[0] < 2:
                    continue
                report = vc.validate(data, gmt_layout.old_to_new_semantic(data))
                self.assertTrue(report["positions_equal"], entry.name)
                self.assertTrue(report["faces_equal"], entry.name)
                self.assertTrue(report["independent_cross_check"], entry.name)
                self.assertTrue(report["material_tail_equal"], entry.name)
                checked += 1
                if checked >= 8:
                    break
            if checked >= 8:
                break
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
