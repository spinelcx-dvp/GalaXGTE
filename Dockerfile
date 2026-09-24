FROM alpine:latest

# نصب ابزارهای لازم
RUN apk add --no-cache nginx nodejs npm curl unzip jq bash

# نصب Xray-core
RUN mkdir -p /usr/local/share/xray && \
    curl -L -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/share/xray && \
    chmod +x /usr/local/share/xray/xray && \
    rm /tmp/xray.zip

# ساخت پوشه‌های لازم
RUN mkdir -p /etc/nginx/http.d /etc/xray /var/log/nginx /var/run

# کپی فایل‌های پروژه
WORKDIR /app
COPY server.js /app/
COPY start.sh /app/
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf.template /app/

RUN chmod +x /app/start.sh

# پورت پیش‌فرض Railway
EXPOSE 8080

CMD ["/app/start.sh"]
