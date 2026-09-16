/**
 * Browser client for the learning-kernel API.
 *
 * The UI preview currently reads the authored samples in learning-content.ts.
 * These contracts are the seam for replacing those samples with versioned,
 * source-aware graph and lesson responses once the API service is connected.
 * Keep this module free of React and provider-specific code so it can also be
 * used by server actions or a future streaming adapter.
 */

export type Gear = 'Quick' | 'Guided' | 'Deep';

export type GraphRevision = {
  id: string;
  version: number;
  status: 'draft' | 'generating' | 'published' | 'superseded' | 'failed';
  createdAt: string;
  publishedAt?: string | null;
};

export type TopicScope = {
  originalRequest: string;
  normalizedTitle: string;
  interpretation: string;
  objective?: string | null;
  depth: 'introductory' | 'intermediate' | 'advanced' | 'survey';
  language?: string | null;
  boundaries: string[];
  revision: number;
};

export type SourceRecord = {
  id: string;
  title: string;
  url?: string | null;
  locator?: string | null;
  publisher?: string | null;
  status: 'supported' | 'partially_supported' | 'conflicting' | 'insufficient';
  retrievedAt?: string | null;
};

export type ConceptTrust = {
  status: 'supported' | 'partially_supported' | 'conflicting' | 'insufficient';
  confidence?: number | null;
  sourceIds: string[];
  claimIds?: string[];
  reviewedAt?: string | null;
};

export type LearnerOverlay = {
  state: 'unassessed' | 'explored' | 'developing' | 'demonstrated' | 'review_due';
  evidenceCount: number;
  stateVersion: number;
  probability?: number | null;
  uncertainty?: number | null;
};

export type GraphConcept = {
  id: string;
  title: string;
  definition: string;
  summary: string;
  scope?: string | null;
  objectiveIds: string[];
  sourceIds: string[];
  trust: ConceptTrust;
  learner?: LearnerOverlay | null;
  layout?: { x: number; y: number; clusterId?: string | null } | null;
};

export type GraphEdgeType =
  | 'requires'
  | 'recommended_before'
  | 'related'
  | 'part_of'
  | 'contrasts'
  | 'enables';

export type GraphEdge = {
  id: string;
  fromConceptId: string;
  toConceptId: string;
  type: GraphEdgeType;
  rationale: string;
  sourceIds: string[];
  status: 'supported' | 'proposed' | 'conflicting' | 'rejected';
  confidence?: number | null;
};

export type KnowledgeGraph = {
  id: string;
  title: string;
  description: string;
  scope: TopicScope;
  revision: GraphRevision;
  concepts: GraphConcept[];
  edges: GraphEdge[];
  sources: SourceRecord[];
  focusConceptId?: string | null;
};

export type ScopeProposal = {
  kind: 'proposal';
  scope: TopicScope;
  graphId?: string | null;
};

export type ClarificationRequired = {
  kind: 'clarification_required';
  question: string;
  options?: string[];
  reason: string;
};

export type TopicResolution = ScopeProposal | ClarificationRequired;

export type LessonBlockKind =
  | 'explanation'
  | 'example'
  | 'analogy'
  | 'visual'
  | 'check'
  | 'reflection'
  | 'source_note';

export type LessonBlock = {
  id: string;
  kind: LessonBlockKind;
  heading?: string | null;
  body: string;
  conceptIds: string[];
  sourceIds: string[];
  trust: ConceptTrust;
  order: number;
};

export type LessonArtifact = {
  id: string;
  sessionId: string;
  conceptId: string;
  graphRevision: number;
  gear: Gear;
  blocks: LessonBlock[];
  nextAction?: 'continue' | 'check_understanding' | 'repair_prerequisite' | 'review' | null;
  status: 'pending' | 'approved' | 'qualified' | 'failed' | 'cancelled';
  verificationRunId?: string | null;
  generatedBy?: string;
};

export type LearningSession = {
  id: string;
  graphId: string;
  graphRevision: number;
  goal?: string | null;
  currentConceptId?: string | null;
  currentLessonId?: string | null;
  stateVersion: number;
};

export type BranchAnchor = {
  blockId?: string | null;
  selectedText?: string | null;
  startOffset?: number | null;
  endOffset?: number | null;
};

export type Branch = {
  id: string;
  sessionId: string;
  learnerId?: string;
  parentBranchId?: string | null;
  parentId?: string | null;
  conceptId?: string | null;
  anchor: BranchAnchor;
  returnPosition?: { conceptId?: string | null; lessonId?: string | null; blockId?: string | null; offset?: number | null };
  lifecycle?: 'open' | 'closed';
  status?: 'open' | 'collapsed' | 'saved' | 'closed';
  localGear?: Gear | null;
  summary?: string | null;
  revision?: number;
  lessonId?: string | null;
  createdAt?: string;
  updatedAt?: string;
  closedAt?: string | null;
};

export type BranchContext = {
  branch: Branch;
  ancestors: Branch[];
  children: Branch[];
  notes: NoteRecord[];
};

export type TeachingIntent =
  | 'teach'
  | 'simplify'
  | 'example'
  | 'why'
  | 'visualize'
  | 'check_understanding'
  | 'resume';

export type TeachingActionInput = {
  intent: TeachingIntent;
  conceptId?: string;
  gear: Gear;
  message?: string | null;
  parentLessonId?: string | null;
  parentBlockId?: string | null;
  branchId?: string | null;
  anchor?: BranchAnchor | null;
  expectedStateVersion?: number | null;
  curriculumVersion?: number | null;
};

export type RunStatus = {
  runId: string;
  status: 'received' | 'authorized' | 'context_ready' | 'planned' | 'generated' | 'verified' | 'delivered' | 'qualified_response' | 'repairing' | 'failed' | 'cancelled';
  progress?: number | null;
  message?: string | null;
  lesson?: LessonArtifact | null;
};

export type AttemptInput = {
  sessionId: string;
  itemId: string;
  response: unknown;
  assistance?: 'none' | 'hint' | 'example' | 'answer_revealed';
  expectedStateVersion?: number | null;
};

export type AttemptStatus = {
  attemptId: string;
  status: 'received' | 'grading' | 'graded' | 'evidence_accepted' | 'state_committed' | 'review_required' | 'failed';
  result?: 'correct' | 'incorrect' | 'partial' | 'unscored' | null;
  stateVersion?: number | null;
  evidenceIds?: string[];
};

export type NoteInput = {
  sessionId?: string | null;
  conceptId?: string | null;
  body: string;
  branchId?: string | null;
};

export type NoteRecord = NoteInput & { id: string; version: number; updatedAt: string };

export class LearningApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'LearningApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type ErrorResponse = { code?: string; message?: string; details?: unknown };

export function apiBaseUrl(): string {
  const configured = typeof process !== 'undefined' ? process.env.NEXT_PUBLIC_LEARNING_API_URL : undefined;
  const desktop = typeof window === 'undefined'
    ? undefined
    : (window as Window & { formaDesktop?: { apiBaseUrl?: string } }).formaDesktop?.apiBaseUrl;
  // The local backend is the default while the hosted API is being wired.
  // Deployments can set NEXT_PUBLIC_LEARNING_API_URL to their API origin.
  return (configured || desktop || 'http://127.0.0.1:8000').replace(/\/$/, '');
}

function desktopToken(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  return (window as Window & { formaDesktop?: { apiToken?: string } }).formaDesktop?.apiToken;
}

function url(path: string): string {
  return `${apiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  const token = desktopToken();
  if (token) headers.set('X-Forma-Desktop-Token', token);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  let response: Response;
  try {
    response = await fetch(url(path), { ...init, headers });
  } catch (cause) {
    if (init.signal?.aborted) throw cause;
    throw new Error('Cannot connect to the tutor service. Your message is still here. Start the local app with start-local.ps1, then try again.');
  }
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!response.ok) {
    const envelope = body && typeof body === 'object' ? body as ErrorResponse & { detail?: ErrorResponse } : {};
    const error = envelope.detail && typeof envelope.detail === 'object' ? envelope.detail : envelope;
    throw new LearningApiError(response.status, error.code || 'request_failed', error.message || `Learning API request failed (${response.status})`, error.details);
  }
  return body as T;
}

export type CreateTopicInput = {
  topic: string;
  objective?: string;
  depth?: TopicScope['depth'];
  language?: string;
  boundaries?: string[];
};

export type CreateGraphResult = {
  graphId: string;
  runId?: string | null;
  status: RunStatus['status'];
  scope?: TopicScope | null;
  clarification?: ClarificationRequired | null;
};

export type BaselineGraphConcept = {
  id: string;
  title: string;
  label: string;
  summary: string;
  objective: string;
  source_ids: string[];
  support_status: 'supported' | 'partial' | 'unverified';
};

export type BaselineGraph = {
  id: string;
  scope_id: string;
  title: string;
  description: string;
  publication_state: 'limited_unverified' | 'published' | 'draft';
  trust_summary: string;
  concepts: BaselineGraphConcept[];
  edges: Array<{ id: string; source: string; target: string; type: string; justification: string; support_status: string }>;
  sources: Array<{ id: string; title: string; url?: string | null; support_status: string }>;
  generated_by: string;
  created_at: string;
};

export type BaselineGraphResponse = {
  job: { id: string; scope_id: string; status: string; stage: string; progress: number; graph_id?: string | null; warnings: string[] };
  graph?: BaselineGraph | null;
};

export type LocalDataExport = {
  format: 'forma-local-export';
  version: number;
  learner_id: string;
  tables: Record<string, Array<Record<string, unknown>>>;
};

/** A learner-owned Markdown document in the local workspace vault. */
export type WorkspaceNoteSummary = {
  id: string;
  title: string;
  frontmatter: Record<string, unknown>;
  revision: number;
  relativePath: string;
  updatedAt: string;
};

export type WorkspaceNote = WorkspaceNoteSummary & {
  learnerId: string;
  body: string;
  createdAt: string;
};

export type WorkspaceNoteInput = {
  title: string;
  body?: string;
  frontmatter?: Record<string, unknown>;
};

export const learningApi = {
  async createBaselineGraph(input: { topic: string; objective?: string; depth?: 'overview' | 'introductory' | 'deep' }, options?: { signal?: AbortSignal; idempotencyKey?: string }): Promise<BaselineGraphResponse> {
    const scope = await request<{ id: string }>('/v1/topic-scopes', {
      method: 'POST',
      signal: options?.signal,
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
    return request<BaselineGraphResponse>(`/v1/topic-scopes/${encodeURIComponent(scope.id)}/graph-jobs`, {
      method: 'POST',
      signal: options?.signal,
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
    });
  },

  resolveTopic(input: CreateTopicInput, options?: { signal?: AbortSignal; idempotencyKey?: string }): Promise<TopicResolution> {
    return request<TopicResolution>('/v1/topics/resolve', {
      method: 'POST',
      signal: options?.signal,
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  },

  createGraph(input: CreateTopicInput & { scopeRevision?: number }, options?: { signal?: AbortSignal; idempotencyKey?: string }): Promise<CreateGraphResult> {
    return request<CreateGraphResult>('/v1/graphs', {
      method: 'POST',
      signal: options?.signal,
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  },

  getGraph(graphId: string, params: { revision?: number; focus?: string; depth?: number; signal?: AbortSignal } = {}): Promise<KnowledgeGraph> {
    const query = new URLSearchParams();
    if (params.revision !== undefined) query.set('revision', String(params.revision));
    if (params.focus) query.set('focus', params.focus);
    if (params.depth !== undefined) query.set('depth', String(params.depth));
    const suffix = query.size ? `?${query.toString()}` : '';
    return request<KnowledgeGraph>(`/v1/graphs/${encodeURIComponent(graphId)}${suffix}`, { signal: params.signal });
  },

  createSession(input: { graphId?: string; topic?: string; gear?: Gear; graphRevision?: number; goal?: string }): Promise<LearningSession> {
    return request<LearningSession>('/v1/sessions', { method: 'POST', body: JSON.stringify(input) });
  },

  explainLesson(lessonId: string, input: { blockId: string; selectedText: string; mode?: 'explain' | 'simpler' | 'example' | 'symbols' | 'why' }, options?: { signal?: AbortSignal }): Promise<{ blocks: Array<{ heading: string; body: string }> }> {
    return request(`/v1/lessons/${encodeURIComponent(lessonId)}/explanations`, { method: 'POST', signal: options?.signal, body: JSON.stringify(input) });
  },

  teachingAction(sessionId: string, input: TeachingActionInput, options?: { signal?: AbortSignal; idempotencyKey?: string }): Promise<RunStatus> {
    return request<RunStatus>(`/v1/sessions/${encodeURIComponent(sessionId)}/actions`, {
      method: 'POST',
      signal: options?.signal,
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  },

  getRun(runId: string, options?: { signal?: AbortSignal }): Promise<RunStatus> {
    return request<RunStatus>(`/v1/runs/${encodeURIComponent(runId)}`, { signal: options?.signal });
  },

  openBranch(input: { learnerId?: string; sessionId: string; parentBranchId?: string | null; conceptId?: string | null; anchor: BranchAnchor; returnPosition?: Branch['returnPosition']; localGear?: Gear | null; summary?: string | null }, options?: { idempotencyKey?: string }): Promise<Branch> {
    const learnerId = input.learnerId || 'local';
    return request<Branch>(`/v1/learners/${encodeURIComponent(learnerId)}/branches`, {
      method: 'POST',
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify({ sessionId: input.sessionId, parentBranchId: input.parentBranchId, anchor: { ...input.anchor, conceptId: input.conceptId }, returnPosition: input.returnPosition || { lessonId: null, blockId: input.anchor.blockId || null }, localGear: input.localGear, summary: input.summary }),
    });
  },

  listBranches(learnerId = 'local', sessionId?: string, includeClosed = false): Promise<Branch[]> {
    const params = new URLSearchParams({ includeClosed: String(includeClosed) });
    if (sessionId) params.set('sessionId', sessionId);
    return request<Branch[]>(`/v1/learners/${encodeURIComponent(learnerId)}/branches?${params}`);
  },

  getBranchContext(learnerId: string, branchId: string): Promise<BranchContext> {
    return request<BranchContext>(`/v1/learners/${encodeURIComponent(learnerId)}/branches/${encodeURIComponent(branchId)}/context`);
  },

  updateBranch(learnerId: string, branchId: string, input: { expectedRevision: number; returnPosition?: Branch['returnPosition']; localGear?: Gear | null; summary?: string | null }): Promise<Branch> {
    return request<Branch>(`/v1/learners/${encodeURIComponent(learnerId)}/branches/${encodeURIComponent(branchId)}`, { method: 'PATCH', body: JSON.stringify(input) });
  },

  closeBranch(learnerId: string, branchId: string, cancelled = false): Promise<Branch> {
    return request<Branch>(`/v1/learners/${encodeURIComponent(learnerId)}/branches/${encodeURIComponent(branchId)}/${cancelled ? 'cancel' : 'close'}`, { method: 'POST' });
  },

  submitAttempt(input: AttemptInput, options?: { idempotencyKey?: string }): Promise<AttemptStatus> {
    return request<AttemptStatus>('/v1/attempts', {
      method: 'POST',
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  },

  getAttempt(attemptId: string): Promise<AttemptStatus> {
    return request<AttemptStatus>(`/v1/attempts/${encodeURIComponent(attemptId)}`);
  },

  saveNote(input: NoteInput, options?: { idempotencyKey?: string }): Promise<NoteRecord> {
    return request<NoteRecord>('/v1/notes', {
      method: 'POST',
      headers: options?.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : undefined,
      body: JSON.stringify(input),
    });
  },

  updateNote(noteId: string, body: string, version: number): Promise<NoteRecord> {
    return request<NoteRecord>(`/v1/notes/${encodeURIComponent(noteId)}`, { method: 'PATCH', body: JSON.stringify({ body, version }) });
  },

  listWorkspaceNotes(learnerId = 'local'): Promise<WorkspaceNoteSummary[]> {
    return request<WorkspaceNoteSummary[]>(`/v1/learners/${encodeURIComponent(learnerId)}/workspace-notes`, {
      headers: { 'X-Dev-Learner-Id': learnerId },
    });
  },

  searchWorkspaceNotes(query: string, learnerId = 'local'): Promise<{ notes: WorkspaceNoteSummary[] }> {
    return request<{ notes: WorkspaceNoteSummary[] }>(`/v1/learners/${encodeURIComponent(learnerId)}/workspace-notes/search?${new URLSearchParams({ query })}`, {
      headers: { 'X-Dev-Learner-Id': learnerId },
    });
  },

  getWorkspaceNote(noteId: string, learnerId = 'local'): Promise<WorkspaceNote> {
    return request<WorkspaceNote>(`/v1/learners/${encodeURIComponent(learnerId)}/workspace-notes/${encodeURIComponent(noteId)}`, {
      headers: { 'X-Dev-Learner-Id': learnerId },
    });
  },

  createWorkspaceNote(input: WorkspaceNoteInput, learnerId = 'local'): Promise<WorkspaceNote> {
    return request<WorkspaceNote>(`/v1/learners/${encodeURIComponent(learnerId)}/workspace-notes`, {
      method: 'POST',
      headers: { 'X-Dev-Learner-Id': learnerId },
      body: JSON.stringify(input),
    });
  },

  updateWorkspaceNote(noteId: string, input: WorkspaceNoteInput & { expectedRevision: number }, learnerId = 'local'): Promise<WorkspaceNote> {
    return request<WorkspaceNote>(`/v1/learners/${encodeURIComponent(learnerId)}/workspace-notes/${encodeURIComponent(noteId)}`, {
      method: 'PATCH',
      headers: { 'X-Dev-Learner-Id': learnerId },
      body: JSON.stringify(input),
    });
  },

  exportLocalData(learnerId = 'local'): Promise<LocalDataExport> {
    return request<LocalDataExport>(`/v1/learners/${encodeURIComponent(learnerId)}/export`);
  },

  deleteLocalData(learnerId = 'local'): Promise<{ deleted: Record<string, number>; total: number }> {
    return request<{ deleted: Record<string, number>; total: number }>(`/v1/learners/${encodeURIComponent(learnerId)}/data`, { method: 'DELETE' });
  },
};
