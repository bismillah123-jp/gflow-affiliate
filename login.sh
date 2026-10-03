#!/bin/bash
# login.sh — login Google Flow, pilih cara paling gampang buatmu.
# TANPA gflow-cli: sesi disimpan di profil browser ~/.config/affiliate-flow
# (dipakai langsung oleh pipeline.py via Playwright).
#
#   ./login.sh                        # menu interaktif
#   ./login.sh --direct               # langsung: butuh layar di mesin ini
#   ./login.sh --import-cookies F     # dari export Cookie-Editor (JSON/txt)
#   ./login.sh --vnc                  # VNC + link Cloudflare, login di browser HP
#   ./login.sh --pack                 # kemas profil (di laptop yg ada layar)
#   ./login.sh --unpack FILE          # pasang profil (di server)
#   ./login.sh --check                # cek sesi masih valid
set -e
cd "$(dirname "$0")"

if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
  echo "✘ Jangan pakai sudo untuk script ini — jalankan sebagai user biasa."
  exit 1
fi

PROFILE_DIR="$HOME/.config/affiliate-flow"
AUTH_MARKER="$PROFILE_DIR/.auth_ok"

has_display() { [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; }

check() {
  echo "== cek sesi Flow =="
  if [ -f "$AUTH_MARKER" ]; then
    echo ""; echo "✔ Sesi tersimpan di $PROFILE_DIR. Pipeline siap jalan."
  else
    echo ""; echo "✘ Belum login. Jalankan: python3 pipeline.py --auth"
    echo "   (atau ./login.sh untuk cara lain)"
    exit 1
  fi
}

FLOW_PROFILE_DIR="$HOME/.config/affiliate-flow"
FLOW_URL="https://labs.google/fx/tools/flow"

chrome_pids_for_profile() {
  # trik [.] biar pgrep nggak match command-line-nya sendiri
  pgrep -f "[.]config/affiliate-flow" 2>/dev/null | grep -vx "$$" || true
}

direct_login() {
  echo "== login langsung =="
  # Bersihkan Chrome profil Flow yang nyangkut dari jalan sebelumnya.
  local pids
  pids=$(chrome_pids_for_profile)
  if [ -n "$pids" ]; then
    echo "Menutup Chrome profil Flow yang masih nyangkut..."
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 2
    pkill -9 -f "[.]config/affiliate-flow" 2>/dev/null || true
  fi
  rm -f "$FLOW_PROFILE_DIR/SingletonLock" "$FLOW_PROFILE_DIR/SingletonCookie" \
        "$FLOW_PROFILE_DIR/SingletonSocket" "$FLOW_PROFILE_DIR/DevToolsActivePort"
  mkdir -p "$FLOW_PROFILE_DIR"

  echo "Membuka SATU jendela Chrome login..."
  # Luncurkan langsung supaya bisa pakai flag anti-crash di container/VNC.
  local chrome_bin
  chrome_bin=$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)
  if [ -z "$chrome_bin" ]; then
    echo "✘ Chrome/Chromium tidak ketemu. Install Google Chrome dulu."
    exit 1
  fi
  "$chrome_bin" --user-data-dir="$FLOW_PROFILE_DIR" \
    --no-first-run --no-default-browser-check \
    --disable-dev-shm-usage --disable-gpu \
    "$FLOW_URL" >/dev/null 2>&1 &
  disown 2>/dev/null || true
  echo ""
  echo "Selesaikan login Google di jendela Chrome tersebut,"
  read -rp "lalu tekan ENTER di sini ... "
  touch "$AUTH_MARKER"
  check
}

import_cookies() {
  local file="$1" extra="${2:-}"
  [ -f "$file" ] || { echo "File tidak ketemu: $file"; exit 1; }
  cat <<'EOF'
== import cookies ==
Cara dapat file-nya (sekali aja, di Chrome HP/laptop yang sudah login Google):
  1. Install ekstensi "Cookie-Editor"
  2. Buka accounts.google.com → klik ikon Cookie-Editor → Export (format JSON)
  3. Simpan sebagai cookies.json, kirim file-nya ke folder repo ini
EOF
  python3 lib/cookies_import.py "$file" $extra
  echo ""
  echo "Profil terisi cookie. Verifikasi sesi..."
  check
}

vnc_login() {
  echo "== login via VNC =="
  bash -- ./vnc.sh start
}

pack() {
  if [ ! -d "$PROFILE_DIR" ]; then
    echo "Belum ada profil login di $PROFILE_DIR."
    echo "Jalankan './login.sh --direct' dulu di komputer ini untuk login."
    exit 1
  fi
  OUT="flow-login-$(date +%Y%m%d).tgz"
  tar czf "$OUT" -C "$HOME" .config/affiliate-flow
  echo ""
  echo "✔ Profil dikemas: $OUT ($(du -h "$OUT" | cut -f1))"
  echo "Kirim ke server, lalu di server: ./login.sh --unpack $OUT"
}

unpack() {
  local file="$1"
  [ -f "$file" ] || { echo "File tidak ketemu: $file"; exit 1; }
  tar xzf "$file" -C "$HOME"
  echo "✔ Profil dipasang."
  check
}

menu() {
  if has_display; then direct_login; return; fi
  cat <<'EOF'
== pilih cara login Google Flow ==

  1) Import cookies (Cookie-Editor) — paling cepat, tanpa layar
  2) VNC, link publik otomatis      — tanpa setting, login di browser HP
  3) Pindah profil dari laptop        — login di laptop, kirim .tgz ke sini

EOF
  read -rp "Pilih [1/2/3]: " c
  case "$c" in
    1) read -rp "Path file cookies.json: " f
       read -rp "Impor semua domain? (default cuma *google*) [y/N]: " a
       [ "$a" = "y" ] || [ "$a" = "Y" ] && extra="--all-domains" || extra=""
       import_cookies "$f" "$extra" ;;
    2) vnc_login ;;
    3) cat <<'EOF'

  DI LAPTOP (ada layar):
    ./login.sh --direct     # login di Chrome yang muncul
    ./login.sh --pack        # -> flow-login-<tgl>.tgz

  DI SERVER INI:
    copy file .tgz ke folder repo ini, lalu:
    ./login.sh --unpack flow-login-<tgl>.tgz
EOF
       ;;
    *) echo "Batal." ;;
  esac
}

case "${1:-}" in
  --direct)          direct_login ;;
  --import-cookies)  import_cookies "$2" "${3:-}" ;;
  --vnc)             vnc_login ;;
  --pack)            pack ;;
  --unpack)          unpack "$2" ;;
  --check)           check ;;
  "")                menu ;;
  *) echo "Pakai: ./login.sh [--direct|--import-cookies FILE|--vnc|--pack|--unpack FILE|--check]"; exit 1 ;;
esac
