#!/bin/bash
# run_tests.sh — jalankan semua test (cuma butuh python3 + ffmpeg).
set -e
cd "$(dirname "$0")/.."
echo "== test prompts =="
python3 -m unittest tests.test_prompts -v 2>&1 | tail -5
echo ""
echo "== test tts (edge-tts dipalsukan) =="
python3 -m unittest tests.test_tts -v 2>&1 | tail -5
echo ""
echo "== test dry-run end-to-end =="
python3 -m unittest tests.test_dryrun -v 2>&1 | tail -5
echo ""
echo "SEMUA TEST SELESAI"
