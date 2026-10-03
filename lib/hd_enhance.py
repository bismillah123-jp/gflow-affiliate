#!/usr/bin/env python3
"""hd_enhance.py — HD-kan gambar katalog pakai Nano Banana 2 (tahap 3).

Strategi konsistensi: gambar katalog di-upload sebagai referensi produk
(`aff-<slug>`, disimpan di profil browser), lalu Nano Banana 2 me-render ulang
produk dalam kualitas HD dengan identitas yang dijaga referensi tersebut.

(Tanpa gflow-cli — Flow dikendalikan langsung via Playwright. Login sekali:
 python3 pipeline.py --auth)

Usage: hd_enhance.py --product <slug> [--max 2] [--dry-run]
Output: products/<slug>/hd/<stem>_hd.png
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_dry_run, log, die, product_dir, load_json  # noqa: E402
from prompts import hd_prompt  # noqa: E402
import flow_cli as flow  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="HD-kan gambar katalog (Nano Banana 2)")
    ap.add_argument("--product", required=True)
    ap.add_argument("--max", type=int, default=2)
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

    imgs = sorted((pdir / "images").glob("img*"))
    imgs = [p for p in imgs if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
            and p.name != "manifest.json"]
    if not imgs:
        die("tidak ada gambar katalog di products/<slug>/images/")

    char_name = f"aff-{a.product}"
    # referensi memakai gambar katalog pertama sebagai identitas visual
    flow.character_ensure(
        char_name, str(imgs[0]),
        prompt=(f"Product reference for affiliate ads: {product['name']}. "
                f"Visual identity: {product.get('product_visual', product['name'])}. "
                "This is a PRODUCT, keep its packaging identical in every use."),
        headed=a.headed)

    hddir = pdir / "hd"
    hddir.mkdir(parents=True, exist_ok=True)
    desc = product.get("product_visual", product["name"])
    for img in imgs[:a.max]:
        out = hddir / f"{img.stem}_hd.png"
        flow.image_generate(
            job_id=f"{a.product}-hd-{img.stem}",
            prompt=hd_prompt(desc),
            out_png=str(out),
            model="Nano Banana 2",
            ratio="9:16",
            refs=[str(img)],          # i2i: gambar katalognya sendiri
            character=char_name,       # + referensi identitas produk
            headed=a.headed)
    log("tahap HD selesai")


if __name__ == "__main__":
    main()
