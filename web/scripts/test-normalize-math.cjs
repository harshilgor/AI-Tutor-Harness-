const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

function loadTs(relativePath) {
  const filename = path.resolve(__dirname, relativePath);
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = new Module(filename, module);
  mod.filename = filename;
  mod.paths = Module._nodeModulePaths(path.dirname(filename));
  mod._compile(compiled, filename);
  return mod.exports;
}

const { normalizeMathMarkdown } = loadTs('../lib/normalize-math-markdown.ts');

const converted = normalizeMathMarkdown('See \\[a\\] and \\(b\\)');
assert.match(converted, /\$\$/);
assert.match(converted, /\$b\$/);
assert.doesNotMatch(converted, /\\\[|\\\(/);

const streaming = normalizeMathMarkdown('Intro\n\\[\n\\begin{bmatrix}\n1 & 2');
assert.match(streaming, /\$\$/);
assert.doesNotMatch(streaming, /\\\[/);

console.log('normalize-math-markdown: ok');
