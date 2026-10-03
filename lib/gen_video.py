#!/usr/bin/env python3
"""gen_video.py — storyboard (gambar) → video 10 detik via Omni Flash (tahap 5).

Mode frames: --start-frame scene01.png --end-frame scene03.png, durasi 10,
rasio 9:16. Prompt video meminta audio ambient alami SAJA (tanpa dialog) —
voice-over Bahasa Indonesia ditambahkan di tahap tts+finish agar bahasa dan
timing-nya terjamin.

Hasilnya video beneran (bukan slideshow gambar).
(Tanpa gflow-cli — Flow dikendalikan langsung via Playwright.)

Usage: gen_video.py --product <slug> [--model NAME] [--dry-run]
Output: products/<slug>/clips/final_10s.mp4
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_dry_run, log, die, product_dir, load_json  # noqa: E402
import flow_cli as flow  # noqa: E402

DURATION = 10


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate video 10s (Omni Flash)")
    ap.add_argument("--product", required=True)
    ap.add_argument("--model", default=os.environ.get("AFFILIATE_VIDEO_MODEL", "Omni Flash"))
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"

    pdir = product_dir(a.product)
    sb_path = pdir / "storyboard.json"
    if not sb_path.exists():
        die("storyboard.json tidak ada; jalankan tahap storyboard dulu")
    sb = load_json(sb_path)

    sdir = pdir / "storyboard"
    scenes = sorted(sdir.glob("scene*.png"))
    if not scenes:
        die("tidak ada gambar storyboard")
    start, end = str(scenes[0]), str(scenes[-1])
    log(f"frames: {Path(start).name} -> {Path(end).name}")

    char_name = f"aff-{a.product}"
    cdir = pdir / "clips"
    cdir.mkdir(parents=True, exist_ok=True)
    out = cdir / "final_10s.mp4"
    flow.video_generate(
        job_id=f"{a.product}-video10s",
        prompt=sb["video_prompt"],
        out_mp4=str(out),
        model=a.model,
        ratio="9:16",
        duration=DURATION,
        start_frame=start,
        end_frame=end if end != start else "",
        character=char_name,
        headed=a.headed)
    log(f"tahap video selesai -> {out.name}")


if __name__ == "__main__":
    main()
