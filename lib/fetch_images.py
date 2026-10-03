#!/usr/bin/env python3
"""fetch_images.py — cari & download gambar katalog produk (tahap 2).

Sumber gambar: DuckDuckGo Images via paket `ddgs` (tanpa API key).
Jalan di Linux manapun. Hormati proxy dari env (http_proxy/https_proxy).

Usage: fetch_images.py --product <slug> [--max 3] [--dry-run]
Output: products/<slug>/images/imgN.{jpg,png,webp} + manifest.json
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, run, product_dir, load_json, save_json, placeholder_png  # noqa: E402


def ddg_search(keywords: str, n: int) -> list:
    """Return list[{image, title, source}]."""
    try:
        from ddgs import DDGS
    except ImportError:
        die("paket 'ddgs' belum diinstall: pip install ddgs")
    log(f"mencari gambar: {keywords}")
    with DDGS() as ddgs:
        results = list(ddgs.images(keywords, max_results=n * 2))
    out = []
    for r in results:
        url = r.get("image") or ""
        if url.startswith("https://"):
            out.append({"image": url, "title": r.get("title", ""),
                        "source": r.get("source", "")})
    return out


def download(url: str, dest: Path, referer: str = "https://duckduckgo.com/") -> bool:
    r = subprocess.run(
        ["curl", "-fsSL", "--connect-timeout", "10", "--max-time", "60",
         "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
         "-H", "Accept: image/*",
         "-H", f"Referer: {referer}",
         "-o", str(dest), url],
        capture_output=True, timeout=90)
    return r.returncode == 0


def is_image(path: Path) -> bool:
    r = subprocess.run(["file", "-b", str(path)],
                       capture_output=True, text=True, timeout=30)
    t = r.stdout.strip().lower()
    return ("image" in t) or ("jpeg" in t) or ("png" in t) or ("webp" in t)


def ext_from_type(path: Path) -> str:
    r = subprocess.run(["file", "-b", str(path)],
                       capture_output=True, text=True, timeout=30)
    t = r.stdout.strip().lower()
    if "jpeg" in t:
        return ".jpg"
    if "png" in t:
        return ".png"
    if "webp" in t:
        return ".webp"
    return ".img"


def main() -> None:
    ap = argparse.ArgumentParser(description="Download gambar katalog produk")
    ap.add_argument("--product", required=True)
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"

    pdir = product_dir(a.product)
    rpath = pdir / "research.json"
    if not rpath.exists():
        die(f"research.json tidak ada; jalankan research.py --pick {a.product} dulu")
    product = load_json(rpath)

    imgdir = pdir / "images"
    imgdir.mkdir(parents=True, exist_ok=True)
    manifest_p = imgdir / "manifest.json"

    if is_dry_run():
        manifest = []
        for i in range(a.max):
            dest = imgdir / f"img{i + 1}.png"
            if not dest.exists():
                placeholder_png(dest)
            manifest.append({"file": dest.name, "url": "dry-run://placeholder",
                             "type": "PNG image data"})
            log(f"[dry-run] {dest.name}")
        save_json(manifest_p, manifest)
        log(f"selesai (dry-run): {len(manifest)} gambar -> {imgdir}")
        return

    q = product.get("image_keywords") or product["name"]
    results = ddg_search(q, a.max)
    if not results:
        die("tidak ada hasil gambar. Coba kata kunci lain di research.")

    manifest = []
    n = 0
    for res in results:
        if n >= a.max:
            break
        url = res["image"]
        tmp = imgdir / f"_tmp{n + 1}"
        log(f"download [{n + 1}]: {url[:70]}")
        if not download(url, tmp):
            log("  skip (gagal download)")
            continue
        if not is_image(tmp):
            log("  skip (bukan gambar)")
            tmp.unlink(missing_ok=True)
            continue
        dest = imgdir / f"img{n + 1}{ext_from_type(tmp)}"
        tmp.rename(dest)
        log(f"  OK -> {dest.name}")
        manifest.append({"file": dest.name, "url": url,
                         "title": res["title"], "source": res["source"]})
        n += 1

    save_json(manifest_p, manifest)
    log(f"selesai: {n} gambar -> {imgdir}")
    if n == 0:
        die("tidak ada gambar yang berhasil didownload")


if __name__ == "__main__":
    main()
