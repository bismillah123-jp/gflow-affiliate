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

direct_login() {
  echo "== login langsung =="
  echo "Jendela Chrome akan muncul — selesaikan login Google di sana."
  gflow auth login
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
