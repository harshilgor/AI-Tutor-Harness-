# AI Tutor Harness backend

This is the first functional backend slice for the learning harness. It
accepts any topic, creates a bounded `TopicScope`, runs a persisted graph job,
and returns a versioned graph with stable IDs, typed edges, and an explicit
trust label.

The default provider is `deterministic_baseline`. It requires no AI API key and
does not invent domain facts: it creates a generic instructional scaffold whose
concepts and relationships are marked `limited_unverified`. This makes the
frontend integration and state contracts testable immediately. The next
provider can implement the same `GraphGenerator.generate(scope)` boundary with
retrieval and a structured model call, followed by the same validation and
publication checks.

## Run locally

From the project root:

```powershell
$env:FORMA_DB_PATH = "backend/data/forma.db"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000` and its OpenAPI document at
`/docs`.

## First graph flow

```text
POST /v1/topic-scopes
  {"topic":"probability","depth":"introductory"}
        ↓
POST /v1/topic-scopes/{scope_id}/graph-jobs
        ↓
GET  /v1/graph-jobs/{job_id}
GET  /v1/graphs/{graph_id}
```

The synchronous completion is intentional for this local slice. The job is
still persisted with stages and status so it can move to a worker without
changing the HTTP contract. `Idempotency-Key` is accepted at the boundary and
will become the deduplication key when retries and authenticated sessions are
added.

## Learning-kernel teaching flow

The first ChatGPT-style action path is now functional with the same
provider-neutral boundary:

```text
POST /v1/sessions
  {"graphId":"graph_...","goal":"Understand the foundations"}
        ↓
POST /v1/sessions/{sessionId}/actions
  {"intent":"teach","conceptId":"concept_...","gear":"Guided",
   "message":"Teach me this from first principles"}
        ↓
GET  /v1/runs/{runId}
GET  /v1/actions/{runId}/events   (text/event-stream)
GET  /v1/lessons/{lessonId}
```

The action persists a session position, classifies free-form intent, assembles
the selected graph concept, applies Teaching Gear, creates a typed lesson
artifact, and emits replayable events (`action.started`, `intent.classified`,
`context.ready`, `plan.created`, `artifact.created`,
`verification.completed`, and `lesson.completed`). JSON uses camelCase for the
web client while the storage adapter keeps the records versionable.

The current local provider is deliberately called
`deterministic_baseline`. Its lesson is a qualified instructional scaffold
with `insufficient` trust and a source-review note. It does not claim to have
answered arbitrary domain questions or update mastery. A model and retrieval
provider can replace `learning_kernel.build_lesson` behind this same action
contract once a server-side API key and source policy are configured.

No API key is required for the current slice. A provider key becomes necessary
when the deterministic baseline is replaced with source retrieval and model
generated concepts. Keep that key server-side using `.env.example` as the
template; never place it in the browser or repository.

## Learner-owned knowledge graph

Topic graphs are bounded source material. The learner graph is a separate,
cross-topic projection that persists what a learner has encountered and the
evidence-backed overlay state that the learner-state service supplies. A topic
graph can be imported into the learner graph without changing the source graph;
repeating the same import does not duplicate its concepts or edges.

```text
POST /v1/learners/{learner_id}/knowledge-graph/import
  {"graph_id":"graph_..."}
GET  /v1/learners/{learner_id}/knowledge-graph
POST /v1/learners/{learner_id}/knowledge-graph/events
GET  /v1/learners/{learner_id}/knowledge-graph/events
```

The current event projection supports concept exploration, lesson completion,
assessment evidence, demonstrated concepts, review due, and detected
misconceptions. It records events separately from the graph snapshot and keeps
mastery estimation owned by the future learner-state module; these states are
an initial visual/UX projection rather than a claim of calibrated mastery.

Session creation now accepts an optional `learner_id` (default `local`) and
imports the session's topic graph into that learner's global projection. This
keeps the graph continuous across sessions and topics. Action evidence is not
implicitly inferred from session creation or generated lesson output; wiring
teaching-action and assessment evidence into the learner-state commit path is
the next step.
