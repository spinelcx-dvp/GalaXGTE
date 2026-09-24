#!/bin/bash
set -e

# ============================================
# 1. دریافت متغیرها از Railway
# ============================================
export APP_PORT=${PORT:-8080}
export UUID=${UUID:-$(cat /proc/sys/kernel/random/uuid)}
export WSPATH=${WSPATH:-/ws}
export PASS=${PASS:-""}
export XRAY_PORT=10000
export PANEL_PORT=3000

echo "=============================================="
echo "  Starting SpinPanel"
echo "=============================================="
echo "  Public Port (Railway) : $APP_PORT"
echo "  Xray Internal Port    : $XRAY_PORT"
echo "  Panel Internal Port   : $PANEL_PORT"
echo "  UUID                  : $UUID"
echo "  WS Path               : $WSPATH"
echo "=============================================="

# ============================================
# 2. ساخت کانفیگ Nginx از روی template
# ============================================
sed -e "s|\$PORT|$APP_PORT|g" \
    -e "s|\$WSPATH|$WSPATH|g" \
    -e "s|\$XRAY_PORT|$XRAY_PORT|g" \
    -e "s|\$PANEL_PORT|$PANEL_PORT|g" \
    /app/nginx.conf.template > /etc/nginx/http.d/default.conf

echo "[+] Nginx site config generated:"
cat /etc/nginx/http.d/default.conf

# ============================================
# 3. ساخت کانفیگ Xray
# ============================================
mkdir -p /etc/xray

cat > /etc/xray/config.json <<EOF
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": $XRAY_PORT,
      "listen": "127.0.0.1",
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "$UUID",
            "level": 0,
            "email": "user@railway"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "$WSPATH"
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "settings": {}
    }
  ]
}
EOF

echo "[+] Xray config generated."

# ============================================
# 4. اجرای Xray در پس‌زمینه
# ============================================
/usr/local/share/xray/xray -c /etc/xray/config.json &
XRAY_PID=$!
echo "[+] Xray started (PID: $XRAY_PID)"

# ============================================
# 5. اجرای پنل Node.js در پس‌زمینه
# ============================================
node /app/server.js &
PANEL_PID=$!
echo "[+] Panel started (PID: $PANEL_PID)"

# ============================================
# 6. انتظار برای بالا آمدن سرویس‌ها
# ============================================
sleep 3

# ============================================
# 7. تست سلامت سرویس‌ها
# ============================================
if ! kill -0 $XRAY_PID 2>/dev/null; then
    echo "[!] Xray failed to start!"
    exit 1
fi

if ! kill -0 $PANEL_PID 2>/dev/null; then
    echo "[!] Panel failed to start!"
    exit 1
fi

# ============================================
# 8. تست کانفیگ Nginx قبل از اجرا
# ============================================
echo "[+] Testing Nginx configuration..."
nginx -t

echo "[+] All services are running. Starting Nginx..."

# ============================================
# 9. اجرای Nginx در foreground
# ============================================
exec /usr/sbin/nginx -g "daemon off;"
