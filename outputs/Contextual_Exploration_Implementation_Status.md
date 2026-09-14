# Contextual Exploration — implementation status

Feature 6 turns “explain this” into a bounded, resumable sidecar exploration. The parent lesson remains the learner’s position while the sidecar gets its own branch identity and context.

## Built in this slice

- Durable branch listing under `GET /v1/learners/{learner_id}/branches` with optional session and closed-branch filters.
- Durable branch context under `GET /v1/learners/{learner_id}/branches/{branch_id}/context`, returning the selected branch, its ordered ancestor chain, direct children, and anchored notes.
- Explicit cancellation endpoint under `POST .../branches/{branch_id}/cancel`; cancellation uses the existing safe, idempotent close transition.
- Teaching actions accept `branchId` and carry branch identity, parent identity, and the immutable anchor snapshot into `ActionContext`.
- Branch teaching does not replace the parent session’s current lesson or concept position.
- Branch completion updates the branch’s return position and summary with optimistic revision checks.
- The ChatGPT-style Learn chat persists a sidecar before generating a focused response, aborts superseded requests, closes cancelled explorations, and labels nested explorations.
- API client contracts now use the durable learner-scoped routes and expose list, context, update, close, and cancel operations.

## Deliberate boundaries

The current synchronous kernel still generates the sidecar response through the existing teaching-action command. A later worker/streaming slice can keep the same branch command and add progressive block delivery without changing the persistence contract. Authentication remains the project’s development learner identity until the hosted auth layer is introduced.

## Verification

- `backend/tests/test_persistent_state_api.py`: 10 passed.
- `python -m compileall backend/app`: passed.
- `web`: `npx tsc --noEmit` passed.
- The production frontend build could not run because the environment’s automatic approval reviewer rejected the required elevated process permission after the account usage limit was reached.

## Next implementation slice

1. Add a branch-aware streaming worker and persisted generation status (`created`, `generating`, `ready`, `failed`, `cancelled`).
2. Add a visible branch breadcrumb and “return to parent” action that restores the parent sidecar from server context instead of closing it.
3. Persist sidecar lesson artifacts and notes under the branch, then expose them in Saved explorations and across devices.
4. Add browser-level flow coverage for passage selection → sidecar → nested branch → cancellation → return.
