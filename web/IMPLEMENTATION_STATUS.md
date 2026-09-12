# Implementation status

## Phase-one website slice

The current website establishes the user-facing shell for the learning harness: a quiet workspace, knowledge-map exploration, first-principles lesson reading, adjustable Teaching Gear, and contextual sidecar branches. State is kept in browser storage and is explicitly labeled as local to this device. Unknown topics now call the local FastAPI service and open a bounded draft graph in the same UI.

## Deliberate product decisions

The map screen shows relationships as suggested routes rather than hard prerequisites. The lesson screen keeps the main context visible while an exploration panel opens beside it. Quick, Guided, and Deep change the authored explanation depth. A selected passage can become the anchor for an exploration. Unknown topics explain that live generation is not connected instead of fabricating an answer.

## Backend slice now working

`backend/app` provides a FastAPI modular-monolith boundary with SQLite persistence. It resolves topic scopes, runs a synchronous graph job, returns seven concepts with typed edges, records structural validation and trust metadata, and exposes generated OpenAPI docs.

The Production Learning Kernel is now implemented behind the existing teaching-action endpoint. Each action exposes a typed context, persisted teaching plan, and deterministic policy-validation result. Prerequisite traversal uses only `requires` edges and stops clearly on missing nodes, cycles, unsupported relationships, or traversal budgets. Quick, Guided, and Deep select distinct pedagogical sequences; contextual controls compile into local typed overrides. Existing lesson fields remain intact, so the UI does not need to parse lesson prose to understand policy decisions.

The deterministic provider remains `limited_unverified` and makes no claim of source-backed correctness, model verification, evidence, or calibrated mastery. Lesson reading does not advance the learner projection, failed actions do not advance lesson position, and idempotent retries do not duplicate committed artifacts or evidence.

## Next engineering slice

1. Add a model-provider abstraction with routing, structured outputs, citations, and real verifier steps behind the current contracts.
2. Generate arbitrary-topic graphs with provenance, confidence, prerequisite closure, and review gates.
3. Connect typed plan fields to UI affordances without redesigning the current workspace.
4. Persist learner state, curriculum state, events, evidence, notes, and branches in PostgreSQL when moving beyond local development.
5. Add assessment blueprints, item-family generation, similarity guards, solver validation, and knowledge tracing as later slices.

The current UI is intentionally ready to connect to those contracts without pretending those services already exist.
