#!/usr/bin/env python3
"""test_tts.py — uji logika tts.py dengan edge-tts PALSU (tanpa network).

Fake Communicate.save() menulis mp3 12 detik via ffmpeg, sehingga loop
penyesuaian rate (+0% -> +15% -> +30%) ikut teruji.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
FAKE = os.path.join(ROOT, "tests", "fake_edge_tts")


class TestTTS(unittest.TestCase):
    def setUp(self):
        self.slug = "__test_tts__"
        pdir = os.path.join(ROOT, "products", self.slug)
        shutil.rmtree(pdir, ignore_errors=True)
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "research.json"), "w") as f:
            json.dump({"slug": self.slug, "name": "Produk Tes"}, f)
        with open(os.path.join(pdir, "storyboard.json"), "w") as f:
            json.dump({"vo_script": "Halo! Ini produk viral, cek keranjang kuning sekarang juga ya!"}, f)

    def tearDown(self):
        shutil.rmtree(os.path.join(ROOT, "products", self.slug), ignore_errors=True)

    def test_tts_rate_loop(self):
        env = dict(os.environ)
        env["AFFILIATE_DRY_RUN"] = ""
        env["PYTHONPATH"] = FAKE + os.pathsep + env.get("PYTHONPATH", "")
        r = subprocess.run(
            [sys.executable, os.path.join(LIB, "tts.py"),
             "--product", self.slug],
            capture_output=True, text=True, timeout=300, env=env, cwd=ROOT)
        self.assertEqual(r.returncode, 0, f"tts.py gagal:\n{r.stdout}\n{r.stderr}")
        # loop rate harus mencapai +30% karena fake selalu 12 dtk
        self.assertIn("+30%", r.stdout)
        vo = os.path.join(ROOT, "products", self.slug, "vo", "vo.mp3")
        self.assertTrue(os.path.exists(vo))
        self.assertGreater(os.path.getsize(vo), 1000)


if __name__ == "__main__":
    unittest.main()
