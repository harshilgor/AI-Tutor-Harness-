/**
 * Prepare LLM Markdown for remark-math / rehype-katex.
 *
 * micromark-extension-math only recognizes `$…$` / `$$…$$`. Models often emit
 * TeX delimiters `\(...\)` / `\[…\]`, which CommonMark then escapes into `[…]`
 * and eats matrix `\\` row breaks — producing the raw LaTeX screenshot bug.
 *
 * Normalization runs only outside fenced/inline code so code samples stay literal.
 */

const FENCE_OR_INLINE = /(```[\s\S]*?```|`[^`\n]+`)/g;
const DISPLAY_TEX = /\\\[([\s\S]*?)\\\]/g;
const INLINE_TEX = /\\\(([\s\S]*?)\\\)/g;
const BARE_ENV =
  /\\begin\{(bmatrix|pmatrix|vmatrix|Vmatrix|matrix|smallmatrix|aligned|align\*?|cases|gather\*?|eqnarray\*?|array)\}[\s\S]*?\\end\{\1\}/g;

function mapOutsideCode(source: string, transform: (segment: string) => string): string {
  const parts = source.split(FENCE_OR_INLINE);
  return parts.map((part, index) => (index % 2 === 1 ? part : transform(part))).join('');
}

function alreadyMath(segment: string, matchIndex: number): boolean {
  const before = segment.slice(0, matchIndex);
  const dollars = before.match(/\$\$?/g) || [];
  return dollars.length % 2 === 1;
}

function wrapBareEnvironments(segment: string): string {
  return segment.replace(BARE_ENV, (match, _env, offset) => {
    if (alreadyMath(segment, offset)) return match;
    const trimmed = match.trim();
    return `\n\n$$\n${trimmed}\n$$\n\n`;
  });
}

function softenIncompleteOpeners(segment: string): string {
  // Unclosed TeX openers would otherwise become `[` / `(` via Markdown escapes.
  // Promote them to dollar openers so remark-math owns the trailing fragment;
  // rehype-katex uses throwOnError:false for incomplete bodies during streaming.
  // Note: String.replace treats `$$` as a single `$`, so use a replacer function.
  if (/\\\[[\s\S]*$/.test(segment) && !/\\\[[\s\S]*\\\]/.test(segment)) {
    segment = segment.replace(/\\\[/, () => '$$\n');
  }
  if (/\\\([\s\S]*$/.test(segment) && !/\\\([\s\S]*\\\)/.test(segment)) {
    segment = segment.replace(/\\\(/, () => '$');
  }
  return segment;
}

export function normalizeMathMarkdown(source: string): string {
  if (!source) return source;
  return mapOutsideCode(source, (segment) => {
    let next = segment
      .replace(DISPLAY_TEX, (_match, body: string) => `\n\n$$\n${String(body).trim()}\n$$\n\n`)
      .replace(INLINE_TEX, (_match, body: string) => `$${String(body).trim()}$`);
    next = wrapBareEnvironments(next);
    next = softenIncompleteOpeners(next);
    return next;
  });
}
