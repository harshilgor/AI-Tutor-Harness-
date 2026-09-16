"use client";

import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import { BookOpen, ChevronLeft, FileText, PanelRightClose, Plus, Save, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LearningApiError, learningApi, type WorkspaceNote, type WorkspaceNoteSummary } from '@/lib/api';
import { QuizWorkspace } from './quiz-workspace';
import styles from './workspace-panel.module.css';
import type { WorkspaceNoteSeed } from '@/lib/workspace-events';

export type WorkspaceTab = 'notes' | 'quiz' | 'sources';
export type WorkspacePanelLayout = { width: number; collapsed: boolean; tabs: WorkspaceTab[]; activeTab: WorkspaceTab };
type NoteDraft = (Pick<WorkspaceNote, 'id' | 'title' | 'body' | 'revision' | 'frontmatter'>) | { id: null; title: string; body: string; revision: null; frontmatter: Record<string, unknown> };

const tabNames: Record<WorkspaceTab, string> = { notes: 'Notes', quiz: 'Quiz', sources: 'Sources' };

function toDraft(note: WorkspaceNote): NoteDraft {
  return { id: note.id, title: note.title, body: note.body, revision: note.revision, frontmatter: note.frontmatter };
}

function blankDraft(): NoteDraft {
  return { id: null, title: 'Untitled note', body: '', revision: null, frontmatter: {} };
}

function NoteEditor({ closeRequest, onClose, onCloseRequestHandled, onDirtyChange, seed, onSeedConsumed, noteToOpen, onNoteOpenConsumed }: { closeRequest: boolean; onClose: () => void; onCloseRequestHandled: () => void; onDirtyChange: (dirty: boolean) => void; seed: WorkspaceNoteSeed | null; onSeedConsumed: (id: string) => void; noteToOpen: string | null; onNoteOpenConsumed: (noteId: string) => void }) {
  const [notes, setNotes] = useState<WorkspaceNoteSummary[]>([]);
  const [draft, setDraft] = useState<NoteDraft | null>(null);
  const [savedDraft, setSavedDraft] = useState<NoteDraft | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  const requestId = useRef(0);
  const consumedSeeds = useRef(new Set<string>());
  const consumedOpenNotes = useRef(new Set<string>());

  const dirty = Boolean(draft && (!savedDraft || draft.title !== savedDraft.title || draft.body !== savedDraft.body));

  useEffect(() => {
    onDirtyChange(dirty);
    return () => onDirtyChange(false);
  }, [dirty, onDirtyChange]);

  async function loadNotes(search = '') {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const result = search.trim()
        ? (await learningApi.searchWorkspaceNotes(search)).notes
        : await learningApi.listWorkspaceNotes();
      if (currentRequest === requestId.current) setNotes(result);
    } catch (cause) {
      if (currentRequest === requestId.current) setError(cause instanceof Error ? cause.message : 'Notes could not be loaded.');
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void loadNotes(query), 180);
    return () => window.clearTimeout(timer);
  }, [query]);

  const confirmBefore = useCallback((action: () => void) => {
    if (!dirty) { action(); return; }
    setPendingAction(() => action);
  }, [dirty]);

  useEffect(() => {
    if (!closeRequest) return;
    const timer = window.setTimeout(() => confirmBefore(onClose), 0);
    return () => window.clearTimeout(timer);
  }, [closeRequest, confirmBefore, onClose]);
  useEffect(() => {
    if (!seed || consumedSeeds.current.has(seed.id)) return;
    const timer = window.setTimeout(() => confirmBefore(() => {
      setDraft({ id: null, title: seed.title, body: seed.body, revision: null, frontmatter: seed.frontmatter });
      setSavedDraft(null);
      setError('');
      consumedSeeds.current.add(seed.id);
      onSeedConsumed(seed.id);
    }), 0);
    return () => window.clearTimeout(timer);
  }, [confirmBefore, onSeedConsumed, seed]);

  function startBlank() {
    confirmBefore(() => {
      setDraft(blankDraft());
      setSavedDraft(null);
      setError('');
    });
  }

  const loadNote = useCallback(async (noteId: string) => {
    setLoading(true);
    setError('');
    try {
      const note = await learningApi.getWorkspaceNote(noteId);
      setDraft(toDraft(note));
      setSavedDraft(toDraft(note));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The note could not be opened.');
    } finally { setLoading(false); }
  }, []);

  function openNote(noteId: string) {
    confirmBefore(() => { void loadNote(noteId); });
  }

  useEffect(() => {
    if (!noteToOpen || consumedOpenNotes.current.has(noteToOpen)) return;
    const timer = window.setTimeout(() => confirmBefore(() => {
      consumedOpenNotes.current.add(noteToOpen);
      onNoteOpenConsumed(noteToOpen);
      void loadNote(noteToOpen);
    }), 0);
    return () => window.clearTimeout(timer);
  }, [confirmBefore, loadNote, noteToOpen, onNoteOpenConsumed]);

  async function save(): Promise<boolean> {
    if (!draft || saving) return false;
    const title = draft.title.trim();
    if (!title) { setError('Give this note a title before saving.'); return false; }
    setSaving(true);
    setError('');
    try {
      const saved = draft.id
        ? await learningApi.updateWorkspaceNote(draft.id, { title, body: draft.body, frontmatter: draft.frontmatter, expectedRevision: draft.revision! })
        : await learningApi.createWorkspaceNote({ title, body: draft.body, frontmatter: draft.frontmatter });
      const next = toDraft(saved);
      setDraft(next);
      setSavedDraft(next);
      await loadNotes(query);
      return true;
    } catch (cause) {
      if (cause instanceof LearningApiError && (cause.code === 'revision_conflict' || cause.code === 'external_change_conflict')) {
        setError(`${cause.message} Your unsaved draft is still in the editor.`);
      } else {
        setError(cause instanceof Error ? cause.message : 'The note could not be saved.');
      }
    } finally { setSaving(false); }
    return false;
  }

  return <section className={styles.notes} aria-label="Notes workspace">
    <div className={styles.noteList}>
      <div className={styles.noteListTop}>
        <div className={styles.search}><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search notes" aria-label="Search notes" /></div>
        <Button type="button" size="icon-sm" variant="outline" onClick={startBlank} aria-label="Create blank note"><Plus size={16} /></Button>
      </div>
      <div className={styles.noteItems} aria-live="polite">
        {loading && notes.length === 0 ? <p className={styles.muted}>Loading notes…</p> : null}
        {!loading && notes.length === 0 ? <div className={styles.emptyList}><FileText size={18} /><span>{query ? 'No matching notes.' : 'No notes yet.'}</span></div> : null}
        {notes.map(note => <button type="button" key={note.id} className={`${styles.noteItem} ${draft?.id === note.id ? styles.selected : ''}`} onClick={() => void openNote(note.id)}>
          <strong>{note.title}</strong><small>Edited {new Date(note.updatedAt).toLocaleDateString()}</small>
        </button>)}
      </div>
    </div>
    <div className={styles.editor}>
      {!draft ? <div className={styles.emptyEditor}><BookOpen size={28} /><h2>Capture what matters</h2><p>Keep your own explanations, examples, and questions in local Markdown notes.</p><Button type="button" onClick={startBlank}><Plus size={16} />New note</Button></div> : <>
        <div className={styles.editorTop}>
          <input value={draft.title} onChange={event => setDraft(current => current ? { ...current, title: event.target.value } : current)} aria-label="Note title" placeholder="Note title" />
          <Button type="button" size="sm" disabled={saving || !dirty} onClick={() => void save()}><Save size={15} />{saving ? 'Saving' : 'Save'}</Button>
        </div>
        <div className={styles.status} role="status">{saving ? 'Saving…' : dirty ? 'Unsaved changes' : draft.id ? 'Saved locally' : 'New note — not saved yet'}</div>
        <textarea value={draft.body} onChange={event => setDraft(current => current ? { ...current, body: event.target.value } : current)} placeholder="Write in Markdown…" aria-label="Note body" spellCheck />
      </>}
      {error ? <p role="alert" className={styles.error}>{error}</p> : null}
    </div>
    {pendingAction ? <div className={styles.confirm} role="dialog" aria-modal="true" aria-label="Unsaved note changes"><div><h2>Keep your changes?</h2><p>Save this note before switching, or discard the unsaved edits.</p><div><Button type="button" variant="outline" onClick={() => { setPendingAction(null); onCloseRequestHandled(); }}>Keep editing</Button><Button type="button" variant="ghost" onClick={() => { setPendingAction(null); onCloseRequestHandled(); pendingAction(); }}>Discard</Button><Button type="button" onClick={() => void save().then(saved => { if (saved) { setPendingAction(null); onCloseRequestHandled(); pendingAction(); } })}>Save changes</Button></div></div></div> : null}
  </section>;
}

export function WorkspacePanel({ quizSessionId, quizConceptId, layout, onLayoutChange, onCollapse, onExpand, noteSeed, noteToOpen, onNoteSeedConsumed, onNoteOpenConsumed }: {
  quizSessionId?: string | null;
  quizConceptId?: string;
  layout: WorkspacePanelLayout;
  onLayoutChange: Dispatch<SetStateAction<WorkspacePanelLayout>>;
  onCollapse: () => void;
  onExpand: () => void;
  noteSeed: WorkspaceNoteSeed | null;
  noteToOpen: string | null;
  onNoteSeedConsumed: (id: string) => void;
  onNoteOpenConsumed: (noteId: string) => void;
}) {
  const [launcherOpen, setLauncherOpen] = useState(false);
  const [notesDirty, setNotesDirty] = useState(false);
  const [noteCloseRequest, setNoteCloseRequest] = useState(false);

  function openTab(tab: WorkspaceTab) {
    onLayoutChange(current => ({ ...current, collapsed: false, tabs: current.tabs.includes(tab) ? current.tabs : [...current.tabs, tab], activeTab: tab }));
    onExpand();
    setLauncherOpen(false);
  }

  function removeActiveTab() {
    onLayoutChange(current => {
      const tabs = current.tabs.filter(tab => tab !== current.activeTab);
      return { ...current, tabs, activeTab: tabs[0] || 'notes', collapsed: tabs.length === 0 };
    });
    if (layout.tabs.length === 1) onCollapse();
  }

  function closeActiveTab() {
    if (layout.activeTab === 'notes' && notesDirty) { setNoteCloseRequest(true); return; }
    removeActiveTab();
  }

  const active = layout.activeTab;
  return <aside className={`${styles.panel} ${layout.collapsed ? styles.collapsed : ''}`} aria-label="Workspace panel">
    {layout.collapsed ? <button type="button" className={styles.expand} onClick={() => openTab('notes')} aria-label="Open workspace panel"><ChevronLeft size={18} /></button> : <>
      <header className={styles.header}>
        <div className={styles.tabs} role="tablist" aria-label="Workspace tabs">
          {layout.tabs.map(tab => <button key={tab} type="button" role="tab" aria-selected={active === tab} className={active === tab ? styles.activeTab : ''} onClick={() => onLayoutChange(current => ({ ...current, activeTab: tab }))}>{tabNames[tab]}</button>)}
          <div className={styles.launcher}><Button type="button" size="icon-xs" variant="ghost" onClick={() => setLauncherOpen(open => !open)} aria-expanded={launcherOpen} aria-label="Open a workspace tab"><Plus size={16} /></Button>{launcherOpen ? <div className={styles.launcherMenu}>{(['notes', 'quiz', 'sources'] as WorkspaceTab[]).map(tab => <button type="button" key={tab} onClick={() => openTab(tab)}>{tabNames[tab]}</button>)}</div> : null}</div>
        </div>
        <div className={styles.headerActions}><Button type="button" size="icon-xs" variant="ghost" onClick={closeActiveTab} aria-label={`Close ${tabNames[active]} tab`}><X size={15} /></Button><Button type="button" size="icon-xs" variant="ghost" onClick={() => { onLayoutChange(current => ({ ...current, collapsed: true })); onCollapse(); }} aria-label="Collapse workspace panel"><PanelRightClose size={16} /></Button></div>
      </header>
      <div className={styles.content}>
        {active === 'notes' ? <NoteEditor closeRequest={noteCloseRequest} onDirtyChange={setNotesDirty} seed={noteSeed} onSeedConsumed={onNoteSeedConsumed} noteToOpen={noteToOpen} onNoteOpenConsumed={onNoteOpenConsumed} onCloseRequestHandled={() => setNoteCloseRequest(false)} onClose={() => { setNoteCloseRequest(false); removeActiveTab(); }} /> : null}
        {active === 'quiz' ? <QuizWorkspace sessionId={quizSessionId} conceptId={quizConceptId} inline /> : null}
        {active === 'sources' ? <div className={styles.comingSoon}><BookOpen size={26} /><h2>Sources</h2><p>Open a lesson citation or attached material to inspect it here. Source context stays explicit and does not silently enter a tutor request.</p></div> : null}
      </div>
    </>}
  </aside>;
}
