#!/bin/bash
# setup.sh — siapkan pipeline video affiliate di Linux manapun (sekali aja).
# Membuat venv .venv, install dependensi Python + browser Playwright.
# TANPA gflow-cli: Flow dikendalikan langsung via Playwright.
set -e
cd "$(dirname "$0")"

echo "== cek python3 =="; python3 --version
echo "== cek ffmpeg =="
command -v ffmpeg >/dev/null || { echo "Install ffmpeg dulu:"; echo "  Ubuntu/Debian: sudo apt install ffmpeg"; echo "  Fedora: sudo dnf install ffmpeg"; echo "  macOS: brew install ffmpeg"; exit 1; }

echo "== buat venv .venv =="
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
echo "== install dependensi python =="
.venv/bin/pip install -r requirements.txt

echo "== install browser playwright (chromium) =="
.venv/bin/playwright install chromium --with-deps 2>/dev/null || .venv/bin/playwright install chromium

echo ""
echo "SELESAI ✔"
echo ""
echo "Langkah terakhir (sekali aja per mesin):"
echo "  .venv/bin/python pipeline.py --auth   # login Google Flow manual sekali"
echo "  ./login.sh                            # alternatif: login dipandu (menu/VNC)"
echo ""
echo "Di server tanpa layar, ./login.sh akan memandu cara pindahan profil"
echo "login dari laptop (./login.sh --pack di laptop -> --unpack di server)."
echo ""
echo "Lalu jalan:  .venv/bin/python pipeline.py --auto --dry-run   # uji tanpa kuota"
echo "             .venv/bin/python pipeline.py --auto             # produksi"
