"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Ellipsis, Plus, Search } from 'lucide-react';
import { learningApi, LearningApiError, type ChatSessionSummary } from '@/lib/api';
import styles from './chat-history.module.css';

type Group = 'Today' | 'Yesterday' | 'Previous 7 days' | 'Older';

function groupFor(iso: string, now: Date): Group {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Older';
  const startOf = (value: Date) => new Date(value.getFullYear(), value.getMonth(), value.getDate());
  const days = Math.round((startOf(now).getTime() - startOf(date).getTime()) / 86400000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days <= 7) return 'Previous 7 days';
  return 'Older';
}

const GROUP_ORDER: Group[] = ['Today', 'Yesterday', 'Previous 7 days', 'Older'];

export function ChatHistory({ activeSessionId, refreshKey, onOpen }: {
  activeSessionId: string | null;
  refreshKey: number;
  onOpen: (sessionId: string | null) => void;
}) {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [errorDetail, setErrorDetail] = useState('');

  function friendlyError(cause: unknown): { message: string; detail: string } {
    const detail = cause instanceof Error ? cause.message : 'Unknown error.';
    if (cause instanceof LearningApiError && (cause.status === 404 || cause.status === 405)) {
      return { message: 'Chat history needs a newer tutor service.', detail: 'Restart the local API (it serves this list), then retry.' };
    }
    if (detail.startsWith('Cannot connect to the tutor service')) {
      return { message: 'Could not reach the tutor service.', detail: 'Start the local app, then retry. Your chats stay saved on the server.' };
    }
    return { message: 'Could not load conversations.', detail: 'Please retry. Your chats stay saved on the server.' };
  }
  const [query, setQuery] = useState('');
  const [menuId, setMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const renameInput = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    setErrorDetail('');
    try {
      const result = await learningApi.listChatSessions({ limit: 100 });
      setSessions(result.sessions);
    } catch (cause) {
      const friendly = friendlyError(cause);
      setError(friendly.message);
      setErrorDetail(friendly.detail);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, refreshKey]);

  useEffect(() => {
    const refresh = () => void load();
    window.addEventListener('forma:chat-history-changed', refresh);
    return () => window.removeEventListener('forma:chat-history-changed', refresh);
  }, [load]);

  useEffect(() => {
    if (renamingId) renameInput.current?.focus();
  }, [renamingId]);

  useEffect(() => {
    if (!menuId) return;
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMenuId(null); setConfirmDeleteId(null); } };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [menuId]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return sessions;
    return sessions.filter(item => item.title.toLowerCase().includes(needle));
  }, [sessions, query]);

  const groups = useMemo(() => {
    const now = new Date();
    const buckets = new Map<Group, ChatSessionSummary[]>();
    for (const item of visible) {
      const group = groupFor(item.updatedAt, now);
      if (!buckets.has(group)) buckets.set(group, []);
      buckets.get(group)!.push(item);
    }
    return GROUP_ORDER.filter(group => buckets.has(group)).map(group => ({ group, items: buckets.get(group)! }));
  }, [visible]);

  async function commitRename(id: string) {
    const title = draft.trim();
    if (!title || busyId) return;
    setBusyId(id);
    try {
      const updated = await learningApi.renameChatSession(id, title);
      setSessions(current => current.map(item => item.id === id ? { ...item, title: updated.title || title } : item));
      setRenamingId(null);
      setMenuId(null);
    } catch (cause) {
      const friendly = friendlyError(cause);
      setError(friendly.message);
      setErrorDetail(friendly.detail);
    } finally {
      setBusyId(null);
    }
  }

  async function commitDelete(id: string) {
    if (busyId) return;
    setBusyId(id);
    try {
      await learningApi.deleteChatSession(id);
      setSessions(current => current.filter(item => item.id !== id));
      setMenuId(null);
      setConfirmDeleteId(null);
      if (id === activeSessionId) onOpen(null);
    } catch (cause) {
      const friendly = friendlyError(cause);
      setError(friendly.message);
      setErrorDetail(friendly.detail);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.history}>
      <div className="side-label"><span>Recent chats</span>{sessions.length > 0 && !loading ? <span>{sessions.length}</span> : null}</div>
      {sessions.length > 8 && !loading ? (
        <div className={styles.search}><Search size={14} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search chats" aria-label="Search chat history" /></div>
      ) : null}
      {loading ? (
        <div aria-busy="true" aria-label="Loading chat history" className={styles.loading}>
          {[0, 1, 2].map(index => <span key={index} className={styles.skeleton} />)}
        </div>
      ) : null}
      {!loading && error ? (
        <div className={styles.state} role="alert">
          <p><strong>{error}</strong></p>
          {errorDetail ? <p className={styles.detail}>{errorDetail}</p> : null}
          <button type="button" className={styles.retry} onClick={() => void load()}>Retry</button>
        </div>
      ) : null}
      {!loading && !error && sessions.length === 0 ? (
        <div className={styles.state}>
          <p>No conversations yet. Ask your first question and it will appear here.</p>
          <button type="button" className={styles.retry} onClick={() => onOpen(null)}><Plus size={14} />New chat</button>
        </div>
      ) : null}
      {!loading && !error && sessions.length > 0 && visible.length === 0 ? (
        <div className={styles.state}><p>No chats match “{query.trim()}”.</p></div>
      ) : null}
      {!loading && !error ? groups.map(({ group, items }) => (
        <div key={group}>
          <div className={styles.groupLabel}>{group}</div>
          <ul className={styles.list}>
            {items.map(item => (
              <li key={item.id} className={styles.row}>
                {renamingId === item.id ? (
                  <form
                    className={styles.renameForm}
                    onSubmit={event => { event.preventDefault(); void commitRename(item.id); }}
                  >
                    <input
                      ref={renameInput}
                      value={draft}
                      maxLength={120}
                      aria-label="Conversation title"
                      onChange={event => setDraft(event.target.value)}
                      onKeyDown={event => { if (event.key === 'Escape') { setRenamingId(null); setMenuId(null); } }}
                    />
                  </form>
                ) : (
                  <button
                    type="button"
                    title={item.title}
                    aria-current={item.id === activeSessionId ? 'true' : undefined}
                    className={'nav-item ' + styles.item + (item.id === activeSessionId ? ' active' : '')}
                    onClick={() => onOpen(item.id)}
                  >
                    <span className={styles.title}>{item.title}</span>
                  </button>
                )}
                {renamingId !== item.id ? (
                  <button
                    type="button"
                    className={styles.dots}
                    aria-label={`Conversation actions for ${item.title}`}
                    aria-expanded={menuId === item.id}
                    onClick={() => { setMenuId(menuId === item.id ? null : item.id); setConfirmDeleteId(null); }}
                  >
                    <Ellipsis size={15} />
                  </button>
                ) : null}
                {menuId === item.id ? (
                  <>
                    <button type="button" aria-hidden tabIndex={-1} className={styles.scrim} onClick={() => { setMenuId(null); setConfirmDeleteId(null); }} />
                    <div className={styles.menu} role="menu" aria-label={`Actions for ${item.title}`}>
                      <button type="button" role="menuitem" onClick={() => { setDraft(item.title); setRenamingId(item.id); setMenuId(null); setConfirmDeleteId(null); }}>Rename</button>
                      {confirmDeleteId === item.id ? (
                        <button type="button" role="menuitem" className={styles.danger} disabled={busyId === item.id} onClick={() => void commitDelete(item.id)}>
                          {busyId === item.id ? 'Deleting…' : 'Confirm delete'}
                        </button>
                      ) : (
                        <button type="button" role="menuitem" className={styles.danger} onClick={() => setConfirmDeleteId(item.id)}>Delete</button>
                      )}
                    </div>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      )) : null}
    </div>
  );
}
