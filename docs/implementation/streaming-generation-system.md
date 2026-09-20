# Shared streaming generation system

## Current architecture audit

The web client renders both Ask and Learn in `web/components/learn-chat.tsx`. It
currently submits `JourneyCommand` objects through `web/lib/learning-workflows.ts`.
Those requests create a durable `learning_jobs` record, run in a FastAPI
background task (`backend/app/learning_routes.py`), and are polled until the
entire `JourneyService.prepare()` result is committed. `JourneyService` already
owns the shared Ask/Learn context, route, policy, source, note-context, and
canonical turn logic. Its result is stored as one versioned `journey` practice
record by `WorkflowStore`.

`backend/app/model_provider.py` provides synchronous, provider-neutral lesson
methods plus an OpenRouter/OpenAI-compatible implementation. Its JSON methods
remain necessary for route proposals, quizzes, and other strict workflows.
`/v1/actions/{action_id}/events` in `backend/app/main.py` is a finite replay of
saved action events; it is not a live generation transport. There is no existing
browser streaming manager.

The database is SQLAlchemy/Alembic (SQLite for desktop and PostgreSQL in
deployment). The new durable generation record therefore belongs in its own
table, while high-volume token events must not be written to the primary
database.

## Target architecture and invariants

```
Ask UI / Learn UI
        |                    (mode-specific rendering only)
shared frontend generation stream manager
        |
Generation API (SSE observer endpoints)
        |
Generation orchestrator -- canonical Journey persistence
        |                 (final Turn/LessonArtifact is authoritative)
provider-neutral streaming adapter
        |
OpenAI Responses API / OpenRouter Chat Completions API
```

The HTTP stream observes a generation; it does not own it. A generation has a
durable ID, owner/session/request identity, mode, lifecycle, provider metadata,
sequence high-water mark, cancellation flag, and final journey revision. The
durable journey result is authoritative. Partial browser state is never
persisted as an answer and `generation.completed` is published only after the
canonical journey transaction succeeds.

## State machine

`queued -> preparing -> streaming -> finalizing -> completed` is the successful
path. `queued`, `preparing`, `streaming`, and `finalizing` may move to `failed`.
`queued`, `preparing`, and `streaming` may move through `cancel_requested` to
`cancelled`. On process startup, active durable records are marked
`interrupted`; terminal records never resume. An explicit cancellation endpoint
is the only user cancellation path; temporary observer disconnects leave the
generation alive for a short grace period.

## API and event contract

* `POST /v1/sessions/{session_id}/generations` requires `Idempotency-Key` and
  creates (or returns) a generation. It returns a JSON generation descriptor;
  observation is deliberately a separate connection so a POST retry never
  starts a second provider request.
* `GET /v1/generations/{generation_id}/events?after=N` streams SSE. It accepts
  `Last-Event-ID` and replays events strictly after the supplied sequence.
* `POST /v1/generations/{generation_id}/cancel` requests upstream cancellation.

Every normalized event includes `generationId` and a monotonically increasing
`sequence`: `generation.started`, `generation.context_ready`, `text.delta`,
`lesson.block_started`, `lesson.block_completed`, `source.added`,
`generation.completed`, `generation.cancelled`, or `generation.error`.
Provider event names and wire formats stay inside `model_provider.py`.

Delivery is at-least-once. The frontend applies an event only if its sequence is
greater than the last applied sequence. Event replay is a bounded in-memory
implementation behind an event-store boundary: the desktop process does not
claim replay survives a process restart. When replay has expired, the backend
returns `REPLAY_EXPIRED` unless a persisted completed result can be reconciled.
A distributed deployment can replace this buffer with a shared Redis-backed
implementation without changing the API or frontend manager.

## Learn semantic representation

The live Learn view uses a progressive parser that turns provider-neutral
Markdown sections into semantic explanation, example, equation, code, check,
and summary blocks. Each block has start, delta, and completion events and is
normalized into the existing `LessonArtifact` contract at finalization.
Markdown remains a content format rather than the transport protocol.

## Implementation tasks

1. Add the generation migration, validated request/record types, store, bounded
   replay buffer, event framing, lifecycle checks, and stable error taxonomy.
2. Add provider-neutral async text streaming for OpenAI Responses SSE and
   OpenRouter chat-completions SSE, preserving synchronous JSON calls.
3. Add a generation orchestrator that uses shared Journey context/persistence,
   normalizes provider chunks, coalesces events, supports cancellation, and
   commits the final Journey atomically with `completed` status.
4. Add generation routes, headers, heartbeat, ownership checks, idempotency,
   reconnect/replay, and terminal recovery.
5. Add one frontend stream manager for creation, SSE parsing, sequence handling,
   reconnect/backoff, cancellation, and canonical reconciliation.
6. Migrate free-form Ask and actual Learn lesson actions to the manager. Route
   proposal, quizzes, note drafts, and other strict workflows remain job-based.
7. Add unit/integration coverage for transitions, idempotency, replay,
   cancellation, failure, and persistence; then exercise the React build.

## Operational limits and decisions

The local buffer keeps a bounded number of events and coalesces text deltas on a
short interval/character threshold. Terminal events are never dropped. SSE uses
`no-cache, no-transform`, `X-Accel-Buffering: no`, and heartbeats; production
reverse proxies must preserve those headers and disable response buffering.
The durable record keeps provider/model identifiers and lifecycle metrics
without raw learner text: queue time, context build time, provider and
application TTFT, completion time, output characters, and clearly labelled
estimated tokens/throughput. A hosted multi-process rollout must provide a
shared implementation of `ReplayEventStore`.

## Acceptance checks

Ask and Learn share the API/orchestrator/stream manager, reconnect never
regenerates, duplicate sequence events do not duplicate text, Stop closes the
provider stream and emits `generation.cancelled`, and a visible completion is
reconciled from the saved journey. The full test suite and browser flow remain
the final verification gate.

## Remaining Gaps — Implementation Plan

| Gap | Current behavior | Implementation and acceptance criteria |
| --- | --- | --- |
| Generation recovery | A stream reconnects only while its `GenerationStream` object remains mounted. | Persist `{generationId, sessionId, mode, lastAppliedSequence, status}` under the existing `forma-*` local-storage convention; reattach on chat initialization without issuing POST. Clear it only after canonical reconciliation. Test active and completed recovery. |
| Replay expiry | The server returns `REPLAY_EXPIRED` metadata, but the client treats it as an ordinary error. | Treat a completed replay-expired generation as a canonical-reconciliation signal and fetch the Journey. Failed/cancelled states restore a terminal message. |
| Semantic Learn stream | One explanation block receives all text. | Use a backend content parser to turn neutral Markdown section markers into normalized explanation/example/equation/code/check/summary blocks, emitting start/delta/complete events and persisting the validated `LessonArtifact`. |
| Selection explanation | Selected text only pre-fills the main composer. | Add a docked contextual explanation surface tied to a selection generation, with progress, stop, recovery, and follow-up handling. |
| Image understanding | Images upload but material processing returns `needs_attention`. | Preserve attachment safety checks, add a provider capability boundary for image inputs, and return a controlled unsupported-vision error where a configured model cannot accept images. |
| Link ingestion | URLs are only text in a prompt. | Add a bounded source-ingestion path that validates public HTTP(S), blocks private/loopback targets, restricts redirects/content types/size/time, extracts readable text, and stores it through the material/span system. |
| Streaming hardening | The local replay buffer is an in-memory concrete class with limited lifecycle timing. | Depend on a replay-store protocol, retain the in-memory implementation for desktop, record lifecycle/TTFT/completion metrics without learner content, and document proxy requirements. |
| Documentation and tests | Web documentation is stale and tests cover the first stream path. | Update the README and add recovery, semantic-block, failure, attachment, and URL tests. Provider live tests stay opt-in; proxy behavior is documented unless a hosted proxy exists. |

### Delivery order

1. Recovery and canonical reconciliation.
2. Semantic Learn block normalization and rendering.
3. Contextual selection explanations.
4. Image capability/input handling and secure URL ingestion.
5. Replay-store protocol, metrics, documentation, and complete regression tests.

### Status

| Feature | Status |
| --- | --- |
| Generation recovery | COMPLETE — local recovery pointer resumes the existing generation without POST |
| Replay reconciliation | COMPLETE — a completed replay-expired generation reconciles from the Journey |
| Semantic Learn streaming | COMPLETE — normalized block start/delta/complete events render progressively |
| Selection explanation | COMPLETE — docked stream, stop, and passage-scoped follow-ups |
| Image understanding | COMPLETE — safe attachments become OpenAI/OpenRouter vision inputs |
| URL ingestion | COMPLETE — SSRF-resistant bounded readable-page extraction |
| Replay store abstraction | COMPLETE — protocol plus desktop in-memory implementation |
| Metrics | COMPLETE — lifecycle and estimated output metrics persist on generation records |
| Provider live tests | COMPLETE — opt-in contract test; skipped unless explicitly enabled |
| Proxy validation | COMPLETE LOCALLY — response header regression; deployment checklist remains environment-specific |
| Documentation | COMPLETE |
| Regression tests | COMPLETE for the new generation, semantic, source, vision, URL, and proxy contracts; the repository-wide legacy suite still contains unrelated failing policy/recommendation tests |
