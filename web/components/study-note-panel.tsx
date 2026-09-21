"use client";

import { useCallback, useEffect, useState } from 'react';
import { BookOpen, Check, Pencil, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi, type NoteProposalRecord, type StudyNoteLink } from '@/lib/api';
import { openWorkspaceNote } from '@/lib/workspace-events';
import styles from './study-note-panel.module.css';

export function StudyNoteBanner({ sessionId }: { sessionId: string }) {
  const [link, setLink] = useState<StudyNoteLink | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoaded(false);
    try { setLink(await learningApi.getStudyNote(sessionId)); }
    catch { setLink(null); }
    finally { setLoaded(true); }
  }, [sessionId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function start() {
    setBusy(true);
    try { setLink(await learningApi.createStudyNote(sessionId)); }
    catch { /* Banner stays in the create state. */ }
    finally { setBusy(false); }
  }

  if (!loaded) return null;
  if (!link) {
    return (
      <div className={styles.banner}>
        <BookOpen size={15} />
        <span>Keep a study note for this chat — key ideas land there, not just here.</span>
        <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => void start()}>
          <Plus size={14} />{busy ? 'Creating…' : 'Start study note'}
        </Button>
      </div>
    );
  }
  return (
    <div className={styles.banner}>
      <BookOpen size={15} />
      <span>This chat maintains <strong>{link.title}</strong></span>
      <Button type="button" size="sm" variant="ghost" onClick={() => openWorkspaceNote(link.noteId)}>Open in Notes</Button>
    </div>
  );
}

function ProposalCard({ proposal, sessionId, onChanged }: {
  proposal: NoteProposalRecord;
  sessionId: string;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(proposal.body);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function accept(body?: string) {
    setBusy(true); setError('');
    try {
      const link = await learningApi.getStudyNote(sessionId);
      await learningApi.acceptNoteProposal(proposal.id, {
        body, heading: proposal.heading, expectedRevision: link?.revision,
      });
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The note changed. Reload and try again.');
    } finally { setBusy(false); }
  }

  async function reject() {
    setBusy(true); setError('');
    try {
      await learningApi.rejectNoteProposal(proposal.id);
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The proposal could not be rejected.');
    } finally { setBusy(false); }
  }

  const question = typeof proposal.source?.question === 'string' ? proposal.source.question as string : '';
  return (
    <div className={styles.proposal} aria-label={`Proposed note section ${proposal.heading}`}>
      <div className={styles.proposalHead}>
        <span className={styles.proposalEyebrow}>{proposal.origin === 'quiz' ? 'Review checklist proposed' : 'New section proposed'}</span>
        <strong>{proposal.heading}</strong>
        {proposal.conceptTitle ? <small>About {proposal.conceptTitle}</small> : null}
        {question ? <p className={styles.why}>From: “{question.slice(0, 140)}{question.length > 140 ? '…' : ''}”</p> : null}
      </div>
      {editing ? (
        <textarea
          className={styles.editor}
          value={draft}
          rows={6}
          aria-label="Edit proposed section"
          onChange={event => setDraft(event.target.value)}
        />
      ) : (
        <p className={styles.preview}>{proposal.body.slice(0, 280)}{proposal.body.length > 280 ? '…' : ''}</p>
      )}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      <div className={styles.actions}>
        {editing ? (
          <>
            <Button type="button" size="sm" disabled={busy || !draft.trim()} onClick={() => void accept(draft)}>
              <Check size={14} />Save edited section
            </Button>
            <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => { setEditing(false); setDraft(proposal.body); }}>Cancel</Button>
          </>
        ) : (
          <>
            <Button type="button" size="sm" disabled={busy} onClick={() => void accept()}>
              <Check size={14} />Add to note
            </Button>
            <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => setEditing(true)}>
              <Pencil size={14} />Edit
            </Button>
          </>
        )}
        <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => void reject()}>
          <X size={14} />Reject
        </Button>
      </div>
    </div>
  );
}

export function NoteProposalList({ sessionId, refreshKey, onChanged }: { sessionId: string; refreshKey: number; onChanged?: () => void }) {
  const [proposals, setProposals] = useState<NoteProposalRecord[]>([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    setLoaded(false);
    try { setProposals((await learningApi.listNoteProposals(sessionId, 'proposed')).proposals); }
    catch { setProposals([]); }
    finally { setLoaded(true); }
  }, [sessionId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, refreshKey]);

  if (!loaded || proposals.length === 0) return null;
  const handled = () => { void load(); onChanged?.(); };
  return (
    <div className={styles.list} aria-label="Proposed note sections">
      {proposals.map(proposal => (
        <ProposalCard key={proposal.id} proposal={proposal} sessionId={sessionId} onChanged={handled} />
      ))}
    </div>
  );
}
