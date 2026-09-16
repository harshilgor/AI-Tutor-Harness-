"use client";

import { useEffect, useRef, useState } from 'react';
import { LoaderCircle, Plus, X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi, type Branch, type Gear, type LessonArtifact } from '@/lib/api';
import styles from './learn-chat.module.css';
import { ChatComposer, type ChatAttachment } from './chat-composer';
import { RichContent } from './rich-content';
import { LessonReader, type ReadingMode } from './lesson-reader';
import { materialRequest, materialCommand, prepareAttachment, type MaterialAnswer } from '@/lib/chat-materials';
import { getJourney, workflow, waitForJob, type ChatMode, type Journey } from '@/lib/learning-workflows';
import { QuizWorkspace } from './quiz-workspace';
import { openWorkspaceNoteDraft } from '@/lib/workspace-events';

type Passage = { blockId: string; selectedText: string; lessonId?: string; sessionId?: string; mode?: ReadingMode; equation?: boolean };
type Explanation = { heading: string; body: string };
type Turn = { question: string; lesson?: LessonArtifact; answer?: MaterialAnswer; files?: string[]; sessionId?: string };

export function LearnChat({ onQuiz }: { onQuiz?: (sessionId: string, conceptId?: string) => void }) {
  const [prompt, setPrompt] = useState('');
  const [gear, setGear] = useState<Gear>('Deep');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState<ChatMode>('ask');
  const [journey, setJourney] = useState<Journey | null>(null);
  const [checking, setChecking] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const attachedVersions = useRef<string[]>([]);
  const [progress, setProgress] = useState('Thinking about that…');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState<Passage | null>(null);
  const [passage, setPassage] = useState<Passage | null>(null);
  const [explanation, setExplanation] = useState<Explanation[]>([]);
  const [explanationBusy, setExplanationBusy] = useState(false);
  const [explanationError, setExplanationError] = useState('');
  const [activeBranch, setActiveBranch] = useState<Branch | null>(null);
  const explanationRequest = useRef(0);
  const explorationAbort = useRef<AbortController | null>(null);
  const branchParents = useRef(new Map<string, Branch>());
  const branchPassages = useRef(new Map<string, Passage>());
  const returnFocus = useRef<HTMLElement | null>(null);
  const closeHelp = useRef<HTMLButtonElement>(null);
  const cache = useRef(new Map<string, Explanation[]>());
  const lesson = turns.at(-1)?.lesson || null;

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

  async function journeyAction(action: string) {
    if (!sessionId || busy) return;
    setBusy(true); setError(''); setProgress('Preparing the next learning step…');
    try {
      await workflow(`/sessions/${sessionId}/journey`, { action, mode: chatMode, gear, message: action === 'adjust' ? prompt : '', expectedRevision: journey?.revision || 1 }, 'chat');
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
      await workflow(`/sessions/${currentSession.id}/journey`, { mode: chatMode, gear, message: text, action: 'message', expectedRevision: journey?.revision || 1 }, 'chat');
      applyJourney(await getJourney(currentSession.id)); setPrompt('');
    } catch (cause) {
      setError(cause instanceof DOMException && cause.name === 'AbortError' ? 'This model is taking too long to respond. Try a shorter question or try again.' : cause instanceof Error ? cause.message : 'The lesson could not be completed. Please try again.');
    } finally { window.clearTimeout(timeout); setBusy(false); }
  }

  async function explore(next: Passage) {
    const mode = next.mode || 'explain';
    const request = ++explanationRequest.current;
    explorationAbort.current?.abort();
    const controller = new AbortController();
    explorationAbort.current = controller;
    const key = `${next.lessonId || next.sessionId}:${next.blockId}:${mode}:${next.selectedText}`;
    if (!passage && !selection) returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setPassage(next); setSelection(null); setExplanationError(''); setExplanation(cache.current.get(key) || []); setExplanationBusy(!cache.current.has(key));
    requestAnimationFrame(() => closeHelp.current?.focus({ preventScroll: true }));
    if (cache.current.has(key)) return;
    let branch: Branch | null = null;
    try {
      const explorationSessionId = next.sessionId || (next.lessonId ? turns.find(turn => turn.lesson?.id === next.lessonId)?.sessionId : undefined);
      const sourceLesson = next.lessonId ? turns.find(turn => turn.lesson?.id === next.lessonId)?.lesson : lesson;
      if (explorationSessionId) {
        branch = await learningApi.openBranch({
          sessionId: explorationSessionId,
          parentBranchId: activeBranch?.id || null,
          conceptId: sourceLesson?.conceptId || null,
          anchor: { blockId: next.blockId, selectedText: next.selectedText },
          returnPosition: { lessonId: next.lessonId || null, blockId: next.blockId },
          localGear: gear,
          summary: next.selectedText.slice(0, 160),
        });
        if (activeBranch) branchParents.current.set(branch.id, activeBranch);
        branchPassages.current.set(branch.id, next);
        if (request === explanationRequest.current) setActiveBranch(branch);
      }
      let blocks: Explanation[];
      if (explorationSessionId && branch) {
        const intent = mode === 'simpler' ? 'simplify' : mode === 'example' ? 'example' : mode === 'why' ? 'why' : mode === 'symbols' ? 'visualize' : 'teach';
        const result = await learningApi.teachingAction(explorationSessionId, {
          intent,
          gear,
          message: next.selectedText,
          conceptId: sourceLesson?.conceptId,
          parentLessonId: next.lessonId,
          parentBlockId: next.blockId,
          branchId: branch.id,
          anchor: { blockId: next.blockId, selectedText: next.selectedText },
        }, { signal: controller.signal });
        blocks = result.lesson?.blocks.filter(item => item.kind !== 'source_note').map(item => ({ heading: item.heading || 'A closer look', body: item.body })) || [{ heading: 'A closer look', body: result.message || 'The exploration is ready.' }];
      } else if (next.lessonId) blocks = (await learningApi.explainLesson(next.lessonId, { blockId: next.blockId, selectedText: next.selectedText, mode }, { signal: controller.signal })).blocks;
      else if (next.sessionId) {
        const result = await materialRequest<MaterialAnswer>(`/sessions/${next.sessionId}/material-answer`, materialCommand({ message: `${mode === 'symbols' ? 'Explain every symbol and its role' : mode === 'example' ? 'Give a worked numerical example' : mode === 'why' ? 'Derive step by step and explain why' : mode === 'simpler' ? 'Explain in simpler language' : 'Explain'} this passage from our discussion, using the attached sources: ${next.selectedText}` }, controller.signal));
        blocks = result.blocks.length ? result.blocks : [{ heading: 'Source context', body: result.message }];
      } else throw new Error('This passage is missing its conversation context.');
      cache.current.set(key, blocks);
      if (request === explanationRequest.current) setExplanation(blocks);
    } catch (cause) {
      if (request === explanationRequest.current && !(cause instanceof DOMException && cause.name === 'AbortError')) setExplanationError(cause instanceof Error ? cause.message : 'Please try again.');
      if (branch && request === explanationRequest.current) void learningApi.closeBranch('local', branch.id, true).catch(() => undefined);
    }
    finally { if (request === explanationRequest.current) setExplanationBusy(false); }
  }

  function dismissHelp() { const branch = activeBranch; explorationAbort.current?.abort(); setPassage(null); setActiveBranch(null); ++explanationRequest.current; if (branch) void learningApi.closeBranch('local', branch.id).catch(() => undefined); returnFocus.current?.focus({ preventScroll: true }); }

  function returnToParent() {
    if (!activeBranch?.parentBranchId) { dismissHelp(); return; }
    const current = activeBranch;
    const parentId = current.parentBranchId as string;
    const parent = branchParents.current.get(parentId);
    const parentPassage = branchPassages.current.get(parentId);
    void learningApi.closeBranch('local', current.id).catch(() => undefined);
    if (!parent || !parentPassage) { dismissHelp(); return; }
    const key = `${parentPassage.lessonId || parentPassage.sessionId}:${parentPassage.blockId}:${parentPassage.mode || 'explain'}:${parentPassage.selectedText}`;
    setActiveBranch(parent); setPassage(parentPassage); setExplanation(cache.current.get(key) || []); setExplanationError('');
  }

  function reset() { dismissHelp(); setTurns([]); setSessionId(null); setJourney(null); setChecking(false); setPrompt(''); setError(''); setSelection(null); setAttachments([]); attachedVersions.current = []; cache.current.clear(); try { localStorage.removeItem('forma-chat-session'); } catch { /* Optional resume pointer. */ } }

  return <div className={`${styles.page} ${turns.length ? styles.reading : styles.empty}`}>
    {!turns.length && !busy ? <h1>Hi, what do you want<br className={styles.break} /> to learn today?</h1> : null}
    {journey?.steps.length && chatMode === 'learn' ? <section className={styles.journey} aria-label="Learning route"><details open={journey.status === 'proposed'}><summary>Your learning route · {journey.status === 'completed' ? journey.steps.length : journey.position} of {journey.steps.length} steps covered</summary><ol>{journey.steps.map((step, i) => <li key={`${step.conceptId}-${i}`} aria-current={i === journey.position ? 'step' : undefined}><strong>{step.title}</strong><p>{step.objective}</p></li>)}</ol></details><p>Coverage is not mastery. Your answers provide separate evidence.</p><div className={styles.lessonActions}>{journey.status === 'proposed' ? <><Button disabled={busy} onClick={() => void journeyAction('start')}>Start learning</Button><Button variant="outline" disabled={busy} onClick={() => setChecking(true)}>Check my starting point</Button><Button variant="ghost" disabled={busy || !prompt.trim()} onClick={() => void journeyAction('adjust')}>Adjust to my message</Button></> : <><Button disabled={busy || journey.status === 'completed'} onClick={() => void journeyAction(journey.status === 'paused' ? 'resume' : 'next')}>{journey.status === 'paused' ? 'Resume' : 'Continue'}</Button><Button variant="ghost" disabled={busy} onClick={() => void journeyAction('repair')}>I’m not following</Button><Button variant="ghost" disabled={busy} onClick={() => void journeyAction('pause')}>Pause</Button></>}</div></section> : null}
    {busy ? <div className={styles.loading} role="status"><LoaderCircle className={styles.spinner} size={22} /><h2>{progress}</h2><p>{prompt}</p><span>A thoughtful answer takes a little time.</span></div> : null}
    {turns.map((turn, turnIndex) => <div key={turn.lesson?.id || `material-${turnIndex}`} className={styles.turn}>
      <div className={styles.userPrompt}><span>You</span><div><p>{turn.question}</p>{turn.files?.map(name => <div className={styles.sentFile} key={name}><FileText size={15} />{name}</div>)}</div></div>
      <article aria-label="Learning lesson" className={styles.lessonArticle}>
        <LessonReader id={turn.lesson?.id || `material-${turnIndex}`}
          blocks={turn.lesson ? turn.lesson.blocks.filter(block => block.kind !== 'source_note') : (turn.answer?.blocks || []).map((block, index) => ({ ...block, id: `block-${index}` }))}
          onSelect={(block, raw, equation) => { returnFocus.current = document.getElementById(`${turn.lesson?.id || `material-${turnIndex}`}-${block.id}`); setSelection({ blockId: block.id, selectedText: raw.slice(0, 1200), equation, lessonId: turn.lesson?.id, sessionId: turn.sessionId }); }}
          onHelp={(block, mode) => void explore({ blockId: block.id, selectedText: block.body.slice(0, 1200), lessonId: turn.lesson?.id, sessionId: turn.sessionId, mode })} />
        {turn.answer && <><p className={styles.hint}>{turn.answer.message}</p>{turn.answer.sources.length > 0 && <details className={styles.sources}><summary>{turn.answer.sources.length} passages from your materials</summary>{turn.answer.sources.map(source => <details key={source.spanId}><summary>{source.title} · Page {source.pageIndex + 1}</summary><RichContent body={source.text} /></details>)}</details>}</>}
      </article>
    </div>)}
    {checking && sessionId && <QuizWorkspace key={`${sessionId}:${journey?.position || 0}`} inline sessionId={sessionId} conceptId={journey?.steps[journey.position]?.conceptId || lesson?.conceptId} onReturn={() => setChecking(false)} />}
    {sessionId && turns.length > 0 && <div className={styles.lessonActions}><Button variant="outline" disabled={busy} onClick={() => setChecking(!checking)}>Check understanding</Button><Button variant="ghost" disabled={busy} onClick={() => onQuiz?.(sessionId, journey?.steps[journey.position]?.conceptId || lesson?.conceptId)}>Quiz this concept</Button></div>}
    <ChatComposer value={prompt} onChange={setPrompt} attachments={attachments} onAttachmentsChange={setAttachments} onSubmit={() => void submit()} busy={busy} followup={turns.length > 0} gear={gear} onGearChange={setGear} mode={chatMode} onModeChange={setChatMode} />
    {turns.length > 0 && !busy ? <div className={styles.lessonActions}><span className={styles.hint}>AI-generated · Sources have not been independently verified.</span><Button variant="ghost" onClick={reset}><Plus size={15} />New lesson</Button></div> : null}
    {error ? <p className={styles.error} role="alert">{error}</p> : null}
    {selection ? <div className={styles.selection}>{([['explain', 'Explain'], ['simpler', 'Simpler'], ['example', 'Example'], ['symbols', 'Symbols'], ['why', 'Why?']] as const).map(([mode, label]) => <Button key={mode} onClick={() => void explore({ ...selection, mode })}>{label}</Button>)}<Button variant="outline" onClick={() => { openWorkspaceNoteDraft({ title: 'Lesson note', body: `> ${selection.selectedText.replace(/\n/g, '\n> ')}\n\n`, frontmatter: { lesson_id: selection.lessonId || null, block_id: selection.blockId, session_id: selection.sessionId || null, source: 'lesson_selection' } }); setSelection(null); }}>Save to notes</Button><Button variant="ghost" onClick={() => setSelection(null)}>Dismiss</Button></div> : null}
    {passage ? <aside className={styles.studyPanel} aria-label="Passage explanation" onKeyDown={event => { if (event.key === 'Escape') dismissHelp(); }}><div className={styles.panelHeader}><div><span>{activeBranch ? 'Exploration' : 'Study this passage'}</span><strong>{activeBranch?.parentBranchId ? 'Nested exploration' : 'A closer look'}</strong></div><Button ref={closeHelp} variant="ghost" size="icon" aria-label="Close explanation" onClick={dismissHelp}><X size={18} /></Button></div><blockquote><RichContent body={passage.equation ? `$$\n${passage.selectedText}\n$$` : passage.selectedText} /></blockquote>{activeBranch ? <p className={styles.branchMeta}>Saved to your learning session · revision {activeBranch.revision || 1}</p> : null}{explanationBusy ? <p role="status">Explaining this passage…</p> : null}{explanation.map((block, index) => <section key={index}><h3>{block.heading}</h3><RichContent body={block.body} /><Button variant="ghost" size="sm" onClick={() => void explore({ blockId: `branch-${index}`, selectedText: block.body.slice(0, 1200), lessonId: passage.lessonId, sessionId: passage.sessionId, mode: 'explain' })}>Explore this explanation</Button></section>)}{explanationError ? <div role="alert"><p>{explanationError}</p><Button variant="outline" onClick={() => void explore(passage)}>Try again</Button></div> : null}<Button variant="ghost" onClick={returnToParent}>{activeBranch?.parentBranchId ? 'Return to parent' : 'Return to lesson'}</Button></aside> : null}
  </div>;
}
