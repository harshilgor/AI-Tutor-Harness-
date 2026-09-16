const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

async function startWebServer({ root, port }) {
  const module = await import(pathToFileURL(path.join(root, 'server', 'index.js')).href);
  const handler = module.default;
  const server = http.createServer(async (incoming, outgoing) => {
    try {
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
