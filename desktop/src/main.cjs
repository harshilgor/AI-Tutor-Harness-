const { app, BrowserWindow, dialog, ipcMain, Menu, Notification, safeStorage, shell } = require('electron');
const { spawn } = require('node:child_process');
const { existsSync } = require('node:fs');
const { readFileSync, writeFileSync, mkdirSync } = require('node:fs');
const { randomBytes } = require('node:crypto');
const net = require('node:net');
const path = require('node:path');
const http = require('node:http');
const { startWebServer } = require('./web-server.cjs');

if (require('electron-squirrel-startup')) app.quit();

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) app.quit();

const isDev = process.argv.includes('--dev') || !app.isPackaged;
const projectRoot = path.resolve(__dirname, '..', '..');
const configuredApiPort = Number(process.env.FORMA_API_PORT);
let apiPort = Number.isInteger(configuredApiPort) && configuredApiPort > 0 && configuredApiPort < 65536 ? configuredApiPort : undefined;
let webPort;
let apiProcess;
let webProcess;
let window;
let apiToken;
let shuttingDown = false;
let restartAttempts = 0;
let restartTimer;
let reviewTimer;

function runtimePaths() {
  const root = app.getPath('userData');
  return {
    root,
    data: path.join(root, 'data'),
    materials: path.join(root, 'materials'),
    logs: path.join(root, 'logs'),
    cache: path.join(root, 'cache'),
  };
}

function ensureRuntimeDirectories() {
  const paths = runtimePaths();
  for (const directory of Object.values(paths)) mkdirSync(directory, { recursive: true });
  return paths;
}

function availableLoopbackPort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close(error => error ? reject(error) : resolve(address.port));
    });
  });
}

function credentialFile() { return path.join(app.getPath('userData'), 'credentials.json'); }
function preferencesFile() { return path.join(app.getPath('userData'), 'preferences.json'); }
function readPreferences() { try { return JSON.parse(readFileSync(preferencesFile(), 'utf8')); } catch { return {}; } }
function writePreferences(values) { mkdirSync(app.getPath('userData'), { recursive: true }); writeFileSync(preferencesFile(), JSON.stringify(values), { mode: 0o600 }); }
function readCredentials() {
  try { return JSON.parse(readFileSync(credentialFile(), 'utf8')); } catch { return {}; }
}
function writeCredentials(values) {
  mkdirSync(app.getPath('userData'), { recursive: true });
  writeFileSync(credentialFile(), JSON.stringify(values), { mode: 0o600 });
}
function readCredential(key) {
  const value = readCredentials()[key];
  if (!value || !safeStorage.isEncryptionAvailable()) return undefined;
  try { return safeStorage.decryptString(Buffer.from(value, 'base64')); } catch { return undefined; }
}
function configureCredentialBridge() {
  ipcMain.handle('credentials:has', (_event, key) => Boolean(readCredential(key)));
  ipcMain.handle('credentials:get', (_event, key) => {
    const value = readCredentials()[key];
    if (!value || !safeStorage.isEncryptionAvailable()) return null;
    try { return safeStorage.decryptString(Buffer.from(value, 'base64')); } catch { return null; }
  });
  ipcMain.handle('credentials:set', (_event, key, value) => {
    if (typeof key !== 'string' || !/^[a-z][a-z0-9_.-]{0,80}$/i.test(key) || typeof value !== 'string' || value.length > 20000) throw new Error('Invalid credential.');
    if (!safeStorage.isEncryptionAvailable()) throw new Error('Secure credential storage is unavailable on this device.');
    const values = readCredentials();
    values[key] = safeStorage.encryptString(value).toString('base64');
    writeCredentials(values);
    return true;
  });
  ipcMain.handle('credentials:delete', (_event, key) => { const values = readCredentials(); delete values[key]; writeCredentials(values); return true; });
  ipcMain.handle('preferences:get', () => ({ reviewNotifications: readPreferences().reviewNotifications === true }));
  ipcMain.handle('preferences:set', (_event, values) => {
    if (!values || typeof values.reviewNotifications !== 'boolean') throw new Error('Invalid desktop preference.');
    const next = { ...readPreferences(), reviewNotifications: values.reviewNotifications };
    writePreferences(next);
    if (next.reviewNotifications) void notifyDueReviews();
    return { reviewNotifications: next.reviewNotifications };
  });
}

function notifyServiceStatus(status) { window?.webContents.send('forma:service-status', status); }

async function notifyDueReviews() {
  const preferences = readPreferences();
  if (!preferences.reviewNotifications || !apiPort || !apiToken || !Notification.isSupported()) return;
  try {
    const response = await fetch(`http://127.0.0.1:${apiPort}/v1/learners/local/review-queue`, { headers: { 'X-Forma-Desktop-Token': apiToken } });
    if (!response.ok) return;
    const due = await response.json();
    const notified = preferences.notifiedReviewKeys && typeof preferences.notifiedReviewKeys === 'object' ? preferences.notifiedReviewKeys : {};
    let changed = false;
    for (const review of due) {
      const key = `${review.id}:${review.due_at}`;
      if (notified[key]) continue;
      new Notification({ title: 'A Forma review is ready', body: `Revisit ${review.concept_id.replace(/[_-]/g, ' ')} while it is fresh.` }).show();
      notified[key] = new Date().toISOString(); changed = true;
    }
    if (changed) writePreferences({ ...preferences, notifiedReviewKeys: notified });
  } catch (error) { console.error('Could not check due Forma reviews', error); }
}

function startReviewNotifications() {
  clearInterval(reviewTimer);
  void notifyDueReviews();
  reviewTimer = setInterval(() => void notifyDueReviews(), 5 * 60 * 1000);
}

function scheduleApiRestart() {
  if (shuttingDown || restartTimer || restartAttempts >= 3) return;
  const delay = 1000 * (2 ** restartAttempts); restartAttempts += 1;
  notifyServiceStatus({ state: 'restarting', attempt: restartAttempts });
  restartTimer = setTimeout(() => {
    restartTimer = undefined;
    startApi().then(() => { restartAttempts = 0; startReviewNotifications(); notifyServiceStatus({ state: 'ready' }); })
      .catch(error => { console.error('Forma API restart failed', error); scheduleApiRestart(); });
  }, delay);
}

function configureApplicationMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { role: 'appMenu' },
    { label: 'File', submenu: [
      { label: 'Local data settings', click: () => window?.webContents.send('forma:open-settings') },
      { type: 'separator' },
      { role: 'quit' },
    ] },
    { role: 'viewMenu' },
    { role: 'windowMenu' },
  ]));
}

function checkHealth() {
  return new Promise(resolve => {
    const request = http.get(`http://127.0.0.1:${apiPort}/health`, response => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', chunk => { body += chunk; });
      response.on('end', () => {
        try { resolve(response.statusCode === 200 && JSON.parse(body).service === 'learning-harness'); }
        catch { resolve(false); }
      });
    });
    request.setTimeout(1500, () => { request.destroy(); resolve(false); });
    request.on('error', () => resolve(false));
  });
}

function pythonExecutable() {
  const configured = process.env.FORMA_PYTHON;
  if (configured && existsSync(configured)) return configured;
  const executableName = process.platform === 'win32' ? 'forma-api.exe' : 'forma-api';
  const bundledCandidates = [
    path.join(process.resourcesPath, 'backend', 'forma-api', executableName),
    path.join(process.resourcesPath, 'backend', executableName),
  ];
  if (!isDev) {
    const bundled = bundledCandidates.find((candidate) => existsSync(candidate));
    if (bundled) return bundled;
  }
  const local = path.join(projectRoot, 'backend', '.venv', process.platform === 'win32' ? 'Scripts' : 'bin', process.platform === 'win32' ? 'python.exe' : 'python');
  return existsSync(local) ? local : (process.platform === 'win32' ? 'python.exe' : 'python3');
}

async function startApi() {
  if (isDev && !apiPort) apiPort = 8000;
  if (isDev && await checkHealth()) return;
  if (!apiPort) apiPort = await availableLoopbackPort();
  const paths = ensureRuntimeDirectories();
  apiToken = apiToken || randomBytes(32).toString('hex');
  process.env.FORMA_API_TOKEN = apiToken;
  process.env.FORMA_API_PORT = String(apiPort);
  const executable = pythonExecutable();
  const providerEnvironment = {};
  for (const key of ['OPENROUTER_API_KEY', 'OPENAI_API_KEY']) {
    const value = readCredential(key);
    if (value) providerEnvironment[key] = value;
  }
  const args = isDev || !executable.endsWith('forma-api.exe') && !executable.endsWith('forma-api')
    ? ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(apiPort)]
    : ['--host', '127.0.0.1', '--port', String(apiPort)];
  const child = spawn(executable, args, {
    cwd: projectRoot,
    env: { ...process.env, ...providerEnvironment, DATABASE_URL: '', AI_TUTOR_ENV: 'development', FORMA_DB_PATH: path.join(paths.data, 'forma.db'), AI_TUTOR_MATERIAL_DIR: paths.materials, FORMA_API_TOKEN: apiToken, FORMA_API_HOST: '127.0.0.1', FORMA_API_PORT: String(apiPort), FORMA_WEB_ORIGIN: `http://127.0.0.1:${webPort || 3000}` },
    stdio: isDev ? 'inherit' : 'ignore',
    windowsHide: true
  });
  apiProcess = child;
  child.on('error', error => console.error('Forma API failed to start', error));
  child.on('exit', (code, signal) => {
    if (apiProcess === child) apiProcess = undefined;
    if (!shuttingDown && !child.killed) {
      console.error(`Forma API stopped unexpectedly (code=${code ?? 'null'}, signal=${signal ?? 'none'})`);
      scheduleApiRestart();
    }
  });
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (await checkHealth()) { restartAttempts = 0; return; }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`The local tutor service did not start on port ${apiPort}.`);
}

function stopApi() {
  clearTimeout(restartTimer); restartTimer = undefined;
  if (!apiProcess || apiProcess.killed) return;
  apiProcess.kill();
  apiProcess = undefined;
}

async function createWindow() {
  if (!isDev) webPort = await availableLoopbackPort();
  await startApi();
  window = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 960,
    minHeight: 680,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.cjs')
    }
  });
  window.once('ready-to-show', () => window.show());
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) void shell.openExternal(url);
    return { action: 'deny' };
  });
  if (isDev) await window.loadURL(process.env.FORMA_WEB_URL || 'http://127.0.0.1:3000');
  else {
    webProcess = await startWebServer({ root: path.join(process.resourcesPath, 'web'), port: webPort });
    await window.loadURL(`http://127.0.0.1:${webPort}`);
  }
}

app.whenReady().then(() => {
  if (!hasSingleInstanceLock) return;
  configureCredentialBridge();
  configureApplicationMenu();
  return createWindow().then(() => startReviewNotifications()).catch(error => {
    dialog.showErrorBox('Forma could not start', error.message);
    app.quit();
  });
});
app.on('window-all-closed', () => { shuttingDown = true; stopApi(); clearInterval(reviewTimer); webProcess?.close(); if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => { shuttingDown = true; stopApi(); clearInterval(reviewTimer); webProcess?.close(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) void createWindow(); });
