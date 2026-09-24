"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { VisualizationList } from '@/components/visualization';
import styles from './preview.module.css';

const provenance = { kind: 'illustrative', label: 'Illustrative teaching data', sourceIds: [] };
const examples = [
  { version: 1, id: 'preview-bar', type: 'bar', title: 'Compare model sizes', description: 'An example category comparison.', provenance,
    categories: ['Small', 'Medium', 'Large'], values: [3, 6, 8], yLabel: 'Relative size' },
  { version: 1, id: 'preview-line', type: 'line', title: 'Training loss over time', provenance,
    series: [{ name: 'Training loss', points: [[0, 9], [1, 6], [2, 4.2], [3, 2.5], [4, 1.5]] }] },
  { version: 1, id: 'preview-scatter', type: 'scatter', title: 'Study time and score', provenance,
    series: [{ name: 'Learners', points: [[1, 48], [2, 55], [3, 63], [4, 68], [5, 79]] }] },
  { version: 1, id: 'preview-pie', type: 'pie', title: 'Dataset composition', provenance,
    categories: ['Training', 'Validation', 'Test'], values: [70, 15, 15], controls: { donut: 1 } },
  { version: 1, id: 'preview-function', type: 'function', title: 'Two functions', xDomain: [-4, 4],
    series: [{ name: 'y = x²', expression: 'x^2' }, { name: 'y = 2x', expression: '2x' }],
    annotations: [{ kind: 'point', label: 'Intersection', x: 0, y: 0 }] },
  { version: 1, id: 'preview-normal', type: 'distribution', title: 'Normal distribution', distributionKind: 'normal',
    distributionParams: { mean: 0, sigma: 1 }, xDomain: [-4, 4] },
  { version: 1, id: 'preview-histogram', type: 'distribution', title: 'Empirical observations', distributionKind: 'histogram',
    provenance, series: [{ name: 'Scores', points: [[1, 0], [2, 0], [2.2, 0], [3, 0], [4.1, 0], [4.3, 0], [5, 0], [6, 0], [7.2, 0], [8, 0]] }] },
  { version: 1, id: 'preview-flow', type: 'flow', title: 'Compiler pipeline', nodes: [
    { id: 'src', label: 'Source code', group: 'Input' }, { id: 'parse', label: 'Parse' },
    { id: 'opt', label: 'Optimize' }, { id: 'machine', label: 'Machine code', group: 'Output' }],
    edges: [{ source: 'src', target: 'parse' }, { source: 'parse', target: 'opt' }, { source: 'opt', target: 'machine' }] },
  { version: 1, id: 'preview-concept', type: 'concept', title: 'Learning approaches', nodes: [
    { id: 'ml', label: 'Machine learning', emphasis: true }, { id: 'sup', label: 'Supervised learning', group: 'Approaches' },
    { id: 'unsup', label: 'Unsupervised learning', group: 'Approaches' }],
    edges: [{ source: 'ml', target: 'sup', label: 'uses labels' }, { source: 'ml', target: 'unsup', label: 'finds structure' }] },
  { version: 1, id: 'preview-architecture', type: 'architecture', title: 'CPU instruction path', nodes: [
    { id: 'pc', label: 'Program counter', group: 'Fetch' }, { id: 'decode', label: 'Decoder', group: 'Execute' },
    { id: 'alu', label: 'ALU', group: 'Execute' }, { id: 'write', label: 'Writeback', group: 'Complete' }],
    edges: [{ source: 'pc', target: 'decode', kind: 'control' }, { source: 'decode', target: 'alu', kind: 'data' },
      { source: 'alu', target: 'write', kind: 'data' }] },
  { version: 1, id: 'preview-science', type: 'science', title: 'Forces on a box', description: 'A simplified free-body diagram.', primitives: [
    { kind: 'axis', x: 0, y: 0 }, { kind: 'object', x: 0, y: 0, label: 'Box' },
    { kind: 'force', x: 0, y: 0, x2: 0, y2: 3, label: 'Normal' },
    { kind: 'force', x: 0, y: 0, x2: 0, y2: -3, label: 'Weight' },
    { kind: 'force', x: 0, y: 0, x2: 3, y2: 0, label: 'Push' }] },
  { version: 1, id: 'preview-timeline', type: 'timeline', title: 'Computing milestones', provenance,
    events: [{ date: '1947', order: 1947, title: 'Transistor', description: 'Illustrative historical entry.' },
      { date: '1971', order: 1971, title: 'Microprocessor', description: 'Illustrative historical entry.' }] },
  { version: 1, id: 'preview-simulation', type: 'simulation', title: 'Explore gradient descent',
    description: 'Adjust the learning rate and step through a simplified loss curve.', simulationModel: 'gradient_descent',
    parameters: [{ id: 'rate', label: 'Learning rate', minimum: 0.05, maximum: 0.5, step: 0.05, initial: 0.2 }] },
];

export default function VisualizationPreview() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    return () => document.documentElement.classList.remove('dark');
  }, [dark]);
  return <main className={styles.page}>
    <Link href="/reading-preview">← Back to the lesson preview</Link>
    <div className={styles.heading}><div><p className={styles.eyebrow}>VISUAL INTELLIGENCE · COMPONENT PREVIEW</p>
      <h1>Learning in more than one way</h1></div>
      <button type="button" aria-pressed={dark} onClick={() => setDark(value => !value)}>{dark ? 'Light theme' : 'Dark theme'}</button></div>
    <p className={styles.intro}>Structured, bounded examples for every visualization renderer. Numerical examples are illustrative.</p>
    <VisualizationList values={examples}/>
  </main>;
}
