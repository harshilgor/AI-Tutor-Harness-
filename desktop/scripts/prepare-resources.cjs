const { cpSync, existsSync, mkdirSync, rmSync } = require('node:fs');
const path = require('node:path');

const desktopRoot = path.resolve(__dirname, '..');
const projectRoot = path.resolve(desktopRoot, '..');
const stagingRoot = path.join(desktopRoot, '.vite', 'resources');
const resources = [
  { source: path.join(projectRoot, 'web', 'dist'), target: path.join(stagingRoot, 'web'), required: path.join('server', 'index.js') },
  { source: path.join(projectRoot, 'backend', 'dist'), target: path.join(stagingRoot, 'backend'), required: path.join('forma-api', process.platform === 'win32' ? 'forma-api.exe' : 'forma-api') },
];

for (const resource of resources) {
  if (!existsSync(path.join(resource.source, resource.required))) {
    throw new Error(`Missing build output: ${path.join(resource.source, resource.required)}. Build this resource before packaging.`);
  }
}

rmSync(stagingRoot, { recursive: true, force: true });
mkdirSync(stagingRoot, { recursive: true });
for (const resource of resources) cpSync(resource.source, resource.target, { recursive: true });
