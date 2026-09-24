#!/bin/bash
set -e

# دریافت متغیرها از Railway
export APP_PORT=${PORT:-8080}
export UUID=${UUID:-$(cat /proc/sys/kernel/random/uuid)}
export WSPATH=${WSPATH:-/ws}
export XRAY_PORT=10000

# اطمینان از اسلش ابتدای WSPATH
case "$WSPATH" in
  /*) ;;
  *) WSPATH="/$WSPATH" ;;
esac
export WSPATH

echo "=============================================="
echo "  SpinPanel - Starting"
echo "=============================================="
echo "  PORT (Railway)  : $APP_PORT"
echo "  Xray Port       : $XRAY_PORT"
echo "  UUID            : $UUID"
echo "  WSPATH          : $WSPATH"
echo "  DOMAIN          : ${RAILWAY_PUBLIC_DOMAIN:-N/A}"
echo "=============================================="

# ساخت کانفیگ Xray
mkdir -p /etc/xray
cat > /etc/xray/config.json <<EOF
{
  "log": {
    "loglevel": "debug"
  },
  "inbounds": [{
    "port": $XRAY_PORT,
    "listen": "127.0.0.1",
    "protocol": "vless",
    "settings": {
      "clients": [{
        "id": "$UUID",
        "level": 0,
        "email": "user@railway"
      }],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "ws",
      "wsSettings": {
        "path": "$WSPATH"
      }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  }]
}
EOF

echo "[+] Xray config file:"
cat /etc/xray/config.json
echo "=============================================="

# اجرای Xray در پس‌زمینه
/usr/local/share/xray/xray -c /etc/xray/config.json &
XRAY_PID=$!
echo "[+] Xray started (PID: $XRAY_PID)"

# انتظار برای بالا آمدن Xray
sleep 3

if ! kill -0 $XRAY_PID 2>/dev/null; then
    echo "[!] Xray crashed on startup!"
    exit 1
fi

# بررسی باز بودن پورت Xray
if ! (echo > /dev/tcp/127.0.0.1/$XRAY_PORT) 2>/dev/null; then
    echo "[!] Xray port $XRAY_PORT is not open!"
    exit 1
fi

echo "[+] Xray is listening on 127.0.0.1:$XRAY_PORT"

# اجرای پنل پایتون در foreground
echo "[+] Starting Python panel..."
exec python3 /app/main.py
