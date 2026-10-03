#!/usr/bin/env python3
"""finish_concat.py — gabung klip video jadi final (concat saja, tanpa edit audio)."""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--product", required=True)
    a.add_argument("--force", action="store_true")
    args = a.parse_args()

    pdir = ROOT / "products" / args.product
    final = pdir / "final.mp4"
    if final.exists() and not args.force:
        print("final.mp4 sudah ada, skip"); return

    clips = sorted((pdir / "clips").glob("scene*.mp4"))
    if not clips:
        print("tidak ada klip!"); sys.exit(1)
    print(f"{len(clips)} klip: {[c.name for c in clips]}")

    lst = pdir / "concat_list.txt"
    lst.write_text("\n".join(f"file '{c}'" for c in clips))
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(final)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(r.stderr[-500:]); sys.exit(1)

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True)
    print(f"final.mp4: {r.stdout.strip()}s — {final}")

if __name__ == "__main__":
    main()
