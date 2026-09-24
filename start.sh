#!/bin/bash
set -e

export APP_PORT=${PORT:-8080}
export UUID=${UUID:-$(cat /proc/sys/kernel/random/uuid)}
export WSPATH=${WSPATH:-/ws}
export XRAY_PORT=10000

case "$WSPATH" in
  /*) ;;
  *) WSPATH="/$WSPATH" ;;
esac
export WSPATH

echo "=============================================="
echo "  SpinPanel"
echo "  PORT    : $APP_PORT"
echo "  UUID    : $UUID"
echo "  WSPATH  : $WSPATH"
echo "=============================================="

# ساخت کانفیگ Xray
mkdir -p /etc/xray
cat > /etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [{
    "port": $XRAY_PORT,
    "listen": "127.0.0.1",
    "protocol": "vless",
    "settings": {
      "clients": [{ "id": "$UUID", "level": 0, "email": "user" }],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "ws",
      "wsSettings": { "path": "$WSPATH" }
    }
  }],
  "outbounds": [{ "protocol": "freedom", "settings": {} }]
}
EOF

/usr/local/share/xray/xray -c /etc/xray/config.json &
echo "[+] Xray started"

sleep 2

exec python3 /app/main.py
