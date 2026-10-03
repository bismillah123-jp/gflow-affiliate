#!/usr/bin/env python3
"""hd_keyframes.py — generate keyframe HD per scene via Nano Banana 2 (tahap 5).

Strategi: gflow edit image butuh --media-id dari aset proyek, jadi:
  1. Buat "canvas" via gflow image (aset kosong di proyek).
  2. Ambil media-id canvas dari `gflow media list`.
  3. Untuk tiap scene: gflow edit image --media-id <canvas> --reference <katalog>
     --prompt <keyframe_prompt>  -> keyframes/sceneN.png (Nano Banana 2)

Usage: hd_keyframes.py --product <slug> [--force]
"""
import argparse
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("GFLOW_CHROME_PATH", "/home/hatch/.local/bin/chrome-nosandbox")
GFLOW = ["gflow"]


def run(cmd, **kw):
    kw.setdefault("timeout", 900)
    print("+", " ".join(cmd[:6]), "...")
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    pdir = os.path.join(BASE, "products", a.product)
    sb_path = os.path.join(pdir, "storyboard.json")
    if not os.path.exists(sb_path):
        print("storyboard.json tidak ada", file=sys.stderr)
        sys.exit(1)
    with open(sb_path) as f:
        sb = json.load(f)

    imgdir = os.path.join(pdir, "images")
    refs = sorted(f for f in os.listdir(imgdir) if f.endswith((".webp", ".png", ".jpg", ".jpeg")))
    if not refs:
        print("tidak ada gambar katalog", file=sys.stderr)
        sys.exit(1)
    catalog = os.path.join(imgdir, refs[0])
    print("referensi katalog:", catalog)

    kfdir = os.path.join(pdir, "keyframes")
    os.makedirs(kfdir, exist_ok=True)

    # 1. canvas
    print("== membuat canvas ==")
    r = run(GFLOW + ["image", "--no-headed", "--id", f"canvas-{a.product}",
                     "--prompt", "empty light gray studio background, no objects, no text, no watermark",
                     "--ratio", "1:1", "--out", kfdir])
    if r.returncode != 0:
        print("gflow image gagal:\n", r.stderr[-2000:], file=sys.stderr)
        sys.exit(1)

    # 2. cari media-id canvas
    print("== mencari media-id canvas ==")
    r = run(GFLOW + ["media", "list", "--no-headed"], timeout=120)
    out = r.stdout + r.stderr
    media_id = None
    # coba JSON
    try:
        data = json.loads(r.stdout)
        items = data if isinstance(data, list) else data.get("items", data.get("media", []))
        for it in items:
            label = json.dumps(it)
            if f"canvas-{a.product}" in label:
                media_id = it.get("id") or it.get("mediaId")
                break
    except Exception:
        pass
    # fallback: regex id
    if not media_id:
        m = re.search(r'"id"\s*:\s*"([^"]+)"', out)
        if m:
            media_id = m.group(1)
    if not media_id:
        print("tidak bisa menemukan media-id canvas. Output mentah:", file=sys.stderr)
        print(out[-1500:], file=sys.stderr)
        sys.exit(1)
    print("media-id canvas:", media_id)

    # 3. edit per scene
    for sc in sb["scenes"]:
        dest = os.path.join(kfdir, f"scene{sc['n']}.png")
        if os.path.exists(dest) and not a.force:
            print(f"scene{sc['n']}: sudah ada, skip")
            continue
        print(f"== keyframe scene {sc['n']} ==")
        r = run(GFLOW + ["edit", "image", "--no-headed",
                         "--media-id", media_id,
                         "--reference", catalog,
                         "--prompt", sc["keyframe_prompt"],
                         "--out", kfdir], timeout=1200)
        if r.returncode != 0:
            print(f"scene {sc['n']} gagal:\n", r.stderr[-1500:], file=sys.stderr)
            continue
        # cari file output terbaru
        cands = sorted(
            (os.path.join(kfdir, f) for f in os.listdir(kfdir)
             if f.endswith((".png", ".jpg", ".webp")) and f.startswith("edit-")),
            key=os.path.getmtime)
        if cands:
            os.rename(cands[-1], dest)
            print("  ->", dest)
    print("selesai:", kfdir)


if __name__ == "__main__":
    main()
