#!/usr/bin/env python3
"""Test lib/cookies_import.py: enkripsi v10 round-trip, filter domain,
format Cookie-Editor JSON + Netscape, idempotensi."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from cookies_import import (chrome_ts, decrypt_value, encrypt_value,
                            import_cookies)

FAKE_EXPORT = [
    {"domain": ".google.com", "expirationDate": 1893456000,
     "hostOnly": False, "httpOnly": True, "name": "SID", "path": "/",
     "sameSite": "no_restriction", "secure": True, "session": False,
     "storeId": "0", "value": "rahasia-sid-123"},
    {"domain": "accounts.google.com", "expirationDate": 1893456000,
     "hostOnly": True, "httpOnly": False, "name": "GAPS", "path": "/",
     "sameSite": "lax", "secure": True, "session": False,
     "storeId": "0", "value": "gaps-456"},
    {"domain": "labs.google", "expirationDate": 0,
     "hostOnly": True, "httpOnly": False, "name": "SESS", "path": "/fx",
     "sameSite": "unspecified", "secure": True, "session": True,
     "storeId": "0", "value": "sesi-fx"},
    {"domain": ".facebook.com", "expirationDate": 1893456000,
     "hostOnly": False, "httpOnly": False, "name": "c_user", "path": "/",
     "sameSite": "lax", "secure": True, "session": False,
     "storeId": "0", "value": "bukan-google"},
]


def read_db(profile):
    con = sqlite3.connect(profile / "Cookies")
    rows = {r[0]: r for r in con.execute(
        "SELECT name, value, host_key, path, expires_utc, is_persistent,"
        " is_secure, is_httponly, samesite FROM cookies")}
    con.close()
    return rows


class TestCookiesImport(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.json_file = self.tmp / "cookies.json"
        self.json_file.write_text(json.dumps(FAKE_EXPORT), encoding="utf-8")
        self.profile = self.tmp / "prof"

    def test_epoch_math(self):
        self.assertEqual(chrome_ts(0), 11644473600000000)

    def test_v10_roundtrip(self):
        for v in [b"abc", b"", "nön-äscii ✓".encode()]:
            self.assertEqual(decrypt_value(encrypt_value(v)), v)

    def test_google_only_by_default(self):
        n = import_cookies(self.json_file, self.profile)
        self.assertEqual(n, 3)
        rows = read_db(self.profile)
        self.assertNotIn("c_user", rows)
        # nilai terdekripsi harus sama persis
        self.assertEqual(decrypt_value(rows["SID"][1]), b"rahasia-sid-123")
        self.assertEqual(rows["SID"][2], ".google.com")
        self.assertEqual(rows["GAPS"][2], "accounts.google.com")
        self.assertEqual(rows["SID"][7], 1)   # httponly
        self.assertEqual(rows["SID"][6], 1)   # secure
        self.assertEqual(rows["SID"][8], 0)   # no_restriction
        self.assertEqual(rows["GAPS"][8], 1)  # lax
        # cookie sesi: tidak persistent, expires 0
        self.assertEqual(rows["SESS"][4], 0)
        self.assertEqual(rows["SESS"][5], 0)
        self.assertEqual(rows["SESS"][3], "/fx")

    def test_idempotent(self):
        import_cookies(self.json_file, self.profile)
        n2 = import_cookies(self.json_file, self.profile)
        self.assertEqual(n2, 3)
        self.assertEqual(len(read_db(self.profile)), 3)

    def test_all_domains(self):
        n = import_cookies(self.json_file, self.profile, all_domains=True)
        self.assertEqual(n, 4)
        self.assertIn("c_user", read_db(self.profile))

    def test_netscape_format(self):
        txt = self.tmp / "cookies.txt"
        txt.write_text(
            "# Netscape HTTP Cookie File\n"
            ".google.com\tTRUE\t/\tTRUE\t1893456000\tNID\tnet-789\n",
            encoding="utf-8")
        n = import_cookies(txt, self.profile)
        self.assertEqual(n, 1)
        rows = read_db(self.profile)
        self.assertEqual(decrypt_value(rows["NID"][1]), b"net-789")


if __name__ == "__main__":
    unittest.main(verbosity=1)
