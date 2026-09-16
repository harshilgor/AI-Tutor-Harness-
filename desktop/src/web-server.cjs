const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.woff': 'font/woff', '.woff2': 'font/woff2'
};

function staticAsset(root, requestUrl) {
  const pathname = new URL(requestUrl, 'http://127.0.0.1').pathname;
  // Vinext emits browser assets under client/ and server-only chunks under
  // server/. The HTML references the former, so try it first.
  for (const assetRoot of [path.resolve(root, 'client'), path.resolve(root, 'server')]) {
    const candidate = path.resolve(assetRoot, `.${pathname}`);
    const relative = path.relative(assetRoot, candidate);
    if (relative.startsWith('..') || path.isAbsolute(relative)) continue;
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  }
  return null;
}

async function startWebServer({ root, port }) {
  const module = await import(pathToFileURL(path.join(root, 'server', 'index.js')).href);
  const handler = module.default;
  const server = http.createServer(async (incoming, outgoing) => {
    try {
      const asset = (incoming.method === 'GET' || incoming.method === 'HEAD') && staticAsset(root, incoming.url || '/');
      if (asset) {
        const immutable = new URL(incoming.url || '/', 'http://127.0.0.1').pathname.startsWith('/_next/static/');
        outgoing.writeHead(200, { 'Content-Type': MIME_TYPES[path.extname(asset).toLowerCase()] || 'application/octet-stream', 'Cache-Control': immutable ? 'public, max-age=31536000, immutable' : 'no-cache' });
        if (incoming.method !== 'HEAD') fs.createReadStream(asset).pipe(outgoing); else outgoing.end();
        return;
      }
      const chunks = [];
      for await (const chunk of incoming) chunks.push(chunk);
      const body = chunks.length && incoming.method !== 'GET' && incoming.method !== 'HEAD' ? Buffer.concat(chunks) : undefined;
      const request = new Request(`http://127.0.0.1:${port}${incoming.url || '/'}`, {
        method: incoming.method,
        headers: incoming.headers,
        body,
        duplex: body ? 'half' : undefined
      });
      const response = await handler.fetch(request, {});
      outgoing.writeHead(response.status, Object.fromEntries(response.headers));
      if (response.body) {
        for await (const chunk of response.body) outgoing.write(Buffer.from(chunk));
      }
      outgoing.end();
    } catch (error) {
      outgoing.statusCode = 500;
      outgoing.end('Forma web server failed.');
      console.error(error);
    }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  return server;
}

if (require.main === module) {
  const root = process.argv[2];
  const port = Number(process.argv[3] || 3000);
  if (!root || !fs.existsSync(path.join(root, 'server', 'index.js'))) throw new Error('A built web directory is required.');
  startWebServer({ root, port }).catch(error => { console.error(error); process.exitCode = 1; });
}

module.exports = { startWebServer };
