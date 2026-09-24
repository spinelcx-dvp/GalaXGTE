const http = require('http');

const UUID = process.env.UUID || 'generated-uuid';
const WSPATH = process.env.WSPATH || '/ws';
const PASS = process.env.PASS || '';
const DOMAIN = process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL || 'localhost';
const PANEL_PORT = process.env.PANEL_PORT || 3000;

const server = http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html') {
    const vlessTLS = `vless://${UUID}@${DOMAIN}:443?encryption=none&security=tls&sni=${DOMAIN}&fp=chrome&type=ws&host=${DOMAIN}&path=${encodeURIComponent(WSPATH)}#SpinPanel-TLS`;
    const vlessNoTLS = `vless://${UUID}@${DOMAIN}:80?encryption=none&security=none&type=ws&host=${DOMAIN}&path=${encodeURIComponent(WSPATH)}#SpinPanel-NonTLS`;

    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(`
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpinPanel</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Tahoma, sans-serif;
      background: #0f0f1a;
      color: #e0e0e0;
      margin: 0;
      padding: 20px;
      min-height: 100vh;
    }
    .container { max-width: 800px; margin: 0 auto; }
    h1 { color: #7c5cff; text-align: center; margin-bottom: 30px; }
    .card {
      background: #1a1a2e;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 4px 20px rgba(124, 92, 255, 0.1);
    }
    .label { color: #7c5cff; font-weight: bold; margin-bottom: 8px; display: block; }
    .value {
      background: #0f0f1a;
      padding: 12px;
      border-radius: 8px;
      word-break: break-all;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      color: #a0ffa0;
      border: 1px solid #2a2a4a;
    }
    textarea {
      width: 100%;
      background: #0f0f1a;
      color: #a0ffa0;
      border: 1px solid #2a2a4a;
      border-radius: 8px;
      padding: 12px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      resize: vertical;
      min-height: 80px;
    }
    .copy-btn {
      background: #7c5cff;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      margin-top: 8px;
      font-size: 13px;
    }
    .copy-btn:hover { background: #6a4ce0; }
    .status { text-align: center; color: #a0ffa0; margin-bottom: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🚀 SpinPanel</h1>
    <p class="status">✅ سرویس فعال است</p>

    <div class="card">
      <span class="label">UUID:</span>
      <div class="value">${UUID}</div>
    </div>

    <div class="card">
      <span class="label">WS Path:</span>
      <div class="value">${WSPATH}</div>
    </div>

    <div class="card">
      <span class="label">VLESS WS TLS:</span>
      <textarea readonly onclick="this.select()">${vlessTLS}</textarea>
      <button class="copy-btn" onclick="copyText(this)">کپی</button>
    </div>

    <div class="card">
      <span class="label">VLESS WS Non-TLS:</span>
      <textarea readonly onclick="this.select()">${vlessNoTLS}</textarea>
      <button class="copy-btn" onclick="copyText(this)">کپی</button>
    </div>
  </div>

  <script>
    function copyText(btn) {
      const textarea = btn.previousElementSibling;
      textarea.select();
      document.execCommand('copy');
      btn.textContent = '✓ کپی شد';
      setTimeout(() => btn.textContent = 'کپی', 1500);
    }
  </script>
</body>
</html>
    `);
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  }
});

server.listen(PANEL_PORT, '0.0.0.0', () => {
  console.log(`[Panel] Running on 0.0.0.0:${PANEL_PORT}`);
});
