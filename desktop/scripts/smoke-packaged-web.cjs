const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const { startWebServer } = require('../src/web-server.cjs');

function availablePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(error => error ? reject(error) : resolve(port));
    });
  });
}

function request(port, pathname) {
  return new Promise((resolve, reject) => {
    const req = http.get({ hostname: '127.0.0.1', port, path: pathname }, response => {
      const chunks = [];
      response.on('data', chunk => chunks.push(chunk));
      response.on('end', () => resolve({ status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.once('error', reject);
  });
}

async function main() {
  const root = process.argv[2] || path.join(__dirname, '..', '.vite', 'resources', 'web');
  const port = await availablePort();
  const server = await startWebServer({ root, port });
  try {
    const page = await request(port, '/');
    if (page.status !== 200) throw new Error(`Expected homepage status 200, received ${page.status}.`);
    const match = page.body.match(/href=["']([^"']*\/_next\/[^"']+\.css[^"']*)["']/i);
    if (!match) throw new Error('The packaged homepage did not reference a CSS asset.');
    const stylesheet = await request(port, match[1]);
    if (stylesheet.status !== 200) throw new Error(`Expected stylesheet status 200, received ${stylesheet.status} for ${match[1]}.`);
    if (!String(stylesheet.headers['content-type']).startsWith('text/css')) throw new Error(`Expected a CSS content type, received ${stylesheet.headers['content-type']}.`);
    if (!stylesheet.body.trim()) throw new Error('The packaged stylesheet was empty.');
    const scriptMatch = page.body.match(/src=["']([^"']*\/_next\/[^"']+\.js[^"']*)["']/i);
    if (!scriptMatch) throw new Error('The packaged homepage did not reference a JavaScript asset.');
    const script = await request(port, scriptMatch[1]);
    if (script.status !== 200) throw new Error(`Expected JavaScript status 200, received ${script.status} for ${scriptMatch[1]}.`);
    if (!String(script.headers['content-type']).includes('javascript')) throw new Error(`Expected a JavaScript content type, received ${script.headers['content-type']}.`);
    if (!script.body.trim()) throw new Error('The packaged JavaScript asset was empty.');
    console.log(`Packaged web smoke test passed: ${match[1]}`);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
