#!/bin/bash
# login.sh — login Google Flow untuk gflow, dibikin semudah mungkin.
#
# Masalah: `gflow auth login` membuka jendela Chrome asli. Di server
# headless (tanpa layar) jendela itu tidak bisa dilihat. Solusinya:
# login SEKALI di komputer yang ada layarnya (laptop/PC), lalu pindahkan
# profil login (.gflow/) ke server pakai script ini.
#
# Pakai:
#   ./login.sh                 # otomatis: langsung login bila ada layar,
#                              #   atau pandu transfer profil bila headless
#   ./login.sh --pack          # di LAPTOP: kemas profil login jadi .tgz
#   ./login.sh --unpack FILE   # di SERVER: pasang profil dari .tgz
#   ./login.sh --check         # cek sesi masih valid (gflow doctor)
set -e
cd "$(dirname "$0")"

PROFILE_DIR=".gflow/profiles/default"

has_display() {
  [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]
}

pack() {
  if [ ! -d "$PROFILE_DIR" ]; then
    echo "Belum ada profil login di $PROFILE_DIR."
    echo "Jalankan './login.sh' dulu di komputer ini untuk login."
    exit 1
  fi
  OUT="gflow-login-$(date +%Y%m%d).tgz"
  tar czf "$OUT" .gflow
  echo ""
  echo "✔ Profil dikemas: $OUT  ($(du -h "$OUT" | cut -f1))"
  echo ""
  echo "Kirim file ini ke server, misal:"
  echo "  scp $OUT user@server:/path/gflow-affiliate/"
  echo "Lalu di server jalankan:"
  echo "  ./login.sh --unpack $OUT"
}

unpack() {
  FILE="$1"
  [ -f "$FILE" ] || { echo "File tidak ketemu: $FILE"; exit 1; }
  tar xzf "$FILE"
  echo "✔ Profil dipasang."
  check
}

check() {
  echo "== cek sesi Flow =="
  if ! command -v gflow >/dev/null; then
    echo "✘ perintah 'gflow' belum diinstall. Jalankan ./setup.sh dulu."
    exit 1
  fi
  if gflow doctor; then
    echo ""
    echo "✔ Sesi valid. Pipeline siap jalan."
  else
    echo ""
    echo "✘ Sesi belum valid. Jalankan ./login.sh untuk login."
    exit 1
  fi
}

direct_login() {
  echo "== login langsung (terdeteksi ada layar) =="
  echo "Jendela Chrome akan muncul — selesaikan login Google di sana."
  echo ""
  gflow auth login
  check
}

guide_headless() {
  cat <<'EOF'
== server ini headless (tanpa layar) ==

gflow butuh login Google di Chrome asli, jadi loginnya dilakukan
SEKALI di komputer yang ada layarnya (laptop/PC), lalu profilnya
dipindah ke sini. Caranya:

  DI LAPTOP/PC (yang ada layar):
    1. git clone repo ini (atau copy foldernya)
    2. ./login.sh            # login di jendela Chrome yang muncul
    3. ./login.sh --pack     # kemas profil -> gflow-login-<tgl>.tgz

  DI SERVER INI:
    4. copy file .tgz ke folder repo ini (scp / upload)
    5. ./login.sh --unpack gflow-login-<tgl>.tgz

  Selesai — profil login pindah, tidak perlu login ulang di server.
  (Profil = folder .gflow/, isinya cookie sesi; aman selama di tanganmu.)

Alternatif: bila laptop bisa SSH dengan X-forwarding:
    ssh -X user@server, lalu ./login.sh   # jendela Chrome diteruskan ke laptop
EOF
}

case "${1:-}" in
  --pack)   pack ;;
  --unpack) unpack "$2" ;;
  --check)  check ;;
  "")
    if has_display; then
      direct_login
    else
      guide_headless
    fi
    ;;
  *) echo "Pakai: ./login.sh [--pack|--unpack FILE|--check]"; exit 1 ;;
esac
