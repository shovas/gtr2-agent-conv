import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import media_tool  # noqa: E402


class MediaToolTest(unittest.TestCase):
    def test_wav_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.wav"
            dst = Path(td) / "b.wav"
            with wave.open(str(src), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(b"\x00\x01\x02\x03" * 100)
            info = media_tool.wav_roundtrip(src, dst)
            self.assertEqual(info.format, "wav")
            self.assertEqual(info.details["channels"], 1)
            self.assertEqual(info.details["framerate"], 22050)
            with wave.open(str(src), "rb") as a, wave.open(str(dst), "rb") as b:
                self.assertEqual(a.getparams(), b.getparams())
                self.assertEqual(a.readframes(a.getnframes()), b.readframes(b.getnframes()))

    def test_identify_dds_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Animations/Objects/FANFEMALE1.DDS"
        if not p.exists():
            self.skipTest("DDS not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "dds")
        self.assertGreater(info.details.get("width", 0), 0)

    def test_identify_bik_if_present(self):
        p = ROOT.parent / "GTR2Steam/GameData/Locations/Barcelona/Barcelona.bik"
        if not p.exists():
            self.skipTest("BIK not present")
        info = media_tool.identify(p)
        self.assertEqual(info.format, "bik")
        self.assertGreater(info.details.get("frames", 0), 0)


if __name__ == "__main__":
    unittest.main()
