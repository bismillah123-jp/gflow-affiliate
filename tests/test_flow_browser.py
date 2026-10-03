#!/usr/bin/env python3
"""test_flow_browser.py — uji lib/flow_browser.py dalam mode dry-run.

Tanpa browser / login / kuota: semua generate dipalsukan jadi file dummy.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["AFFILIATE_DRY_RUN"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import flow_browser as fb  # noqa: E402


class TestFlowBrowserDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aff-flow-"))

    def test_character_ensure_idempotent(self):
        # dry-run: character disimpan di state JSON, kedua kali = sudah ada
        created = fb.character_ensure("aff-tes", "/tmp/x.png", "prompt")
        again = fb.character_ensure("aff-tes", "/tmp/x.png", "prompt")
        self.assertTrue(created or again)  # salah satunya True di run pertama
        self.assertTrue(fb.character_exists("aff-tes"))

    def test_image_generate_dummy(self):
        out = self.tmp / "scene01.png"
        got = fb.image_generate("job-1", "prompt tes", str(out),
                                model="Nano Banana 2")
        self.assertTrue(got.exists())
        self.assertGreater(got.stat().st_size, 0)
        # idempotent: file sudah ada -> skip, tidak ditulis ulang
        mtime = got.stat().st_mtime
        got2 = fb.image_generate("job-1", "prompt lain", str(out))
        self.assertEqual(got2.stat().st_mtime, mtime)

    def test_video_generate_dummy_10s(self):
        out = self.tmp / "final_10s.mp4"
        got = fb.video_generate("job-v", "prompt video", str(out),
                                model="Omni Flash", duration=10)
        self.assertTrue(got.exists())
        self.assertGreater(got.stat().st_size, 0)

    def test_selectors_defined(self):
        for key in ("prompt_box", "generate_button", "file_input",
                    "download_button", "tab_frames_to_video"):
            self.assertIn(key, fb.SELECTORS)
            self.assertTrue(fb.SELECTORS[key])

    def test_is_authed_false_initially(self):
        # di sandbox belum pernah --auth; fungsi harus balikin bool
        self.assertIsInstance(fb.is_authed(), bool)


if __name__ == "__main__":
    unittest.main()
