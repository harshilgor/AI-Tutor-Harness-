/** A small bounded expression interpreter. Model output is never evaluated as JavaScript. */
const functions: Record<string, (value: number) => number> = {
  sin: Math.sin, cos: Math.cos, tan: Math.tan, exp: Math.exp,
  log: Math.log, sqrt: Math.sqrt, abs: Math.abs,
};

export function normalizeMathExpression(raw: string): string {
  let text = raw.trim().replace(/π/g, 'pi').replace(/−/g, '-').replace(/×/g, '*').replace(/÷/g, '/')
    .replace(/²/g, '^2').replace(/³/g, '^3');
  text = text.replace(/(\d|\))\s*(x|pi|e)\b/g, '$1*$2')
    .replace(/(\d|x|\))\s*\(/g, '$1*(')
    .replace(/(\d|\))\s*(sin|cos|tan|exp|log|sqrt|abs)\b/g, '$1*$2');
  return text;
}

export function compileMathExpression(raw: string): ((x: number) => number) | null {
  if (raw.length > 120) return null;
  const source = normalizeMathExpression(raw);
  const tokens = source.match(/[A-Za-z_][A-Za-z_0-9]*|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[()+*/^,-]/g) ?? [];
  if (!tokens.length || tokens.join('') !== source.replace(/\s/g, '') || tokens.length > 60) return null;
  let index = 0;
  type Operation = (x: number) => number;
  const primary = (depth: number): Operation => {
    if (depth > 32) throw Error('Expression nesting limit');
    const token = tokens[index++];
    if (token === '(') {
      const value = addition(depth + 1);
      if (tokens[index++] !== ')') throw Error('Unclosed group');
      return value;
    }
    if (token === 'x') return x => x;
    if (token === 'e') return () => Math.E;
    if (token === 'pi') return () => Math.PI;
    if (Object.hasOwn(functions, token)) {
      if (tokens[index++] !== '(') throw Error('Function argument required');
      const argument = addition(depth + 1);
      if (tokens[index++] !== ')') throw Error('Unclosed function');
      return x => functions[token](argument(x));
    }
    if (/^(?:\d|\.)/.test(token || '')) {
      const value = Number(token);
      if (!Number.isFinite(value) || Math.abs(value) > 1e6) throw Error('Constant is too large');
      return () => value;
    }
    throw Error('Unknown symbol');
  };
  const power = (depth: number): Operation => {
    const left = primary(depth + 1);
    if (tokens[index] !== '^') return left;
    index++;
    const right = unary(depth + 1);
    return x => Math.pow(left(x), right(x));
  };
  const unary = (depth: number): Operation => {
    if (tokens[index] === '-' || tokens[index] === '+') {
      const sign = tokens[index++] === '-' ? -1 : 1;
      const value = unary(depth + 1);
      return x => sign * value(x);
    }
    return power(depth + 1);
  };
  const multiplication = (depth: number): Operation => {
    let left = unary(depth + 1);
    while (tokens[index] === '*' || tokens[index] === '/') {
      const operator = tokens[index++], previous = left, right = unary(depth + 1);
      left = operator === '*' ? x => previous(x) * right(x) : x => previous(x) / right(x);
    }
    return left;
  };
  const addition = (depth: number): Operation => {
    let left = multiplication(depth + 1);
    while (tokens[index] === '+' || tokens[index] === '-') {
      const operator = tokens[index++], previous = left, right = multiplication(depth + 1);
      left = operator === '+' ? x => previous(x) + right(x) : x => previous(x) - right(x);
    }
    return left;
  };
  try {
    const operation = addition(0);
    return index === tokens.length ? operation : null;
  } catch {
    return null;
  }
}

export type PlotPoint = { x: number; y: number | null };
export function sampleFunction(expression: string, domain: readonly [number, number], count = 181): PlotPoint[] {
  const operation = compileMathExpression(expression);
  if (!operation || domain[0] >= domain[1] || Math.max(Math.abs(domain[0]), Math.abs(domain[1])) > 1e6) return [];
  const samples: PlotPoint[] = [];
  for (let i = 0; i < Math.min(241, Math.max(21, count)); i++) {
    const x = domain[0] + (domain[1] - domain[0]) * i / (Math.min(241, Math.max(21, count)) - 1);
    let y: number | null;
    try {
      const result = operation(x);
      y = Number.isFinite(result) && Math.abs(result) < 1e6 ? result : null;
    } catch { y = null; }
    samples.push({ x, y });
  }
  // A vertical asymptote should not become a diagonal line across the chart.
  for (let i = 1; i < samples.length; i++) {
    const a = samples[i - 1].y, b = samples[i].y;
    if (a !== null && b !== null && Math.sign(a) !== Math.sign(b) && Math.abs(a - b) > 40) samples[i].y = null;
  }
  return samples;
}

export function normalDistribution(mean: number, sigma: number, count = 121): PlotPoint[] {
  if (!Number.isFinite(mean) || !Number.isFinite(sigma) || !Number.isFinite(count) || sigma <= 0 || sigma > 1e4) return [];
  const length = Math.min(241, Math.max(2, Math.floor(count)));
  return Array.from({ length }, (_, i) => {
    const x = mean - 4 * sigma + 8 * sigma * i / (length - 1);
    return { x, y: Math.exp(-0.5 * ((x - mean) / sigma) ** 2) / (sigma * Math.sqrt(2 * Math.PI)) };
  });
}

export function binomialDistribution(n: number, p: number): PlotPoint[] {
  if (!Number.isInteger(n) || n < 1 || n > 100 || !Number.isFinite(p) || p < 0 || p > 1) return [];
  const choose = (k: number) => {
    let result = 1;
    for (let i = 1; i <= k; i++) result = result * (n - i + 1) / i;
    return result;
  };
  return Array.from({ length: n + 1 }, (_, k) => ({
    x: k, y: choose(k) * p ** k * (1 - p) ** (n - k),
  }));
}
