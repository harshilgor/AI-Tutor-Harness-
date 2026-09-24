"use client";

import { useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ReferenceArea, ReferenceDot, ReferenceLine, ResponsiveContainer, Scatter,
  ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts';
import type { VisualizationSpec } from '@/lib/visualization-spec';
import { binomialDistribution, normalDistribution, sampleFunction } from '@/lib/visual-math';
import styles from './visualization.module.css';

const palette = ['#59836b', '#a3764a', '#627aa9', '#9c6483', '#8878ad', '#478c91'];
type Props = { spec: VisualizationSpec };

function annotations(spec: VisualizationSpec) {
  return spec.annotations.flatMap((annotation, index) => {
    if (typeof annotation === 'string') return [];
    if (annotation.kind === 'region' || annotation.kind === 'interval')
      return annotation.x !== undefined && annotation.x2 !== undefined
        ? [<ReferenceArea key={index} x1={annotation.x} x2={annotation.x2} fill="#91aa91" fillOpacity={0.16} label={annotation.label} />] : [];
    if (annotation.kind === 'asymptote')
      return annotation.x !== undefined
        ? [<ReferenceLine key={index} x={annotation.x} stroke="#a3764a" strokeDasharray="4 4" label={annotation.label} />] : [];
    if (['tangent', 'secant', 'derivative', 'arrow'].includes(annotation.kind) &&
      annotation.x !== undefined && annotation.y !== undefined && annotation.x2 !== undefined && annotation.y2 !== undefined)
      return [<ReferenceLine key={index} segment={[{ x: annotation.x, y: annotation.y }, { x: annotation.x2, y: annotation.y2 }]}
        stroke="#a3764a" strokeWidth={2} label={annotation.label}/>];
    if (annotation.x !== undefined && annotation.y !== undefined)
      return [<ReferenceDot key={index} x={annotation.x} y={annotation.y} r={5} fill="#a3764a" stroke="var(--card)" label={annotation.label} />];
    return [];
  });
}

export function ChartRenderer({ spec }: Props) {
  const [hidden, setHidden] = useState<string[]>([]);
  const [zoom, setZoom] = useState(1);
  const chartSeries = useMemo(() => {
    if (spec.type === 'distribution') {
      if (spec.distributionKind === 'normal') return [{ name: 'Density', points: normalDistribution(spec.distributionParams.mean ?? 0, spec.distributionParams.sigma ?? 1).map(p => [p.x, p.y] as [number, number]) }];
      if (spec.distributionKind === 'binomial') return [{ name: 'Probability', points: binomialDistribution(spec.distributionParams.n ?? 10, spec.distributionParams.p ?? 0.5).map(p => [p.x, p.y] as [number, number]) }];
    }
    return spec.series.map(s => ({ name: s.name, points: s.expression
      ? sampleFunction(s.expression, spec.xDomain).map(p => [p.x, p.y] as [number, number | null])
      : s.points }));
  }, [spec]);
  const histogram = useMemo(() => {
    if (spec.type !== 'distribution' || spec.distributionKind !== 'histogram') return [];
    const observations = spec.series.flatMap(series => series.points.map(([x]) => x)).filter(Number.isFinite);
    if (!observations.length) return [];
    const low = Math.min(...observations); const high = Math.max(...observations);
    const width = high === low ? 1 : (high - low) / Math.min(12, Math.max(5, Math.ceil(Math.sqrt(observations.length))));
    const count = high === low ? 1 : Math.ceil((high - low) / width);
    const bins = Array.from({ length: count }, (_, i) => ({ x: low + (i + 0.5) * width, label: `${(low + i * width).toPrecision(3)}–${(low + (i + 1) * width).toPrecision(3)}`, series0: 0 }));
    for (const value of observations) bins[Math.min(bins.length - 1, Math.floor((value - low) / width))].series0++;
    return bins;
  }, [spec]);
  const merged = useMemo(() => {
    const rows = new Map<number, Record<string, number | null>>();
    chartSeries.forEach((s, i) => s.points.forEach(([x, y]) => {
      const key = Math.round(x * 1e6) / 1e6;
      const row = rows.get(key) ?? { x: key };
      row[`series${i}`] = y;
      rows.set(key, row);
    }));
    return [...rows.values()].sort((a, b) => Number(a.x) - Number(b.x));
  }, [chartSeries]);
  const shown = (name: string) => !hidden.includes(name);
  const toggle = (name: string) => setHidden(old => old.includes(name) ? old.filter(n => n !== name) : [...old, name]);
  const axis = { stroke: 'var(--muted-foreground)', tick: { fill: 'var(--muted-foreground)', fontSize: 11 } };
  const grid = { stroke: 'var(--border)', strokeDasharray: '3 4', vertical: false };
  const tip = { contentStyle: { background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--foreground)', borderRadius: 8 } };
  const categoryData = spec.categories.map((name, i) => ({ name, value: spec.values[i] ?? 0 }));
  const barData: Array<Record<string, unknown>> = spec.type === 'bar' ? categoryData : spec.distributionKind === 'histogram' ? histogram : merged;
  const center = (spec.xDomain[0] + spec.xDomain[1]) / 2;
  const half = (spec.xDomain[1] - spec.xDomain[0]) / (2 * zoom);
  const isBar = spec.type === 'bar' || (spec.type === 'distribution' && ['binomial', 'histogram'].includes(spec.distributionKind ?? ''));

  return <>
    {chartSeries.length > 1 && <div className={styles.seriesControls} aria-label="Visible series">
      {chartSeries.map((series, i) => <button type="button" key={i} aria-pressed={shown(series.name)}
        onClick={() => toggle(series.name)}><span style={{ backgroundColor: palette[i % palette.length] }} />{series.name}</button>)}
    </div>}
    {spec.type === 'function' && <div className={styles.zoomControls} aria-label="Graph zoom">
      <button type="button" onClick={() => setZoom(z => Math.max(0.5, z / 1.5))} aria-label="Zoom out">−</button>
      <span>Zoom {zoom.toFixed(1)}×</span>
      <button type="button" onClick={() => setZoom(z => Math.min(8, z * 1.5))} aria-label="Zoom in">+</button>
    </div>}
    <div className={styles.chart}>
      <ResponsiveContainer width="100%" height="100%">
        {spec.type === 'pie' ?
          <PieChart><Tooltip {...tip} /><Legend /><Pie data={categoryData} dataKey="value" nameKey="name"
            innerRadius={spec.controls.donut ? '44%' : 0} outerRadius="76%" label>
            {categoryData.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}
          </Pie></PieChart>
          : spec.type === 'scatter' || (spec.type === 'distribution' && spec.distributionKind === 'empirical') ?
          <ScatterChart margin={{ top: 14, right: 14, bottom: 26, left: 4 }}>
            <CartesianGrid {...grid} /><XAxis type="number" dataKey="x" name={spec.xLabel || 'x'} {...axis} />
            <YAxis type="number" dataKey="y" name={spec.yLabel || 'y'} {...axis} /><Tooltip {...tip} cursor={{ strokeDasharray: '3 3' }} /><Legend />
            {chartSeries.map((s, i) => shown(s.name) && <Scatter key={i} name={s.name}
              data={s.points.map(([x, y]) => ({ x, y }))} fill={palette[i % palette.length]} />)}
          </ScatterChart>
          : isBar ?
          <BarChart data={barData} margin={{ top: 18, right: 14, bottom: 28, left: 4 }}>
            <CartesianGrid {...grid} /><XAxis dataKey={spec.type === 'bar' ? 'name' : 'x'} {...axis} interval={0} />
            <YAxis {...axis} /><Tooltip {...tip} />
            {spec.type === 'bar' ? <Bar dataKey="value" name={spec.yLabel || 'Value'} radius={[4, 4, 0, 0]}>
              {categoryData.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}
            </Bar> : chartSeries.map((s, i) => shown(s.name) && <Bar key={i} dataKey={`series${i}`} name={s.name}
              fill={palette[i % palette.length]} radius={[3, 3, 0, 0]} />)}
          </BarChart>
          : <LineChart data={merged} margin={{ top: 18, right: 18, bottom: 28, left: 4 }}>
            <CartesianGrid {...grid} />
            <XAxis type="number" dataKey="x" domain={spec.type === 'function' ? [center - half, center + half] : ['dataMin', 'dataMax']}
              allowDataOverflow={spec.type === 'function'} {...axis} />
            <YAxis {...axis} /><Tooltip {...tip} /><Legend />
            {chartSeries.map((s, i) => shown(s.name) && <Line key={i} dataKey={`series${i}`} name={s.name}
              stroke={palette[i % palette.length]} strokeWidth={2.5} dot={spec.type === 'line' && s.points.length < 30}
              connectNulls={false} isAnimationActive={false} type="linear" />)}
            {annotations(spec)}
          </LineChart>}
      </ResponsiveContainer>
    </div>
    <details className={styles.dataDetails}><summary>View data as text</summary>
      <div className={styles.dataTable}><table><thead><tr><th scope="col">{spec.xLabel || (spec.categories.length ? 'Category' : 'x')}</th>
        <th scope="col">{spec.yLabel || 'Value'}</th></tr></thead><tbody>
        {spec.categories.length ? spec.categories.map((name, i) => <tr key={i}><td>{name}</td><td>{spec.values[i]}</td></tr>)
          : chartSeries.flatMap(s => s.points.slice(0, 120).map(([x, y], i) => <tr key={`${s.name}-${i}`}><td>{s.name}: {Number(x).toPrecision(4)}</td><td>{y === null ? 'Undefined' : Number(y).toPrecision(4)}</td></tr>))}
      </tbody></table></div>
    </details>
  </>;
}
