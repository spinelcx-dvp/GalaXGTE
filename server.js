const http = require('http');
const os = require('os');

const UUID = process.env.UUID || 'generated-uuid';
const WSPATH = process.env.WSPATH || '/ws';
const PASS = process.env.PASS || 'password';
const DOMAIN = process.env.RAILWAY_PUBLIC_DOMAIN || 'localhost';

const server = http.createServer((req, res) => {
  if (req.url === '/') {
    const config = `vless://${UUID}@${DOMAIN}:443?encryption=none&security=tls&sni=${DOMAIN}&fp=chrome&type=ws&host=${DOMAIN}&path=${encodeURIComponent(WSPATH)}#Railway-Node`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(`
      <!DOCTYPE html>
      <html>
      <head><title>SpinPanel</title></head>
      <body style="font-family: monospace; padding: 20px;">
        <h1>Xray Panel</h1>
        <p><strong>UUID:</strong> ${UUID}</p>
        <p><strong>WS Path:</strong> ${WSPATH}</p>
        <p><strong>Config (VLESS WS TLS):</strong></p>
        <textarea rows="4" cols="80">${config}</textarea>
        <p><strong>Config (VLESS WS non-TLS):</strong></p>
        <textarea rows="4" cols="80">${config.replace('security=tls&sni='+DOMAIN+'&fp=chrome', 'security=none')}</textarea>
      </body>
      </html>
    `);
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Panel running on port 3000');
});
