const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({ ws: true });
const port = process.env.PORT || 8000;

proxy.on('error', (err, req, res) => {
  console.error('Proxy error:', err);
  if (res.writeHead) {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('Bad Gateway');
  }
});

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    proxy.web(req, res, { target: 'http://127.0.0.1:8010' });
  } else if (req.url.startsWith('/vnc') || req.url.startsWith('/websockify')) {
    // Basic routing for noVNC if needed
    proxy.web(req, res, { target: 'http://127.0.0.1:6082' });
  } else {
    proxy.web(req, res, { target: 'http://127.0.0.1:3000' });
  }
});

server.on('upgrade', (req, socket, head) => {
  if (req.url.startsWith('/api/')) {
    proxy.ws(req, socket, head, { target: 'http://127.0.0.1:8010' });
  } else if (req.url.startsWith('/vnc') || req.url.startsWith('/websockify')) {
    proxy.ws(req, socket, head, { target: 'http://127.0.0.1:6082' });
  } else {
    proxy.ws(req, socket, head, { target: 'http://127.0.0.1:3000' });
  }
});

console.log(`Unified Proxy listening on port ${port}`);
server.listen(port);
