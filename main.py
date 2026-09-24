#!/usr/bin/env python3
import os, sys, socket, select, threading, socketserver, datetime

APP_PORT  = int(os.environ.get("PORT", 8080))
XRAY_PORT = int(os.environ.get("XRAY_PORT", 10000))
UUID      = os.environ.get("UUID", "generated-uuid")
WSPATH    = os.environ.get("WSPATH", "/ws")
DOMAIN    = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")

if not WSPATH.startswith("/"): WSPATH = "/" + WSPATH
if WSPATH.endswith("/") and len(WSPATH) > 1: WSPATH = WSPATH.rstrip("/")


def log(tag, msg):
    ts = datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}", flush=True)

log("BOOT", f"PORT={APP_PORT} XRAY={XRAY_PORT} WSPATH={WSPATH} DOMAIN={DOMAIN}")


def relay(a, b, tag):
    total = 0
    try:
        while True:
            r, _, _ = select.select([a, b], [], [], 600)
            if not r: break
            for s in r:
                try: data = s.recv(65536)
                except Exception: return
                if not data: return
                total += len(data)
                other = b if s is a else a
                try: other.sendall(data)
                except Exception: return
    finally:
        for s in (a, b):
            try: s.close()
            except: pass
        log(tag, f"closed ({total} bytes)")


PANEL_HTML = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SpinPanel</title>
<style>body{{font-family:'Segoe UI',Tahoma;background:#0f0f1a;color:#e0e0e0;padding:20px}}
.container{{max-width:800px;margin:0 auto}}h1{{color:#7c5cff;text-align:center}}
.card{{background:#1a1a2e;border-radius:12px;padding:18px;margin-bottom:18px}}
.label{{color:#7c5cff;font-weight:bold;margin-bottom:8px;display:block}}
.value{{background:#0f0f1a;padding:12px;border-radius:8px;font-family:monospace;
color:#a0ffa0;border:1px solid #2a2a4a;word-break:break-all}}
textarea{{width:100%;background:#0f0f1a;color:#a0ffa0;border:1px solid #2a2a4a;
border-radius:8px;padding:12px;font-family:monospace;min-height:80px}}</style></head>
<body><div class="container"><h1>🚀 SpinPanel</h1>
<div class="card"><span class="label">UUID:</span><div class="value">{UUID}</div></div>
<div class="card"><span class="label">WSPATH:</span><div class="value">{WSPATH}</div></div>
<div class="card"><span class="label">VLESS WS TLS (443):</span>
<textarea readonly>vless://{UUID}@{DOMAIN}:443?encryption=none&security=tls&sni={DOMAIN}&fp=chrome&type=ws&host={DOMAIN}&path={WSPATH}#SpinPanel-TLS</textarea></div>
<div class="card"><span class="label">VLESS WS Non-TLS (80):</span>
<textarea readonly>vless://{UUID}@{DOMAIN}:80?encryption=none&security=none&type=ws&host={DOMAIN}&path={WSPATH}#SpinPanel-NonTLS</textarea></div>
</div></body></html>""".encode("utf-8")


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = self.client_address
        sock = self.request
        sock.settimeout(15)
        try:
            first = sock.recv(16384)
        except Exception as e:
            log("HTTP", f"{peer} recv: {e}"); sock.close(); return
        if not first:
            sock.close(); return

        try:
            line = first.split(b"\r\n", 1)[0].decode("latin-1", "ignore")
            parts = line.split(" ")
            method = parts[0] if parts else "?"
            path   = parts[1] if len(parts) > 1 else "/"
        except Exception:
            method, path = "?", "/"

        head = first.lower()
        is_ws = (b"upgrade: websocket" in head) and (b"connection: upgrade" in head)

        log("HTTP", f"{peer} {method} {path} WS={is_ws}")

        if is_ws and (path == WSPATH or path.startswith(WSPATH)):
            log("WS", f"{peer} → Xray")
            try:
                up = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
            except Exception as e:
                log("WS", f"Xray fail: {e}")
                try: sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                except: pass
                sock.close(); return
            try: up.sendall(first)
            except Exception: up.close(); sock.close(); return
            sock.settimeout(None); up.settimeout(None)
            relay(sock, up, tag=f"WS-{peer[0]}")
            return

        if path in ("/", "/index.html"):
            resp = (b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                    b"Content-Length: " + str(len(PANEL_HTML)).encode() +
                    b"\r\nConnection: close\r\n\r\n") + PANEL_HTML
        else:
            body = b"Not Found"
            resp = (b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n"
                    b"Connection: close\r\n\r\n") + body

        try: sock.sendall(resp)
        except: pass
        finally:
            try: sock.close()
            except: pass


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 200


if __name__ == "__main__":
    srv = Server(("0.0.0.0", APP_PORT), Handler)
    log("BOOT", f"listening 0.0.0.0:{APP_PORT}")
    try: srv.serve_forever()
    except KeyboardInterrupt: srv.shutdown()
