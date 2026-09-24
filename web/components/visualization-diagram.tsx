"use client";

import { useMemo, useState } from 'react';
import type { VisualizationSpec } from '@/lib/visualization-spec';
import { layoutDiagram } from '@/lib/visual-layout';
import styles from './visualization.module.css';

export function DiagramRenderer({ spec }: { spec: VisualizationSpec }) {
  const layout = useMemo(() => layoutDiagram(spec.nodes, spec.edges), [spec.nodes, spec.edges]);
  const [practice, setPractice] = useState(false);
  const [revealed, setRevealed] = useState<string[]>([]);
  const markerId = `visual-arrow-${spec.id}`;
  const nodeNames = new Map(spec.nodes.map(n => [n.id, n.label]));
  return <>
    <div className={styles.diagramToolbar}>
      <span>{spec.type === 'architecture' ? 'Components and connections' : spec.type === 'concept' ? 'Ideas and relationships' : 'Process steps'}</span>
      <button type="button" onClick={() => { setPractice(value => !value); setRevealed([]); }}
        aria-pressed={practice}>{practice ? 'Show labels' : 'Practice labels'}</button>
    </div>
    <div className={styles.diagramScroll}>
      <svg width={layout.width} height={layout.height} viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="img" aria-label={spec.description || spec.title}>
        <defs><marker id={markerId} markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
          <path d="M0 0 L9 4.5 L0 9 Z" className={styles.arrowhead} /></marker></defs>
        {layout.groups.map(group => <g key={group.label}><rect className={styles.diagramGroup} x={group.x} y={group.y}
          width={group.width} height={group.height} rx={14}/><text className={styles.groupLabel} x={group.x + 12} y={group.y + 18}>{group.label}</text></g>)}
        {layout.edges.map((edge, i) => {
          const bend = Math.max(20, Math.abs(edge.x2 - edge.x1) / 2);
          const path = `M${edge.x1} ${edge.y1} C${edge.x1 + bend} ${edge.y1},${edge.x2 - bend} ${edge.y2},${edge.x2} ${edge.y2}`;
          return <g key={i}><path d={path} className={edge.emphasis ? styles.diagramEdgeEmphasis : styles.diagramEdge}
            markerEnd={`url(#${markerId})`} /><text className={styles.edgeLabel}
            x={(edge.x1 + edge.x2) / 2} y={(edge.y1 + edge.y2) / 2 - 8}>{edge.label}</text></g>;
        })}
        {layout.nodes.map(node => {
          const hidden = practice && !revealed.includes(node.id);
          const label = hidden ? 'Reveal' : node.label;
          const words = label.split(' ');
          const lines = words.length > 3 ? [words.slice(0, Math.ceil(words.length / 2)).join(' '), words.slice(Math.ceil(words.length / 2)).join(' ')] : [label];
          return <g key={node.id} role={practice ? 'button' : undefined} tabIndex={practice ? 0 : undefined}
            aria-label={hidden ? `Reveal ${node.id}` : node.label}
            onClick={() => setRevealed(old => old.includes(node.id) ? old : [...old, node.id])}
            onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setRevealed(old => old.includes(node.id) ? old : [...old, node.id]); } }}>
            <rect className={node.emphasis ? styles.diagramNodeEmphasis : styles.diagramNode}
              x={node.x - 82} y={node.y - 32} width={164} height={64} rx={10}/>
            <text className={styles.nodeLabel} x={node.x} y={node.y - (lines.length - 1) * 8}>
              {lines.map((line, i) => <tspan key={i} x={node.x} dy={i ? 16 : 0}>{line}</tspan>)}
            </text>
          </g>;
        })}
      </svg>
    </div>
    <details className={styles.dataDetails}><summary>Read the diagram as text</summary>
      <ol>{layout.nodes.map(node => <li key={node.id}><strong>{node.label}</strong>{node.detail ? ` — ${node.detail}` : ''}</li>)}</ol>
      {spec.edges.length > 0 && <p>{spec.edges.map(e => `${nodeNames.get(e.source)} → ${nodeNames.get(e.target)}${e.label ? ` (${e.label})` : ''}`).join('; ')}</p>}
    </details>
  </>;
}
