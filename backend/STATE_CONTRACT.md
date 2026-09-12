# Persistent learner-state contract

## Authority and safety invariant

`LearnerStateService` is the sole writer of canonical `learner_concept_states`.
Tutor output, lesson reading, concept clicks, notebook edits, and raw answer
submissions may append activity events, but they cannot award mastery. A state
change is committed only while admitting accepted evidence, in the same
transaction as its audit events, and always records the evidence ID and reducer
policy version.

The earlier learner-owned knowledge graph remains a cross-topic UI projection.
Its event vocabulary is retained for API compatibility, but it is not the
canonical mastery record and is never read by the state reducer. Consumers must
use `GET /v1/learners/{learnerId}/state` for learner-state decisions.

## Implemented now

- `DATABASE_URL` selects PostgreSQL (`postgresql+psycopg://...`) or the
  SQLite local/test fallback. `AI_TUTOR_ENV=production` refuses SQLite and a
  missing URL. Alembic upgrades run at API startup and can also run explicitly.
- Existing graph, graph-job, session, teaching-action, lesson, action-event,
  and learner-graph payloads remain readable. Migration `0003` backfills
  explicit session owner, state version, and durable concept/lesson position
  from legacy payloads without resetting history.
- Learners have a development identity record. Curriculum records pin graph
  ID/version, scope compatibility key, schema version, concept references, and
  generation metadata.
- Evidence records capture independent/assisted conditions, outcome, score,
  evaluator, reliability, source event, provenance, policy, curriculum version,
  admission state, deduplication key, and supersession links.
- Canonical concept state captures status, tentative confidence, uncertainty,
  version, timestamps, graph version, reducer policy, and all active evidence
  IDs used by the reduction.
- Misconception hypotheses link to evidence and have active/resolved lifecycle
  state. Accepted correct/partial evidence creates a review schedule; admitted
  `kind=review` evidence completes the originating schedule, writes review
  history, and schedules the next conservative review.
- Branches persist learner/session ownership, nesting, a typed anchor, typed
  return position, lifecycle, revision, optional local Teaching Gear, and
  summary. Notes persist typed anchors, learner/private scope, provenance,
  immutable revisions, and recoverable soft deletion.
- State events and evidence requests deduplicate by learner-owned idempotency
  keys. Branch and note updates use optimistic revisions.

## HTTP surface

All new response bodies use camelCase. Collection access is learner-scoped.

| Route | Contract |
|---|---|
| `GET /v1/learners/{id}/state` | Read canonical concept states |
| `POST/GET /v1/learners/{id}/events` | Append/inspect non-authoritative activity and audit events |
| `POST/GET /v1/learners/{id}/evidence` | Admit/deduplicate/supersede and inspect evidence |
| `GET /v1/learners/{id}/review-queue` | Read due reviews; `include_future=true` also returns scheduled work |
| `POST/GET/PATCH /v1/learners/{id}/branches/...` | Create/read/update a branch |
| `POST /v1/learners/{id}/branches/{branchId}/close` | Close while retaining its return position and authored data |
| `POST/GET/PATCH/DELETE /v1/learners/{id}/notes/...` | Learner-scoped anchored note CRUD |
| `GET /v1/learners/{id}/notes/{noteId}/revisions` | Inspect immutable note history |

Until authentication exists, non-`local` routes require an
`X-Dev-Learner-Id` header exactly matching the learner path. Missing headers
resolve only to `local`. This prevents accidental mixing during development; it
is not authentication and is unsafe for a hosted multi-user service. Disable it
with `AI_TUTOR_DEV_IDENTITY=false`; requests then fail closed until a trusted
auth integration replaces the dependency.

## Deliberately conservative or uncalibrated

`learner-reducer-v1` is a transparent rule, not knowledge tracing. One reliable
independent correct observation may set `demonstrated`; assisted success remains
`developing`; reliability and assistance bound confidence and uncertainty.
Review intervals are fixed at seven days for independent correct evidence and
one day for assisted/partial evidence. These values are operational defaults,
not validated mastery probabilities, difficulty estimates, learning claims, or
certification. `demonstrated` is revisable through later or superseding evidence.

Rejected evidence is retained with a reason and never enters the reducer.
Unknown graphs, concept/version mismatches, invalid supersession, raw activity,
and retried requests cannot mutate canonical state.

## Future ownership

- **Assessment:** item blueprints, private rubrics, answer evaluation, transfer
  validation, similarity guards, and calibrated evaluator reliability. It may
  propose evidence but must still call this admission boundary.
- **Knowledge tracing:** multi-observation estimators, forgetting calibration,
  prerequisite propagation, self-reported confidence, and empirical review
  intervals. It replaces the versioned reducer; it does not create another
  state store.
- **Authentication:** provider sessions, account/tenant membership, server-side
  learner derivation, permissions for shared notes, retention/deletion policy,
  and hosted isolation. The development header must be removed, not promoted
  into a security claim.
