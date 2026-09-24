#!/usr/bin/env python3
"""
SpinPanel - Python Edition (Transparent WebSocket Proxy)
پروکسی شفاف TCP برای Xray VLESS WS + پنل وب
"""

import os
import sys
import socket
import select
import threading
import socketserver

# ============================================
# تنظیمات
# ============================================
APP_PORT  = int(os.environ.get("PORT", 8080))
XRAY_PORT = int(os.environ.get("XRAY_PORT", 10000))
UUID      = os.environ.get("UUID", "generated-uuid")
WSPATH    = os.environ.get("WSPATH", "/ws")
DOMAIN    = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")

# اطمینان از اینکه WSPATH با / شروع می‌شود
if not WSPATH.startswith("/"):
    WSPATH = "/" + WSPATH

print(f"[Config] APP_PORT={APP_PORT}", flush=True)
print(f"[Config] XRAY_PORT={XRAY_PORT}", flush=True)
print(f"[Config] UUID={UUID}", flush=True)
print(f"[Config] WSPATH={WSPATH}", flush=True)
print(f"[Config] DOMAIN={DOMAIN}", flush=True)


# ============================================
# رله دوطرفه TCP
# ============================================
def relay(a, b):
    socks = [a, b]
    try:
        while True:
            r, _, _ = select.select(socks, [], [], 600)
            if not r:
                break
            for s in r:
                try:
                    data = s.recv(65536)
                except Exception:
                    return
                if not data:
                    return
                other = b if s is a else a
                try:
                    other.sendall(data)
                except Exception:
                    return
    finally:
        for s in (a, b):
            try: s.close()
            except Exception: pass


# ============================================
# ساخت صفحه پنل
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
    html = f"""<!DOCTYPE html>
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
    return html.encode("utf-8")


PANEL_HTML = build_panel()
PANEL_BYTES = PANEL_HTML


# ============================================
# هندلر TCP خام
# ============================================
class RawHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        client.settimeout(10)

        # خواندن اولین بخش داده (تا 8 کیلوبایت)
        try:
            first_chunk = client.recv(8192)
        except Exception:
            client.close()
            return

        if not first_chunk:
            client.close()
            return

        # تشخیص WebSocket با بررسی هدر Upgrade
        first_line = first_chunk.split(b"\r\n", 1)[0].decode("latin-1", "ignore")
        lower = first_chunk.lower()

        is_ws = (b"upgrade: websocket" in lower) or (b"upgrade:websocket" in lower)

        if is_ws:
            # رله شفاف به Xray
            try:
                upstream = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
            except Exception as e:
                print(f"[WS] Cannot connect to Xray: {e}", flush=True)
                try:
                    client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                except Exception:
                    pass
                client.close()
                return

            try:
                upstream.sendall(first_chunk)
            except Exception:
                upstream.close()
                client.close()
                return

            client.settimeout(None)
            upstream.settimeout(None)
            relay(client, upstream)
            return

        # HTTP معمولی: صفحه پنل
        path = "/"
        try:
            parts = first_line.split(" ")
            if len(parts) >= 2:
                path = parts[1]
        except Exception:
            pass

        try:
            if path in ("/", "/index.html"):
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    b"Content-Length: " + str(len(PANEL_BYTES)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n"
                ) + PANEL_BYTES
            else:
                resp = (
                    b"HTTP/1.1 404 Not Found\r\n"
                    b"Content-Type: text/plain\r\n"
                    b"Content-Length: 9\r\n"
                    b"Connection: close\r\n\r\n"
                    b"Not Found"
                )
            client.sendall(resp)
        except Exception:
            pass
        finally:
            try: client.close()
            except Exception: pass


# ============================================
# سرور
# ============================================
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    server = ThreadedTCPServer(("0.0.0.0", APP_PORT), RawHandler)
    print(f"[+] SpinPanel listening on 0.0.0.0:{APP_PORT}", flush=True)
    print(f"[+] WebSocket path: {WSPATH}", flush=True)
    print(f"[+] Xray upstream: 127.0.0.1:{XRAY_PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...", flush=True)


if __name__ == "__main__":
    main()
