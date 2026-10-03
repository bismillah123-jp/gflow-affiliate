#!/bin/bash
# login.sh — login Google Flow, pilih cara paling gampang buatmu.
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

PROFILE_DIR=".gflow/profiles/default"

has_display() { [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; }

check() {
  echo "== cek sesi Flow =="
  if ! command -v gflow >/dev/null; then
    echo "✘ perintah 'gflow' belum diinstall. Jalankan ./setup.sh dulu."
    exit 1
  fi
  if gflow doctor; then
    echo ""; echo "✔ Sesi valid. Pipeline siap jalan."
  else
    echo ""; echo "✘ Sesi belum valid. Coba cara login lain: ./login.sh"
    exit 1
  fi
}

GFLOW_PROFILE_DIR=".gflow/profiles/default"
FLOW_URL="https://labs.google/fx/tools/flow"

chrome_pids_for_profile() {
  # trik [.] biar pgrep nggak match command-line-nya sendiri
  pgrep -f "[.]gflow/profiles/default" 2>/dev/null | grep -vx "$$" || true
}

direct_login() {
  echo "== login langsung =="
  # Bersihkan Chrome gflow yang nyangkut dari jalan sebelumnya.
  # Chrome-nya gflow di-spawn detached (imun Ctrl+C); tiap spawn baru
  # di profil yang sama = tab baru numpuk. Ini sumber "tab nyepam".
  local pids
  pids=$(chrome_pids_for_profile)
  if [ -n "$pids" ]; then
    echo "Menutup Chrome gflow lama yang masih nyangkut..."
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 2
    pkill -9 -f "[.]gflow/profiles/default" 2>/dev/null || true
  fi
  rm -f "$GFLOW_PROFILE_DIR/SingletonLock" "$GFLOW_PROFILE_DIR/SingletonCookie" \
        "$GFLOW_PROFILE_DIR/SingletonSocket" "$GFLOW_PROFILE_DIR/DevToolsActivePort"
  mkdir -p "$GFLOW_PROFILE_DIR"

  echo "Membuka SATU jendela Chrome login..."
  # Luncurkan langsung (bukan via `gflow auth login`) supaya bisa pakai
  # flag anti-crash di container/VNC: --disable-dev-shm-usage --disable-gpu.
  # Tetap Chrome biasa tanpa remote-debugging (syarat login Google).
  local chrome_bin
  chrome_bin=$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)
  if [ -z "$chrome_bin" ]; then
    echo "✘ Chrome/Chromium tidak ketemu. Install Google Chrome dulu."
    exit 1
  fi
  "$chrome_bin" --user-data-dir="$PWD/$GFLOW_PROFILE_DIR" \
    --no-first-run --no-default-browser-check \
    --disable-dev-shm-usage --disable-gpu \
    "$FLOW_URL" >/dev/null 2>&1 &
  disown 2>/dev/null || true
  echo ""
  echo "Selesaikan login Google di jendela Chrome tersebut,"
  read -rp "lalu tekan ENTER di sini untuk verifikasi... "
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
  OUT="gflow-login-$(date +%Y%m%d).tgz"
  tar czf "$OUT" .gflow
  echo ""
  echo "✔ Profil dikemas: $OUT ($(du -h "$OUT" | cut -f1))"
  echo "Kirim ke server, lalu di server: ./login.sh --unpack $OUT"
}

unpack() {
  local file="$1"
  [ -f "$file" ] || { echo "File tidak ketemu: $file"; exit 1; }
  tar xzf "$file"
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
    ./login.sh --pack        # -> gflow-login-<tgl>.tgz

  DI SERVER INI:
    copy file .tgz ke folder repo ini, lalu:
    ./login.sh --unpack gflow-login-<tgl>.tgz
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
