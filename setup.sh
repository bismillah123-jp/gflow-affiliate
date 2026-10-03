#!/bin/bash
# setup.sh — siapkan pipeline video affiliate di Linux manapun (sekali aja).
# Membuat venv .venv, install dependensi Python, install gflow-cli global.
set -e
cd "$(dirname "$0")"

echo "== cek python3 =="; python3 --version
echo "== cek node =="
command -v node >/dev/null || { echo "Install Node.js 20+: https://nodejs.org"; exit 1; }
node --version
echo "== cek ffmpeg =="
command -v ffmpeg >/dev/null || { echo "Install ffmpeg dulu:"; echo "  Ubuntu/Debian: sudo apt install ffmpeg"; echo "  Fedora: sudo dnf install ffmpeg"; echo "  macOS: brew install ffmpeg"; exit 1; }
echo "== cek Google Chrome =="
if command -v google-chrome >/dev/null || command -v chromium >/dev/null || command -v chromium-browser >/dev/null; then
  echo "Chrome OK"
else
  echo "Install Google Chrome: https://www.google.com/chrome/ (dibutuhkan gflow)"
  exit 1
fi

echo "== buat venv .venv =="
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
echo "== install dependensi python =="
.venv/bin/pip install -r requirements.txt

echo "== install gflow-cli =="
if command -v gflow >/dev/null; then
  echo "gflow sudah ada: $(gflow --version 2>/dev/null || echo ok)"
else
  npm install -g @swissmarley/gflow-cli
fi

echo ""
echo "SELESAI ✔"
echo ""
echo "Langkah terakhir (interaktif, sekali aja per mesin):"
echo "  1. gflow auth login        # login Google di Chrome yang muncul"
echo "  2. gflow doctor           # verifikasi sesi Flow"
echo "Lalu jalan:  .venv/bin/python pipeline.py --auto --dry-run   # uji tanpa kuota"
echo "             .venv/bin/python pipeline.py --auto             # produksi"
