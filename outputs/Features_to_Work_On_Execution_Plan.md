# Features to Work On — Execution Plan

## Purpose and authority

This file instructs a coding agent how to deliver the feature roadmap safely and incrementally. Product behavior, UI detail, contracts, and acceptance criteria live in [Features to Work On](Features_to_Work_On.md). Notes-specific design lives in [Note Taking Feature Plan](Note_Taking_Feature_Plan.md). Current system truth lives in [Forma Main Doc](Forma_Main_Doc.md).

Read all three before editing. When documents conflict, preserve existing canonical-state, ownership, and privacy rules; identify the conflict in the implementation report rather than silently choosing a new architecture.

## Non-negotiable rules

1. Inspect the current repository and relevant tests before designing a change. Reuse existing FastAPI, React, workflow-job, material, state, and Electron patterns.
2. `LearnerStateService` remains the sole writer of canonical learner concept state. No UI component, note service, planner, or model response may update mastery directly.
3. Start with local desktop mode. Do not make hosted auth, sync, billing, extensions, or a plugin marketplace a prerequisite for learner-facing features.
4. Do not create general abstractions, microservices, queues, vector databases, or new dependencies without an immediate requirement and an explanation in the implementation report.
5. Make every model-backed operation durable, idempotent, cancellable where appropriate, and recoverable after page refresh. Follow existing `WorkflowStore` patterns.
6. Keep raw learner notes, answers, and materials out of broad logs and telemetry. Persist only the minimum display-safe event data needed for product history.
7. Do not publish a release, create a tag, modify remote secrets, push a branch, or run destructive local-data actions unless the user explicitly asks.

## Mandatory work loop

For every work package below, perform this loop before moving on:

1. Read the referenced section in `Features_to_Work_On.md` and the relevant current code paths.
2. Write a short implementation note in the PR/turn report: reused infrastructure, new persistent data, new routes, UI entry point, and intentional non-goals.
3. Add the smallest complete vertical slice: schema/migration → service → route/job → API client → UI → error/recovery state.
4. Add targeted unit and API tests before polishing UI.
5. Run type checking, targeted lint, backend tests, migration tests, and a browser flow for the changed feature.
6. Inspect the diff for duplication, unbounded context access, direct learner-state writes, new secrets, accidental data exposure, and unused code.
7. Update `Forma_Main_Doc.md` from “planned” to “implemented” only after the acceptance tests pass.

## Baseline verification before any feature work

Run and record the outcome of:

```powershell
cd "C:\Projects\AI Tutor harness"
.\backend\.venv\Scripts\python.exe -m pytest backend\tests

cd web
node_modules\.bin\tsc --noEmit
npm run build

cd ..\desktop
node --check src\main.cjs
node --check src\preload.cjs
```

If the complete backend suite is environment-blocked, run the closest targeted test module and report the blocker. Do not describe an unrun test as passing.

For desktop work, also run `npm run package` after the production web build. For changes to the packaged web adapter, test one page plus its CSS and JavaScript asset URLs from the packaged web server; a page HTTP 200 alone is insufficient.

## Work package 0 — Stabilize the local desktop development loop

**Reference:** “Shared conventions” and “Local data, sync, extensions, and hosting” in [Features to Work On](Features_to_Work_On.md); current runtime details in [Forma Main Doc](Forma_Main_Doc.md).

1. Reproduce local start using `start-local.ps1`, then Electron development mode.
2. Ensure both processes agree on a reachable loopback address family and port. Avoid testing `localhost` and launching Electron against a different IPv4/IPv6 address.
3. Ensure the start script waits for a real web response before reporting success, handles stale local-server lock files, and reports a useful log path on failure.
4. Ensure Electron production static assets are served with correct status and MIME types.
5. Add automated smoke coverage for development service availability and packaged CSS asset loading.

**Gate:** A clean checkout starts the local web/API pair, `npm run dev` opens Electron without connection refusal, and packaged UI is styled.

## Work package 1 — Workspace shell and local Markdown notes

**Reference:** “Linked notes and workspace panel” plus its engineering handoff in [Features to Work On](Features_to_Work_On.md), and Phases 1–2 in [Note Taking Feature Plan](Note_Taking_Feature_Plan.md).

### Implementation order (before implmenting any of these features go through their in depth explaination and implmentation guideline in the features to work on file )

1. Add workspace layout state in the existing learning workspace, persisted locally after hydration: split ratio, collapsed state, tab list, active tab, and per-tab state.
2. Implement an accessible resizable right panel with only three tab types: Notes, Quiz, Sources. Do not build Review, Progress, Map, extensions, or a generic tab framework yet.
3. Add local note vault paths under Electron app data. Create a backend service that safely resolves paths and rejects traversal.
4. Add a schema migration for note metadata/index records. Markdown files are the source of truth for note bodies; index data must be rebuildable.
5. Add note CRUD, optimistic revision behavior, title search, and a clean API client.
6. Build Notes tab empty state, editor, save status, unsaved-close confirmation, and search.
7. Add selected-lesson-text capture into a new note, retaining a stable lesson/block/source anchor.
8. Add Notes/Quiz/Sources contextual tab opening from chat without changing the current left-chat conversation.

### Required tests

- Unit: front-matter parse/write preserves unknown keys; link parser handles valid/invalid IDs; path resolver blocks traversal.
- API: create/read/update with revision conflict, delete/export authorization, index rebuild, and learner isolation.
- Browser: resize panel, create/edit/save note, restart/reload and restore it, close a dirty note, save selected lesson text.
- Desktop: verify note directory belongs to app data, not installation directory.

**Gate:** One user can chat, save a selected passage to a right-side note, restart, reopen the note, and retain its text and anchor.

## Work package 2 — Note links, backlinks, and chat mention context

**Reference:** “Mentioning notes in Ask / Learn” and “Contextual tab behavior” in [Note Taking Feature Plan](Note_Taking_Feature_Plan.md).

1. Add stable typed link records for note↔note, note↔concept, note↔lesson block, note↔attempt, and note↔source passage.
2. Implement link autocomplete and backlink display. Broken targets must be visible and repairable; never silently delete a learner link.
3. Add `@` mention picker to the chat composer. The picker searches note title/body locally and inserts a stable-ID chip.
4. Add context receipt UI showing exactly which notes/sections will be sent; allow removal and opening the note tab.
5. Extend request contracts with a note-context manifest. Resolve only explicitly mentioned note content and selected section/revision.
6. Make the model prompt and UI label notes as learner-provided context, not source-verified truth.

### Required tests

- Unit: manifest resolution includes selected excerpt only and strips unrelated content.
- API: a learner cannot mention another learner’s note; stale revisions report conflict; deleted link targets remain visible.
- Browser: mention a note, remove it, send it, inspect the receipt, and open the linked note from chat.
- Security: send a note containing prompt-like text and verify it remains data/context, not executable instruction.

**Gate:** A learner can write “Explain this using @My note,” see the exact excerpt receipt, and get a response without exposing their other notes.

## Work package 3 — AI note drafts and repair notes

**Reference:** “AI-assisted note creation” in [Note Taking Feature Plan](Note_Taking_Feature_Plan.md).

1. Create typed `CreateNoteDraft` input and `NoteDraft` output contracts; include source anchors, generated label, proposed title/tags/links, and an origin reference.
2. Implement the internal note-draft skill using only current lesson, selected text, quiz feedback, explicit note mentions, and authorized materials.
3. Render a chat draft card with **Open in Notes**, **Save as new note**, **Replace selected section**, and **Discard**.
4. Replacements must use expected revision and preserve original content until the user confirms.
5. Persist provenance and generated-state metadata; permit the learner to edit/accept it.

### Required tests

- Unit: generated draft cannot contain an unapproved source anchor; replacement creates a conflict on stale note revision.
- API: model/provider failures leave no partial saved note.
- Browser: create a draft from lesson and quiz feedback, edit it, save it, discard it, and verify a draft never changes learner state.

**Gate:** No AI-created note enters the vault unless the learner explicitly saves it; no draft can award mastery or complete a review.

## Work package 4 — Next-action recommendation cards

**Reference:** “Adaptive learning planner” and “Next-action recommendations inside Learn” in [Features to Work On](Features_to_Work_On.md).

1. Define persisted recommendation and interaction schemas/migration.
2. Implement deterministic candidate generation from journey route, graph neighbors, evidence/state, review queue, and material coverage.
3. Implement transparent rule scoring and a policy version. Add hard exclusions before ranking.
4. Add recommendation endpoint/job and API client. Do not call models for the first slice.
5. Render 2–4 cards after a completed Learn response and in Progress. Wire Learn, Ask-prefill, Quiz-tab, and Review actions.
6. Record impression, selection, dismissal, completion, and failure without treating selection as evidence.

### Required tests

- Unit: neural-network fixture ranks backpropagation after neural-network introduction; unavailable/duplicate actions are excluded.
- API: recommendation set is owner-scoped, idempotent, and stores policy version.
- Browser: Learn card continues route, Ask card fills but does not send composer, Quiz card opens scoped tab.
- Regression: no recommendation path modifies canonical learner state without evidence admission.

**Gate:** The post-lesson UI offers actionable Learn, Ask, and Quiz paths with clear rationales and correct context.

## Work package 5 — Explainable state, review workspace, and timeline

**Reference:** “Evidence-driven review,” “Explainable concept state,” and “Learner timeline and review inbox” in [Features to Work On](Features_to_Work_On.md).

1. Build read projections for concept explanation and timeline from canonical state/evidence/events. Keep projections read-only.
2. Add Progress and Review tabs only after the workspace shell is stable.
3. Implement due review activities through durable workflow records, then reuse assessment rendering/evaluation.
4. Implement evidence challenge/invalidation with audit trail and recomputation, including clear confirmation UI.
5. Add timeline cursor pagination and deep links to original lesson/attempt/note contexts.

### Required tests

- API: state projection only reflects admitted evidence; challenge supersedes evidence and recomputes state.
- API: review completion reschedules conservatively; abandoned review does not upgrade state.
- Browser: inspect state rationale, complete one review, view the timeline entry, and follow a deep link.
- Migration: existing learner state and schedules remain readable.

**Gate:** A learner can understand why a concept is fragile, complete a review, and observe the evidence/timeline consequences.

## Work package 6 — Assessment quality gates and practice modes

**Reference:** “Assessment quality pipeline” and “Exam and practice modes” in [Features to Work On](Features_to_Work_On.md).

1. Separate item author, checker, and evaluator persisted artifacts before adding new practice modes.
2. Add deterministic quality checks, source-manifest linkage, question exposure accounting, and challenge invalidation behavior.
3. Keep all assessment UI shared between inline Learn and workspace Quiz.
4. Add `mode`/validated `modeConfig` to Quiz records, beginning only with topic drill and timed short quiz.
5. Defer voice/oral and code execution until a secure dedicated runtime is available.

### Required tests

- Fixture tests: leakage, duplicated template, ambiguous item, alternate valid answer, unsupported source, challenge withdrawal.
- API: unapproved item cannot be presented; evaluator cannot directly change state; timed session resumes accurately.
- Browser: start a topic drill, use hint, submit, create repair note, challenge item, resume a paused quiz.

**Gate:** A question must pass quality status before presentation, and all state changes still flow through evidence admission.

## Work package 7 — Materials grounding and one domain pack

**Reference:** “Materials-grounded learning” and “Domain packs” in [Features to Work On](Features_to_Work_On.md).

1. Complete bounded material selection and passage context receipts for Learn and Quiz before adopting a vector database.
2. Add source chips and Sources workspace tab deep links.
3. Build one small first-party domain-pack manifest with reviewed sources, graph seed, assessment blueprints, and evaluation fixtures.
4. Pin sessions to domain-pack and graph versions.

### Required tests

- API: only selected/owned material passages can enter a manifest.
- Browser: attach material, ask grounded question, open cited passage, see limited-coverage status when needed.
- Pack validation: invalid source/concept/skill reference fails at load time; existing session remains pinned after a pack update.

**Gate:** One real subject can be taught and assessed against bounded sources with inspectable support.

## Work package 8 — Evaluation, data portability, and release readiness

**Reference:** “Evaluation and policy experiments” and “Learner-controlled local and synced data” in [Features to Work On](Features_to_Work_On.md), plus [Desktop Application and GitHub Release Plan](Desktop_Application_and_GitHub_Release_Plan.md).

1. Add version-controlled fixtures and a deterministic evaluation runner for recommendation, note-context, item quality, grading, and false-mastery cases.
2. Add local backup archive support only after export schema is stable; confirm it excludes provider secrets.
3. Keep sync explicitly out of scope until conflict, ownership, encryption, and restore design are approved.
4. Run desktop packaged smoke tests, CSS/static-asset checks, local data persistence, export/delete, and installer upgrade scenarios.
5. Before public release, complete the existing signed-beta runbook; do not bypass signing/notarization gates.

**Gate:** CI runs evaluation fixtures without provider secrets; local backup/export/restore is documented and tested; packaged desktop validation passes on target platforms.

## Deferred work packages

Do not begin these without an explicit product decision and architecture review:

- Public skill marketplace and third-party executable extensions
- Cloud synchronization and collaboration
- Hosted multi-user edition, billing, and organization administration
- Voice tutoring and untrusted code execution
- Note graph visualization as primary navigation
- Calibrated knowledge tracing or claims about learning effectiveness

## Final completion report template

For each completed work package, report:

1. Feature/package and linked plan sections.
2. Learner-visible behavior delivered.
3. Files, migrations, routes, services, and components added/changed.
4. Data and state authority decisions.
5. Tests run with exact result.
6. Browser/desktop validation performed.
7. Known limitations and intentionally deferred scope.
8. Documentation updates needed or completed.
