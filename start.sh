#!/bin/bash
set -e

export APP_PORT=${PORT:-8080}
export UUID=${UUID:-$(cat /proc/sys/kernel/random/uuid)}
export WSPATH=${WSPATH:-/ws}
export PASS=${PASS:-""}
export XRAY_PORT=10000

echo "=============================================="
echo "  Starting SpinPanel (Transparent WS Proxy)"
echo "=============================================="
echo "  Public Port : $APP_PORT"
echo "  Xray Port   : $XRAY_PORT"
echo "  UUID        : $UUID"
echo "  WS Path     : $WSPATH"
echo "=============================================="

mkdir -p /etc/xray
cat > /etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [{
    "port": $XRAY_PORT,
    "listen": "127.0.0.1",
    "protocol": "vless",
    "settings": {
      "clients": [{ "id": "$UUID", "level": 0, "email": "user@railway" }],
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

echo "[+] Xray config generated."

/usr/local/share/xray/xray -c /etc/xray/config.json &
XRAY_PID=$!
echo "[+] Xray started (PID: $XRAY_PID)"

sleep 2

if ! kill -0 $XRAY_PID 2>/dev/null; then
    echo "[!] Xray failed to start!"
    exit 1
fi

echo "[+] Starting Python panel on port $APP_PORT..."
exec python3 /app/main.py
