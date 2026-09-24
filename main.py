#!/usr/bin/env python3
"""
SpinPanel - Transparent WebSocket Proxy for Xray VLESS WS
- تمام درخواست‌های WebSocket را شفاف به Xray رله می‌کند
- صفحه پنل را روی / نشان می‌دهد
- لاگ کامل در Railway Deploy Logs
"""

import os
import sys
import socket
import select
import threading
import socketserver
import datetime
import json

# ============================================
# تنظیمات
# ============================================
APP_PORT  = int(os.environ.get("PORT", 8080))
XRAY_PORT = int(os.environ.get("XRAY_PORT", 10000))
UUID      = os.environ.get("UUID", "generated-uuid")
WSPATH    = os.environ.get("WSPATH", "/ws")
DOMAIN    = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")

if not WSPATH.startswith("/"):
    WSPATH = "/" + WSPATH
if WSPATH.endswith("/") and len(WSPATH) > 1:
    WSPATH = WSPATH.rstrip("/")


def log(tag, msg):
    """لاگ با timestamp به stdout که Railway می‌بیند"""
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    print(line, flush=True)


log("BOOT", f"APP_PORT={APP_PORT}")
log("BOOT", f"XRAY_PORT={XRAY_PORT}")
log("BOOT", f"UUID={UUID}")
log("BOOT", f"WSPATH={WSPATH}")
log("BOOT", f"DOMAIN={DOMAIN}")


# ============================================
# رله دوطرفه TCP
# ============================================
def relay(a, b, tag="RELAY"):
    """انتقال دوطرفه داده بین دو سوکت تا بسته شدن یکی"""
    socks = [a, b]
    total = 0
    try:
        while True:
            r, _, _ = select.select(socks, [], [], 300)
            if not r:
                log(tag, "idle timeout, closing")
                break
            for s in r:
                try:
                    data = s.recv(65536)
                except Exception as e:
                    log(tag, f"recv error: {e}")
                    return
                if not data:
                    log(tag, "peer closed")
                    return
                total += len(data)
                other = b if s is a else a
                try:
                    other.sendall(data)
                except Exception as e:
                    log(tag, f"send error: {e}")
                    return
    finally:
        for s in (a, b):
            try: s.close()
            except Exception: pass
        log(tag, f"closed, total bytes relayed: {total}")


# ============================================
# صفحه پنل
# ============================================
def build_panel():
    vless_tls = (
        f"vless://{UUID}@{DOMAIN}:443"
        f"?encryption=none&security=tls&sni={DOMAIN}&fp=chrome"
        f"&type=ws&host={DOMAIN}&path={WSPATH}#SpinPanel-TLS"
    )
    vless_notls = (
        f"vless://{UUID}@{DOMAIN}:8080"
        f"?encryption=none&security=none"
        f"&type=ws&host={DOMAIN}&path={WSPATH}#SpinPanel-NonTLS"
    )
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpinPanel</title>
<style>
  *{{box-sizing:border-box}}
  body{{font-family:'Segoe UI',Tahoma,sans-serif;background:#0f0f1a;color:#e0e0e0;margin:0;padding:20px;min-height:100vh}}
  .container{{max-width:800px;margin:0 auto}}
  h1{{color:#7c5cff;text-align:center;margin-bottom:10px}}
  .status{{text-align:center;color:#a0ffa0;margin-bottom:25px}}
  .card{{background:#1a1a2e;border-radius:12px;padding:18px;margin-bottom:18px;box-shadow:0 4px 20px rgba(124,92,255,.1)}}
  .label{{color:#7c5cff;font-weight:bold;margin-bottom:8px;display:block}}
  .value{{background:#0f0f1a;padding:12px;border-radius:8px;word-break:break-all;font-family:'Courier New',monospace;font-size:13px;color:#a0ffa0;border:1px solid #2a2a4a}}
  textarea{{width:100%;background:#0f0f1a;color:#a0ffa0;border:1px solid #2a2a4a;border-radius:8px;padding:12px;font-family:'Courier New',monospace;font-size:12px;resize:vertical;min-height:80px}}
  .copy-btn{{background:#7c5cff;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin-top:8px;font-size:13px}}
  .copy-btn:hover{{background:#6a4ce0}}
</style>
</head>
<body>
<div class="container">
  <h1>🚀 SpinPanel</h1>
  <p class="status">✅ سرویس فعال است</p>
  <div class="card"><span class="label">UUID:</span><div class="value">{UUID}</div></div>
  <div class="card"><span class="label">WS Path:</span><div class="value">{WSPATH}</div></div>
  <div class="card">
    <span class="label">VLESS WS TLS (پورت 443):</span>
    <textarea readonly onclick="this.select()">{vless_tls}</textarea>
    <button class="copy-btn" onclick="copyText(this)">کپی</button>
  </div>
  <div class="card">
    <span class="label">VLESS WS Non-TLS (پورت 8080):</span>
    <textarea readonly onclick="this.select()">{vless_notls}</textarea>
    <button class="copy-btn" onclick="copyText(this)">کپی</button>
  </div>
</div>
<script>
function copyText(btn){{
  const t=btn.previousElementSibling;
  t.select();document.execCommand('copy');
  btn.textContent='✓ کپی شد';
  setTimeout(()=>btn.textContent='کپی',1500);
}}
</script>
</body>
</html>"""


PANEL_HTML = build_panel().encode("utf-8")


# ============================================
# هندلر اصلی TCP
# ============================================
class Handler(socketserver.BaseRequestHandler):

    def handle(self):
        peer = self.client_address
        client = self.request
        client.settimeout(15)

        # خواندن اولین تکه داده
        try:
            first = client.recv(16384)
        except Exception as e:
            log("HTTP", f"{peer} recv fail: {e}")
            client.close(); return

        if not first:
            log("HTTP", f"{peer} empty request")
            client.close(); return

        # پارس کردن خط اول درخواست
        try:
            first_line = first.split(b"\r\n", 1)[0].decode("latin-1", "ignore")
            parts = first_line.split(" ")
            method = parts[0] if len(parts) > 0 else "?"
            path   = parts[1] if len(parts) > 1 else "/"
        except Exception:
            method, path = "?", "/"

        # تشخیص WebSocket
        head_lower = first.lower()
        is_ws = (b"upgrade: websocket" in head_lower) and (b"connection: upgrade" in head_lower)

        log("HTTP", f"{peer} {method} {path} WS={is_ws}")

        # ============ WebSocket → Xray ============
        if is_ws and (path == WSPATH or path.startswith(WSPATH)):
            log("WS", f"{peer} forwarding to Xray 127.0.0.1:{XRAY_PORT}")
            try:
                upstream = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
            except Exception as e:
                log("WS", f"{peer} cannot connect to Xray: {e}")
                try:
                    client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                except Exception:
                    pass
                client.close(); return

            # ارسال کل داده اولیه به Xray
            try:
                upstream.sendall(first)
            except Exception as e:
                log("WS", f"{peer} send to Xray fail: {e}")
                upstream.close(); client.close(); return

            client.settimeout(None)
            upstream.settimeout(None)
            relay(client, upstream, tag=f"WS-{peer[0]}")
            return

        # ============ HTTP معمولی → پنل ============
        if path in ("/", "/index.html"):
            log("HTTP", f"{peer} serving panel")
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(PANEL_HTML)).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            ) + PANEL_HTML
        else:
            log("HTTP", f"{peer} 404 on {path}")
            body = b"Not Found"
            resp = (
                b"HTTP/1.1 404 Not Found\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            ) + body

        try:
            client.sendall(resp)
        except Exception as e:
            log("HTTP", f"{peer} send resp fail: {e}")
        finally:
            try: client.close()
            except Exception: pass


# ============================================
# سرور Threaded
# ============================================
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 100


def main():
    try:
        server = ThreadedTCPServer(("0.0.0.0", APP_PORT), Handler)
    except Exception as e:
        log("BOOT", f"Cannot bind {APP_PORT}: {e}")
        sys.exit(1)

    log("BOOT", f"SpinPanel listening on 0.0.0.0:{APP_PORT}")
    log("BOOT", f"WebSocket path: {WSPATH}")
    log("BOOT", f"Xray upstream: 127.0.0.1:{XRAY_PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("BOOT", "Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
