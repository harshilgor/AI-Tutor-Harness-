"use client";

import { useSyncExternalStore } from 'react';
import { RichContent } from './rich-content';
import styles from './reading.module.css';

export type ReadingBlock = { id: string; heading?: string | null; body: string };
const defaults = '{"size":"standard","spacing":"comfortable"}';
const memory = defaults;
function subscribe(callback: () => void) { window.addEventListener('storage', callback); window.addEventListener('forma-reading', callback); return () => { window.removeEventListener('storage', callback); window.removeEventListener('forma-reading', callback); }; }
function snapshot() { try { return window.localStorage.getItem('forma-reading') || memory; } catch { return memory; } }

export function LessonReader({ id, blocks, onSelect }: { id: string; blocks: ReadingBlock[]; onSelect?: (block: ReadingBlock, raw: string, equation?: boolean) => void }) {
  const stored = useSyncExternalStore(subscribe, snapshot, () => defaults);
  const prefs = { size: 'standard', spacing: 'comfortable' };
  try { const parsed = JSON.parse(stored); if (['standard', 'large', 'larger'].includes(parsed.size)) prefs.size = parsed.size; if (['compact', 'comfortable', 'spacious'].includes(parsed.spacing)) prefs.spacing = parsed.spacing; } catch { /* Ignore malformed stored settings. */ }
  const size = prefs.size === 'large' ? '17px' : prefs.size === 'larger' ? '19px' : '15px';
  const leading = prefs.spacing === 'compact' ? '1.55' : prefs.spacing === 'spacious' ? '1.85' : '1.65';
  return <div style={{ '--reading-size': size, '--reading-leading': leading } as React.CSSProperties}>
    {blocks.map(block => <section key={block.id} id={`${id}-${block.id}`} tabIndex={-1} data-reading-block className={styles.block} style={{ fontSize: size }}><h2>{block.heading || 'Explore this idea'}</h2><RichContent body={block.body} onExplore={onSelect ? (raw, equation) => onSelect(block, raw, equation) : undefined} /></section>)}
  </div>;
}
