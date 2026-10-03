#!/bin/bash
# vnc.sh — VNC sementara di server headless, diakses lewat link Cloudflare.
# Dipakai untuk login Google Flow: Chrome dibuka di dalam sesi VNC,
# user login manual lewat browser HP/laptop.
#
#   ./vnc.sh start    # pasang + jalankan VNC + noVNC, tampilkan link
#   ./vnc.sh stop     # matikan semuanya (lakukan setelah login selesai)
#   ./vnc.sh status   # cek status
#
# Link tampil setelah 'start'. Agar link publik jalan, tambahkan SATU KALI
# di dashboard Cloudflare (Zero Trust → Networks → Tunnels → tunnel kamu
# → Public Hostname → Add):
#   Subdomain : vnc        (bisa diganti via VNC_HOSTNAME)
#   Domain    : sirihsan.my.id
#   Service   : http://127.0.0.1:6080
set -euo pipefail

DISPLAY_NUM="${VNC_DISPLAY:-99}"
VNC_PORT=$((5900 + DISPLAY_NUM))
WEB_PORT="${VNC_WEB_PORT:-6080}"
NOVNC_DIR="$HOME/.local/share/novnc"
NOVNC_VER="v1.5.0"
# Link publik ikut settingan tunnel-mu sendiri (jangan dipatok di sini).
# Kalau mau script langsung menampilkan link jadi, isi VNC_HOSTNAME, misal:
#   VNC_HOSTNAME=vnc.contoh.id ./vnc.sh start
VNC_HOSTNAME="${VNC_HOSTNAME:-}"

need_pkg() { dpkg -s "$1" >/dev/null 2>&1 || echo "$1"; }

install_deps() {
  local missing=()
  for p in tigervnc-standalone-server openbox xterm; do
    n=$(need_pkg "$p"); [ -n "$n" ] && missing+=("$n")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "== install: ${missing[*]} =="
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${missing[@]}"
  fi
  python3 -c "import websockify" 2>/dev/null || {
    echo "== install websockify (pip --user) =="
    pip install --quiet --user websockify
  }
  if [ ! -f "$NOVNC_DIR/vnc.html" ]; then
    echo "== download noVNC $NOVNC_VER =="
    mkdir -p "$NOVNC_DIR"
    curl -sL "https://github.com/novnc/noVNC/archive/refs/tags/$NOVNC_VER.tar.gz" \
      | tar xz -C "$NOVNC_DIR" --strip-components=1
  fi
}

vnc_running()  { pgrep -f "Xtigervnc.*:$DISPLAY_NUM" >/dev/null 2>&1; }
web_running()  { pgrep -f "websockify.*$WEB_PORT" >/dev/null 2>&1; }

do_start() {
  install_deps

  if [ ! -f "$HOME/.vnc/passwd" ]; then
    echo "== set password VNC (dipakai untuk buka link) =="
    mkdir -p "$HOME/.vnc"
    vncpasswd
  fi

  mkdir -p "$HOME/.vnc"
  cat > "$HOME/.vnc/xstartup" <<'EOF'
#!/bin/sh
openbox-session &
xterm -geometry 100x30+10+10 &
EOF
  chmod +x "$HOME/.vnc/xstartup"

  vnc_running || {
    echo "== start VNC display :$DISPLAY_NUM =="
    vncserver ":$DISPLAY_NUM" -localhost yes -geometry 1280x800 -depth 24 \
      >/dev/null
  }
  web_running || {
    echo "== start noVNC di port $WEB_PORT =="
    nohup python3 -m websockify --web "$NOVNC_DIR" \
      "127.0.0.1:$WEB_PORT" "127.0.0.1:$VNC_PORT" \
      >/tmp/novnc.log 2>&1 &
    sleep 1
  }

  if [ -n "$VNC_HOSTNAME" ]; then
    PUBLIC_LINK="  https://$VNC_HOSTNAME/vnc.html"
  else
    PUBLIC_LINK="  https://<hostname-pilihanmu>/vnc.html   (isi VNC_HOSTNAME kalau mau tampil otomatis)"
  fi

  cat <<EOF

================ VNC SIAP ================
Buka di HP/laptop:

$PUBLIC_LINK

(Lokal, kalau kamu SSH dengan port-forward: http://127.0.0.1:$WEB_PORT/vnc.html)

Login dengan password VNC yang tadi dibuat, lalu di dalam VNC:
  1. buka Terminal (sudah terbuka otomatis)
  2. cd ~/workspace/gflow-affiliate   (atau folder repo ini)
  3. ./login.sh                        # login Google di Chrome yang muncul

Setelah login sukses:  ./vnc.sh stop

CATATAN:
- Petakan SATU hostname di tunnel Cloudflare-mu ke:
    http://127.0.0.1:$WEB_PORT
  (dashboard Cloudflare → Zero Trust → Tunnels → Public Hostname → Add)
- VNC hanya jalan saat kamu butuh; jangan dibiarkan nyala.
- (Opsional, lebih aman) pasang Cloudflare Access di depan hostname itu.
==========================================
EOF
}

do_stop() {
  web_running && pkill -f "websockify.*$WEB_PORT" || true
  vnc_running && vncserver -kill ":$DISPLAY_NUM" >/dev/null 2>&1 || true
  echo "VNC dimatikan."
}

do_status() {
  vnc_running && echo "VNC :$DISPLAY_NUM : JALAN" || echo "VNC :$DISPLAY_NUM : mati"
  web_running && echo "noVNC port $WEB_PORT : JALAN" || echo "noVNC port $WEB_PORT : mati"
}

case "${1:-}" in
  start)  do_start ;;
  stop)   do_stop ;;
  status) do_status ;;
  *) echo "Pakai: ./vnc.sh [start|stop|status]"; exit 1 ;;
esac
