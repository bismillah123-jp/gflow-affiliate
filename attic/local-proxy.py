#!/usr/bin/env python3
"""local-proxy.py: proxy HTTP/CONNECT lokal tanpa auth -> forward ke egress proxy.
Untuk Chrome: --proxy-server=http://127.0.0.1:3129
"""
import base64
import os
import socket
import threading
import urllib.parse

LISTEN_PORT = 3129


def upstream():
    pu = urllib.parse.urlparse(os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or "")
    auth = base64.b64encode(f"{pu.username}:{pu.password}".encode()).decode()
    return pu.hostname, pu.port or 3128, auth


UP_HOST, UP_PORT, AUTH = upstream()


def relay(a, b):
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
        head = data.split(b"\r\n\r\n")[0].decode("latin1")
        line = head.split("\r\n")[0]
        method, url, _ = line.split(" ", 2)
        up = socket.create_connection((UP_HOST, UP_PORT), timeout=15)
        if method == "CONNECT":
            # url = host:port
            up.sendall(
                f"CONNECT {url} HTTP/1.1\r\nHost: {url}\r\n"
                f"Proxy-Authorization: Basic {AUTH}\r\nConnection: keep-alive\r\n\r\n".encode()
            )
            resp = b""
            while b"\r\n\r\n" not in resp:
                c = up.recv(4096)
                if not c:
                    break
                resp += c
            if b" 200 " not in resp.split(b"\r\n", 1)[0]:
                client.close()
                up.close()
                return
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        else:
            # plain HTTP: forward as-is dengan auth
            headers, _, body = data.partition(b"\r\n\r\n")
            lines = headers.decode("latin1").split("\r\n")
            out = [lines[0]]
            for l in lines[1:]:
                if not l.lower().startswith("proxy-authorization:"):
                    out.append(l)
            out.append(f"Proxy-Authorization: Basic {AUTH}")
            up.sendall(("\r\n".join(out) + "\r\n\r\n").encode("latin1") + body)
        t = threading.Thread(target=relay, args=(client, up), daemon=True)
        t.start()
        relay(up, client)
    except OSError:
        try:
            client.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LISTEN_PORT))
    srv.listen(100)
    print(f"local-proxy 127.0.0.1:{LISTEN_PORT} -> {UP_HOST}:{UP_PORT}", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()


if __name__ == "__main__":
    main()
