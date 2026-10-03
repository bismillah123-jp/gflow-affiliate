#!/usr/bin/env python3
"""Import cookies (export dari ekstensi Cookie-Editor) ke profil browser gflow (~/.local/share/gflow-cli/profile_default).

Kenapa ribet begini: Chrome di Linux mengenkripsi isi cookie di file
`Cookies` (SQLite) pakai AES-128-CBC dengan kunci turunan dari password
"peanuts" (fallback bawaan Chromium bila tidak ada keyring). Script ini
menulis ulang cookie dengan enkripsi yang sama persis, jadi Chrome
menerimanya apa adanya — tanpa perlu jendela login.

Format yang didukung:
  - JSON export bawaan Cookie-Editor (disarankan): array of
    {domain, expirationDate, hostOnly, httpOnly, name, path,
     sameSite, secure, session, value}
  - Netscape cookies.txt (fallback): dipakai bila file bukan JSON.

Default hanya cookie domain *google* yang diimpor (cukup untuk login
Flow: accounts.google.com, .google.com, labs.google). Pakai
--all-domains untuk impor semuanya.

Contoh:
  python3 lib/cookies_import.py cookies.json
  python3 lib/cookies_import.py cookies.json --all-domains
  python3 lib/cookies_import.py cookies.txt  # default: profil gflow
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Epoch Chrome: mikrodetik sejak 1601-01-01
CHROME_EPOCH_DELTA = 11644473600

SAMESITE = {"no_restriction": 0, "lax": 1, "strict": 2, "unspecified": -1}


def _linux_key() -> bytes:
    """Kunci AES-128 fallback Chromium di Linux ("peanuts"/"saltysalt")."""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16,
                     salt=b"saltysalt", iterations=1)
    return kdf.derive(b"peanuts")


def encrypt_value(plain: bytes) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain) + padder.finalize()
    enc = Cipher(algorithms.AES(_linux_key()),
                 modes.CBC(b" " * 16)).encryptor()
    return b"v10" + enc.update(padded) + enc.finalize()


def decrypt_value(blob: bytes) -> bytes:
    """Kebalikan encrypt_value — dipakai untuk verifikasi/test."""
    assert blob[:3] == b"v10", "bukan format v10"
    dec = Cipher(algorithms.AES(_linux_key()),
                 modes.CBC(b" " * 16)).decryptor()
    padded = dec.update(blob[3:]) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def chrome_ts(unix_ts: float) -> int:
    return int((unix_ts + CHROME_EPOCH_DELTA) * 1_000_000)


def parse_cookie_editor(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):  # kadang dibungkus {"cookies": [...]}
        data = data.get("cookies", [])
    out = []
    for c in data:
        exp = c.get("expirationDate") or 0
        session = bool(c.get("session")) or not exp
        out.append({
            "domain": c["domain"],
            "name": c["name"],
            "value": c.get("value", ""),
            "path": c.get("path", "/"),
            "secure": bool(c.get("secure")),
            "httponly": bool(c.get("httpOnly")),
            "samesite": SAMESITE.get(str(c.get("sameSite", "unspecified")).lower(), -1),
            "session": session,
            "expires": 0 if session else chrome_ts(float(exp)),
        })
    return out


def parse_netscape(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _, pth, secure, exp, name, value = parts[:7]
        exp_i = int(exp)
        out.append({
            "domain": domain,
            "name": name,
            "value": value,
            "path": pth or "/",
            "secure": secure.upper() == "TRUE",
            "httponly": False,
            "samesite": -1,
            "session": exp_i == 0,
            "expires": 0 if exp_i == 0 else chrome_ts(exp_i),
        })
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS cookies(
  creation_utc INTEGER NOT NULL,
  host_key TEXT NOT NULL,
  top_frame_site_key TEXT NOT NULL DEFAULT '',
  name TEXT NOT NULL,
  value TEXT NOT NULL,
  path TEXT NOT NULL,
  expires_utc INTEGER NOT NULL,
  is_secure INTEGER NOT NULL DEFAULT 0,
  is_httponly INTEGER NOT NULL DEFAULT 0,
  last_access_utc INTEGER NOT NULL,
  has_expires INTEGER NOT NULL DEFAULT 1,
  is_persistent INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 1,
  samesite INTEGER NOT NULL DEFAULT -1,
  source_scheme INTEGER NOT NULL DEFAULT 0,
  source_port INTEGER NOT NULL DEFAULT -1,
  is_same_party INTEGER NOT NULL DEFAULT 0,
  last_update_utc INTEGER NOT NULL DEFAULT 0,
  UNIQUE(host_key, name, path)
)"""


def chrome_holds_profile(profile_dir: Path) -> bool:
    try:
        r = subprocess.run(["pgrep", "-f", str(profile_dir)],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def import_cookies(src: Path, profile_dir: Path,
                   all_domains: bool = False) -> int:
    cookies = (parse_netscape(src) if src.suffix.lower() == ".txt"
               else parse_cookie_editor(src))
    if not all_domains:
        cookies = [c for c in cookies if "google" in c["domain"].lower()]
    if not cookies:
        print("Tidak ada cookie yang cocok (filter: *google*). "
              "Pakai --all-domains bila perlu.")
        return 0

    profile_dir.mkdir(parents=True, exist_ok=True)
    if chrome_holds_profile(profile_dir):
        sys.exit("Chrome sedang memakai profil ini — tutup dulu Chrome "
                 "profil Flow, lalu ulangi.")

    db = profile_dir / "Cookies"
    if db.exists():
        bak = profile_dir / f"Cookies.bak.{int(time.time())}"
        shutil.copy2(db, bak)
        print(f"Backup: {bak.name}")

    con = sqlite3.connect(db)
    con.execute(SCHEMA)
    now = chrome_ts(time.time())
    n = 0
    for c in cookies:
        enc = encrypt_value(c["value"].encode("utf-8"))
        con.execute(
            """INSERT OR REPLACE INTO cookies(
                 creation_utc, host_key, top_frame_site_key, name, value,
                 path, expires_utc, is_secure, is_httponly, last_access_utc,
                 has_expires, is_persistent, priority, samesite,
                 source_scheme, source_port, is_same_party, last_update_utc)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (now, c["domain"], "", c["name"], enc,
             c["path"], c["expires"], int(c["secure"]), int(c["httponly"]),
             now, int(not c["session"]), int(not c["session"]), 1,
             c["samesite"], 2 if c["secure"] else 1, -1, 0, now))
        n += 1
    con.commit()
    con.close()
    print(f"✔ {n} cookie diimpor ke {db}")
    return n


def _default_profile() -> str:
    home = os.environ.get("GFLOW_CLI_HOME",
                          str(Path.home() / ".local" / "share" / "gflow-cli"))
    return str(Path(home) / "profile_default")


def main() -> None:
    ap = argparse.ArgumentParser(description="Import cookies ke profil browser gflow")
    ap.add_argument("file", help="export JSON Cookie-Editor / cookies.txt")
    ap.add_argument("--profile-dir", default=_default_profile())
    ap.add_argument("--all-domains", action="store_true",
                    help="impor semua domain, bukan cuma *google*")
    args = ap.parse_args()
    import_cookies(Path(args.file), Path(args.profile_dir),
                   all_domains=args.all_domains)


if __name__ == "__main__":
    main()
