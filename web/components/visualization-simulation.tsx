"use client";

import { useMemo, useState } from 'react';
import type { VisualizationSpec } from '@/lib/visualization-spec';
import styles from './visualization.module.css';

const get = (values: Record<string, number>, key: string, fallback: number) => values[key] ?? fallback;

export function SimulationRenderer({ spec, onSaveParameters }: {
  spec: VisualizationSpec; onSaveParameters?: (values: Record<string, number>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(spec.parameters.map(p => [p.id, p.initial])));
  const [step, setStep] = useState(0);
  const [queue, setQueue] = useState<number[]>([]);
  const [cache, setCache] = useState<string[]>([]);
  const [cacheResult, setCacheResult] = useState('');
  const [nextItem, setNextItem] = useState(1);
  const [packetStep, setPacketStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const model = spec.simulationModel;
  const positions = useMemo(() => {
    const rate = get(values, 'rate', 0.2), target = get(values, 'target', 0), start = get(values, 'start', 4);
    const states = [start];
    for (let i = 0; i < 18; i++) {
      const next = states.at(-1)! - rate * 2 * (states.at(-1)! - target);
      states.push(Math.max(-1e4, Math.min(1e4, next)));
    }
    return states;
  }, [values]);
  const trajectory = useMemo(() => {
    const speed = get(values, 'speed', 18), angle = get(values, 'angle', 45) * Math.PI / 180;
    const gravity = Math.max(0.1, get(values, 'gravity', 9.8));
    const flight = Math.max(0.1, 2 * speed * Math.sin(angle) / gravity);
    return Array.from({ length: 61 }, (_, i) => {
      const t = flight * i / 60;
      return { x: speed * Math.cos(angle) * t, y: Math.max(0, speed * Math.sin(angle) * t - gravity * t * t / 2) };
    });
  }, [values]);
  const maxX = Math.max(1, ...trajectory.map(p => p.x));
  const maxY = Math.max(1, ...trajectory.map(p => p.y));
  const path = trajectory.map((p, i) => `${i ? 'L' : 'M'}${40 + 520 * p.x / maxX} ${260 - 210 * p.y / maxY}`).join(' ');
  const ball = trajectory[Math.round(step / 18 * 60)] ?? trajectory[0];
  const addCache = (key: string) => {
    if (cache.includes(key)) { setCacheResult(`Hit: ${key} was already cached`); return; }
    setCacheResult(`Miss: ${key} was fetched and cached`);
    setCache(old => [...old.filter(item => item !== key), key].slice(-4));
  };

  return <div className={styles.simulation}>
    {spec.parameters.length > 0 && <div className={styles.parameterGrid}>{spec.parameters.map(parameter => <label key={parameter.id}>
      <span>{parameter.label} <output>{(values[parameter.id] ?? parameter.initial).toFixed(2)}</output></span>
      <input type="range" min={parameter.minimum} max={parameter.maximum} step={parameter.step}
        value={values[parameter.id] ?? parameter.initial}
        onChange={event => { setValues(old => ({ ...old, [parameter.id]: Number(event.target.value) })); setStep(0); }} />
    </label>)}</div>}
    {onSaveParameters && spec.parameters.some(p => values[p.id] !== p.initial) &&
      <button type="button" disabled={saving} onClick={async () => {
        setSaving(true); setSaveError('');
        try { await onSaveParameters(values); } catch (cause) { setSaveError(cause instanceof Error ? cause.message : 'Could not save the parameter.'); }
        finally { setSaving(false); }
      }}>{saving ? 'Saving…' : 'Save these values to the lesson'}</button>}
    {saveError && <p role="alert">{saveError}</p>}
    {model === 'gradient_descent' && <>
      <div className={styles.simStage} role="img" aria-label="Loss curve with gradient descent positions">
        <svg viewBox="0 0 600 300"><path className={styles.simAxis} d="M40 260 H560 M300 25 V265"/>
          <path className={styles.simCurve} d={Array.from({ length: 101 }, (_, i) => {
            const x = -5 + i / 10, target = get(values, 'target', 0);
            return `${i ? 'L' : 'M'}${300 + x * 45} ${260 - Math.min(220, (x - target) ** 2 * 11)}`;
          }).join(' ')}/>
          {positions.slice(0, step + 1).map((x, i) => <circle key={i} cx={300 + x * 45}
            cy={260 - Math.min(220, (x - get(values, 'target', 0)) ** 2 * 11)}
            r={i === step ? 8 : 4} className={i === step ? styles.simCurrent : styles.simPrevious}/>)}
        </svg>
      </div>
      <p>Step {step}: position {positions[step].toFixed(3)}, loss {((positions[step] - get(values, 'target', 0)) ** 2).toFixed(3)}.</p>
      <button type="button" onClick={() => setStep(old => Math.min(18, old + 1))} disabled={step >= 18}>Take a step</button>
      <button type="button" onClick={() => setStep(0)}>Reset</button>
    </>}
    {model === 'projectile' && <>
      <div className={styles.simStage} role="img" aria-label="Projectile path under gravity"><svg viewBox="0 0 600 300">
        <path className={styles.simAxis} d="M40 260 H560"/><path className={styles.simPath} d={path}/>
        <circle className={styles.simCurrent} cx={40 + 520 * ball.x / maxX} cy={260 - 210 * ball.y / maxY} r="9"/>
      </svg></div>
      <label className={styles.timeControl}>Time <input type="range" min="0" max="18" value={step}
        onChange={event => setStep(Number(event.target.value))}/><output>{Math.round(step / 18 * 100)}%</output></label>
      <p>Horizontal distance {ball.x.toFixed(1)} m; height {ball.y.toFixed(1)} m.</p>
    </>}
    {model === 'ohms_law' && <>
      <div className={styles.circuit} role="img" aria-label="A voltage source connected to a resistor">
        <span>Voltage source<br/><strong>{get(values, 'voltage', 12).toFixed(1)} V</strong></span><b>→</b>
        <span>Resistor<br/><strong>{Math.max(0.1, get(values, 'resistance', 6)).toFixed(1)} Ω</strong></span>
      </div>
      <p>Current = voltage ÷ resistance = <strong>{(get(values, 'voltage', 12) / Math.max(0.1, get(values, 'resistance', 6))).toFixed(2)} A</strong>.</p>
    </>}
    {model === 'queue' && <>
      <div className={styles.queue} role="img" aria-label={`Queue, front to back: ${queue.join(', ') || 'empty'}`}>
        <span>Front</span>{queue.length ? queue.map((item, i) => <b key={i}>{item}</b>) : <em>Empty queue</em>}<span>Back</span>
      </div>
      <button type="button" disabled={queue.length >= 8} onClick={() => { setQueue(old => [...old, nextItem]); setNextItem(n => n + 1); }}>Enqueue</button>
      <button type="button" disabled={!queue.length} onClick={() => setQueue(old => old.slice(1))}>Dequeue</button>
    </>}
    {model === 'cache' && <>
      <div className={styles.queue} role="img" aria-label={`Cache contains ${cache.join(', ') || 'nothing'}`}>
        <span>Cache</span>{cache.length ? cache.map(key => <b key={key}>{key}</b>) : <em>Empty</em>}
      </div>
      <div className={styles.simButtons}>{['A', 'B', 'C', 'D', 'E'].map(key =>
        <button type="button" key={key} onClick={() => addCache(key)}>Access {key}</button>)}</div>
      <p role="status">{cacheResult || 'Access a key to see a hit or miss. Capacity is four.'}</p>
    </>}
    {model === 'network' && <>
      <div className={styles.network} role="img" aria-label={`Packet at ${['client', 'router', 'service', 'destination'][packetStep]}`}>
        {['Client', 'Router', 'Service', 'Destination'].map((name, i) => <div key={name}
          className={i === packetStep ? styles.activeHop : ''}><b>{name}</b>{i === packetStep && <span>● Packet</span>}</div>)}
      </div>
      <button type="button" onClick={() => setPacketStep(old => (old + 1) % 4)}>Move packet</button>
      <p>The packet moves to the next hop. Network delays and loss are omitted in this teaching model.</p>
    </>}
  </div>;
}
