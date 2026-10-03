#!/usr/bin/env bash
# pipeline.sh — auto-generate video affiliate TikTok/Shopee via Google Flow.
#
#   pipeline.sh --product <slug> [--from STAGE] [--to STAGE] [--force] [--auto]
#
# Tahapan:
#   research    riset/pilih produk          (lib/research.py)
#   images      cari+download gambar katalog (lib/fetch_images.py)
#   storyboard  susun storyboard POV-tangan (lib/storyboard.py)
#   keyframes   HD keyframe per scene via Nano Banana 2 (lib/hd_keyframes.py)
#   video       generate klip per scene via Omni Flash (lib/gen_video.py)
#   finish      gabung 10 dtk + teks ID + verifikasi (lib/finish.py)
#
# Contoh:
#   pipeline.sh --auto                        # pilih produk skor tertinggi, jalan semua
#   pipeline.sh --product pembersih-noda       # full pipeline satu produk
#   pipeline.sh --product pembersih-noda --from video   # lanjutkan dari tahap video
#
# Butuh: gflow login Google Flow (sekali). Cek: gflow doctor
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
LIB="$BASE/lib"
# Chrome wrapper (tambah --no-sandbox, jalan sebagai root)
export GFLOW_CHROME_PATH="${GFLOW_CHROME_PATH:-/home/hatch/.local/bin/chrome-nosandbox}"

PRODUCT=""; FROM="research"; TO="finish"; FORCE=""; AUTO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --product) PRODUCT="$2"; shift 2;;
    --from) FROM="$2"; shift 2;;
    --to) TO="$2"; shift 2;;
    --force) FORCE="--force"; shift;;
    --auto) AUTO="--auto"; shift;;
    *) echo "opsi tidak dikenal: $1"; exit 1;;
  esac
done

STAGES="research images storyboard keyframes video finish"
in_range=0
for s in $STAGES; do
  [ "$s" = "$FROM" ] && in_range=1
  if [ "$in_range" = 1 ]; then
    case "$s" in
      research)
        if [ -n "$AUTO" ]; then python3 "$LIB/research.py" --auto
        elif [ -n "$PRODUCT" ]; then python3 "$LIB/research.py" --pick "$PRODUCT"
        else python3 "$LIB/research.py" --list; echo "pilih: pipeline.sh --product <slug>"; exit 0; fi
        [ -z "$PRODUCT" ] && PRODUCT=$(ls -t "$BASE/products" | head -1)
        ;;
      images)     python3 "$LIB/fetch_images.py" --product "$PRODUCT" ;;
      storyboard) python3 "$LIB/storyboard.py" --product "$PRODUCT" ;;
      keyframes)  python3 "$LIB/hd_keyframes.py" --product "$PRODUCT" $FORCE ;;
      video)      python3 "$LIB/gen_video.py" --product "$PRODUCT" $FORCE ;;
      finish)     python3 "$LIB/finish.py" --product "$PRODUCT" $FORCE ;;
    esac
  fi
  [ "$s" = "$TO" ] && break
done

echo "SELESAI: $BASE/products/$PRODUCT/final.mp4"
