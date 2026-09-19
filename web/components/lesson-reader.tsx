"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { RichContent } from './rich-content';
import styles from './reading.module.css';

export type ReadingBlock = { id: string; heading?: string | null; body: string };
const defaults = '{"size":"standard","spacing":"comfortable"}';
let memory = defaults;
function subscribe(callback: () => void) { window.addEventListener('storage', callback); window.addEventListener('forma-reading', callback); return () => { window.removeEventListener('storage', callback); window.removeEventListener('forma-reading', callback); }; }
function snapshot() { try { return window.localStorage.getItem('forma-reading') || memory; } catch { return memory; } }
function savePreferences(value: { size: string; spacing: string }) { memory = JSON.stringify(value); try { window.localStorage.setItem('forma-reading', memory); } catch { /* Still apply preferences for this visit. */ } window.dispatchEvent(new Event('forma-reading')); }

export function LessonReader({ id, blocks, onSelect }: { id: string; blocks: ReadingBlock[]; onSelect?: (block: ReadingBlock, raw: string, equation?: boolean) => void }) {
  const stored = useSyncExternalStore(subscribe, snapshot, () => defaults);
  const prefs = { size: 'standard', spacing: 'comfortable' };
  try { const parsed = JSON.parse(stored); if (['standard', 'large', 'larger'].includes(parsed.size)) prefs.size = parsed.size; if (['compact', 'comfortable', 'spacious'].includes(parsed.spacing)) prefs.spacing = parsed.spacing; } catch { /* Ignore malformed stored settings. */ }
  const container = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState('');
  useEffect(() => {
    const observer = new IntersectionObserver(entries => { for (const entry of entries) if (entry.isIntersecting) setActive(entry.target.id); }, { rootMargin: '-10% 0px -65% 0px' });
    container.current?.querySelectorAll('section[data-reading-block]').forEach(section => observer.observe(section));
    return () => observer.disconnect();
  }, [id, blocks]);
  const size = prefs.size === 'large' ? '19px' : prefs.size === 'larger' ? '21px' : '17px';
  const leading = prefs.spacing === 'compact' ? '1.6' : prefs.spacing === 'spacious' ? '2' : '1.8';
  return <div ref={container} style={{ '--reading-size': size, '--reading-leading': leading } as React.CSSProperties}>
    <div className={styles.toolbar} aria-label="Reading preferences"><label>Text<select aria-label="Reading text size" value={prefs.size} onChange={event => savePreferences({ ...prefs, size: event.target.value })}><option value="standard">Standard</option><option value="large">Large</option><option value="larger">Larger</option></select></label><label>Spacing<select aria-label="Reading spacing" value={prefs.spacing} onChange={event => savePreferences({ ...prefs, spacing: event.target.value })}><option value="compact">Compact</option><option value="comfortable">Comfortable</option><option value="spacious">Spacious</option></select></label>
      {blocks.length >= 4 && <label className={styles.outline}>In this lesson<select aria-label="Lesson outline — reading position" value={active} onChange={event => { setActive(event.target.value); document.getElementById(event.target.value)?.scrollIntoView({ block: 'start', behavior: 'instant' }); }}><option value="">Jump to a section</option>{blocks.map((block, index) => <option key={block.id} value={`${id}-${block.id}`}>{index + 1}. {block.heading || 'Continue'}</option>)}</select></label>}
    </div>
    {blocks.map(block => <section key={block.id} id={`${id}-${block.id}`} tabIndex={-1} data-reading-block className={styles.block} style={{ fontSize: size }}><h2>{block.heading || 'Explore this idea'}</h2><RichContent body={block.body} onExplore={onSelect ? (raw, equation) => onSelect(block, raw, equation) : undefined} /></section>)}
  </div>;
}
