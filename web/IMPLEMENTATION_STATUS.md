# Implementation status

## Phase-one website slice

The current website establishes the user-facing shell for the learning harness: a quiet workspace, knowledge-map exploration, first-principles lesson reading, adjustable Teaching Gear, and contextual sidecar branches. State is kept in browser storage and is explicitly labeled as local to this device. Unknown topics now call the local FastAPI service and open a bounded draft graph in the same UI.

## Deliberate product decisions

The map screen shows relationships as suggested routes rather than hard prerequisites. The lesson screen keeps the main context visible while an exploration panel opens beside it. Quick, Guided, and Deep change the authored explanation depth. A selected passage can become the anchor for an exploration. Unknown topics explain that live generation is not connected instead of fabricating an answer.

## Backend slice now working

`backend/app` provides a FastAPI modular-monolith boundary with SQLite persistence. It resolves topic scopes, runs a synchronous graph job, returns seven concepts with typed edges, records structural validation and trust metadata, and exposes generated OpenAPI docs. The deterministic provider is intentionally labeled `limited_unverified`; it does not fabricate source support.

## Next engineering slice

1. Add a model-provider abstraction with routing, structured outputs, citations, and verifier/critic steps.
2. Generate arbitrary-topic graphs with provenance, confidence, prerequisite closure, and review gates.
4. Persist learner state, curriculum state, events, evidence, notes, and branches in PostgreSQL.
5. Add assessment blueprints, item-family generation, similarity guards, solver validation, and knowledge tracing.

The current UI is intentionally ready to connect to those contracts without pretending those services already exist.
