#!/usr/bin/env python3
"""
pipeline.py — Pipeline otomatis video affiliate TikTok/Shopee via gflow-cli.

Alur (7 tahap):
  1. research   : riset produk viral (curated/manual/trends)
  2. images     : download gambar katalog (DuckDuckGo, tanpa API key)
  3. hd         : HD + perjelas produk via Nano Banana 2 (gflow)
  4. storyboard : storyboard BERUPA GAMBAR per scene via Nano Banana 2 (gflow)
  5. video      : storyboard -> video 10 dtk via Omni Flash (gflow, frames mode)
  6. tts        : voice-over Bahasa Indonesia via edge-tts (tanpa API key)
  7. finish     : mux video + VO (+teks overlay opsional) via ffmpeg

Konsistensi produk dijaga via gflow character (referensi visual `aff-<slug>`).
Anti-anomali via ANOMALY_GUARD di setiap prompt (lihat lib/prompts.py).

Syarat sekali per mesin: ./setup.sh lalu `gflow auth login` (interaktif),
karena gflow mengendalikan Chrome + sesi Google Flow milikmu.

Pakai:
  python3 pipeline.py --auto                       # full pipeline, produk top viral
  python3 pipeline.py --product <slug>             # full pipeline 1 produk
  python3 pipeline.py --product <slug> --from hd   # mulai dari tahap hd
  python3 pipeline.py --product <slug> --only video
  python3 pipeline.py --auto --dry-run             # uji end-to-end TANPA API/browser
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))

from common import log, die  # noqa: E402

STAGES = ["research", "images", "hd", "storyboard", "video", "tts", "finish"]


def sh(*cmd: str) -> None:
    import subprocess
    log("+ " + " ".join(cmd[:5]))
    r = subprocess.run(cmd, timeout=3600)
    if r.returncode != 0:
        die(f"tahap gagal (exit {r.returncode}): {cmd[1]}")


def main() -> None:
    a = argparse.ArgumentParser(description="Pipeline video affiliate otomatis")
    a.add_argument("--product", default="",
                   help="slug produk (mis. pembersih-noda)")
    a.add_argument("--auto", action="store_true",
                   help="pilih produk skor viral tertinggi")
    a.add_argument("--manual-name", default="",
                   help="nama produk (mode manual, tanpa riset)")
    a.add_argument("--project", default=os.environ.get("GFLOW_PROJECT", ""),
                   help="nama Flow project gflow (opsional)")
    a.add_argument("--voice", default=os.environ.get("AFFILIATE_VOICE", ""),
                   help="suara TTS (default id-ID-GadisNeural)")
    a.add_argument("--from", dest="from_stage", default="research",
                   choices=STAGES, help="mulai dari tahap")
    a.add_argument("--only", choices=STAGES, help="cuma jalankan satu tahap")
    a.add_argument("--list-stages", action="store_true")
    a.add_argument("--dry-run", action="store_true",
                   help="uji end-to-end tanpa API key / browser / kuota")
    a.add_argument("--headed", action="store_true",
                   help="tampilkan browser gflow (debug)")
    args = a.parse_args()

    if args.list_stages:
        print("\n".join(f"{i + 1}. {s}" for i, s in enumerate(STAGES)))
        return

    if args.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"
        log("mode DRY-RUN: semua panggilan gflow/API dipalsukan")

    if not args.product and not args.auto and not args.manual_name:
        die("tentukan --product, --auto, atau --manual-name")

    py = sys.executable
    common = ["--dry-run"] if args.dry_run else []
    gflow_flags = (["--project", args.project] if args.project else []) \
        + (["--headed"] if args.headed else [])

    def stage_research():
        log("== [1/7] research ==")
        if args.manual_name:
            sh(py, str(LIB / "research.py"), "--manual", "--name", args.manual_name,
               *common)
            # slug dari nama -> baca kembali dari products/
            return
        if args.auto:
            sh(py, str(LIB / "research.py"), "--auto", *common)
        else:
            sh(py, str(LIB / "research.py"), "--pick", args.product, *common)

    def stage_images(slug):
        log("== [2/7] images ==")
        sh(py, str(LIB / "fetch_images.py"), "--product", slug, *common)

    def stage_hd(slug):
        log("== [3/7] hd (Nano Banana 2) ==")
        sh(py, str(LIB / "hd_enhance.py"), "--product", slug, *gflow_flags, *common)

    def stage_storyboard(slug):
        log("== [4/7] storyboard (gambar) ==")
        sh(py, str(LIB / "storyboard.py"), "--product", slug, *gflow_flags, *common)

    def stage_video(slug):
        log("== [5/7] video (Omni Flash 10s) ==")
        sh(py, str(LIB / "gen_video.py"), "--product", slug, *gflow_flags, *common)

    def stage_tts(slug):
        log("== [6/7] tts (VO Bahasa Indonesia) ==")
        cmd = [py, str(LIB / "tts.py"), "--product", slug, *common]
        if args.voice:
            cmd += ["--voice", args.voice]
        sh(*cmd)

    def stage_finish(slug):
        log("== [7/7] finish ==")
        sh(py, str(LIB / "finish.py"), "--product", slug, *common)

    # Tentukan slug: untuk --manual-name, slugify dari nama
    if args.manual_name:
        from common import slugify
        slug = slugify(args.manual_name)
    elif args.auto:
        slug = None  # di-resolve setelah stage research jalan
    else:
        slug = args.product

    stages = [args.only] if args.only else STAGES[STAGES.index(args.from_stage):]

    if slug is None and "research" not in stages:
        die("--auto/--manual-name butuh tahap research untuk resolve slug; "
            "pakai --product <slug> bila mulai dari tengah")

    if "research" in stages:
        stage_research()
        if args.auto or args.manual_name:
            import time
            cands = sorted((ROOT / "products").glob("*/research.json"),
                           key=lambda p: p.stat().st_mtime)
            if not cands:
                die("research tidak menghasilkan produk")
            # pilih yang baru dibuat (mtime terbaru)
            slug = max(cands, key=lambda p: p.stat().st_mtime).parent.name
            log(f"slug ter-resolve: {slug}")

    rest = {"images": stage_images, "hd": stage_hd, "storyboard": stage_storyboard,
            "video": stage_video, "tts": stage_tts, "finish": stage_finish}
    for s in stages:
        if s == "research":
            continue
        rest[s](slug)

    out = ROOT / "products" / slug / "final.mp4"
    print(f"\nPIPELINE SELESAI ✔  ->  {out} "
          f"({'ADA' if out.exists() else 'TIDAK ADA!'})")


if __name__ == "__main__":
    main()
