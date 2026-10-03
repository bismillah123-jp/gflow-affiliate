#!/usr/bin/env python3
"""tts.py — voice-over Bahasa Indonesia via edge-tts (tahap 6).

Naskah diambil dari storyboard.json (vo_script, ~10 detik). edge-tts
paket `edge-tts`: suara neural Microsoft, tanpa API key.
  - default: id-ID-GadisNeural (perempuan) — ganti via --voice
    mis. id-ID-ArdiNeural (laki-laki)

Fitur:
  - otomatis sesuaikan rate agar durasi VO <= 10.2 dtk (target video 10 dtk)
  - hormati proxy dari env (https_proxy/HTTPS_PROXY)
  - --dry-run: bikin vo.mp3 dummy 10 dtk via ffmpeg (tanpa network)

Usage: tts.py --product <slug> [--voice id-ID-ArdiNeural] [--dry-run]
Output: products/<slug>/vo/vo.mp3
"""
import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_dry_run, log, die, run, product_dir, load_json, which_or_die  # noqa: E402

TARGET_MAX = 10.2  # detik
DEFAULT_VOICE = os.environ.get("AFFILIATE_VOICE", "id-ID-GadisNeural")


def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def synth(text: str, voice: str, out: Path, rate: str) -> None:
    try:
        import edge_tts
    except ImportError:
        die("paket 'edge-tts' belum diinstall: pip install edge-tts")
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")

    async def _go():
        comm = edge_tts.Communicate(text, voice, rate=rate, proxy=proxy)
        await comm.save(str(out))

    asyncio.run(_go())


def main() -> None:
    ap = argparse.ArgumentParser(description="Voice-over Bahasa Indonesia")
    ap.add_argument("--product", required=True)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        os.environ["AFFILIATE_DRY_RUN"] = "1"

    pdir = product_dir(a.product)
    sb_path = pdir / "storyboard.json"
    if not sb_path.exists():
        die("storyboard.json tidak ada")
    script = load_json(sb_path).get("vo_script", "").strip()
    if not script:
        die("vo_script kosong di storyboard.json")
    log(f"naskah ({len(script)} char): {script[:70]}")

    vodir = pdir / "vo"
    vodir.mkdir(parents=True, exist_ok=True)
    out = vodir / "vo.mp3"

    if is_dry_run():
        which_or_die("ffmpeg")
        # nada 660Hz 10 dtk sebagai pengganti suara (biar durasi realistis)
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "sine=frequency=660:duration=10",
             "-c:a", "libmp3lame", "-b:a", "128k", str(out)], timeout=120)
        log(f"[dry-run] vo.mp3 dummy -> {out.name}")
        return

    for rate in ("+0%", "+15%", "+30%"):
        if out.exists():
            out.unlink()
        log(f"synth voice={a.voice} rate={rate} ...")
        synth(script, a.voice, out, rate)
        dur = ffprobe_duration(out)
        log(f"  durasi VO: {dur:.1f} dtk")
        if dur <= TARGET_MAX:
            break
        log("  kepanjangan, naikkan rate ...")
    else:
        log("peringatan: VO tetap > 10.2 dtk setelah rate +30%")

    if not out.exists() or out.stat().st_size == 0:
        die("gagal membuat vo.mp3")
    log(f"tahap TTS selesai -> {out.name}")


if __name__ == "__main__":
    main()
