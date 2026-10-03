#!/usr/bin/env python3
"""research.py — riset produk affiliate (tahap 1).

Sumber kandidat (dipilih via --provider):
  curated : data/trending_id.json (kurasi manual, default & paling bisa diandalkan)
  manual  : input manual via argumen (--name, --keywords, ...)
  trends  : Google Trends Indonesia via pytrends (best-effort, butuh internet;
            bila gagal otomatis fallback ke curated)

Catatan jujur: API resmi TikTok Shop / Shopee Affiliate butuh kredensial
yang disetujui (app review). Pipeline ini TIDAK mengarang-ngarang data API —
modul ini menyediakan titik ekstensi: set env TIKTOK_SHOP_KEY / SHOPEE_KEY
dan implementasikan provider sendiri mengikuti pola di bawah.

Usage:
  research.py --list
  research.py --pick <slug> | --auto
  research.py --manual --name "Nama" --keywords "..." --visual "..." --slug <slug>
  research.py --provider trends --category "skincare"
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, product_dir, load_json, save_json, slugify  # noqa: E402

DB = ROOT / "data" / "trending_id.json"


def load_db() -> list:
    return load_json(DB)["products"]


def cmd_list(products: list) -> None:
    print(f"{'SLUG':<22} {'SKOR':<5} {'NAMA'}")
    print("-" * 72)
    for p in sorted(products, key=lambda x: -x.get("viral_score", 0)):
        print(f"{p['slug']:<22} {p.get('viral_score', 0):<5} {p['name']} ({p.get('price_range', '-')})")
        print(f"  -> {p.get('why_viral', '')}")


def write_research(product: dict) -> Path:
    slug = product["slug"]
    pdir = product_dir(slug)
    out = pdir / "research.json"
    save_json(out, product)
    log(f"OK: {product['name']} -> products/{slug}/research.json")
    return out


def provider_trends(category: str = "") -> list:
    """Best-effort: ambil topik naik daun Google Trends (ID)."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log("pytrends belum diinstall (pip install pytrends) — fallback ke curated")
        return []
    try:
        kw = category or "skincare viral"
        tr = TrendReq(hl="id", tz=420)
        tr.build_payload([kw], timeframe="now 7-d", geo="ID")
        rising = tr.related_queries()[kw]["rising"]
        out = []
        for _, row in rising.head(8).iterrows():
            out.append({"query": row["query"], "value": int(row["value"])})
        return out
    except Exception as e:
        log(f"pytrends gagal ({e}) — fallback ke curated")
        return []


def cmd_trends(category: str) -> None:
    rows = provider_trends(category)
    if not rows:
        print("tidak ada sinyal trends; pakai --list untuk kurasi manual.")
        return
    print(f"sinyal naik daun (ID, 7 hari) untuk '{category or 'skincare viral'}':")
    for r in rows:
        print(f"  +{r['value']:>4}  {r['query']}")
    print("\nTambahkan produk menjanjikan ke data/trending_id.json lalu --pick.")


def cmd_manual(args) -> None:
    if not args.name:
        die("--manual butuh --name")
    slug = args.slug or slugify(args.name)
    product = {
        "slug": slug,
        "name": args.name,
        "category": args.category or "Umum",
        "price_range": args.price or "-",
        "image_keywords": args.keywords or args.name,
        "product_visual": args.visual or args.name,
        "angle": args.angle or "",
        "cta": "cek keranjang kuning",
        "pov_scenes": "hands-only",
        "viral_score": args.score or 50,
        "why_viral": "input manual",
    }
    write_research(product)


def main() -> None:
    ap = argparse.ArgumentParser(description="Riset produk affiliate")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--pick")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--provider", default="curated",
                    choices=["curated", "manual", "trends"])
    ap.add_argument("--category", default="")
    # argumen mode manual
    ap.add_argument("--manual", action="store_true")
    ap.add_argument("--name", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--visual", default="")
    ap.add_argument("--angle", default="")
    ap.add_argument("--price", default="")
    ap.add_argument("--score", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true",
                    help="diterima agar konsisten; riset tidak butuh network")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"

    if a.manual or a.provider == "manual":
        cmd_manual(a)
        return
    if a.provider == "trends":
        cmd_trends(a.category)
        return
    products = load_db()
    if a.list or not any([a.pick, a.auto]):
        cmd_list(products)
        return
    if a.pick:
        p = next((x for x in products if x["slug"] == a.pick), None)
        if not p:
            die(f"slug '{a.pick}' tidak ada. Pakai --list.")
        write_research(p)
    elif a.auto:
        top = max(products, key=lambda x: x.get("viral_score", 0))
        log(f"auto-pick skor tertinggi: {top['slug']}")
        write_research(top)


if __name__ == "__main__":
    main()
