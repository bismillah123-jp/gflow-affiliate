#!/usr/bin/env python3
"""Test lib/vncpasswd.py: port d3des TigerVNC (bukan DES FIPS!)."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from vncpasswd import VNC_FILE_KEY, d3des, deobfuscate, obfuscate

# Vektor dari d3des.c TigerVNC v1.13.1 asli (dikompilasi via gcc).
# BUKAN vektor FIPS — d3des VNC memang bukan DES standar (bytebit dibalik).
D3DES_VECTORS = [
    ("17526b06234e5807", "7465737431323334", "70685069802a5e92"),
    ("133457799bbcdff1", "0123456789abcdef", "cee55acd2386b23f"),
]


class TestVncPasswd(unittest.TestCase):
    def test_d3des_matches_c_oracle(self):
        for kh, ph, ch in D3DES_VECTORS:
            self.assertEqual(d3des(bytes.fromhex(kh), bytes.fromhex(ph)).hex(), ch)

    def test_d3des_decrypt(self):
        k = bytes.fromhex("17526b06234e5807")
        p = bytes.fromhex("7465737431323334")
        c = d3des(k, p)
        self.assertEqual(d3des(k, c, decrypt=True), p)

    def test_obfuscate_matches_tigervnc(self):
        # "test1234" -> file passwd persis buatan vncpasswd TigerVNC
        self.assertEqual(obfuscate("test1234").hex(), "70685069802a5e92")

    def test_roundtrip(self):
        for pw in ["test1234", "a", "password-panjang-sekali", "12345678"]:
            blob = obfuscate(pw)
            self.assertEqual(len(blob), 8)
            self.assertEqual(deobfuscate(blob), pw[:8].encode())

    def test_utf8_bytes_semantics(self):
        self.assertEqual(deobfuscate(obfuscate("pässwörd")),
                         "pässwörd".encode()[:8])

    def test_deterministic(self):
        self.assertEqual(obfuscate("rahasia"), obfuscate("rahasia"))
        self.assertNotEqual(obfuscate("rahasia1"), obfuscate("rahasia2"))

    def test_key_from_tigervnc_source(self):
        self.assertEqual(list(VNC_FILE_KEY), [23, 82, 107, 6, 35, 78, 88, 7])


if __name__ == "__main__":
    unittest.main(verbosity=1)
