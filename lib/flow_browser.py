#!/usr/bin/env python3
"""flow_browser.py — kendalikan Google Flow LANGSUNG via Playwright (TANPA gflow-cli).

Menggantikan gflow_shim.py dengan INTERFACE YANG SAMA persis, jadi
hd_enhance.py / storyboard.py / gen_video.py hampir tidak berubah:

  character_ensure(name, image, prompt) -> bool   (True bila baru dibuat)
  image_generate(job_id, prompt, out_png, ...)    # Nano Banana 2
  video_generate(job_id, prompt, out_mp4, ...)    # Omni Flash

Cara kerja (mode real):
  - Playwright persistent Chromium profile di ~/.config/affiliate-flow/
  - Login Google/Flow SEKALI via:  python3 pipeline.py --auth
    (browser kebuka, login manual, tutup — sesi tersimpan di profil)
  - Tiap generate: buka Flow -> pilih model -> upload gambar referensi
    sebagai ingredient -> isi prompt -> generate -> tunggu -> download hasil.

Mode dry-run (AFFILIATE_DRY_RUN=1): file dummy deterministik, tanpa browser —
pipeline bisa diuji end-to-end tanpa login/kuota.

CATATAN JUJUR (baca sebelum protes kalau UI berubah):
  Flow TIDAK punya API publik. Otomasi ini memakai UI web yang bisa berubah
  sewaktu-waktu. Semua selector terpusat di SELECTORS di bawah — kalau Flow
  ganti UI, tune di SATU tempat ini. Debug dengan --headed.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, is_dry_run, log, die, placeholder_png, placeholder_mp4  # noqa: E402

FLOW_URL = "https://labs.google/fx/tools/flow"
PROFILE_DIR = Path.home() / ".config" / "affiliate-flow"
AUTH_MARKER = PROFILE_DIR / ".auth_ok"
REF_DIR = PROFILE_DIR / "references"

# ---------------------------------------------------------------------------
# SELECTORS — satu-satunya tempat yang perlu di-tune kalau UI Flow berubah.
# Strategi: role/text dulu (tahan banting), CSS spesifik sebagai fallback.
# ---------------------------------------------------------------------------
SELECTORS = {
    # tombol/tab mode di Flow
    "tab_text_to_video": 'button:has-text("Text to video")',
    "tab_frames_to_video": 'button:has-text("Frames to video")',
    "tab_ingredients": 'button:has-text("Ingredients")',
    # pemilih model
    "model_picker": '[aria-label*="model" i], button:has-text("Veo"), button:has-text("Nano")',
    # prompt + generate
    "prompt_box": 'textarea[placeholder*="prompt" i], textarea[aria-label*="prompt" i], div[contenteditable="true"]',
    "generate_button": 'button:has-text("Generate"), button[aria-label*="Generate" i]',
    # upload ingredient / frame (input file tersembunyi)
    "file_input": 'input[type="file"]',
    # hasil: tombol download di kartu output
    "output_card": '[data-testid*="output" i], div:has(> button[aria-label*="Download" i])',
    "download_button": 'button[aria-label*="Download" i], a[download]',
    # indikator masih generating
    "generating": ':text("Generating"), :text("In queue"), [aria-busy="true"]',
}

MODEL_ALIASES = {
    "nano banana 2": ["Nano Banana 2", "nano-banana-2", "Nano Banana"],
    "omni flash": ["Omni Flash", "omni-flash"],
}


def _need_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        die("paket 'playwright' belum diinstall.\n"
            "  pip install playwright && playwright install chromium")
    from playwright.sync_api import sync_playwright
    return sync_playwright


def is_authed() -> bool:
    """True bila user sudah pernah login via --auth."""
    return AUTH_MARKER.exists()


def auth_interactive() -> None:
    """Buka Flow di profil persistent; user login manual; tutup bila selesai."""
    sync_playwright = _need_playwright()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"membuka Flow (profil: {PROFILE_DIR}) — login Google di jendela itu")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False,
            args=["--disable-dev-shm-usage", "--disable-gpu",
                  "--no-first-run", "--no-default-browser-check"],
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
        print("\n== LOGIN MANUAL ==")
        print("1. Login akun Google di jendela Chromium yang terbuka")
        print("2. Pastikan halaman Flow kebuka (bukan halaman login)")
        print("3. Tutup jendela browser-nya kalau sudah selesai\n")
        try:
            while ctx.pages:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        ctx.close()
    AUTH_MARKER.touch()
    log("✔ sesi tersimpan. Pipeline siap jalan.")


def _launch(headed: bool):
    sync_playwright = _need_playwright()
    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE_DIR), headless=not headed,
        args=["--disable-dev-shm-usage", "--disable-gpu",
              "--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1366, "height": 900},
        accept_downloads=True,
    )
    return p, ctx


def _pick_model(page, model: str) -> None:
    """Pilih model di dropdown Flow (best-effort, beberapa strategi)."""
    names = MODEL_ALIASES.get(model.strip().lower(), [model])
    try:
        page.click(SELECTORS["model_picker"], timeout=8000)
    except Exception:
        log("model picker tidak ketemu via selector utama, coba text match")
    for name in names:
        try:
            page.get_by_text(name, exact=False).first.click(timeout=5000)
            log(f"model terpilih: {name}")
            return
        except Exception:
            continue
    log(f"WARNING: model '{model}' tidak ketemu di dropdown — lanjut pakai default")


def _upload_ingredient(page, image_path: str) -> None:
    """Upload 1 gambar sebagai ingredient/reference."""
    page.set_input_files(SELECTORS["file_input"], image_path)
    page.wait_for_timeout(2500)
    log(f"ingredient ter-upload: {Path(image_path).name}")


def _fill_prompt(page, prompt: str) -> None:
    box = page.locator(SELECTORS["prompt_box"]).first
    box.click(timeout=10000)
    box.fill("")
    # ketik pelan biar event React-nya ke-trigger
    box.press_sequentially(prompt, delay=8)
    page.wait_for_timeout(800)


def _click_generate_and_wait(page, timeout_ms: int) -> None:
    page.locator(SELECTORS["generate_button"]).first.click(timeout=15000)
    log("generate diklik, menunggu selesai ...")
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        busy = page.locator(SELECTORS["generating"]).count()
        if busy == 0:
            page.wait_for_timeout(3000)  # jeda tambahan biar render settle
            if page.locator(SELECTORS["generating"]).count() == 0:
                return
        time.sleep(5)
    die("timeout menunggu hasil generate — coba --headed untuk lihat UI-nya")


def _download_result(page, out: Path, kind: str) -> Path:
    """Klik download di kartu output terbaru."""
    cards = page.locator(SELECTORS["output_card"])
    target = cards.first
    btn = target.locator(SELECTORS["download_button"]).first
    with page.expect_download(timeout=120000) as dl_info:
        btn.click(timeout=15000)
    dl = dl_info.value
    out.parent.mkdir(parents=True, exist_ok=True)
    dl.save_as(str(out))
    log(f"hasil tersimpan: {out} ({out.stat().st_size // 1024} KB)")
    return out


# ---------------------------------------------------------------------------
# Interface publik (sama persis dengan gflow_shim lama)
# ---------------------------------------------------------------------------
def character_exists(name: str) -> bool:
    if is_dry_run():
        st = _dry_state()
        return name in st.get("characters", [])
    return (REF_DIR / f"{name}.png").exists()


def character_ensure(name: str, image: str, prompt: str,
                     headed: bool = False, project: str = "") -> bool:
    """Simpan gambar referensi produk (dipakai sebagai ingredient tiap generate).

    Di UI Flow tidak ada konsep 'character' via CLI — padanannya adalah
    ingredient/reference image yang di-upload ulang tiap generate. Fungsi ini
    memastikan file referensinya ada dan konsisten.
    """
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
    # normalisasi ke PNG via Pillow bila ada, else copy mentah
    dest = REF_DIR / f"{name}.png"
    try:
        from PIL import Image
        Image.open(image).convert("RGB").save(dest)
    except Exception:
        shutil.copy(image, dest)
    log(f"referensi tersimpan: {dest}")
    return True


def _reference_for(character: str) -> str:
    if not character:
        return ""
    p = REF_DIR / f"{character}.png"
    if not p.exists():
        die(f"referensi '{character}' belum ada — jalankan tahap hd dulu")
    return str(p)


def image_generate(job_id: str, prompt: str, out_png: str,
                   model: str = "Nano Banana 2", ratio: str = "9:16",
                   character: str = "", headed: bool = False,
                   project: str = "", timeout: int = 900) -> Path:
    """Generate 1 gambar via Flow (Nano Banana 2). Return path output."""
    out = Path(out_png)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] flow image --id {job_id} --model '{model}'")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_png(out)

    _require_auth()
    ref = _reference_for(character)
    p, ctx = _launch(headed)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _pick_model(page, model)
        if ref:
            _upload_ingredient(page, ref)
        _fill_prompt(page, prompt)
        _click_generate_and_wait(page, timeout * 1000)
        return _download_result(page, out, "image")
    finally:
        ctx.close()
        p.stop()


def video_generate(job_id: str, prompt: str, out_mp4: str,
                   model: str = "Omni Flash", ratio: str = "9:16",
                   duration: int = 10, start_frame: str = "",
                   end_frame: str = "", character: str = "",
                   headed: bool = False, project: str = "",
                   timeout: int = 1800) -> Path:
    """Generate 1 video via Flow (Omni Flash, frames mode bila start_frame diisi)."""
    out = Path(out_mp4)
    if out.exists():
        log(f"{out.name} sudah ada, skip")
        return out
    if is_dry_run():
        log(f"[dry-run] flow video --id {job_id} --model '{model}' "
            f"--duration {duration}")
        out.parent.mkdir(parents=True, exist_ok=True)
        return placeholder_mp4(out, duration=duration)

    _require_auth()
    p, ctx = _launch(headed)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        # mode frames-to-video
        try:
            page.locator(SELECTORS["tab_frames_to_video"]).first.click(timeout=8000)
        except Exception:
            log("tab Frames to video tidak ketemu — lanjut di mode aktif")
        _pick_model(page, model)
        for frame in (start_frame, end_frame):
            if frame:
                _upload_ingredient(page, frame)
        ref = _reference_for(character)
        if ref:
            _upload_ingredient(page, ref)
        _fill_prompt(page, prompt)
        _click_generate_and_wait(page, timeout * 1000)
        return _download_result(page, out, "video")
    finally:
        ctx.close()
        p.stop()


# ---------------------------------------------------------------------------
# helpers internal
# ---------------------------------------------------------------------------
_DRY_STATE = ROOT / ".dryrun_flow.json"


def _dry_state(data: dict | None = None) -> dict:
    if data is not None:
        _DRY_STATE.write_text(json.dumps(data))
        return data
    if _DRY_STATE.exists():
        return json.loads(_DRY_STATE.read_text())
    return {}


def _require_auth() -> None:
    if not is_authed():
        die("belum login Flow.\n"
            "  Jalankan sekali:  python3 pipeline.py --auth\n"
            "  (browser kebuka — login Google manual, lalu tutup)")
