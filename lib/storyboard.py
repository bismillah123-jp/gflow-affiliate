#!/usr/bin/env python3
"""storyboard.py — susun & render storyboard BERUPA GAMBAR (tahap 4).

1. Susun products/<slug>/storyboard.json dari:
     data/storyboards/<slug>.json (override khusus, bila ada), atau
     template generik 3-scene (total 10 detik) dari lib/prompts.py
2. Render tiap scene jadi gambar 9:16 via Nano Banana 2, dengan
   referensi produk agar identitas konsisten.
   (Tanpa gflow-cli — Flow dikendalikan langsung via Playwright.)

Aturan keras:
  - HANYA tangan / POV tangan, tidak ada wajah
  - Bahasa Indonesia untuk teks & voice-over (teks overlay ditambah via
    ffmpeg di tahap finish, BUKAN di-generate AI — default: tanpa teks)
  - Anti-anomali via ANOMALY_GUARD di setiap prompt

Usage: storyboard.py --product <slug> [--dry-run]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, product_dir, load_json, save_json  # noqa: E402
from prompts import build_storyboard  # noqa: E402
import flow_cli as flow  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Render storyboard (gambar)")
    ap.add_argument("--product", required=True)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"

    pdir = product_dir(a.product)
    rpath = pdir / "research.json"
    if not rpath.exists():
        die("research.json tidak ada")
    product = load_json(rpath)

    override = None
    ov_path = ROOT / "data" / "storyboards" / f"{a.product}.json"
    if ov_path.exists():
        log(f"pakai override storyboard: {ov_path.name}")
        override = load_json(ov_path)
    else:
        log("pakai template generik 3-scene")

    sb = build_storyboard(product, override)
    sb_path = pdir / "storyboard.json"
    save_json(sb_path, sb)
    log(f"storyboard.json: {len(sb['scenes'])} scene, total {sb['total_seconds']} dtk")
    for s in sb["scenes"]:
        log(f"  scene {s['n']}: {s['trim']}d | VO: {s['vo_line'][:50]}")

    char_name = f"aff-{a.product}"
    sdir = pdir / "storyboard"
    sdir.mkdir(parents=True, exist_ok=True)
    for s in sb["scenes"]:
        out = sdir / f"scene{s['n']:02d}.png"
        flow.image_generate(
            job_id=f"{a.product}-scene{s['n']:02d}",
            prompt=s["keyframe_prompt"],
            out_png=str(out),
            model="Nano Banana 2",
            ratio="9:16",
            character=char_name,
            headed=a.headed)
    log("tahap storyboard selesai")


if __name__ == "__main__":
    main()
