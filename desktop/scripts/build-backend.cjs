const { spawnSync } = require('node:child_process');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const python = process.env.FORMA_PYTHON || (process.platform === 'win32'
  ? path.join(root, 'backend', '.venv', 'Scripts', 'python.exe')
  : path.join(root, 'backend', '.venv', 'bin', 'python'));
const executable = process.platform === 'win32' ? `${python}` : (python || 'python3');
const result = spawnSync(executable, [
  '-m', 'PyInstaller', path.join(root, 'backend', 'forma-api.spec'),
  '--noconfirm', '--distpath', path.join(root, 'backend', 'dist'),
  '--workpath', path.join(root, 'backend', 'build')
], { cwd: root, stdio: 'inherit', windowsHide: true });
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status || 1);
