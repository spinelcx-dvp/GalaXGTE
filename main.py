#!/usr/bin/env python3
"""
SpinPanel - Python Edition
پروکسی معکوس + پنل وب برای Xray VLESS WS
بدون Nginx - فقط کتابخانه استاندارد پایتون
"""

import os
import sys
import json
import socket
import select
import threading
import http.server
import socketserver
from urllib.parse import urlparse

# ============================================
# تنظیمات از متغیرهای محیطی Railway
# ============================================
APP_PORT  = int(os.environ.get("PORT", 8080))
XRAY_PORT = int(os.environ.get("XRAY_PORT", 10000))
UUID      = os.environ.get("UUID", "generated-uuid")
WSPATH    = os.environ.get("WSPATH", "/ws")
PASS      = os.environ.get("PASS", "")
DOMAIN    = (
    os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    or os.environ.get("RAILWAY_STATIC_URL")
    or "localhost"
)

print(f"[Config] APP_PORT={APP_PORT}", flush=True)
print(f"[Config] XRAY_PORT={XRAY_PORT}", flush=True)
print(f"[Config] UUID={UUID}", flush=True)
print(f"[Config] WSPATH={WSPATH}", flush=True)
print(f"[Config] DOMAIN={DOMAIN}", flush=True)


# ============================================
# رله دوطرفه TCP (قلب WebSocket)
# ============================================
def relay(sock_a, sock_b):
    """انتقال دوطرفه داده بین دو سوکت"""
    sockets = [sock_a, sock_b]
    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], 300)
            if not readable:
                break
            for s in readable:
                try:
                    data = s.recv(65536)
                except Exception:
                    return
                if not data:
                    return
                other = sock_b if s is sock_a else sock_a
                try:
                    other.sendall(data)
                except Exception:
                    return
    except Exception:
        pass
    finally:
        for s in (sock_a, sock_b):
            try:
                s.close()
            except Exception:
                pass


# ============================================
# هندلر HTTP اصلی
# ============================================
class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SpinPanel/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()

    # ---------- تشخیص WebSocket ----------
    def is_websocket(self):
        upgrade = self.headers.get("Upgrade", "").lower()
        connection = self.headers.get("Connection", "").lower()
        return "websocket" in upgrade and "upgrade" in connection

    # ---------- پروکسی WebSocket به Xray ----------
    def proxy_to_xray_ws(self):
        try:
            upstream = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {e}")
            return

        # ساخت درخواست خام HTTP
        lines = [f"{self.command} {self.path} {self.request_version}"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        raw_request = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8", "ignore")

        try:
            upstream.sendall(raw_request)
        except Exception:
            upstream.close()
            self.send_error(502, "Xray write error")
            return

        # خواندن پاسخ اولیه از Xray (تا انتهای هدرها)
        upstream.settimeout(10)
        response = b""
        try:
            while b"\r\n\r\n" not in response:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                response += chunk
        except Exception:
            upstream.close()
            return

        # ارسال پاسخ Xray به کلاینت
        try:
            self.wfile.write(response)
            self.wfile.flush()
        except Exception:
            upstream.close()
            return

        # اگر 101 Switching Protocols بود، رله خام دوطرفه
        first_line = response.split(b"\r\n", 1)[0]
        if b" 101 " in first_line:
            self.close_connection = True
            client_sock = self.connection
            relay(client_sock, upstream)
        else:
            upstream.close()
            self.close_connection = True

    # ---------- پروکسی HTTP معمولی به Xray ----------
    def proxy_to_xray_http(self):
        content_length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(content_length) if content_length else b""

        lines = [f"{self.command} {self.path} {self.request_version}"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        raw_request = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8", "ignore") + body

        try:
            upstream = socket.create_connection(("127.0.0.1", XRAY_PORT), timeout=10)
            upstream.sendall(raw_request)

            response = b""
            upstream.settimeout(30)
            while True:
                try:
                    chunk = upstream.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                response += chunk
            upstream.close()

            self.wfile.write(response)
            self.wfile.flush()
        except Exception as e:
            try:
                self.send_error(502, f"Bad Gateway: {e}")
            except Exception:
                pass

    # ---------- صفحه پنل ----------
    def serve_panel(self):
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

        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- مسیریابی ----------
    def route(self):
        path = urlparse(self.path).path

        # مسیر WebSocket
        if path == WSPATH or path.startswith(WSPATH + "?") or path.startswith(WSPATH + "/"):
            if self.is_websocket():
                self.proxy_to_xray_ws()
            else:
                self.proxy_to_xray_http()
        # صفحه پنل
        elif path in ("/", "/index.html"):
            self.serve_panel()
        # سایر مسیرها
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_GET(self):    self.route()
    def do_POST(self):   self.route()
    def do_HEAD(self):   self.route()
    def do_PUT(self):    self.route()
    def do_DELETE(self): self.route()


# ============================================
# سرور با Threading
# ============================================
class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    server = ThreadingHTTPServer(("0.0.0.0", APP_PORT), ProxyHandler)
    print(f"[+] SpinPanel listening on 0.0.0.0:{APP_PORT}", flush=True)
    print(f"[+] WebSocket: {WSPATH} -> 127.0.0.1:{XRAY_PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
