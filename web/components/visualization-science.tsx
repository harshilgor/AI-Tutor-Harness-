"use client";

import { useId } from 'react';
import type { VisualizationSpec } from '@/lib/visualization-spec';
import styles from './visualization.module.css';

const sx = (x: number) => 300 + x * 25;
const sy = (y: number) => 160 - y * 13;

export function ScienceRenderer({ spec }: { spec: VisualizationSpec }) {
  const marker = useId().replace(/:/g, '_');
  return <>
    <div className={styles.scienceFrame}>
      <svg viewBox="0 0 600 320" role="img" aria-label={spec.description || spec.title}>
        <defs><marker id={marker} markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
          <path d="M0 0 L9 4.5 L0 9 Z" className={styles.arrowhead}/></marker></defs>
        {spec.primitives.map((item, index) => {
          const x = sx(item.x), y = sy(item.y);
          const x2 = sx(item.x2 ?? item.x + 2), y2 = sy(item.y2 ?? item.y + 2);
          const label = item.label && <text className={styles.scienceLabel} x={x + 7} y={y - 14}>{item.label}</text>;
          if (item.kind === 'axis') return <g key={index}><path className={styles.scienceAxis} d={`M50 ${y} H550 M${x} 24 V296`}/>{label}</g>;
          if (['force', 'vector', 'velocity'].includes(item.kind)) return <g key={index}><line className={styles.scienceVector}
            x1={x} y1={y} x2={x2} y2={y2} markerEnd={`url(#${marker})`}/>{label}</g>;
          if (item.kind === 'trajectory' || item.kind === 'field_line') return <g key={index}><path
            className={item.kind === 'field_line' ? styles.fieldLine : styles.trajectory}
            d={`M${x} ${y} Q${(x + x2) / 2} ${Math.min(y, y2) - 70} ${x2} ${y2}`}
            markerEnd={item.kind === 'field_line' ? `url(#${marker})` : undefined}/>{label}</g>;
          if (item.kind === 'wave') {
            const path = Array.from({ length: 41 }, (_, i) => {
              const px = x + (x2 - x) * i / 40;
              const py = y + Math.sin(i / 40 * Math.PI * 4) * 24;
              return `${i ? 'L' : 'M'}${px} ${py}`;
            }).join(' ');
            return <g key={index}><path className={styles.trajectory} d={path}/>{label}</g>;
          }
          if (item.kind === 'object' || item.kind === 'circuit_component') return <g key={index}>
            <rect className={styles.scienceObject} x={x - 38} y={y - 25} width={76} height={50} rx={item.kind === 'object' ? 6 : 2}/>
            {item.label && <text className={styles.scienceCenter} x={x} y={y + 4}>{item.label}</text>}</g>;
          return <g key={index}><circle className={item.kind === 'charge' ? styles.scienceCharge : styles.scienceParticle}
            cx={x} cy={y} r={item.kind === 'charge' ? 16 : 11}/>{item.kind === 'charge' && <text className={styles.scienceCenter}
            x={x} y={y + 5}>{(item.magnitude ?? 1) < 0 ? '−' : '+'}</text>}{label}</g>;
        })}
      </svg>
    </div>
    <details className={styles.dataDetails}><summary>Read the scientific visual as text</summary>
      <ul>{spec.primitives.map((p, i) => <li key={i}>{p.label || p.kind}: {p.kind}, position ({p.x}, {p.y})
        {p.x2 !== undefined && p.y2 !== undefined ? ` to (${p.x2}, ${p.y2})` : ''}</li>)}</ul>
    </details>
  </>;
}
