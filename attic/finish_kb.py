#!/usr/bin/env python3
"""finish_kb.py — buat video final dari keyframes + efek Ken Burns.

- Tiap keyframe jadi klip dengan zoompan (3s, 4s, 3s)
- Teks overlay Bahasa Indonesia via drawtext
- Output: products/<slug>/final.mp4 (tanpa audio dulu, VO ditambah terpisah)
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# storyboard: (keyframe, durasi detik, teks overlay)
SCENES = [
    ("scene1.png", 3, "Noda bandel?"),
    ("scene2.png", 4, "Gosok... kinclong!"),
    ("scene3.png", 3, "Cek keranjang kuning!"),
]

def run(cmd, **kw):
    kw.setdefault("timeout", 300)
    print("+", " ".join(cmd[:6]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-500:])
        sys.exit(1)
    return r

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--product", required=True)
    a.add_argument("--force", action="store_true")
    args = a.parse_args()

    pdir = ROOT / "products" / args.product
    kdir = pdir / "keyframes"
    final = pdir / "final.mp4"
    if final.exists() and not args.force:
        print("final.mp4 sudah ada, skip")
        return

    # cari font
    r = subprocess.run(["fc-list", ":style=Bold", "file"], capture_output=True, text=True)
    font = None
    for line in r.stdout.splitlines():
        if "DejaVuSans-Bold" in line:
            font = line.split(":")[0]
            break
    if not font:
        print("font tidak ketemu"); sys.exit(1)

    tmpdir = pdir / "tmp_kb"
    tmpdir.mkdir(exist_ok=True)

    clips = []
    for i, (kf, dur, text) in enumerate(SCENES, 1):
        src = kdir / kf
        if not src.exists():
            print(f"{kf} tidak ada!"); sys.exit(1)
        out = tmpdir / f"clip{i}.mp4"
        # Ken Burns: zoompan dari 1.0 ke 1.1, 30fps
        # Teks overlay di tengah bawah
        frames = dur * 30
        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
            f"drawtext=fontfile={font}:text='{text}':fontsize=64:fontcolor=white:"
            f"borderw=3:bordercolor=black@0.8:x=(w-text_w)/2:y=h-280"
        )
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(src),
            "-vf", vf,
            "-t", str(dur), "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out),
        ])
        clips.append(out)
        print(f"clip{i} OK ({dur}s)")

    # concat
    lst = tmpdir / "list.txt"
    lst.write_text("\n".join(f"file '{c}'" for c in clips))
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(lst), "-c", "copy", str(final),
    ])
    # verifikasi durasi
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True)
    print(f"final.mp4 durasi: {r.stdout.strip()}s")
    print("SELESAI:", final)

if __name__ == "__main__":
    main()
