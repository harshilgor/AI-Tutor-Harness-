"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { WorkspacePanel, type WorkspacePanelLayout } from './workspace-panel';
import { WORKSPACE_NOTE_OPEN_EVENT, WORKSPACE_NOTE_SEED_EVENT, WORKSPACE_SOURCE_OPEN_EVENT, type WorkspaceNoteSeed } from '@/lib/workspace-events';
import styles from './workspace-split.module.css';

const STORAGE_KEY = 'forma-workspace-panel-v1';
const DEFAULT_LAYOUT: WorkspacePanelLayout = { width: 50, collapsed: false, tabs: ['notes'], activeTab: 'notes' };

function validLayout(value: unknown): value is WorkspacePanelLayout {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<WorkspacePanelLayout>;
  return typeof candidate.width === 'number' && typeof candidate.collapsed === 'boolean'
    && Array.isArray(candidate.tabs) && candidate.tabs.every(tab => tab === 'notes' || tab === 'quiz' || tab === 'sources')
    && (candidate.activeTab === 'notes' || candidate.activeTab === 'quiz' || candidate.activeTab === 'sources');
}

export function WorkspaceSplit({ children, quizSessionId, quizConceptId }: { children: ReactNode; quizSessionId?: string | null; quizConceptId?: string }) {
  const [layout, setLayout] = useState<WorkspacePanelLayout>(DEFAULT_LAYOUT);
  const [ready, setReady] = useState(false);
  const [compact, setCompact] = useState(false);
  const [noteSeed, setNoteSeed] = useState<WorkspaceNoteSeed | null>(null);
  const [noteToOpen, setNoteToOpen] = useState<string | null>(null);
  const [sourceToOpen, setSourceToOpen] = useState<{ spanId: string; versionId?: string } | null>(null);
  const groupRef = useRef<HTMLDivElement | null>(null);
  const resizing = useRef(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1050px)');
    const update = () => setCompact(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    const receiveDraft = (event: Event) => {
      const draft = (event as CustomEvent<WorkspaceNoteSeed>).detail;
      if (!draft?.id) return;
      setNoteSeed(draft);
      setLayout(current => ({ ...current, collapsed: false, tabs: current.tabs.includes('notes') ? current.tabs : [...current.tabs, 'notes'], activeTab: 'notes' }));
    };
    window.addEventListener(WORKSPACE_NOTE_SEED_EVENT, receiveDraft);
    return () => window.removeEventListener(WORKSPACE_NOTE_SEED_EVENT, receiveDraft);
  }, []);
  useEffect(() => {
    const receiveOpen = (event: Event) => {
      const noteId = (event as CustomEvent<string>).detail;
      if (!noteId) return;
      setNoteToOpen(noteId);
      setLayout(current => ({ ...current, collapsed: false, tabs: current.tabs.includes('notes') ? current.tabs : [...current.tabs, 'notes'], activeTab: 'notes' }));
    };
    window.addEventListener(WORKSPACE_NOTE_OPEN_EVENT, receiveOpen);
    return () => window.removeEventListener(WORKSPACE_NOTE_OPEN_EVENT, receiveOpen);
  }, []);
  useEffect(() => {
    const receiveSource = (event: Event) => { const detail = (event as CustomEvent<{ spanId: string; versionId?: string }>).detail; if (!detail?.spanId) return; setSourceToOpen(detail); setLayout(current => ({ ...current, collapsed: false, tabs: current.tabs.includes('sources') ? current.tabs : [...current.tabs, 'sources'], activeTab: 'sources' })); };
    window.addEventListener(WORKSPACE_SOURCE_OPEN_EVENT, receiveSource);
    return () => window.removeEventListener(WORKSPACE_SOURCE_OPEN_EVENT, receiveSource);
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (validLayout(stored)) setLayout({ ...stored, width: Math.min(70, Math.max(30, stored.width)), tabs: stored.tabs.length ? stored.tabs : ['notes'] });
      } catch { /* A session remains usable without browser storage. */ }
      setReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(layout)); } catch { /* Layout persistence is optional. */ }
  }, [layout, ready]);
  useEffect(() => {
    const resize = (event: PointerEvent) => {
      if (!resizing.current || !groupRef.current) return;
      const bounds = groupRef.current.getBoundingClientRect();
      const width = ((bounds.right - event.clientX) / bounds.width) * 100;
      setLayout(current => ({ ...current, collapsed: false, width: Math.round(Math.min(70, Math.max(30, width))) }));
    };
    const stop = () => { resizing.current = false; };
    window.addEventListener('pointermove', resize);
    window.addEventListener('pointerup', stop);
    return () => { window.removeEventListener('pointermove', resize); window.removeEventListener('pointerup', stop); };
  }, []);

  const panel = <WorkspacePanel quizSessionId={quizSessionId} quizConceptId={quizConceptId} layout={layout} onLayoutChange={setLayout} noteSeed={noteSeed} noteToOpen={noteToOpen} sourceToOpen={sourceToOpen} onNoteSeedConsumed={id => setNoteSeed(current => current?.id === id ? null : current)} onNoteOpenConsumed={noteId => setNoteToOpen(current => current === noteId ? null : current)}
    onCollapse={() => setLayout(current => ({ ...current, collapsed: true }))}
    onExpand={() => setLayout(current => ({ ...current, collapsed: false }))} />;

  if (compact) return <div className={styles.compact}><div className={styles.compactMain}>{children}</div>{panel}</div>;

  return <div ref={groupRef} className={styles.group}>
    <div className={styles.main}>{children}</div>
    <div className={styles.handle} role="separator" aria-orientation="vertical" aria-label="Resize workspace panel" aria-valuemin={30} aria-valuemax={70} aria-valuenow={layout.width} tabIndex={0}
      onPointerDown={event => { event.preventDefault(); resizing.current = true; }}
      onKeyDown={event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); const change = event.key === 'ArrowLeft' ? 2 : -2; setLayout(current => ({ ...current, collapsed: false, width: Math.max(30, Math.min(70, current.width + change)) })); } }} />
    <div className={`${styles.panel} ${layout.collapsed ? styles.collapsed : ''}`} style={{ '--workspace-panel-width': layout.collapsed ? '42px' : `${layout.width}%` } as CSSProperties}>{panel}</div>
  </div>;
}
