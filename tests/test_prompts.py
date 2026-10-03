#!/usr/bin/env python3
"""test_prompts.py — unit test template prompt (tanpa network)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import prompts  # noqa: E402


class TestPrompts(unittest.TestCase):
    def test_anomaly_guard_lengkap(self):
        g = prompts.ANOMALY_GUARD.lower()
        for kw in ["five fingers", "no extra limbs", "no morphing",
                   "no on-screen text", "no watermark"]:
            self.assertIn(kw, g, f"guard kehilangan: {kw}")

    def test_hd_prompt_memakai_deskripsi_dan_guard(self):
        p = prompts.hd_prompt("botol biru 'X'")
        self.assertIn("botol biru 'X'", p)
        self.assertIn("Nano Banana 2", p)
        self.assertIn(prompts.ANOMALY_GUARD, p)

    def test_storyboard_total_10_detik(self):
        product = {"name": "Sabun Viral", "product_visual": "botol sabun hijau"}
        sb = prompts.build_storyboard(product)
        self.assertEqual(sb["total_seconds"], 10)
        self.assertEqual(len(sb["scenes"]), 3)
        for s in sb["scenes"]:
            self.assertIn(prompts.ANOMALY_GUARD, s["keyframe_prompt"])
            self.assertTrue(s["vo_line"], "vo_line tidak boleh kosong")

    def test_vo_script_bahasa_indonesia_dan_pendek(self):
        product = {"name": "Sabun Viral"}
        sb = prompts.build_storyboard(product)
        vo = sb["vo_script"]
        self.assertTrue(len(vo) <= 140, f"VO kepanjangan: {len(vo)}")
        self.assertTrue(len(vo) > 20)
        # penanda Bahasa Indonesia kasual
        self.assertTrue(any(w in vo.lower() for w in
                            ["cek keranjang", "gampang", "banget"]))

    def test_video_prompt_tanpa_dialog(self):
        product = {"name": "Sabun Viral", "product_visual": "botol sabun hijau"}
        sb = prompts.build_storyboard(product)
        vp = sb["video_prompt"].lower()
        self.assertIn("9:16", sb["video_prompt"])
        self.assertIn("10 seconds", vp)
        self.assertIn("no spoken dialogue", vp)

    def test_override_storyboard_dipakai(self):
        product = {"name": "X"}
        override = {
            "product_name": "Y",
            "product_desc": "wadah Y",
            "scenes": [
                {"trim": 5, "keyframe": "kf1", "motion": "m1",
                 "overlay_text": "", "vo_line": "Halo!"},
                {"trim": 5, "keyframe": "kf2", "motion": "m2",
                 "overlay_text": "", "vo_line": "Beli!"},
            ],
        }
        sb = prompts.build_storyboard(product, override)
        self.assertEqual(sb["product"], "Y")
        self.assertEqual(sb["total_seconds"], 10)
        self.assertEqual(len(sb["scenes"]), 2)


if __name__ == "__main__":
    unittest.main()
