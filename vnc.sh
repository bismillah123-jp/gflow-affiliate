#!/bin/bash
# vnc.sh — VNC sementara di server headless + link publik OTOMATIS.
# Sekali 'start': VNC nyala, noVNC nyala, Cloudflare Quick Tunnel bikin
# domain publik acak (https://xxx.trycloudflare.com) — tanpa akun,
# tanpa setting dashboard apa pun. Buka link di HP → login Google Flow.
#
#   ./vnc.sh start    # nyalakan semua, tampilkan link jadi
#   ./vnc.sh stop     # matikan semuanya (lakukan setelah login selesai)
#   ./vnc.sh status   # cek status
set -euo pipefail

DISPLAY_NUM="${VNC_DISPLAY:-99}"
VNC_PORT=$((5900 + DISPLAY_NUM))
WEB_PORT="${VNC_WEB_PORT:-6080}"
NOVNC_DIR="$HOME/.local/share/novnc"
NOVNC_VER="v1.5.0"
QUICK_LOG="/tmp/cloudflared-quick.log"
export PATH="$HOME/.local/bin:$PATH"

need_pkg() { dpkg -s "$1" >/dev/null 2>&1 || echo "$1"; }

ensure_cloudflared() {
  command -v cloudflared >/dev/null 2>&1 && return 0
  echo "== download cloudflared (sekali aja) =="
  mkdir -p "$HOME/.local/bin"
  curl -sL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" \
    -o "$HOME/.local/bin/cloudflared"
  chmod +x "$HOME/.local/bin/cloudflared"
}

install_deps() {
  local missing=()
  for p in tigervnc-standalone-server openbox xterm curl; do
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
    echo "== download noVNC $NOVNC_VER (sekali aja) =="
    mkdir -p "$NOVNC_DIR"
    curl -sL "https://github.com/novnc/noVNC/archive/refs/tags/$NOVNC_VER.tar.gz" \
      | tar xz -C "$NOVNC_DIR" --strip-components=1
  fi
  ensure_cloudflared
}

vnc_running()   { pgrep -f "Xtigervnc.*:$DISPLAY_NUM" >/dev/null 2>&1; }
web_running()   { pgrep -f "websockify.*$WEB_PORT" >/dev/null 2>&1; }
quick_running() { pgrep -f "cloudflared tunnel --url" >/dev/null 2>&1; }

quick_url() {
  grep -oE "https://[A-Za-z0-9.-]+\.trycloudflare\.com" "$QUICK_LOG" 2>/dev/null | head -1
}

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
    vncserver ":$DISPLAY_NUM" -localhost yes -geometry 1280x800 -depth 24 >/dev/null
  }
  web_running || {
    echo "== start noVNC di port $WEB_PORT =="
    nohup python3 -m websockify --web "$NOVNC_DIR" \
      "127.0.0.1:$WEB_PORT" "127.0.0.1:$VNC_PORT" >/tmp/novnc.log 2>&1 &
    sleep 1
  }
  if ! quick_running; then
    echo "== bikin link publik otomatis (quick tunnel) =="
    : > "$QUICK_LOG"
    nohup cloudflared tunnel --url "http://127.0.0.1:$WEB_PORT" \
      >>"$QUICK_LOG" 2>&1 &
    for _ in $(seq 1 40); do
      [ -n "$(quick_url)" ] && break
      sleep 1
    done
  fi

  URL="$(quick_url)"
  PUB_OK=0
  if [ -n "$URL" ]; then
    echo "== verifikasi link publik =="
    for _ in $(seq 1 6); do
      if curl -s --max-time 15 "$URL/vnc.html" 2>/dev/null | grep -q "noVNC"; then
        PUB_OK=1; break
      fi
      sleep 5
    done
  fi
  if [ "$PUB_OK" = "0" ]; then
    # tunnel ke-block di jaringan ini (mis. sandbox tanpa UDP/egress bebas)
    quick_running && pkill -f "cloudflared tunnel --url" || true
    URL=""
  fi

  if [ -n "$URL" ]; then
    LINK_BLOCK="Buka di HP/laptop (tanpa setting apa pun):

  $URL/vnc.html"
    TUNNEL_NOTE="- Link di atas acak & sementara — cukup untuk sekali login."
  else
    LINK_BLOCK="Link otomatis tidak bisa dibuat di jaringan ini.
Petakan SATU hostname di tunnel Cloudflare-mu ke:
    http://127.0.0.1:$WEB_PORT
lalu buka:  https://<hostname-pilihanmu>/vnc.html"
    TUNNEL_NOTE="- (Otomatis gagal karena jaringan ini memblokir tunnel keluar;
  di VPS normal link otomatis langsung jadi.)"
  fi

  cat <<EOF

================ VNC SIAP ================
$LINK_BLOCK

Login dengan password VNC yang tadi dibuat, lalu di dalam VNC:
  1. buka Terminal (sudah terbuka otomatis)
  2. cd ~/workspace/gflow-affiliate   (atau folder repo ini)
  3. ./login.sh                        # login Google di Chrome yang muncul

Setelah login sukses:  ./vnc.sh stop

CATATAN:
$TUNNEL_NOTE
  (Kadang Cloudflare menampilkan halaman verifikasi sekali klik
  sebelum masuk — itu normal, klik lanjutkan.)
- VNC + tunnel hanya jalan saat kamu butuh; matikan setelah selesai.
==========================================
EOF
}

do_stop() {
  quick_running && pkill -f "cloudflared tunnel --url" || true
  web_running && pkill -f "websockify.*$WEB_PORT" || true
  vnc_running && vncserver -kill ":$DISPLAY_NUM" >/dev/null 2>&1 || true
  echo "VNC + tunnel dimatikan."
}

do_status() {
  vnc_running && echo "VNC :$DISPLAY_NUM : JALAN" || echo "VNC :$DISPLAY_NUM : mati"
  web_running && echo "noVNC port $WEB_PORT : JALAN" || echo "noVNC port $WEB_PORT : mati"
  if quick_running; then echo "quick tunnel: JALAN — $(quick_url)/vnc.html"
  else echo "quick tunnel: mati"; fi
}

case "${1:-}" in
  start)  do_start ;;
  stop)   do_stop ;;
  status) do_status ;;
  *) echo "Pakai: ./vnc.sh [start|stop|status]"; exit 1 ;;
esac
