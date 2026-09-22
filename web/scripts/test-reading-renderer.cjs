// Exercise the actual TSX renderer with a CSS-only stub in Node.
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const assert = require('node:assert/strict');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

function loadTsx(relativePath) {
  const filename = path.resolve(__dirname, relativePath);
  if (require.cache[filename]) return require.cache[filename].exports;
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
      esModuleInterop: true,
      target: ts.ScriptTarget.ES2022,
      moduleResolution: ts.ModuleResolutionKind.NodeJs,
    },
  }).outputText;
  const renderer = new Module(filename, module);
  renderer.filename = filename;
  renderer.paths = Module._nodeModulePaths(path.dirname(filename));
  const originalRequire = renderer.require.bind(renderer);
  renderer.require = (name) => {
    if (name.endsWith('.css')) return new Proxy({}, { get: (_, property) => String(property) });
    if (name.startsWith('@/')) {
      const resolved = path.resolve(__dirname, '..', name.slice(2));
      const withTs = fs.existsSync(resolved + '.ts') ? resolved + '.ts'
        : fs.existsSync(resolved + '.tsx') ? resolved + '.tsx'
        : resolved;
      if (withTs.endsWith('.ts') || withTs.endsWith('.tsx')) {
        return loadTsx(path.relative(__dirname, withTs));
      }
      return originalRequire(withTs);
    }
    return originalRequire(name);
  };
  require.cache[filename] = renderer;
  renderer._compile(compiled, filename);
  return renderer.exports;
}

const { normalizeMathMarkdown } = loadTsx('../lib/normalize-math-markdown.ts');
const { RichContent } = loadTsx('../components/rich-content.tsx');
const render = (body) => renderToStaticMarkup(React.createElement(RichContent, { body, onExplore() {} }));

const matrixBody = String.raw`Weights can be arranged into a matrix:

$$
W =
\begin{bmatrix}
1 & 2 \\
-1 & 0.5
\end{bmatrix}
$$

Multiplying the matrix by the input vector:

$$
W\mathbf{x}
=
\begin{bmatrix}
1 & 2 \\
-1 & 0.5
\end{bmatrix}
\begin{bmatrix}
3 \\
5
\end{bmatrix}
=
\begin{bmatrix}
1(3)+2(5) \\
-1(3)+0.5(5)
\end{bmatrix}
=
\begin{bmatrix}
13 \\
-0.5
\end{bmatrix}
$$

So one compact matrix expression represents two weighted combinations at once.`;

const texDelimiterBody = String.raw`Weights can be arranged into a matrix:

\[
W =
\begin{bmatrix}
1 & 2 \\
-1 & 0.5
\end{bmatrix}
\]

The loss is \(L = -\log p(y|x)\).`;

// Normalizer unit checks
assert.match(normalizeMathMarkdown(String.raw`\[x^2\]`), /\$\$/);
assert.match(normalizeMathMarkdown(String.raw`Inline \(a+b\) here`), /\$a\+b\$/);
assert.match(
  normalizeMathMarkdown(String.raw`Bare \begin{bmatrix}1 & 2\\3 & 4\end{bmatrix} matrix`),
  /\$\$[\s\S]*\\begin\{bmatrix\}/,
);
assert.equal(
  normalizeMathMarkdown('```latex\n\\[E = mc^2\\]\n```'),
  '```latex\n\\[E = mc^2\\]\n```',
);
assert.match(normalizeMathMarkdown(String.raw`The price is $20.`), /\$20/);

// Renderer regressions
const math = render('Inline $x^2$\n\n$$\n\\frac{\\partial L}{\\partial w}\n$$');
assert.match(math, /katex-display/);
assert.match(math, /<math/);
assert.doesNotMatch(math, /Explain this equation/);
assert.doesNotMatch(math, /katex-error/);
assert.match(render('$\\frac{1$'), /katex-error/);
assert.doesNotThrow(() => render('Incomplete $\\frac{'));
assert.doesNotThrow(() => render(String.raw`$$\n\begin{bmatrix}\n1 & 2`));

const screenshot = render(matrixBody);
assert.match(screenshot, /katex-display/);
assert.match(screenshot, /katex/);
assert.doesNotMatch(screenshot.replace(/application\/x-tex[\s\S]*?<\/annotation>/g, ''), /\\begin\{bmatrix\}/);

const texDelims = render(texDelimiterBody);
assert.match(texDelims, /katex-display/);
assert.match(texDelims, /katex/);
assert.doesNotMatch(texDelims.replace(/application\/x-tex[\s\S]*?<\/annotation>/g, ''), /\\begin\{bmatrix\}/);

const aligned = render(String.raw`$$
\begin{aligned}
y &= mx + b \\
y' &= m
\end{aligned}
$$`);
assert.match(aligned, /katex-display/);
assert.doesNotMatch(aligned, /katex-error/);

const cases = render(String.raw`$$
f(x)=
\begin{cases}
x^2 & x>0 \\
0 & x\le0
\end{cases}
$$`);
assert.match(cases, /katex/);
assert.doesNotMatch(cases, /katex-error/);

const mixed = render(String.raw`## Gradient Descent

The update rule is:

$$
\theta_{t+1}
=
\theta_t
-
\eta \nabla_\theta L(\theta_t)
$$

Where:

- $\theta$ is the parameter vector.
- $\eta$ is the learning rate.

| Variable | Meaning |
| --- | --- |
| $\theta$ | Model parameters |
| $\eta$ | Learning rate |

> Keep learning rates small at first.

` + '```python\nprint("$x^2$")\n```');
assert.match(mixed, /katex-display/);
assert.match(mixed, /<table/);
assert.match(mixed, /Copy/);
assert.match(mixed, /print\("\$x\^2\$"\)|print\(&quot;\$x\^2\$&quot;\)/);

const codeSafe = render('```latex\n\\[E = mc^2\\]\n```');
assert.doesNotMatch(codeSafe, /katex-display/);
assert.match(codeSafe, /E = mc\^2|E = mc/);

const unsafe = render('<script>alert(1)</script>\n\n[unsafe](javascript:alert)\n\n<img src=x onerror=alert(1)>');
assert.doesNotMatch(unsafe, /<script|<img|href="javascript:/);
assert.match(render('```details\nShow why\n**A key idea**\n```'), /<details/);
assert.match(render('```text\nA → B\n    ↓\n    C\n```'), /Copy/);
assert.match(render('| Symbol | Meaning |\n| --- | --- |\n| x | Input |'), /<table/);
assert.doesNotMatch(render('The magnitude |x| remains ordinary prose.'), /<table/);
assert.match(render('Legacy plain text remains readable.'), /Legacy plain text remains readable/);
assert.match(render('The price is $20 and stays prose.'), /\$20|20/);

console.log('Reading renderer: math + markdown regression suite passed.');
