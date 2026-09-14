"use client";

import { Children, isValidElement, useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import styles from './reading.module.css';

type SourceNode = { type?: string; tagName?: string; value?: string; children?: SourceNode[]; properties?: Record<string, unknown> };
function texSource(node: SourceNode): string {
  if (node.tagName === 'annotation' && node.properties?.encoding === 'application/x-tex') return node.children?.map(child => child.value || '').join('') || '';
  return node.children?.map(texSource).find(Boolean) || '';
}
function CodeBlock({ children, onExplore }: { children?: ReactNode; onExplore?: (raw: string, equation?: boolean) => void }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  const child = Children.toArray(children)[0];
  const props = isValidElement<{ className?: string; children?: ReactNode }>(child) ? child.props : {};
  const language = props.className?.replace('language-', '') || 'text';
  const raw = String(props.children || '').replace(/\n$/, '');
  if (language === 'details') {
    const [title, ...body] = raw.split('\n');
    return <details className={styles.detail}><summary>{title || 'A closer look'}</summary><RichContent body={body.join('\n')} onExplore={onExplore} /></details>;
  }
  return <div className={styles.code}><div className={styles.codeTop}><span>{language}</span><button type="button" onClick={async () => { try { await navigator.clipboard.writeText(raw); setCopied(true); setError(false); } catch { setError(true); } }}>{copied ? 'Copied' : 'Copy'}</button></div><pre>{children}</pre>{error && <span role="status">Copy unavailable. Select the text to copy it.</span>}</div>;
}

export function RichContent({ body, onExplore }: { body: string; onExplore?: (raw: string, equation?: boolean) => void }) {
  return <div className={styles.rich}><ReactMarkdown remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: true }]]}
    rehypePlugins={[[rehypeKatex, { throwOnError: false, trust: false, maxExpand: 1000, maxSize: 20, output: 'htmlAndMathml', strict: 'warn' }]]}
    skipHtml components={{
      pre: ({ children }) => <CodeBlock onExplore={onExplore}>{children}</CodeBlock>,
      a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
      img: ({ alt }) => <span className={styles.imagePlaceholder}>{alt || 'Image reference'}</span>,
      table: ({ children }) => <div className={styles.table}><table>{children}</table></div>,
      span: ({ node, children, className, ...props }) => {
        if (className?.split(' ').includes('katex-display')) {
          const tex = texSource(node as SourceNode);
          return <span className={styles.equation}><span className={styles.mathScroll}><span {...props} className={className}>{children}</span></span>{onExplore && tex && <button type="button" className={styles.equationHelp} onClick={() => onExplore(tex, true)}>Explain this equation ↗</button>}</span>;
        }
        return <span {...props} className={className}>{children}</span>;
      },
      p: ({ node, children }) => <p onMouseUp={event => {
        if (!onExplore) return;
        const selection = window.getSelection();
        const selected = selection?.toString().trim();
        if (!selected || !event.currentTarget.contains(selection!.anchorNode) || !event.currentTarget.contains(selection!.focusNode)) return;
        const raw = body.slice(node?.position?.start.offset ?? 0, node?.position?.end.offset ?? body.length);
        onExplore(raw.includes(selected) ? selected.slice(0, 1200) : raw.slice(0, 1200));
      }}>{children}</p>,
    }}>{body}</ReactMarkdown></div>;
}
