"use client";

import { useEffect, useRef, useState } from 'react';
import { LoaderCircle, Plus, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi, type Gear, type LessonArtifact, type WorkspaceNoteSummary, type NoteDraft } from '@/lib/api';
import styles from './learn-chat.module.css';
import { ChatComposer, type ChatAttachment, type ChatNoteMention } from './chat-composer';
import { LessonReader } from './lesson-reader';
import { materialRequest, materialCommand, prepareAttachment, type MaterialAnswer } from '@/lib/chat-materials';
import { getJourney, workflow, waitForJob, type ChatMode, type Journey } from '@/lib/learning-workflows';
import { QuizWorkspace } from './quiz-workspace';
import { NoteDraftCard } from './note-draft-card';
import { NextActionCards } from './next-action-cards';
import { openWorkspaceNote, openWorkspaceNoteDraft, openWorkspaceSource, WORKSPACE_NOTE_MENTION_EVENT, WORKSPACE_NOTE_REPLACE_DRAFT_EVENT, type WorkspaceNoteMention } from '@/lib/workspace-events';

type NoteContextReceipt = { label: string; notes: { noteId: string; title: string; revision: number; startOffset?: number | null; endOffset?: number | null }[]; totalCharacters: number };
type ReplacementTarget = { noteId: string; title: string; revision: number; startOffset: number; endOffset: number };
type Turn = { question: string; lesson?: LessonArtifact; answer?: MaterialAnswer; files?: string[]; sessionId?: string; noteContext?: NoteContextReceipt };
type SelectedPassage = { blockId: string; selectedText: string; lessonId?: string; sessionId?: string };

export function LearnChat({ onQuiz }: { onQuiz?: (sessionId: string, conceptId?: string) => void }) {
  const [prompt, setPrompt] = useState('');
  const [gear, setGear] = useState<Gear>('Deep');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState<ChatMode>('ask');
  const [journey, setJourney] = useState<Journey | null>(null);
  const [checking, setChecking] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [noteMentions, setNoteMentions] = useState<ChatNoteMention[]>([]);
  const [noteDrafts, setNoteDrafts] = useState<NoteDraft[]>([]);
  const [replacementTarget, setReplacementTarget] = useState<ReplacementTarget | null>(null);
  const attachedVersions = useRef<string[]>([]);
  const [progress, setProgress] = useState('Thinking about that…');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState<SelectedPassage | null>(null);
  const scrollArea = useRef<HTMLDivElement | null>(null);
  const lesson = turns.at(-1)?.lesson || null;

  useEffect(() => {
    const element = scrollArea.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: turns.length > 1 ? 'smooth' : 'auto' });
  }, [turns.length, busy]);

  function applyJourney(next: Journey) { setJourney(next); setTurns(next.turns); setChatMode(next.mode); setGear(next.gear); }
  useEffect(() => {
    let active = true;
    async function restore() {
      try {
        const sid = localStorage.getItem('forma-chat-session');
        if (!sid) return;
        setBusy(true); setSessionId(sid);
        const pending = localStorage.getItem('forma-job:chat');
        if (pending) await waitForJob(pending, 'chat');
        const saved = await getJourney(sid);
        if (active) applyJourney(saved);
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : 'Could not restore the conversation.'); }
      finally { if (active) setBusy(false); }
    }
    void restore(); return () => { active = false; };
  }, []);

  useEffect(() => {
    const receiveExcerpt = (event: Event) => {
      const mention = (event as CustomEvent<WorkspaceNoteMention>).detail;
      if (!mention || mention.startOffset >= mention.endOffset) return;
      setNoteMentions(current => [
        ...current.filter(item => item.noteId !== mention.noteId),
        mention,
      ]);
      setError('');
    };
    window.addEventListener(WORKSPACE_NOTE_MENTION_EVENT, receiveExcerpt);
    return () => window.removeEventListener(WORKSPACE_NOTE_MENTION_EVENT, receiveExcerpt);
  }, []);

  useEffect(() => {
    const receiveReplacementTarget = (event: Event) => {
      const target = (event as CustomEvent<ReplacementTarget>).detail;
      if (!target || target.startOffset >= target.endOffset) return;
      setReplacementTarget(target); setError(`Selected section in “${target.title}” is ready for a draft replacement.`);
    };
    window.addEventListener(WORKSPACE_NOTE_REPLACE_DRAFT_EVENT, receiveReplacementTarget);
    return () => window.removeEventListener(WORKSPACE_NOTE_REPLACE_DRAFT_EVENT, receiveReplacementTarget);
  }, []);
  const noteContext = noteMentions.length ? { notes: noteMentions.map(note => ({ noteId: note.noteId, expectedRevision: note.revision, startOffset: note.startOffset, endOffset: note.endOffset })) } : undefined;

  async function addNoteMention(summary: WorkspaceNoteSummary) {
    try {
      const note = await learningApi.getWorkspaceNote(summary.id);
      if (note.body.length > 6000) { setError(`“${note.title}” is too long to mention as a whole note. Select a shorter passage from the note first.`); return; }
      setNoteMentions(current => current.some(item => item.noteId === note.id) ? current : [...current, { noteId: note.id, title: note.title, revision: note.revision, startOffset: 0, endOffset: note.body.length, excerpt: note.body }]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'This note could not be added as context.'); }
  }

  async function createLessonDraft(lessonId: string) {
    if (!sessionId || busy) return;
    setBusy(true); setError(''); setProgress('Preparing an editable note draft…');
    try {
      const result = await workflow(`/sessions/${sessionId}/note-drafts`, { originKind: 'lesson', lessonId, replacement: replacementTarget ? { noteId: replacementTarget.noteId, expectedRevision: replacementTarget.revision, startOffset: replacementTarget.startOffset, endOffset: replacementTarget.endOffset } : undefined }, `note-draft:${lessonId}`);
      if (!result?.noteDraftId) throw new Error('The note draft could not be recovered.');
      const draft = await learningApi.getNoteDraft(result.noteDraftId);
      setNoteDrafts(current => [...current.filter(item => item.id !== draft.id), draft]);
      setReplacementTarget(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create a note draft.'); }
    finally { setBusy(false); }
  }

  async function createQuizFeedbackDraft(attemptId: string) {
    if (!sessionId || busy) return;
    setBusy(true); setError(''); setProgress('Preparing a repair note draft…');
    try {
      const result = await workflow(`/sessions/${sessionId}/note-drafts`, { originKind: 'quiz_feedback', quizAttemptId: attemptId, replacement: replacementTarget ? { noteId: replacementTarget.noteId, expectedRevision: replacementTarget.revision, startOffset: replacementTarget.startOffset, endOffset: replacementTarget.endOffset } : undefined }, `note-draft:quiz:${attemptId}`);
      if (!result?.noteDraftId) throw new Error('The note draft could not be recovered.');
      const draft = await learningApi.getNoteDraft(result.noteDraftId);
      setNoteDrafts(current => [...current.filter(item => item.id !== draft.id), draft]); setReplacementTarget(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create a repair note draft.'); }
    finally { setBusy(false); }
  }
  async function journeyAction(action: string) {
    if (!sessionId || busy) return;
    setBusy(true); setError(''); setProgress('Preparing the next learning step…');
    try {
      await workflow(`/sessions/${sessionId}/journey`, { action, mode: chatMode, gear, message: action === 'adjust' ? prompt : '', expectedRevision: journey?.revision || 1, noteContext }, 'chat');
      applyJourney(await getJourney(sessionId));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Please try again.'); }
    finally { setBusy(false); }
  }

  async function submit() {
    const text = prompt.trim() || (attachments.length ? `Help me understand ${attachments.map(item => item.name).join(', ')}` : '');
    if (!text || busy) return;
    setBusy(true); setError('');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 170000);
    try {
      setProgress(attachments.length ? 'Reading your attachments…' : 'Thinking about that…');
      const currentSession = sessionId ? { id: sessionId } : await learningApi.createSession({ topic: text.slice(0, 200), goal: text.slice(0, 1000), gear });
      if (!sessionId) setSessionId(currentSession.id);
      try { localStorage.setItem('forma-chat-session', currentSession.id); } catch { /* Session remains server-side. */ }
      const ready: ChatAttachment[] = [];
      for (const item of attachments) ready.push(await prepareAttachment(item, controller.signal, uploaded => setAttachments(previous => previous.map(existing => existing.id === uploaded.id ? uploaded : existing))));
      const versions = ready.map(item => item.versionId!);
      for (const version of attachedVersions.current.filter(id => !versions.includes(id))) {
        await materialRequest(`/sessions/${currentSession.id}/materials/${version}`, { method: 'DELETE', signal: controller.signal });
        attachedVersions.current = attachedVersions.current.filter(id => id !== version);
      }
      for (const version of versions.filter(id => !attachedVersions.current.includes(id))) {
        await materialRequest(`/sessions/${currentSession.id}/materials`, materialCommand({ materialVersionId: version }, controller.signal));
        attachedVersions.current.push(version);
      }
      await workflow(`/sessions/${currentSession.id}/journey`, { mode: chatMode, gear, message: text, action: 'message', expectedRevision: journey?.revision || 1, noteContext }, 'chat');
      applyJourney(await getJourney(currentSession.id)); setPrompt(''); setNoteMentions([]);
    } catch (cause) {
      setError(cause instanceof DOMException && cause.name === 'AbortError' ? 'This model is taking too long to respond. Try a shorter question or try again.' : cause instanceof Error ? cause.message : 'The lesson could not be completed. Please try again.');
    } finally { window.clearTimeout(timeout); setBusy(false); }
  }

  function reset() { setTurns([]); setSessionId(null); setJourney(null); setChecking(false); setPrompt(''); setError(''); setAttachments([]); setNoteMentions([]); setNoteDrafts([]); setReplacementTarget(null); setSelection(null); attachedVersions.current = []; try { localStorage.removeItem('forma-chat-session'); } catch { /* Optional resume pointer. */ } }

  return <div className={styles.chatShell}>
    <div ref={scrollArea} className={styles.chatScroll}>
    <div className={`${styles.page} ${turns.length ? styles.reading : styles.empty}`}>
    {!turns.length && !busy ? <h1>Hi, what do you want<br className={styles.break} /> to learn today?</h1> : null}
    {journey?.steps.length && chatMode === 'learn' ? <section className={styles.journey} aria-label="Learning route"><details open={journey.status === 'proposed'}><summary>Your learning route · {journey.status === 'completed' ? journey.steps.length : journey.position} of {journey.steps.length} steps covered</summary><ol>{journey.steps.map((step, i) => <li key={`${step.conceptId}-${i}`} aria-current={i === journey.position ? 'step' : undefined}><strong>{step.title}</strong><p>{step.objective}</p></li>)}</ol></details><p>Coverage is not mastery. Your answers provide separate evidence.</p><div className={styles.lessonActions}>{journey.status === 'proposed' ? <><Button disabled={busy} onClick={() => void journeyAction('start')}>Start learning</Button><Button variant="outline" disabled={busy} onClick={() => setChecking(true)}>Check my starting point</Button><Button variant="ghost" disabled={busy || !prompt.trim()} onClick={() => void journeyAction('adjust')}>Adjust to my message</Button></> : <><Button disabled={busy || journey.status === 'completed'} onClick={() => void journeyAction(journey.status === 'paused' ? 'resume' : 'next')}>{journey.status === 'paused' ? 'Resume' : 'Continue'}</Button><Button variant="ghost" disabled={busy} onClick={() => void journeyAction('repair')}>I’m not following</Button><Button variant="ghost" disabled={busy} onClick={() => void journeyAction('pause')}>Pause</Button></>}</div></section> : null}
    {busy ? <div className={styles.loading} role="status"><LoaderCircle className={styles.spinner} size={22} /><h2>{progress}</h2><p>{prompt}</p><span>A thoughtful answer takes a little time.</span></div> : null}
    {turns.map((turn, turnIndex) => <div key={turn.lesson?.id || `material-${turnIndex}`} className={styles.turn}>
      <div className={styles.userPrompt}><span>You</span><div><p>{turn.question}</p>{turn.files?.map(name => <div className={styles.sentFile} key={name}><FileText size={15} />{name}</div>)}</div></div>
      <article aria-label="Learning lesson" className={styles.lessonArticle}>
        <LessonReader id={turn.lesson?.id || `material-${turnIndex}`}
          blocks={turn.lesson ? turn.lesson.blocks.filter(block => block.kind !== 'source_note') : (turn.answer?.blocks || []).map((block, index) => ({ ...block, id: `block-${index}` }))}
          onSelect={(block, raw) => setSelection({ blockId: block.id, selectedText: raw.slice(0, 1200), lessonId: turn.lesson?.id, sessionId: turn.sessionId })} />
        {turn.answer && <><p className={styles.hint}>{turn.answer.message}</p>{turn.answer.sources.length > 0 && <details className={styles.sources}><summary>{turn.answer.sources.length} passages from your materials</summary><p className={styles.hint}>Coverage is limited to these selected passages.</p>{turn.answer.sources.map(source => <button type="button" className={styles.sourceChip} key={source.spanId} onClick={() => openWorkspaceSource(source)}>{source.title} · Page {source.pageIndex + 1}</button>)}</details>}</>}
        {turn.noteContext?.notes.length ? <div className={styles.noteContextReceipt}><span>Learner note context · {turn.noteContext.totalCharacters} characters</span>{turn.noteContext.notes.map(note => <button type="button" key={note.noteId} onClick={() => openWorkspaceNote(note.noteId)}>@{note.title}</button>)}</div> : null}
        {turn.lesson ? <div className={styles.lessonActions}><Button variant="ghost" size="sm" disabled={busy} onClick={() => void createLessonDraft(turn.lesson!.id)}><FileText size={14} />{replacementTarget ? `Replace selected section with lesson draft` : `Create note draft`}</Button></div> : null}
        {noteDrafts.filter(draft => draft.sessionId === turn.sessionId).map(draft => <NoteDraftCard key={draft.id} draft={draft} onHandled={updated => setNoteDrafts(current => current.map(item => item.id === updated.id ? updated : item))} />)}
      </article>
    </div>)}
    {checking && sessionId && <QuizWorkspace key={`${sessionId}:${journey?.position || 0}`} inline sessionId={sessionId} conceptId={journey?.steps[journey.position]?.conceptId || lesson?.conceptId} onReturn={() => setChecking(false)} onCreateRepairNote={attemptId => void createQuizFeedbackDraft(attemptId)} />}
    {sessionId && turns.length > 0 && chatMode === 'learn' ? <NextActionCards sessionId={sessionId} enabled={!busy}
      onLearn={() => journeyAction('next')}
      onAsk={item => setPrompt(`Help me understand ${item.conceptTitle || 'this concept'}.`)}
      onQuiz={item => onQuiz?.(sessionId, item.conceptId || undefined)}
      onReview={() => setError('A review is not available for this recommendation yet.')} /> : null}    {sessionId && turns.length > 0 && <div className={styles.lessonActions}><Button variant="outline" disabled={busy} onClick={() => setChecking(!checking)}>Check understanding</Button><Button variant="ghost" disabled={busy} onClick={() => onQuiz?.(sessionId, journey?.steps[journey.position]?.conceptId || lesson?.conceptId)}>Quiz this concept</Button></div>}
    {turns.length > 0 && !busy ? <div className={styles.lessonActions}><span className={styles.hint}>AI-generated · Sources have not been independently verified.</span><Button variant="ghost" onClick={reset}><Plus size={15} />New lesson</Button></div> : null}
    {error ? <p className={styles.error} role="alert">{error}</p> : null}
    {selection ? <div className={styles.selection}><Button onClick={() => { setPrompt(`Explain this passage in the context of our conversation:\n\n${selection.selectedText}`); setSelection(null); }}>Ask about selection</Button><Button variant="outline" onClick={() => { openWorkspaceNoteDraft({ title: 'Lesson note', body: `> ${selection.selectedText.replace(/\n/g, '\n> ')}\n\n`, frontmatter: { lesson_id: selection.lessonId || null, block_id: selection.blockId, session_id: selection.sessionId || null, source: 'lesson_selection' } }); setSelection(null); }}>Save to notes</Button><Button variant="ghost" onClick={() => setSelection(null)}>Dismiss</Button></div> : null}
    </div>
    </div>
    <div className={styles.composerDock}><div className={styles.composerInner}><ChatComposer value={prompt} onChange={setPrompt} attachments={attachments} onAttachmentsChange={setAttachments} onSubmit={() => void submit()} busy={busy} followup={turns.length > 0} gear={gear} onGearChange={setGear} mode={chatMode} onModeChange={setChatMode} noteMentions={noteMentions} onAddNoteMention={note => void addNoteMention(note)} onRemoveNoteMention={noteId => setNoteMentions(current => current.filter(note => note.noteId !== noteId))} onOpenNoteMention={openWorkspaceNote} /></div></div>
  </div>;
}
