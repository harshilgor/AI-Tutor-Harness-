import { request, type Gear, type LessonArtifact } from './api';

export type ChatMode = 'ask' | 'learn';
export type Source = { spanId: string; title: string; text: string; pageIndex: number };
export type Journey = {
  id: string; sessionId: string; revision: number; mode: ChatMode; gear: Gear; goal: string;
  status: string; position: number; steps: { conceptId: string; title: string; objective: string }[];
  turns: { question: string; lesson: LessonArtifact; sessionId: string; sources?: Source[]; noteContext?: { label: string; totalCharacters: number; notes: { noteId: string; title: string; revision: number; startOffset?: number | null; endOffset?: number | null }[] } }[];
};
export type Presentation = {
  id: string; quizId: string; concept_id: string; kind: 'single' | 'multiple' | 'short'; stem: string;
  options: { id: string; label: string }[]; hints: string[]; attemptId: string | null; difficulty: string;
  hintCount?: number; sources?: Source[]; retryOf?: string;
};
export type Attempt = {
  id: string; presentationId: string; conceptId: string; response: string; selectedIds: string[];
  score: number | null; feedback: string; solution: string; correctIds: string[]; status: string;
  outcome: string; assisted: boolean; conceptState: string | null;
};
export type Quiz = {
  id: string; sessionId: string; title: string; revision: number; status: string; count: number;
  mode: 'topic_drill' | 'timed_short_quiz'; modeConfig: { duration_seconds?: number }; deadlineAt: string | null; remainingSeconds: number | null;
  current: Presentation | null; attempts: Attempt[];
  summary: { score: number | null; evaluated: number; attempted: number; total: number; assisted: number; skipped: number; dontKnow: number; independentCorrect: number; retries: number; contested: number };
};
type Job = { id: string; status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'; result: { quizId?: string; sessionId?: string; itemId?: string; attemptId?: string; noteDraftId?: string; noteId?: string; proposalId?: string; status?: string; heading?: string; applyKind?: string; skipped?: string; message?: string } | null };
export const getJourney = (sid: string) => request<Journey>(`/v1/sessions/${sid}/journey`);
export const getQuiz = (qid: string) => request<Quiz>(`/v1/quizzes/${qid}`);

/** Persist the job ID before polling so reloads recover committed operations. */
export async function workflow(path: string, body: unknown, scope: string): Promise<Job['result']> {
  const serialized = JSON.stringify(body);
  let key = crypto.randomUUID();
  try {
    const pending = JSON.parse(localStorage.getItem(`forma-command:${scope}`) || 'null');
    if (pending?.path === path && pending?.body === serialized) key = pending.key;
    localStorage.setItem(`forma-command:${scope}`, JSON.stringify({ path, body: serialized, key }));
  } catch { /* In-memory requests remain idempotent. */ }
  const job = await request<Job>(`/v1${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key }, body: JSON.stringify(body) });
  try { localStorage.setItem(`forma-job:${scope}`, job.id); } catch { /* Server retains the operation. */ }
  return waitForJob(job.id, scope);
}
export async function waitForJob(id: string, scope: string): Promise<Job['result']> {
  for (let i = 0; i < 600; i++) {
    const job = await request<Job>(`/v1/learning-jobs/${id}`);
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      try { localStorage.removeItem(`forma-job:${scope}`); localStorage.removeItem(`forma-command:${scope}`); } catch { /* Optional recovery pointer. */ }
      if (job.status === 'failed') throw new Error(job.result?.message || 'Please try again.');
      if (job.status === 'cancelled') throw new Error('Stopped. Your last completed step and saved answers are preserved.');
      return job.result;
    }
    await new Promise(resolve => setTimeout(resolve, 1200));
  }
  throw new Error('This operation is still running. Reload to reconnect.');
}

export async function cancelWorkflow(scope: string): Promise<void> {
  const id = localStorage.getItem(`forma-job:${scope}`);
  if (id) await request(`/v1/learning-jobs/${id}/cancel`, { method: 'POST' });
}
