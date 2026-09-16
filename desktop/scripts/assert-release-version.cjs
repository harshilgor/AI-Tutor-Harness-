const { version } = require('../package.json');

const tag = process.env.GITHUB_REF_NAME;
const expectedTag = `v${version}`;

if (!tag) {
  console.error('::error::GITHUB_REF_NAME is required for a release build.');
  process.exit(1);
}

if (tag !== expectedTag) {
  console.error(`::error::Release tag ${tag} must exactly match desktop/package.json version ${expectedTag}.`);
  process.exit(1);
}

console.log(`Release version verified: ${tag}`);
