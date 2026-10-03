#!/usr/bin/env python3
"""Generate keyframes via Flow agent (UI baru) untuk setiap scene."""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_URL = "https://flow.google.com/project/451f9ae9-d679-4cd4-9b72-1b9cb8bb48c0"

SCENES = [
    {
        "n": 1,
        "prompt": (
            "Using Nano Banana 2, create a vertical 9:16 HD product scene. "
            "Use the EXACT stain remover bottle from the reference image — keep the packaging design, "
            "label text, and colors identical, do not redesign it. "
            "Scene: a person's hand (exactly 5 fingers, natural anatomy, no extra limbs) holding the bottle "
            "next to a white shirt with a visible red sauce stain, on a clean bright laundry table. "
            "Smartphone product photography style, bright daylight, photorealistic. "
            "No text overlay, no watermark, no faces."
        ),
    },
    {
        "n": 2,
        "prompt": (
            "Using Nano Banana 2, create a vertical 9:16 HD product scene. "
            "Use the EXACT stain remover bottle from the reference image — keep the packaging design, "
            "label text, and colors identical, do not redesign it. "
            "Scene: close-up of hands (exactly 5 fingers each, natural anatomy) sprinkling white cleaning powder "
            "from the bottle onto a red sauce stain on white fabric, mid-scrubbing motion with a small brush. "
            "The stain is visibly fading. Clean bright bathroom background. "
            "Smartphone product photography style, bright daylight, photorealistic. "
            "No text overlay, no watermark, no faces."
        ),
    },
    {
        "n": 3,
        "prompt": (
            "Using Nano Banana 2, create a vertical 9:16 HD product scene. "
            "Use the EXACT stain remover bottle from the reference image — keep the packaging design, "
            "label text, and colors identical, do not redesign it. "
            "Scene: two hands (exactly 5 fingers each, natural anatomy) proudly holding up a sparkling clean "
            "white shirt, with the stain remover bottle clearly visible standing on the table in front. "
            "Bright cheerful laundry room background. "
            "Smartphone product photography style, bright daylight, photorealistic. "
            "No text overlay, no watermark, no faces."
        ),
    },
]

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--product", required=True)
    a.add_argument("--project", default=PROJECT_URL)
    args = a.parse_args()

    pdir = ROOT / "products" / args.product
    ref = pdir / "images" / "img1.webp"
    kdir = pdir / "keyframes"
    kdir.mkdir(parents=True, exist_ok=True)

    if not ref.exists():
        # cari gambar pertama yang ada
        imgs = sorted((pdir / "images").glob("img*"))
        ref = imgs[0] if imgs else None
    if not ref or not ref.exists():
        print("tidak ada gambar referensi"); sys.exit(1)
    print("referensi:", ref)

    for sc in SCENES:
        out = kdir / f"scene{sc['n']}.png"
        if out.exists():
            print(f"scene{sc['n']} sudah ada, skip")
            continue
        print(f"== generate keyframe scene{sc['n']} ==")
        cmd = [
            "node", str(ROOT / "lib" / "flow-agent.js"),
            "--project", args.project,
            "--ref", str(ref),
            "--prompt", sc["prompt"],
            "--out", str(out),
            "--wait", "300",
        ]
        r = subprocess.run(cmd, cwd=str(ROOT), timeout=420)
        if r.returncode != 0 or not out.exists():
            print(f"scene{sc['n']} GAGAL"); sys.exit(1)
        print(f"scene{sc['n']} OK: {out}")

    print("semua keyframes selesai")

if __name__ == "__main__":
    main()
