const fs = require('node:fs');

const platform = process.env.RUNNER_OS;
const failures = [];

function requireValue(name) {
  if (!process.env[name]) failures.push(name);
}

if (platform === 'Windows') {
  requireValue('WINDOWS_CERTIFICATE_FILE');
  requireValue('WINDOWS_CERTIFICATE_PASSWORD');
  if (process.env.WINDOWS_CERTIFICATE_FILE && !fs.existsSync(process.env.WINDOWS_CERTIFICATE_FILE)) {
    failures.push('WINDOWS_CERTIFICATE_FILE (file does not exist)');
  }
} else if (platform === 'macOS') {
  requireValue('APPLE_ID');
  requireValue('APPLE_APP_SPECIFIC_PASSWORD');
  requireValue('APPLE_TEAM_ID');
  requireValue('MACOS_CERTIFICATE_IMPORTED');
  if (process.env.MACOS_CERTIFICATE_IMPORTED !== 'true') {
    failures.push('MACOS_CERTIFICATE_IMPORTED=true');
  }
} else {
  failures.push(`unsupported signing platform ${platform || 'unknown'}`);
}

if (failures.length > 0) {
  console.error(`::error::Refusing to build a public release without signing configuration: ${failures.join(', ')}.`);
  process.exit(1);
}

console.log(`Signing configuration verified for ${platform}.`);
