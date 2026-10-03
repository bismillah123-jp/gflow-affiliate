#!/bin/bash
# login.sh — login Google Flow, pilih cara paling gampang buatmu.
# Memakai `gflow` CLI dari https://github.com/ffroliva/gflow-cli
# (pip install gflow-cli). Sesi/profil di ~/.local/share/gflow-cli
# (atau $GFLOW_CLI_HOME bila di-set).
#
#   ./login.sh                        # menu interaktif
#   ./login.sh --direct               # langsung: gflow auth login
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

PROFILE_DIR="${GFLOW_CLI_HOME:-$HOME/.local/share/gflow-cli}"
AUTH_HINT="python3 pipeline.py --auth   # = gflow auth login"

has_display() { [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; }

need_gflow() {
  command -v gflow >/dev/null || {
    echo "✘ perintah 'gflow' belum diinstall."
    echo "  Install: pip install gflow-cli  (atau ./setup.sh)"
    exit 1
  }
}

check() {
  echo "== cek sesi Flow =="
  need_gflow
  if gflow doctor >/dev/null 2>&1; then
    echo ""; echo "✔ Sesi valid. Pipeline siap jalan."
  else
    echo ""; echo "✘ Sesi belum valid."
    gflow doctor 2>&1 | tail -5
    echo "Coba: $AUTH_HINT"
    exit 1
  fi
}

FLOW_URL="https://labs.google/fx/tools/flow"

direct_login() {
  echo "== login langsung =="
  need_gflow
  echo "Membuka browser login (gflow auth login)..."
  echo "Selesaikan login Google di jendela yang muncul."
  echo ""
  gflow auth login
  echo ""
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
  tar czf "$OUT" -C "$(dirname "$PROFILE_DIR")" "$(basename "$PROFILE_DIR")"
  echo ""
  echo "✔ Profil dikemas: $OUT ($(du -h "$OUT" | cut -f1))"
  echo "Kirim ke server, lalu di server: ./login.sh --unpack $OUT"
}

unpack() {
  local file="$1"
  [ -f "$file" ] || { echo "File tidak ketemu: $file"; exit 1; }
  mkdir -p "$(dirname "$PROFILE_DIR")"
  tar xzf "$file" -C "$(dirname "$PROFILE_DIR")"
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
