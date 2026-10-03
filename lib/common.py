#!/usr/bin/env python3
"""common.py — utilitas bersama pipeline affiliate.

Semua path relatif terhadap ROOT (folder repo), jadi jalan di Linux manapun.
Mode dry-run: set env AFFILIATE_DRY_RUN=1 (atau --dry-run di pipeline.py).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def is_dry_run() -> bool:
    return os.environ.get("AFFILIATE_DRY_RUN", "") == "1"


def log(msg: str) -> None:
    print(f"[aff] {msg}", flush=True)


def die(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    print(f"[aff] FATAL: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd, check: bool = True, timeout: int = 900, **kw):
    """Jalankan subprocess dengan logging. cmd = list[str]."""
    printable = " ".join(str(c) for c in cmd)
    log(f"+ {printable[:160]}")
    try:
        r = subprocess.run(cmd, timeout=timeout, **kw)
    except FileNotFoundError:
        die(f"perintah tidak ditemukan: {cmd[0]}")
    if check and r.returncode != 0:
        die(f"perintah gagal (exit {r.returncode}): {printable[:120]}")
    return r


def product_dir(slug: str) -> Path:
    d = ROOT / "products" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: Path, obj) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "produk"


def which_or_die(name: str) -> str:
    from shutil import which
    p = which(name)
    if not p:
        die(f"'{name}' tidak ditemukan di PATH")
    return p


def placeholder_png(path: Path, w: int = 768, h: int = 1360) -> Path:
    """Bikin PNG dummy valid pakai ffmpeg (untuk dry-run)."""
    which_or_die("ffmpeg")
    run(["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=1:duration=1",
         "-frames:v", "1", str(path)],
        timeout=120)
    return path


def placeholder_mp4(path: Path, duration: int = 10, w: int = 576, h: int = 1024,
                     with_audio: bool = True) -> Path:
    """Bikin MP4 dummy valid pakai ffmpeg (untuk dry-run)."""
    which_or_die("ffmpeg")
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "lavfi", "-i",
           f"testsrc=size={w}x{h}:rate=30:duration={duration}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i",
                f"sine=frequency=440:duration={duration}",
                "-shortest"]
    cmd += ["-pix_fmt", "yuv420p", str(path)]
    run(cmd, timeout=180)
    return path
