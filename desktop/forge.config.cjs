const path = require('node:path');
const owner = process.env.GITHUB_OWNER;
const repository = process.env.GITHUB_REPOSITORY;
const stagedResources = path.join(__dirname, '.vite', 'resources');

module.exports = {
  packagerConfig: {
    asar: true,
    name: 'Forma',
    executableName: 'forma',
    appBundleId: 'dev.forma.learning',
    extraResource: [
      path.join(stagedResources, 'web'),
      path.join(stagedResources, 'backend')
    ]
  },
  rebuildConfig: {},
  makers: [
    { name: '@electron-forge/maker-squirrel', config: { name: 'forma', authors: 'Forma Contributors', description: 'Local-first AI learning environment' } },
    { name: '@electron-forge/maker-dmg', platforms: ['darwin'] },
    { name: '@electron-forge/maker-zip', platforms: ['darwin', 'win32'] }
  ],
  ...(owner && repository ? { publishers: [
    { name: '@electron-forge/publisher-github', config: { repository: { owner, name: repository } } }
  ] } : {})
};
