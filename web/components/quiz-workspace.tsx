"use client";

import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { learningApi, request } from '@/lib/api';
import { cancelWorkflow, getQuiz, workflow, waitForJob, type Quiz } from '@/lib/learning-workflows';
import { AssessmentCard } from './assessment-card';
import { openWorkspaceSource } from '@/lib/workspace-events';
import styles from './quiz.module.css';

export function QuizWorkspace({ sessionId, conceptId, inline = false, onReturn, onCreateRepairNote }: { sessionId?: string | null; conceptId?: string; inline?: boolean; onReturn?: () => void; onCreateRepairNote?: (attemptId: string) => void }) {
  const reduceMotion = useReducedMotion();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [saved, setSaved] = useState<{ id: string; title: string; status: string }[]>([]);
  const [count, setCount] = useState(inline ? 1 : 5);
  const [difficulty, setDifficulty] = useState('adaptive');
  const [mode, setMode] = useState<'topic_drill' | 'timed_short_quiz'>('topic_drill');
  const [duration, setDuration] = useState(600);
  const [now, setNow] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const scope = inline ? `inline:${sessionId}:${conceptId || 'current'}` : 'quiz';
  useEffect(() => {
    let active = true;
    async function restore() {
      try {
        const pending = localStorage.getItem(`forma-job:${scope}`);
        if (pending) { setBusy(true); const result = await waitForJob(pending, scope); if (result?.quizId) localStorage.setItem(`forma-${scope}`, result.quizId); }
        const id = localStorage.getItem(`forma-${scope}`);
        if (id) { const found = await getQuiz(id); if (active) setQuiz(found); }
        if (!inline) { const list = await request<{ quizzes: typeof saved }>('/v1/quizzes'); if (active) setSaved(list.quizzes); }
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : 'Could not restore this quiz.'); }
      finally { if (active) setBusy(false); }
    }
    void restore(); return () => { active = false; };
  }, [scope, inline]);
  useEffect(() => { const tick = () => setNow(Date.now()); const timer = window.setInterval(tick, 1000); const first = window.setTimeout(tick, 0); return () => { window.clearInterval(timer); window.clearTimeout(first); }; }, []);
  async function act(path: string, body: unknown) {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const result = await workflow(path, body, scope);
      const id = result?.quizId || quiz?.id;
      if (id) { setQuiz(await getQuiz(id)); try { localStorage.setItem(`forma-${scope}`, id); } catch { /* Server retains quiz. */ } }
      if (path.endsWith('/challenges')) setNotice('Flag saved. This response is excluded from scoring and learning evidence while disputed.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Please try again.'); }
    finally { setBusy(false); }
  }
  function start() {
    let sid = sessionId;
    try { sid ||= localStorage.getItem('forma-chat-session'); } catch { /* No current session. */ }
    if (!sid) { setError('Start a chat and attach reference material first, then quiz that topic.'); return; }
    void act('/quizzes', { sessionId: sid, conceptIds: conceptId ? [conceptId] : [], count, difficulty, origin: inline ? 'learn_inline' : 'quiz', mode, modeConfig: mode === 'timed_short_quiz' ? { duration_seconds: duration } : {} });
  }
  async function saveReviewChecklist() {
    let sid = sessionId;
    try { sid ||= localStorage.getItem('forma-chat-session'); } catch { /* No current session. */ }
    if (!sid || !quiz || busy) return;
    const weak = quiz.attempts.filter(attempt => attempt.score === null || attempt.score < 0.7).map(attempt => attempt.id);
    if (!weak.length) { setNotice('No gaps found — nothing to add to your study note.'); return; }
    setBusy(true); setError('');
    try {
      const link = sid ? await learningApi.getStudyNote(sid).catch(() => null) : null;
      const result = await workflow(`/sessions/${sid}/note-proposals`, { origin: 'quiz', attemptIds: weak, expectedNoteRevision: link?.revision ?? null }, `note-proposal:quiz:${quiz.id}`);
      setNotice(result?.status === 'applied' ? 'Review checklist added to your study note.' : 'Review checklist proposed — accept it from the chat.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The checklist could not be proposed.'); }
    finally { setBusy(false); }
  }
  const secondsLeft = quiz?.mode === 'timed_short_quiz' ? Math.max(0, Math.ceil((quiz.deadlineAt ? new Date(quiz.deadlineAt).getTime() - now : (quiz.remainingSeconds || 0) * 1000) / 1000)) : null;
  const timeExpired = secondsLeft === 0 && !!quiz?.deadlineAt;
  return <section className={inline ? styles.inline : styles.page} aria-label={inline ? 'Understanding check' : 'Quiz workspace'}>
    <header><span className={styles.meta}>{inline ? 'CHECK YOUR UNDERSTANDING' : 'PRACTICE WITH PURPOSE'}</span><h1>{inline ? 'Try the idea' : 'Quiz'}</h1><p>Test the reasoning, then try it in a different situation.</p></header>
    {!quiz ? <div className={styles.card}>
      <h2>{inline ? 'One short check' : 'Quiz your recent learning'}</h2><p>Questions use the reference material attached to your conversation.</p>
      {!inline && <div className={styles.setup}><label>Questions<select value={count} onChange={e => setCount(Number(e.target.value))}>{[1, 3, 5, 10].map(n => <option key={n}>{n}</option>)}</select></label><label>Difficulty<select value={difficulty} onChange={e => setDifficulty(e.target.value)}>{['adaptive', 'foundational', 'standard', 'stretch'].map(d => <option key={d} value={d}>{d}</option>)}</select></label><label>Practice mode<select value={mode} onChange={e => setMode(e.target.value as typeof mode)}><option value="topic_drill">Topic drill</option><option value="timed_short_quiz">Timed short quiz</option></select></label>{mode === 'timed_short_quiz' && <label>Time<select value={duration} onChange={e => setDuration(Number(e.target.value))}>{[300,600,900,1200].map(seconds => <option key={seconds} value={seconds}>{seconds / 60} minutes</option>)}</select></label>}</div>}
      <Button disabled={busy} onClick={start}>Prepare quiz</Button>
      {!inline && saved.map(q => <button className={styles.saved} key={q.id} disabled={busy} onClick={() => { setError(''); void getQuiz(q.id).then(setQuiz).catch(e => setError(e.message)); }}>{q.title}<span>{q.status.replaceAll('_', ' ')}</span></button>)}
    </div> : <>
      <div className={styles.progress}><strong>{quiz.title}</strong><span>{quiz.summary.attempted} of {quiz.count} answered</span><div className={styles.progressTrack} aria-hidden="true"><motion.span initial={false} animate={{ width: `${(quiz.summary.attempted / quiz.count) * 100}%` }} transition={reduceMotion ? { duration: 0 } : { duration: 0.24, ease: 'easeOut' }} /></div>{quiz.mode === 'timed_short_quiz' && <span aria-live="polite">Time left {secondsLeft} seconds</span>}</div>
      {timeExpired && <div className={styles.card} role="status"><h2>Time is up</h2><p>Your saved work is still available, but this timed quiz no longer accepts answers.</p></div>}
      <AnimatePresence mode="wait">{quiz.current && quiz.status !== 'paused' && !timeExpired && <motion.div key={quiz.current.id} initial={reduceMotion ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -10 }} transition={{ duration: 0.2, ease: 'easeOut' }}><AssessmentCard item={quiz.current} busy={busy} attempt={quiz.attempts.find(a => a.id === quiz.current?.attemptId)}
        onAnswer={answer => void act(`/quizzes/${quiz.id}/attempts`, { ...answer, presentationId: quiz.current!.id, expectedRevision: quiz.revision })}
        onHint={() => void act(`/presentations/${quiz.current!.id}/hints`, {})}
        onChallenge={reason => void act(`/attempts/${quiz.current!.attemptId}/challenges`, { reason })} onCreateRepairNote={onCreateRepairNote} onOpenSource={openWorkspaceSource} /></motion.div>}</AnimatePresence>
      {quiz.status !== 'completed' && quiz.current?.attemptId && <Button disabled={busy} variant="outline" onClick={() => void act(`/quizzes/${quiz.id}/retry`, { expectedRevision: quiz.revision })}>Try again with help</Button>}
      {quiz.status === 'completed' ? <div className={styles.card}><h2>Session complete</h2><p>{quiz.summary.score === null ? 'No scored answers yet.' : `${quiz.summary.score}% across ${quiz.summary.evaluated} evaluated answers.`}</p><p>{quiz.summary.assisted} with help · {quiz.summary.skipped} skipped · {quiz.summary.dontKnow} marked “I don’t know”</p><p className={styles.meta}>Practice score, not mastery. Questions adapt, so scores are not rankings.</p><div className={styles.actions}><Button variant="outline" onClick={onReturn}>Return to Learn</Button><Button variant="outline" disabled={busy} onClick={() => void saveReviewChecklist()}>Save review checklist</Button><Button variant="ghost" onClick={() => { setQuiz(null); localStorage.removeItem(`forma-${scope}`); }}>New quiz</Button></div></div> : <div className={styles.actions}>
        {!timeExpired && (!quiz.current || quiz.current.attemptId) && <Button disabled={busy} onClick={() => void act(`/quizzes/${quiz.id}/next`, { expectedRevision: quiz.revision })}>{quiz.current ? 'Next question' : 'Generate first question'}</Button>}
        {!timeExpired && <Button disabled={busy} variant="ghost" onClick={() => void act(`/quizzes/${quiz.id}/${quiz.status === 'paused' ? 'resume' : 'pause'}`, { expectedRevision: quiz.revision })}>{quiz.status === 'paused' ? 'Resume quiz' : 'Pause'}</Button>}
        {onReturn && <Button variant="outline" onClick={onReturn}>Return to Learn</Button>}
      </div>}
    </>}
    {busy && <div><p role="status">Saving and checking this activity… You can return to it later.</p><Button variant="ghost" onClick={() => void cancelWorkflow(scope).catch(cause => setError(cause.message))}>Stop</Button></div>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </section>;
}
