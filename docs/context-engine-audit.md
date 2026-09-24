# Context architecture audit (2026-09-23)

This audit describes the implemented Ask/Learn streaming path, not the proposed architecture in the product brief.

## Request path

1. `LearnChat` resolves a session ID from its active state or URL and sends `mode`, `gear`, `message`, action, expected Journey revision, and selected note context through `GenerationStream.start` (`web/components/learn-chat.tsx`, `web/lib/generation-stream.ts`). The browser creates a random idempotency key.
2. `POST /v1/sessions/{sid}/generations` accepts that request (`backend/app/generation_routes.py`). `material_owner` resolves the learner identity. `GenerationManager.create` inserts a durable generation record containing the request and session ID (`generation_service.py`, `generation_store.py`). The route does not itself resolve the session; `JourneyService.prepare_stream` does so before retrieval.
3. The generation task loads `JourneyService.get(owner, sid)`, which reads `journey_{sid}` from `practice_records` or returns an empty Journey. It rejects an outdated expected revision. `MaterialService.session(owner, sid)` enforces session ownership. The session ID is the conversation ID on this path; `journey.turns` is the visible transcript.
4. `prepare_stream` resolves explicitly selected note excerpts, attached source passages, image attachments, learner evidence, concept/teaching plan, up to four previous complete turns, up to three attempts for the concept, optional course metadata, and optional web evidence. It serializes these as JSON in a single prompt (`journey_service.py`, `context_service.py`, `workspace_note_context.py`). The web evidence loop and saved retrieval manifest are separate from the final prompt.
5. `GenerationManager` passes this prompt to `provider.stream_text`. OpenRouter sends a single `user` message, with image parts when present. OpenAI sends `input` as a string or a single `user` content array (`model_provider.py`). Both cap generated output at 3,500 tokens on this path. Neither uses provider conversation chaining.
6. Provider deltas become in-process SSE events. The frontend assembles temporary blocks and can reconnect using the generation ID and sequence (`generation_service.py`, `web/lib/generation-stream.ts`). Events are bounded in memory. After a process restart, a completed generation can be reconciled from canonical Journey state; live deltas cannot be replayed.
7. Only after the stream finishes, `commit_stream` writes the lesson artifact and appends a combined `{question, lesson}` turn to Journey in the same transaction as the generation completion record. `JourneyService.commit` updates the session snapshot and emits a `lesson.completed` state event for Learn. The frontend reloads Journey after completion.

## Already correct

- Learner and session ownership are checked during context preparation; owned note and attached source lookup maintain the same boundary.
- Existing Journey writes use an expected revision, so two completed generations from one revision cannot both append a turn.
- Generation creation has an idempotency key and request hash. A duplicate key with different content is rejected.
- Source retrieval excludes answer keys, sample papers, and private solutions. Explicit note selection has revision and size checks.
- The provider boundary captures exact usage when present; the generation record keeps timing and output estimates.
- The frontend restores saved Journey state after refresh and after a completed stream whose event replay expired.

## Partially correct

- The generation request is durable at submission, but the canonical visible user turn appears in Journey only with a successful assistant response. A failed/cancelled turn has no corresponding Journey message.
- Recent history is the last four completed turn pairs, regardless of size or relevance. Earlier turns remain in storage but are absent from the model request.
- Course and learner context are structured before serialization, but are flattened into one user prompt. The current learner message is not a distinct provider message.
- The 16 KB source budget and 12,000 character note budget are independent; there is no total input token budget. Assessment selection filters by concept but then takes the last three records from an ID-ordered listing.
- The session snapshot can point to an active generation, but the generation route itself does not reject concurrent requests for the same session. Optimistic Journey commit rejects one only after it has generated a full response.

## Missing

- A single context planner for all generation features, provider-neutral role/content serialization, token-aware recent history, durable conversation summary, context version, and context provenance diagnostics.
- Automatic note retrieval, semantic course retrieval, branch-specific prompt assembly, and context integration across Quiz and other generation flows.
- A durable stream replay store across process restarts and a developer context inspector.

## Potential bugs

- Two requests with the same expected revision can both reach the provider. The later one can fail its final Journey write, wasting a generation and leaving its user request only in `generation_records`.
- A failed generation disappears from the Journey transcript, even though its submitted request exists in the generation record.
- A large recent lesson plus notes, sources, and web evidence can exceed a model's input limit because there is no unified budget.
- `generation_store.create` returns an existing queued record for an idempotent retry; `GenerationManager.create` may start it again if it has no local task. This matters after a restart or multiple workers.
- Exact usage is read from mutable provider instance state after a stream. Concurrent generations sharing one provider can attribute usage to the wrong generation.

## Proposed migration path

1. Make submitted user turns durable and ordered before model work; ensure retry and failure states remain visible. Reserve one active generation per session or atomically claim the expected revision before provider work.
2. Add a provider-neutral `GenerationContext` and central planner. Preserve current source, note, image, evidence, course, and teaching-plan helpers as inputs.
3. Replace the four-turn slice with a budgeted recent window. Add durable compact conversation state for older turns with explicit version and provenance.
4. Serialize distinct instruction, supporting context, recent conversation, and current user messages at the provider boundary. Include context metrics in generation records.
5. Extend the planner to Quiz, Notes, Courses, and branches. Add retrieval improvements and a development inspector after continuity and budgeting are reliable.

## Implementation in this change

The streamed Ask/Learn path now uses `ContextEngine` to select complete recent turn pairs within an estimated input budget, includes compact state for older turns, and sends the current request as a distinct provider user message. The input budget defaults to 12,000 estimated tokens and can be set with `AI_TUTOR_CONTEXT_INPUT_BUDGET_TOKENS`. Explicitly selected notes remain required context; lexical automatic note matches are optional and course scoped. Assessment selection prioritizes attempts from the current session and concept.

One active generation is enforced per learner session by a partial unique index. `GET /v1/generations/{id}/context` exposes metadata without source text when `AI_TUTOR_DEV_CONTEXT_INSPECTOR=1`. The endpoint still requires learner ownership.

The implementation now reserves the submitted user turn in canonical Journey state in the same transaction as the generation record. The assistant response fills that turn on completion. Failed, cancelled, and interrupted generations retain the submitted turn and its status. The frontend reconciles the pending turn by generation ID and shows its terminal state. Generation descriptors include the submitted Journey revision.

Quiz assessment generation, review question generation and evaluation, remediation, lesson and branch teaching, note drafting, and study-note synthesis now call the shared budget planner. Retrieval ranks lexical matches and can add provider embeddings for owned, eligible materials and notes when `AI_TUTOR_EMBEDDING_MODEL` is configured. The embedding cache is covered by migrations 0022 and 0023, and retrieval falls back to lexical ranking when embeddings are unavailable. The development-only inspector exposes context metadata in the UI when both backend and frontend flags are enabled.

The baseline sections above describe findings before implementation and are retained as the migration record. The later P0 work made compaction strict: every completed turn displaced from the recent window must be folded into a validated, durable compact state before generation continues. A failed compaction fails the generation instead of silently losing earlier turns. The planner also includes an explicit lesson-state block and scores retrieval candidates for relevance. OpenAI and OpenRouter JSON generation now receive native role-separated messages from the shared planner. Generation events are persisted with sequence numbers for cross-worker and restart replay, and the terminal event is committed with the terminal record state. The inspector records selected and omitted block provenance, hashes, token estimates, and context version without storing raw provider inputs.

Remaining limits: token counts are estimates rather than a provider tokenizer. Embedding retrieval stays opt-in through `AI_TUTOR_EMBEDDING_MODEL` because it sends private learner material to OpenAI; a key alone does not enable it. When configured, failures fall back to lexical ranking plus metadata-aware reranking. The context inspector deliberately stores payload hashes and metadata, not full prompt text.

## P2 retrieval relevance

Material retrieval now applies owner/attachment/status/role checks and course scoping before ranking. A course session accepts general references and material in its own course; material from another course is excluded, including explicit passage selection. Candidate retrieval computes lexical signals and optional cached embedding similarity when `AI_TUTOR_EMBEDDING_MODEL` is explicitly configured, then a separate deterministic reranking pass combines normalized lexical relevance, phrase match, semantic similarity, and available title/heading/section/concept/lesson/course metadata. Structured concept, lesson, section, and course IDs can contribute an exact metadata boost; sparse metadata never acts as an authorization rule. Selected passages expose lexical, semantic, metadata, and combined relevance scores. With embeddings unconfigured or unavailable, retrieval safely uses lexical and metadata scores without transmitting source text externally.

Assessment context remains limited to the current concept, then ranks evidence using active quiz, matching lesson when the presentation links one, current session, weakness, latest quiz activity, and timestamp. Journey generation supplies active quiz and latest lesson IDs where available. Missing records and missing metadata safely fall back to concept/session/weakness/recency ordering.

## Live verification

An isolated current-build frontend (`localhost:3001`) and backend (`127.0.0.1:8001`) were run against a separate SQLite database on 2026-09-23. A first generation failed while the backend lacked outbound provider access; the submitted Journey turn remained visible as failed. After starting the isolated backend with provider access, the UI completed a 10-turn conversation: initial lesson, follow-up, correction from one coin flip to two, topic narrowing, a side question on independence, and a return to conditional probability. The saved answer recalled the exact correction and original blue-lighthouse cue. The final context inspector reported 18 recent messages, 5,608 estimated input tokens against a 12,000-token budget, and 4,516 exact provider prompt tokens. No summary was needed at that length. This verifies continuity on the hot-window path; it does not by itself validate semantic retrieval or live compaction under a smaller budget.

The completed implementation was then exercised through a fresh isolated UI session with a 4,500 estimated-token input budget. Thirteen turns covered an initial lesson, a correction from one flip to two, narrowing to at least one head, a side question on independence, return to the original problem, and recall of the initial blue-lighthouse cue. The last answer correctly recalled both the cue and correction. Its generation record reports `compactionTriggered=true`, `summaryUsed=true`, 16 recent messages, 4,339 estimated input tokens, and a provider payload SHA-256. The selected blocks include `conversationState` and `lessonState`, and 81 generation events have durable sequence numbers. This checks actual context assembly and the continuity behavior under compaction, while the raw provider prompt is intentionally not persisted.

## Verification and recovery completion

The API integration suite now runs a 25-turn conversation with a 4,500-token estimate budget and a provider-boundary capture on every turn. It asserts structured system/supporting/current-user roles, the exact current message, and equality between the payload captured at `stream_text` and the persisted provider/model/payload fingerprint. It verifies that compaction occurred, that the initial cue remains in compact state, the canonical Journey retains all 25 turns, and every generation remains within budget. A two-tab race test holds the first generation active while a second request attempts to use the same session revision; the second gets `409 generation_in_progress`. Two simultaneous SSE observers plus a reconnect using the last observed event ID receive a gapless, non-duplicated event sequence. A restart recovery test closes and reopens the store during a stream, verifies startup recovery marks it interrupted, and confirms the reconnect receives the durable terminal interruption event.

On 2026-09-23, the real local UI and configured provider completed a 20-turn conditional-probability conversation at the same 4,500 estimated-token budget. The turns included a one-to-two-flip correction, narrowing the conditioning event, a side question about independence, a return to the first question, and a final recall request. All 20 generations completed, had distinct provider-input SHA-256 fingerprints, and stayed within the estimated budget. Eleven included compact state and eight advanced the compaction boundary. The final answer and durable state retained the original blue-lighthouse cue and the two-flip correction. The provider payload itself remains intentionally unpersisted; the API integration test captures and verifies the exact provider-boundary object on every turn, while live records provide its matching fingerprint and per-block decisions.

The final focused recovery/relevance/provider suite passed: 35 tests. Semantic coverage includes explicit embedding opt-in and cache use, query-dependent semantic ranking, oversized-corpus and API-failure fallback, note owner/course/explicit-selection filtering, lexical and metadata reranking, and structured concept/lesson/section/course boosts. Embedding API failures fall back to lexical/metadata relevance. Embedding calls remain opt-in, and live UI verification deliberately disabled them to avoid sending learner materials externally.

## P1 context foundation status

All four P1 items in the task sheet are implemented:

1. `ContextEngine` is the shared planner for streamed Ask/Learn context, typed teaching context, and bounded JSON/assessment context. Existing retrieval and learning-state helpers feed it as candidate blocks.
2. The old fixed four-turn slice is replaced by a newest-first, token-estimated hot window. Complete user/assistant pairs are included together and returned in canonical order. Older turns remain canonical and P0 compaction must preserve them before the planner can proceed without them.
3. `GenerationContext` is provider-neutral: application instructions, typed supporting blocks, recent role-tagged turns, and the current user message remain separate. OpenAI and OpenRouter serializers consume this structure. The non-streaming Journey path now also passes the typed structure to providers that advertise support; legacy adapters retain the string compatibility path.
4. The planner enforces one estimated input-token allowance across instructions, the current message, required and optional context blocks, recent turns, and reserved image cost. Provider configuration caps the allowance and can subtract output and safety reserves from an explicitly configured model window. Existing per-source limits remain secondary safety caps.

Focused regression coverage checks complete hot-window turn pairs, extension beyond four turns, prioritization under pressure, required context, image reserves, model-window configuration, distinct current-message serialization, and structured context on the non-streaming Journey path. Token counting remains conservative and approximate; the system does not load per-model tokenizers, and the exact model window must be configured in `AI_TUTOR_MODEL_CONTEXT_WINDOWS` when the default cap is unsuitable.

## P1 context decision traceability

Each streamed generation stores a deterministic SHA-256 over canonical JSON containing the provider name, model name, and exact serialized provider request. `contextVersion` and `providerInputSha256` refer to that digest; the schema and serialization identifiers are stored alongside it. This identifies the exact wire payload and makes later reconstructed payloads verifiable, but the digest itself cannot recreate content.

For each included context block, the inspector reports its source, priority, required status, relevance score, estimated tokens, recursively discovered source IDs and revision/version markers, and a SHA-256 of the block content. It reports omitted blocks with a specific budget reason, estimated and remaining tokens, relevance, and omitted source IDs; recent turns omitted by the hot-window budget are recorded by turn index and count. Raw text and image bytes are not persisted in context metadata. Reconstructing the exact request therefore depends on canonical Journey state and the referenced source revisions still being available; where a source is mutable or external, the block hash can verify a reconstruction but cannot recover the original text.
