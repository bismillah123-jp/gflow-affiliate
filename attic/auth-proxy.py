#!/usr/bin/env python3
"""auth-proxy.py: Basic Auth di depan noVNC/websockify.
Listen 127.0.0.1:6081 -> forward ke 127.0.0.1:6080 (websockify).
Menangani HTTP biasa + WebSocket upgrade (relay TCP mentah setelah handshake).
"""
import base64
import os
import socket
import threading

LISTEN_PORT = 6081
TARGET_PORT = 6080
USER = "shania"
PASS = os.environ.get("VNC_PROXY_PASS", "ganti-aku")


def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.close()
            except OSError:
                pass


def handle(client):
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                client.close()
                return
            data += chunk
            if len(data) > 65536:
                client.close()
                return
        lines = data.split(b"\r\n\r\n")[0].decode("latin1").split("\r\n")
        ok = False
        for l in lines[1:]:
            if l.lower().startswith("authorization: basic "):
                try:
                    creds = base64.b64decode(l.split(" ", 2)[2].strip()).decode()
                    ok = creds == f"{USER}:{PASS}"
                except Exception:
                    pass
        if not ok:
            client.sendall(
                b"HTTP/1.1 401 Unauthorized\r\n"
                b'WWW-Authenticate: Basic realm="Login Chrome"\r\n'
                b"Content-Length: 0\r\nConnection: close\r\n\r\n"
            )
            client.close()
            return
        target = socket.create_connection(("127.0.0.1", TARGET_PORT), timeout=10)
        target.sendall(data)
        t = threading.Thread(target=pipe, args=(client, target), daemon=True)
        t.start()
        pipe(target, client)
    except OSError:
        try:
            client.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LISTEN_PORT))
    srv.listen(50)
    print(f"auth-proxy listen 127.0.0.1:{LISTEN_PORT} -> 127.0.0.1:{TARGET_PORT}", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()


if __name__ == "__main__":
    main()
