#!/bin/bash
set -e

# خواندن متغیرها از Railway
export UUID=${UUID:-$(cat /proc/sys/kernel/random/uuid)}
export WSPATH=${WSPATH:-/ws}
export PASS=${PASS:-""}
export PORT=${PORT:-8080}

# جایگزینی مقادیر در کانفیگ Nginx
sed -e "s|\$PORT|$PORT|g" \
    -e "s|\$WSPATH|$WSPATH|g" \
    /app/nginx.conf.template > /etc/nginx/http.d/default.conf

# ساخت کانفیگ Xray
mkdir -p /etc/xray
cat > /etc/xray/config.json <<EOF
{
  "inbounds": [{
    "port": 10000,
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

# اجرای Xray در پس‌زمینه
/usr/local/share/xray/xray -c /etc/xray/config.json &

# اجرای پنل Node.js
node /app/server.js &

# اجرای Nginx
nginx -g "daemon off;"
