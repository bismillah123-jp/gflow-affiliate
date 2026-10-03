#!/usr/bin/env python3
"""finish.py — rakit video final 10 detik (tahap 7).

  - Input : products/<slug>/clips/final_10s.mp4 (hasil Omni Flash)
            products/<slug>/vo/vo.mp3 (voice-over Bahasa Indonesia)
  - Proses: mix audio asli video (diredam) + VO, opsional teks overlay
    Bahasa Indonesia via ffmpeg drawtext (deterministik — teks TIDAK
    di-generate AI agar tidak garbled; default: tanpa teks overlay,
    sesuai permintaan "jangan terlalu rame teks")
  - Output: products/<slug>/final.mp4 (9:16, siap upload TikTok/Shopee)

Usage: finish.py --product <slug> [--overlay-text "Teks"] [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_dry_run, log, die, run, product_dir, load_json, which_or_die  # noqa: E402


def has_audio(path: Path) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60)
    return bool(r.stdout.strip())


def find_font() -> str:
    """Cari font TTF sistem untuk drawtext."""
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(cand).exists():
            return cand
    r = subprocess.run(["fc-list", ":style=Bold", "file"],
                       capture_output=True, text=True, timeout=30)
    for line in r.stdout.splitlines():
        p = line.split(":")[0].strip()
        if p.endswith(".ttf"):
            return p
    return ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Rakit video final")
    ap.add_argument("--product", required=True)
    ap.add_argument("--overlay-text", default="",
                    help="teks overlay Bahasa Indonesia (opsional, default: tanpa teks)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"
    which_or_die("ffmpeg")

    pdir = product_dir(a.product)
    clip = pdir / "clips" / "final_10s.mp4"
    vo = pdir / "vo" / "vo.mp3"
    if not clip.exists():
        die("clips/final_10s.mp4 tidak ada; jalankan tahap video dulu")
    if not vo.exists():
        die("vo/vo.mp3 tidak ada; jalankan tahap tts dulu")

    final = pdir / "final.mp4"
    tmp = pdir / "_final_tmp.mp4"

    # --- 1. mix audio: ambient video diredam + VO di depan ---
    if has_audio(clip):
        afilter = ("[0:a]volume=0.25[bg];"
                   "[1:a]adelay=400|400,volume=1.0[vo];"
                   "[bg][vo]amix=inputs=2:duration=first:dropout_transition=0[a]")
        amap = ["-map", "0:v", "-map", "[a]"]
    else:
        afilter = "[1:a]adelay=400|400,volume=1.0[a]"
        amap = ["-map", "0:v", "-map", "[a]"]

    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", str(clip), "-i", str(vo),
           "-filter_complex", afilter] + amap + [
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k",
           "-shortest", str(tmp)]
    run(cmd, timeout=300)
    log("audio mix OK (VO + ambient diredam)")

    # --- 2. teks overlay opsional (drawtext, deterministik) ---
    if a.overlay_text:
        font = find_font()
        if not font:
            log("peringatan: font tidak ketemu, overlay teks dilewati")
            tmp.rename(final)
        else:
            safe = a.overlay_text.replace(":", "\\:").replace("'", "")
            vf = (f"drawtext=fontfile={font}:text='{safe}':"
                  "fontsize=44:fontcolor=white:borderw=2:bordercolor=black@0.8:"
                  "x=(w-text_w)/2:y=h-180")
            run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp),
                 "-vf", vf, "-c:a", "copy", str(final)], timeout=300)
            tmp.unlink(missing_ok=True)
            log(f"overlay teks: {a.overlay_text}")
    else:
        tmp.rename(final)

    # --- 3. verifikasi ---
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height",
         "-of", "json", str(final)],
        capture_output=True, text=True, timeout=60)
    info = json.loads(r.stdout or "{}")
    dur = float(info.get("format", {}).get("duration", 0))
    streams = [s["codec_type"] for s in info.get("streams", [])]
    log(f"final.mp4: {dur:.1f} dtk | streams: {streams} | {final.stat().st_size // 1024} KB")
    if "video" not in streams or "audio" not in streams:
        die("final.mp4 tidak lengkap (butuh video+audio)")
    log("tahap finish selesai ✔")


if __name__ == "__main__":
    main()
