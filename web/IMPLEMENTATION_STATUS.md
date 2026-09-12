# Implementation status

## Phase-one website slice

The current website establishes the user-facing shell for the learning harness: a quiet workspace, knowledge-map exploration, first-principles lesson reading, adjustable Teaching Gear, and contextual sidecar branches. State is kept in browser storage and is explicitly labeled as local to this device. Unknown topics now call the local FastAPI service and open a bounded draft graph in the same UI.

## Deliberate product decisions

The map screen shows relationships as suggested routes rather than hard prerequisites. The lesson screen keeps the main context visible while an exploration panel opens beside it. Quick, Guided, and Deep change the authored explanation depth. A selected passage can become the anchor for an exploration. Unknown topics explain that live generation is not connected instead of fabricating an answer.

## Backend slice now working

`backend/app` now provides a FastAPI modular-monolith boundary with PostgreSQL selected by `DATABASE_URL` in deployed environments and a SQLite local/test fallback. Versioned Alembic migrations preserve the existing graph, session, action, lesson, event, and learner-graph data. The deterministic graph/teaching provider remains intentionally labeled `limited_unverified`; it does not fabricate source support.

The backend now exposes camelCase learner-state contracts for activity events, evidence admission and supersession, canonical concept state, review queues, nested branches, and anchored versioned notes. Reading a lesson records activity only. Canonical state changes only from accepted evidence through the versioned learner-state reducer. The web UI has not yet connected these routes and still uses browser storage for its visible state.

## Next engineering slice

1. Add a model-provider abstraction with routing, structured outputs, citations, and verifier/critic steps.
2. Generate arbitrary-topic graphs with provenance, confidence, prerequisite closure, and review gates.
3. Connect the existing workspace to durable sessions, learner state, branches, notes, and review queues.
4. Add assessment blueprints, item-family generation, similarity guards, solver validation, and calibrated knowledge tracing through the evidence-admission boundary.
5. Replace development learner headers with real authentication-derived ownership before hosted multi-user use.

The current UI is intentionally ready to connect to those contracts without pretending those services already exist.
