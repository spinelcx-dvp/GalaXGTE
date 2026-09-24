FROM python:3.12-alpine

RUN apk add --no-cache curl unzip bash

# نصب Xray
RUN mkdir -p /usr/local/share/xray && \
    curl -L -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/share/xray && \
    chmod +x /usr/local/share/xray/xray && \
    rm /tmp/xray.zip

# نصب cloudflared
RUN curl -L -o /usr/local/bin/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && \
    chmod +x /usr/local/bin/cloudflared

WORKDIR /app
COPY main.py /app/
COPY start.sh /app/
RUN chmod +x /app/start.sh

EXPOSE 8080
CMD ["/app/start.sh"]
