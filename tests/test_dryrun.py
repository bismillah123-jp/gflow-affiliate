#!/usr/bin/env python3
"""test_dryrun.py — uji end-to-end pipeline dalam mode --dry-run.

Tidak butuh: API key, browser, login Google, kuota Flow, maupun network
(ffmpeg tetap dibutuhkan untuk membuat file dummy).
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDryRun(unittest.TestCase):
    SLUG = "__test_dryrun__"

    def setUp(self):
        shutil.rmtree(os.path.join(ROOT, "products", self.SLUG), ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(os.path.join(ROOT, "products", self.SLUG), ignore_errors=True)

    def test_full_pipeline_dryrun(self):
        env = dict(os.environ, AFFILIATE_DRY_RUN="1")
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "pipeline.py"),
             "--manual-name", "Sabun Viral Tes", "--dry-run"],
            capture_output=True, text=True, timeout=900, env=env, cwd=ROOT)
        # slug berasal dari slugify("Sabun Viral Tes")
        slug = "sabun-viral-tes"
        pdir = os.path.join(ROOT, "products", slug)
        self.assertEqual(r.returncode, 0,
                         f"pipeline dry-run gagal:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
        expected = [
            "research.json",
            "images/img1.png", "images/manifest.json",
            "hd/img1_hd.png",
            "storyboard.json",
            "storyboard/scene01.png", "storyboard/scene02.png",
            "storyboard/scene03.png",
            "clips/final_10s.mp4",
            "vo/vo.mp3",
            "final.mp4",
        ]
        for rel in expected:
            p = os.path.join(pdir, rel)
            self.assertTrue(os.path.exists(p), f"hilang: {rel}")
            self.assertGreater(os.path.getsize(p), 0, f"kosong: {rel}")

        # storyboard.json valid & total 10 dtk
        sb = json.load(open(os.path.join(pdir, "storyboard.json")))
        self.assertEqual(sb["total_seconds"], 10)

        # final.mp4 punya stream video+audio, durasi ~10 dtk
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type",
             "-of", "json", os.path.join(pdir, "final.mp4")],
            capture_output=True, text=True, timeout=60)
        info = json.loads(probe.stdout)
        dur = float(info["format"]["duration"])
        kinds = {s["codec_type"] for s in info["streams"]}
        self.assertTrue(8.0 <= dur <= 12.0, f"durasi aneh: {dur}")
        self.assertIn("video", kinds)
        self.assertIn("audio", kinds)

        shutil.rmtree(pdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
