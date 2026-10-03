# 🎬 Affiliate Video Pipeline — TikTok/Shopee via Google Flow

Bikin video affiliate vertikal 9:16 (±10 detik, voice-over Bahasa Indonesia)
**otomatis** dari riset produk sampai file final siap upload — pakai
[`gflow-cli`](https://github.com/swissmarley/gflow-cli) (Nano Banana 2 +
Omni Flash), `edge-tts`, dan `ffmpeg`. Jalan di Linux manapun.

```
riset → images → hd → storyboard → video → tts → finish
  1       2       3        4          5       6       7
```

| Tahap | Kerja | Teknologi |
|---|---|---|
| 1. `research` | Riset produk viral / FYP-potential | kurasi `data/trending_id.json`, manual, atau Google Trends |
| 2. `images` | Download gambar katalog produk | DuckDuckGo Images (`ddgs`, tanpa API key) |
| 3. `hd` | HD-kan + perjelas produk, buang background berantakan | Nano Banana 2 via `gflow` |
| 4. `storyboard` | Storyboard **berupa gambar** (3 scene, total 10 dtk) | Nano Banana 2 via `gflow` |
| 5. `video` | Storyboard → video 10 dtk beneran (bukan slideshow) | Omni Flash via `gflow` (frames mode) |
| 6. `tts` | Voice-over Bahasa Indonesia | `edge-tts` neural (tanpa API key) |
| 7. `finish` | Mux video + VO (+teks overlay opsional) | `ffmpeg` |

## ✨ Aturan kualitas (dijaga pipeline)

- **Hanya tangan / POV tangan**, tidak ada wajah — di semua prompt visual.
- **Bahasa Indonesia** untuk voice-over dan teks apa pun di video.
- **Anti-anomali**: `ANOMALY_GUARD` ditempel di setiap prompt
  (tangan anatomis benar — tepat 2 tangan, 5 jari per tangan, tanpa
  anggota tubuh ekstra, tanpa morphing). Dicetak di `lib/prompts.py`
  supaya bisa diaudit/di-tune.
- **Konsistensi produk**: gambar katalog di-upload sekali sebagai gflow
  `character` (`aff-<slug>`), lalu dipakai sebagai referensi di semua
  tahap HD, storyboard, dan video — kemasan/label/warna tidak berubah.
- **Teks di video minimal**: teks overlay TIDAK di-generate AI (rawan
  garbled); default tanpa teks, opsional via `--overlay-text` di tahap
  finish (deterministik via ffmpeg).
- **Voice-over**: naskah ±120–140 karakter (pas 10 detik), otomatis
  dipercepat bila kepanjangan; audio asli video diredam 25% di bawah VO.

## ⚠️ Yang TIDAK bisa 100% otomatis

Jujur dulu biar ekspektasi pas:

1. **Login Google sekali per mesin** — `gflow` mengendalikan Chrome +
   sesi Google Flow milikmu. Jalankan `./login.sh` (otomatis dipandu:
   langsung login bila ada layar, atau pindah profil dari laptop bila
   headless). Setelah itu semuanya bisa `--no-headed` (otomatis).
2. **Kuota Flow** — generate gambar/video memakan kredit Flow; butuh
   akun/paket Flow yang aktif.
3. **Anti-anomali = best-effort** — prompt guard + referensi karakter
   sangat membantu, tapi model generatif tidak memberi garansi.
   **Selalu tonton hasil sebelum publish.**
4. **Riset "FYP"** — tidak ada API publik gratis yang memberi tahu
   produk apa yang akan FYP besok. Pipeline memakai kurasi manual
   (`data/trending_id.json`, update berkala), input manual, atau sinyal
   Google Trends. API resmi TikTok Shop/Shopee butuh kredensial yang
   disetujui — ada titik ekstensi di `lib/research.py`.

## 🚀 Setup (sekali per mesin)

```bash
git clone <repo-ini> && cd gflow-affiliate
./setup.sh            # venv .venv + dependensi + gflow-cli
./login.sh            # login Google Flow (dipandu, sekali aja)
```

## 🔑 Login (sekali per mesin) — pilih yang paling gampang

```bash
./login.sh            # menu: pilih cara login
```

**Opsi 1 — Import cookies (paling cepat, tanpa layar).**
Di Chrome HP/laptop yang sudah login Google: install ekstensi
"Cookie-Editor" → buka `accounts.google.com` → Export (JSON) →
kirim `cookies.json` ke folder repo ini, lalu:
```bash
./login.sh --import-cookies cookies.json
```
Script menulis cookie ke profil gflow dengan enkripsi yang sama
persis seperti Chrome Linux, lalu verifikasi via `gflow doctor`.

**Opsi 2 — VNC via link Cloudflare (login manual di browser HP).**
```bash
./login.sh --vnc
# atau: VNC_HOSTNAME=vnc.domainmu.id ./vnc.sh start   (tampilkan link jadi)
```
Script menampilkan URL yang harus dibuka — hostname publiknya ikut
settingan tunnel Cloudflare-mu sendiri (petakan satu hostname ke
`http://127.0.0.1:6080` di dashboard). Buka link di HP, masukkan
password VNC, buka Terminal di dalam VNC, lalu:
```bash
cd ~/workspace/gflow-affiliate && ./login.sh   # login di Chrome yang muncul
./vnc.sh stop                                    # matikan VNC setelah selesai
```
Jangan biarkan VNC nyala terus.

**Opsi 3 — Pindah profil dari laptop (ada layar).**
```bash
# di LAPTOP:  ./login.sh --direct   # login di Chrome yang muncul
#             ./login.sh --pack      # -> gflow-login-<tgl>.tgz
# di SERVER:  ./login.sh --unpack gflow-login-<tgl>.tgz
```

Cek kapan saja: `./login.sh --check`. Pipeline juga otomatis
`preflight` (`gflow doctor`) sebelum tahap berat jalan.

Butuh: Python 3.10+, Node.js 20+, Google Chrome, ffmpeg, internet.

## ▶️ Pakai

```bash
# Uji end-to-end TANPA kuota/API/browser (wajib lolos sebelum produksi)
.venv/bin/python pipeline.py --auto --dry-run

# Produksi: produk skor viral tertinggi
.venv/bin/python pipeline.py --auto

# Produk spesifik dari daftar kurasi
.venv/bin/python pipeline.py --product pembersih-noda

# Produk bebas (tanpa riset)
.venv/bin/python pipeline.py --manual-name "Sikat Gigi Elektrik Viral"

# Mulai dari tahap tertentu / cuma satu tahap
.venv/bin/python pipeline.py --product X --from storyboard
.venv/bin/python pipeline.py --product X --only tts

# Suara cowok
.venv/bin/python pipeline.py --product X --voice id-ID-ArdiNeural

# Lihat daftar tahap
.venv/bin/python pipeline.py --list-stages
```

Output per produk di `products/<slug>/`:

```
research.json  images/  hd/  storyboard.json  storyboard/  clips/
vo/  final.mp4   ← siap upload ke TikTok/Shopee
```

Tahap yang sudah selesai otomatis di-skip (aman diulang / dilanjut).

## 🔁 Contoh cron harian (1 video/hari)

```cron
0 7 * * * cd /path/gflow-affiliate && .venv/bin/python pipeline.py --auto >> logs/cron.log 2>&1
```

## 🧪 Testing

```bash
./tests/run_tests.sh
# atau: python3 -m unittest discover -s tests -v
```

- `test_prompts` — guard anti-anomali, VO ≤140 char, total storyboard 10 dtk.
- `test_tts` — loop penyesuaian rate dengan `edge-tts` dipalsukan.
- `test_dryrun` — full pipeline `--dry-run`: semua artefak ada,
  `final.mp4` valid (video+audio, durasi ~10 dtk).

## ⚙️ Konfigurasi (env, semua opsional)

| Var | Default | Guna |
|---|---|---|
| `GFLOW_PROJECT` | — | nama Flow project gflow |
| `GFLOW_VIDEO_MODEL` | `Omni Flash` | model video |
| `GFLOW_CHROME_PATH` | — | path Chrome non-standar |
| `AFFILIATE_VOICE` | `id-ID-GadisNeural` | suara VO |
| `AFFILIATE_DRY_RUN` | — | `1` = mode dry-run |
| `https_proxy`/`HTTPS_PROXY` | — | dipakai otomatis oleh `ddgs` & `edge-tts` |

Lihat `config.env.example`.

## 🧠 Cara kerja tiap tahap (detail)

**1. research** — `lib/research.py`. Provider `curated` (default):
`data/trending_id.json` berisi 8 produk + `viral_score`, `why_viral`,
`image_keywords`, `product_visual`. `--auto` pilih skor tertinggi.
`--manual` untuk produk bebas. `--provider trends` = sinyal Google
Trends ID (best-effort).

**2. images** — `lib/fetch_images.py`. Cari via `ddgs` (DuckDuckGo, tanpa
key), download 3 teratas pakai curl + Referer, verifikasi `file(1)`,
simpan manifest.

**3. hd** — `lib/hd_enhance.py`. `gflow character create --image`
katalog → referensi `aff-<slug>`, lalu `gflow image --character`
model Nano Banana 2 dengan prompt HD (produk identik, background bersih).

**4. storyboard** — `lib/storyboard.py`. Susun `storyboard.json`
(override di `data/storyboards/<slug>.json` bila ada, else template
3-scene). Render tiap scene 9:16 via Nano Banana 2 + character.

**5. video** — `lib/gen_video.py`. `gflow video --model "Omni Flash"
--duration 10 --ratio 9:16 --start-frame scene01.png --end-frame
scene03.png --character …` — satu klip 10 detik kontinu, audio ambient
saja (tanpa dialog; VO ditambah terpisah agar bahasa terjamin).

**6. tts** — `lib/tts.py`. `edge-tts` suara `id-ID-*`, naskah dari
`storyboard.json`. Auto rate-fit (+0/+15/+30%) agar ≤10.2 dtk.

**7. finish** — `lib/finish.py`. ffmpeg: ambient diredam ke 25% +
VO di-mix, opsional `drawtext` overlay, verifikasi stream video+audio.

## 🩺 Troubleshooting

| Gejala | Solusi |
|---|---|
| `gflow: command not found` | `npm install -g @swissmarley/gflow-cli` |
| `Google Flow login is required` | `./login.sh` (atau manual: `gflow auth login` → `gflow doctor`) |
| Tangan/jari aneh di hasil | Perketat `ANOMALY_GUARD` di `lib/prompts.py`; generate ulang scene |
| Produk berubah di video | Pastikan character `aff-<slug>` terbuat (`gflow character list`); pakai gambar katalog yang jelas |
| VO kepanjangan | Sudah auto rate-fit; bila masih, pendekkan `vo_line` di override storyboard |
| `edge-tts` timeout di balik proxy | Set `https_proxy`/`HTTPS_PROXY`; butuh internet langsung ke Microsoft |
| `pytrends` 429 | Normal (rate-limit Google); fallback otomatis ke kurasi |

## 📁 Struktur repo

```
├── pipeline.py          # orkestrator 7 tahap
├── setup.sh             # setup sekali per mesin
├── requirements.txt
├── config.env.example
├── data/
│   ├── trending_id.json # kurasi produk viral
│   └── storyboards/     # override storyboard per produk (opsional)
├── lib/
│   ├── common.py        # util: run, dry-run, placeholder via ffmpeg
│   ├── prompts.py       # SEMUA prompt + ANOMALY_GUARD + naskah VO
│   ├── gflow_shim.py    # pembungkus gflow-cli (+ dry-run)
│   ├── research.py      # tahap 1
│   ├── fetch_images.py  # tahap 2
│   ├── hd_enhance.py    # tahap 3
│   ├── storyboard.py    # tahap 4
│   ├── gen_video.py     # tahap 5
│   ├── tts.py           # tahap 6
│   ├── finish.py        # tahap 7
├── tests/               # unittest + run_tests.sh
├── examples/            # contoh output (segera)
└── attic/               # arsip eksperimen lama (tidak dipakai pipeline)
```

## 📜 Lisensi

MIT — lihat `LICENSE`. `gflow-cli` © swissmarley (MIT).
Pipeline ini tidak berafiliasi dengan Google; patuhi ToS Google Flow
dan kuota akunmu.
