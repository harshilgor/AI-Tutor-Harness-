# Adaptive decision lifecycle gate

## Verdict

The immediate adaptive tutor does not require a separate `adaptive_decisions`
table. Immutable recommendation sets are the decision snapshots.

The original recommendation schema was insufficient for two required
invariants:

1. a stale tab could select a superseded recommendation;
2. a completed recommendation could not identify its accepted evidence.

Migration `0017_recommendation_lifecycle` therefore adds the minimum lifecycle
fields to `recommendation_sets`:

- `status`
- `input_digest`
- `superseded_by_set_id`
- `fulfilled_evidence_id`

## Invariants

- At most one recommendation set is `current` per learner session.
- A new evidence-sensitive input digest supersedes the previous current set.
- Selection and completion interactions reject superseded sets.
- Completion may link only accepted, owner-scoped evidence.
- Recommendation interactions remain context and audit records; they never
  create evidence or mutate learner concept state.

## Revisit the decision

Introduce a dedicated decision table only if a later phase requires multiple
simultaneous decisions per session/concept, independent cancellation state
machines, or normalized many-to-many decision/evidence relationships that
cannot be represented by one fulfilled evidence link.
