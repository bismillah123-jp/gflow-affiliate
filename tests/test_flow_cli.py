#!/usr/bin/env python3
"""test_flow_cli.py — uji lib/flow_cli.py dalam mode dry-run.

Tanpa gflow / browser / kuota: semua generate dipalsukan jadi file dummy.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["AFFILIATE_DRY_RUN"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import flow_cli as fc  # noqa: E402


class TestFlowCliDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aff-flow-"))

    def test_character_ensure_idempotent(self):
        fc.character_ensure("aff-tes2", "/tmp/x.png", "prompt")
        self.assertTrue(fc.character_exists("aff-tes2"))
        # kedua kali: sudah ada -> return False
        self.assertFalse(fc.character_ensure("aff-tes2", "/tmp/x.png", "prompt"))

    def test_image_generate_dummy(self):
        out = self.tmp / "scene01.png"
        got = fc.image_generate("job-1", "prompt tes", str(out),
                                model="Nano Banana 2")
        self.assertTrue(got.exists())
        self.assertGreater(got.stat().st_size, 0)
        mtime = got.stat().st_mtime
        got2 = fc.image_generate("job-1", "prompt lain", str(out))
        self.assertEqual(got2.stat().st_mtime, mtime)

    def test_image_generate_with_refs(self):
        ref = self.tmp / "ref.png"
        ref.write_bytes(b"fake")
        out = self.tmp / "hd.png"
        got = fc.image_generate("job-2", "hd-kan", str(out),
                                refs=[str(ref)], character="")
        self.assertTrue(got.exists())

    def test_video_generate_dummy_10s(self):
        out = self.tmp / "final_10s.mp4"
        got = fc.video_generate("job-v", "prompt video", str(out),
                                model="Omni Flash", duration=10,
                                start_frame=str(self.tmp / "s.png"))
        # dry-run: start_frame tidak dicek ketat
        self.assertTrue(got.exists())
        self.assertGreater(got.stat().st_size, 0)

    def test_model_map(self):
        self.assertEqual(fc._model("Nano Banana 2", "image"), "nano2")
        self.assertEqual(fc._model("Omni Flash", "video"), "omni-flash")


if __name__ == "__main__":
    unittest.main()
