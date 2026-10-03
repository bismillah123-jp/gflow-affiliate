#!/usr/bin/env python3
"""gflow_shim.py — pembungkus CLI `gflow` (https://github.com/swissmarley/gflow-cli).

Semua pemanggilan gflow lewat fungsi di sini, supaya:
  - argumen konsisten (model, ratio, timeout, headed),
  - dry-run (AFFILIATE_DRY_RUN=1) menghasilkan file dummy deterministik
    tanpa menyentuh browser / akun Google — pipeline bisa diuji end-to-end.

Fungsi utama:
  character_ensure(name, image, prompt) -> bool (True bila baru dibuat)
  image_generate(job_id, prompt, out_png, ...)      # Nano Banana 2
  video_generate(job_id, prompt, out_mp4, ...)      # Omni Flash / Veo
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, run, placeholder_png, placeholder_mp4  # noqa: E402

GFLOW_BIN = shutil.which("gflow") or "gflow"

# state karakter yang sudah dibuat saat dry-run
_DRY_STATE = ROOT / ".dryrun_gflow.json"


def _dry_chars() -> set:
    if _DRY_STATE.exists():
        return set(json.loads(_DRY_STATE.read_text()).get("characters", []))
    return set()


def _dry_add_char(name: str) -> None:
    chars = _dry_chars()
    chars.add(name)
    _DRY_STATE.write_text(json.dumps({"characters": sorted(chars)}))


def _base_args(headed: bool = False, project: str = "") -> list:
    args = []
    if project:
        args += ["--project", project]
    args += ["--no-headed" if not headed else "--headed"]
    return args


def _exec(args: list, timeout: int) -> None:
    if shutil.which("gflow") is None and not is_dry_run():
        die("perintah `gflow` tidak ditemukan. Install: npm install -g @swissmarley/gflow-cli")
    run(["gflow"] + args, timeout=timeout)


def character_exists(name: str) -> bool:
    """Cek apakah character sudah ada (agar tidak dibuat ulang)."""
    if is_dry_run():
        return name in _dry_chars()
    r = subprocess.run(["gflow", "character", "list"],
                       capture_output=True, text=True, timeout=120)
    return name.lower() in r.stdout.lower()


def character_ensure(name: str, image: str, prompt: str,
                     headed: bool = False, project: str = "") -> bool:
    """Buat character referensi produk bila belum ada. Return True jika baru."""
    if character_exists(name):
        log(f"character '{name}' sudah ada, skip")
        return False
    log(f"membuat character '{name}' dari {image}")
    if is_dry_run():
        log(f"[dry-run] gflow character create --name {name} --image {image}")
        _dry_add_char(name)
        return True
    _exec(["character", "create",
           "--name", name,
           "--image", image,
           "--prompt", prompt,
           "--model", "nano-banana-2"]
          + _base_args(headed, project), timeout=600)
    return True


def image_generate(job_id: str, prompt: str, out_png: str,
                   model: str = "Nano Banana 2", ratio: str = "9:16",
                   character: str = "", headed: bool = False,
                   project: str = "", timeout: int = 900) -> Path:
    """Generate 1 gambar via gflow image. Return path output."""
    out = Path(out_png)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] gflow image --id {job_id} --model '{model}'")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_png(out)
    args = ["image", "--id", job_id, "--prompt", prompt,
            "--model", model, "--ratio", ratio, "--outputs", "1",
            "--out", str(out.parent)] + _base_args(headed, project)
    if character:
        args += ["--character", character]
    _exec(args, timeout=timeout)
    # gflow menulis <job-id>-001.png di --out; pindahkan ke nama yang diminta
    produced = out.parent / f"{job_id}-001.png"
    if produced.exists() and produced != out:
        produced.rename(out)
    if not out.exists():
        # fallback: ambil png terbaru di folder out
        cands = sorted(out.parent.glob("*.png"), key=os.path.getmtime)
        if cands:
            cands[-1].rename(out)
    if not out.exists():
        die(f"gflow image tidak menghasilkan file untuk job {job_id}")
    return out


def video_generate(job_id: str, prompt: str, out_mp4: str,
                   model: str = "Omni Flash", ratio: str = "9:16",
                   duration: int = 10, start_frame: str = "",
                   end_frame: str = "", character: str = "",
                   headed: bool = False, project: str = "",
                   timeout: int = 1800) -> Path:
    """Generate 1 video via gflow video (frames mode bila start_frame diisi)."""
    out = Path(out_mp4)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] gflow video --id {job_id} --model '{model}' "
            f"--duration {duration}")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_mp4(out, duration=duration)
    args = ["video", "--id", job_id, "--prompt", prompt,
            "--model", model, "--ratio", ratio,
            "--duration", str(duration), "--outputs", "1",
            "--out", str(out.parent)] + _base_args(headed, project)
    if start_frame:
        args += ["--start-frame", start_frame]
    if end_frame:
        args += ["--end-frame", end_frame]
    if character:
        args += ["--character", character]
    _exec(args, timeout=timeout)
    produced = out.parent / f"{job_id}-001.mp4"
    if produced.exists() and produced != out:
        produced.rename(out)
    if not out.exists():
        cands = sorted(out.parent.glob("*.mp4"), key=os.path.getmtime)
        if cands:
            cands[-1].rename(out)
    if not out.exists():
        die(f"gflow video tidak menghasilkan file untuk job {job_id}")
    return out
