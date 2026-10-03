#!/usr/bin/env python3
"""flow_cli.py — pembungkus `gflow` CLI (https://github.com/ffroliva/gflow-cli).

Drive Google Flow dari terminal: Nano Banana 2 (image) + Omni Flash (video),
via browser session milik sendiri. Install: pip install gflow-cli.

Interface (disengaja mirip shim lama supaya stage script tidak berubah):
  character_ensure(name, image, prompt) -> bool (True bila baru dibuat)
  image_generate(job_id, prompt, out_png, ...)      # Nano Banana 2 (i2i/t2i)
  video_generate(job_id, prompt, out_mp4, ...)      # Omni Flash (i2v)

Catatan:
  - Konsistensi produk: gambar referensi disimpan di
    ~/.config/affiliate-flow/references/<name>.png lalu di-pass sebagai
    --ref di tiap generate (padanan "character" untuk PRODUK — Flow Character
    entity hanya untuk wajah/orang dan butuh project id).
  - Mode dry-run (AFFILIATE_DRY_RUN=1): file dummy, tanpa browser/kuota.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, run, placeholder_png, placeholder_mp4  # noqa: E402

GFLOW_BIN = shutil.which("gflow") or "gflow"
REF_DIR = Path.home() / ".config" / "affiliate-flow" / "references"

MODEL_MAP = {
    "nano banana 2": "nano2",
    "nano-banana-2": "nano2",
    "omni flash": "omni-flash",
}

_DRY_STATE = ROOT / ".dryrun_flow.json"


def _dry_state(data: dict | None = None) -> dict:
    if data is not None:
        _DRY_STATE.write_text(json.dumps(data))
        return data
    if _DRY_STATE.exists():
        return json.loads(_DRY_STATE.read_text())
    return {}


def _model(name: str, kind: str) -> str:
    m = MODEL_MAP.get(name.strip().lower(), name.strip().lower().replace(" ", "-"))
    return m


def _check_bin() -> None:
    if shutil.which("gflow") is None and not is_dry_run():
        die("perintah `gflow` tidak ditemukan.\n"
            "  Install: pip install gflow-cli  (atau ./setup.sh)")


def _newest(outdir: Path, exts: tuple) -> Path | None:
    cands = [p for p in outdir.iterdir()
             if p.is_file() and p.suffix.lower() in exts]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def character_exists(name: str) -> bool:
    if is_dry_run():
        return name in _dry_state().get("characters", [])
    return (REF_DIR / f"{name}.png").exists()


def character_ensure(name: str, image: str, prompt: str,
                     headed: bool = False, project: str = "") -> bool:
    """Simpan gambar referensi produk (dipakai sebagai --ref tiap generate)."""
    if character_exists(name):
        log(f"referensi '{name}' sudah ada, skip")
        return False
    log(f"menyimpan referensi '{name}' dari {image}")
    if is_dry_run():
        st = _dry_state()
        chars = st.get("characters", [])
        chars.append(name)
        _dry_state({"characters": sorted(set(chars))})
        return True
    REF_DIR.mkdir(parents=True, exist_ok=True)
    dest = REF_DIR / f"{name}.png"
    try:
        from PIL import Image
        Image.open(image).convert("RGB").save(dest)
    except Exception:
        shutil.copy(image, dest)
    log(f"referensi tersimpan: {dest}")
    return True


def _ref_for(character: str) -> str:
    if not character:
        return ""
    p = REF_DIR / f"{character}.png"
    if not p.exists():
        die(f"referensi '{character}' belum ada — jalankan tahap hd dulu")
    return str(p)


def image_generate(job_id: str, prompt: str, out_png: str,
                   model: str = "Nano Banana 2", ratio: str = "9:16",
                   refs: list | None = None, character: str = "",
                   headed: bool = False, project: str = "",
                   timeout: int = 900) -> Path:
    """Generate 1 gambar. refs=[path...] -> i2i; tanpa refs -> t2i."""
    out = Path(out_png)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] gflow image --id {job_id} --model '{model}'")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_png(out)

    _check_bin()
    all_refs = list(refs or [])
    cref = _ref_for(character)
    if cref and cref not in all_refs:
        all_refs.append(cref)
    for r in all_refs:
        if not Path(r).exists():
            die(f"file referensi tidak ada: {r}")

    tmpdir = Path(tempfile.mkdtemp(prefix=f"aff-{job_id}-"))
    try:
        if all_refs:
            cmd = [GFLOW_BIN, "image", "i2i", prompt]
            for r in all_refs:
                cmd += ["--ref", r]
        else:
            cmd = [GFLOW_BIN, "image", "t2i", prompt]
        cmd += ["--model", _model(model, "image"),
                "--aspect", ratio,
                "--out", str(tmpdir)]
        run(cmd, timeout=timeout)
        got = _newest(tmpdir, (".png", ".jpg", ".jpeg", ".webp"))
        if not got:
            die(f"gflow image tidak menghasilkan file untuk job {job_id}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(got), str(out))
        log(f"OK: {out.name}")
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def video_generate(job_id: str, prompt: str, out_mp4: str,
                   model: str = "Omni Flash", ratio: str = "9:16",
                   duration: int = 10, start_frame: str = "",
                   end_frame: str = "", character: str = "",
                   headed: bool = False, project: str = "",
                   timeout: int = 1800) -> Path:
    """Generate 1 video via i2v (frames mode bila start_frame diisi)."""
    out = Path(out_mp4)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] gflow video --id {job_id} --model '{model}' "
            f"--duration {duration}")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_mp4(out, duration=duration)

    _check_bin()
    if not start_frame:
        die("video butuh start_frame (storyboard scene01)")
    for f in (start_frame, end_frame):
        if f and not Path(f).exists():
            die(f"file frame tidak ada: {f}")

    tmpdir = Path(tempfile.mkdtemp(prefix=f"aff-{job_id}-"))
    try:
        cmd = [GFLOW_BIN, "video", "i2v", prompt,
               "--initial-frame", start_frame]
        if end_frame:
            cmd += ["--end-frame", end_frame]
        cmd += ["--model", _model(model, "video"),
                "--aspect", ratio,
                "--duration", str(duration),
                "--out-dir", str(tmpdir)]
        run(cmd, timeout=timeout)
        got = _newest(tmpdir, (".mp4",))
        if not got:
            die(f"gflow video tidak menghasilkan file untuk job {job_id}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(got), str(out))
        log(f"OK: {out.name}")
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
