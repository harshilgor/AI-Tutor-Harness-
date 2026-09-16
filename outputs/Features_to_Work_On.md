# Features to Work On

## Product goal

Forma should be a learning runtime, not a general-purpose coding harness. Its advantage comes from persistent learner evidence, high-quality assessment, adaptive planning, source-bounded teaching, durable notes, and delayed-retention measurement.

## Priority 1 — Make the learning loop trustworthy

### Adaptive learning planner

Create a planner that selects the next useful action: teach, diagnose, repair, quiz, review, connect concepts, or pause. Every recommendation must explain the evidence and policy behind it.

### Evidence-driven review

Extend the review queue to account for independent versus assisted success, confidence, response time, repeated errors, delayed recall, and transfer. Reviews should choose the concept and activity, not merely send a generic reminder.

### Explainable concept state

Show the learner a concept-level state such as unknown, exposed, developing, independently demonstrated, fragile, or misconception suspected. Display the evidence supporting the status and allow corrections, resets, and challenges.

### Assessment quality pipeline

Separate question authoring, independent checking, and answer evaluation. Reject duplicate templates, answer leakage, ambiguous items, superficial numeric variations, and unsupported rubrics. Track item exposure and preserve challenge/invalidations.

## Priority 2 — Complete the learner workspace

### Linked notes workspace

Add a right-side note-taking workspace, initially taking half the horizontal space next to Learn chat. Notes are local, learner-owned Markdown documents with links to concepts, lessons, source passages, quiz attempts, and branches.

### Materials-grounded learning

Connect uploaded syllabi, slides, books, notes, papers, and rubrics to lessons and assessments. A learner should see which passages support a teaching claim or question.

### Learner timeline and review inbox

Provide a chronological view of lessons, attempts, evidence updates, review decisions, and note activity. A dedicated review inbox should make due work actionable and explain urgency.

### Exam and practice modes

Support source-bounded drills, timed papers, oral-viva practice, coding exercises, worked-solution comparison, mistake notebooks, and “same concept, different context” questions.

## Priority 3 — Make teaching modular and measurable

### Typed learning skills

Build skills such as `diagnose_gap`, `explain_concept`, `ask_socratic_question`, `generate_counterexample`, `author_assessment`, `grade_reasoning`, `repair_misconception`, `schedule_review`, and `summarize_learning_state` behind typed inputs and outputs.

### Evaluation and policy experiments

Create benchmark material with expert-reviewed questions, flawed questions, alternative valid reasoning, misconceptions, and delayed-transfer checks. Measure false mastery, ambiguity, quality of feedback, retention, completion, and cost.

### Domain packs

Develop one well-supported pack at a time, beginning with a concrete learner need. A pack contains source material, a concept map, assessment templates, rubrics, vocabulary, and domain-specific skills.

## Priority 4 — Extend Forma safely

### Learner-controlled local and synced data

Keep a local-first vault and learner database. Add encrypted, opt-in sync only after ownership, conflict handling, backups, export, and deletion behavior are designed.

### Skill and curriculum SDK

After internal contracts stabilize, let third parties package skills, concept maps, materials, and assessment rubrics. Every extension must declare permissions, data access, model usage, and evaluation evidence.

### Hosted edition

Introduce authenticated ownership, collaboration, billing, hosted retrieval, and multi-device sync only after local workflows have proven reliable.

## Suggested delivery order

1. Stabilize packaged desktop testing and release workflow.
2. Add the split chat-and-notes workspace and local Markdown note model.
3. Link notes to concepts, lesson passages, source spans, and quiz attempts.
4. Make learner state and review decisions visible.
5. Strengthen assessment author/check/evaluate quality gates.
6. Ground learning flows in materials and implement one domain pack.
7. Build evaluation datasets before broad adaptation claims.
8. Add sync, extensions, and hosted capabilities after the local product is dependable.

## Feature-by-feature product and build plan

### 1. Adaptive learning planner

**Learner experience.** After each meaningful event—starting a topic, answering a question, finishing a lesson, missing a quiz item, or returning after a delay—Forma shows one recommended next action in the chat and workspace header. The recommendation reads plainly: “Review the chain rule before integration by parts because your last attempt depended on a hint.” Learners can accept it, choose an alternative, or ask why.

**UI.** Add a small “Next best step” card below the chat response and in the Review/Progress workspace tab. It contains the suggested action, reason, estimated effort band, target concepts, and actions: **Start**, **Choose another action**, and **Why this?** Do not turn the interface into a dashboard of scores.

**Build.** Create a typed `LearningAction` contract and planner service. It reads canonical learner state, review schedules, prerequisites, active session checkpoint, material coverage, and current goal. Start with transparent deterministic rules; persist every recommendation, chosen alternative, reason, and outcome. The planner asks existing Learn, Quiz, and Review services to do work rather than owning their databases.

**First useful release.** Recommend either one due review, one prerequisite repair, or the next planned Learn step. Show the explanation and record whether the learner accepted it.

### Next-action recommendations inside Learn

**Learner experience.** After a learner asks “Teach me neural networks,” completes a lesson, answers a check, or pauses a quiz, Forma presents a small set of next moves directly below the response. It can recommend a Learn lesson such as **Learn backpropagation**, an Ask action such as **Ask why activation functions matter**, or an assessment action such as **Quiz your neural-network foundations**. Recommendations are optional pathways, not a compulsory curriculum.

**UI.** Render two to four action cards below the final lesson block. Each card has an action type icon (Learn, Ask, Quiz, Review), a short imperative label, one-sentence rationale, targeted concepts, and an expected effort band. Include **Show other paths** and **Why these?**. A user action opens the appropriate flow in place: Learn continues the chat, Ask pre-fills the composer without sending, Quiz opens a contextual Quiz workspace tab, and Review opens a retrieval prompt.

**Build.** Add a `NextActionRecommendation` contract: `id`, `kind`, `label`, `rationale`, `conceptIds`, `origin`, `context`, `rank`, and `policyVersion`. Generate candidate actions from the active journey, graph neighbors/prerequisites, state evidence, due schedules, and material coverage. A deterministic ranker begins with relevance, prerequisite readiness, review urgency, and novelty/exposure limits. Persist impressions, selections, dismissals, and outcomes for future evaluation; do not use clicks alone as proof of learning.

**First useful release.** After a lesson, offer the next route concept, one “ask a deeper question” composer prompt, and a short quiz. For the neural-network example: **Learn backpropagation**, **Ask how gradients change weights**, and **Quiz neural-network basics**.

### 2. Evidence-driven review

**Learner experience.** The learner opens Review from the right workspace panel and sees a calm queue: “Due now,” “Coming up,” and “Why this is due.” A review is a short retrieval activity, not a replay of a lesson. After it, Forma explains whether the concept looks more stable, still fragile, or needs repair.

**UI.** The Review tab has one active card at a time, a short prompt, optional hint, answer area, and “Not ready—teach me first.” A detail sheet explains schedule timing, previous attempts, and the evidence considered. Desktop reminders open the Review tab only when the learner chooses the notification.

**Build.** Extend review schedules with activity type, due reason, prior outcome, assistance level, and originating evidence. Use the existing schedule queue, assessment renderer, attempt/evaluation service, and learner-state writer. Select a low-cost recall or transfer activity based on the evidence gap; never infer success merely from opening a reminder.

**First useful release.** Use due schedules plus a short question generated from a previously assessed concept. Record independent/assisted outcome and reschedule through the existing state policy.

### 3. Explainable concept state

**Learner experience.** A learner can open any concept chip from chat, a note, quiz feedback, or map and see “What Forma currently knows.” The view says “Developing” or “Needs more evidence,” never a misleading percentage of mastery. The learner can inspect supporting attempts, mark an event inaccurate, and request a fresh check.

**UI.** Concept detail appears in a Progress or Concept-map tab: state label, latest evidence, review status, related notes, next suggested action, and a timeline. Include **Challenge this result**, **Reset local state**, and **Take a fresh check** actions with clear consequences.

**Build.** Reuse canonical `LearnerConceptState` and evidence records as the sole source. Build a read-only projection API for UI, plus deliberate challenge/invalidation actions that supersede evidence and recompute state. Do not let browser state, chat completions, or note edits become an alternate state store.

**First useful release.** Display current state, evidence list, due review, and a fresh-check path for concepts touched by Learn or Quiz.

### 4. Assessment quality pipeline

**Learner experience.** Questions feel genuinely different and test reasoning. Learners can ask for a hint, explain their reasoning, challenge an item, or choose a different question. Feedback identifies the idea to repair and links directly to Learn and a repair note.

**UI.** Quiz cards show purpose, concept targets, question type, optional hint, answer input, and feedback. The workspace Quiz tab provides progress and an exit/resume affordance. A **Challenge question** action opens a concise form instead of burying a complaint in chat.

**Build.** Keep author, independent checker, and evaluator as separate services with typed artifacts. Store question blueprint, concept targets, rubric, quality results, model/provider provenance, exposure count, and challenge state. The checker receives the prompt and sources but not the author key. Quality rules reject leakage, insufficient support, ambiguous distractors, repeated templates, and scopes outside the active material boundary.

**First useful release.** Implement two-stage generate/check for multiple-choice and short-answer questions, reuse approved items, and support learner challenge plus evidence invalidation.

### 5. Linked notes workspace

**Learner experience.** The workspace panel on the right is a personal learning desk. A learner reads chat on the left, captures a note on the right, tags that note with `@` in chat, opens quiz feedback beside it, and comes back later without losing their work.

**UI.** Use the Notes/Quiz/Sources tab strip and split-pane rules in [Note Taking Feature Plan](Note_Taking_Feature_Plan.md). Notes are Markdown, locally owned, searchable, linkable, and editable. AI can draft notes only after a user command; the learner saves or discards the draft.

**Build.** Store Markdown files under the user data directory; maintain a reconstructable SQLite note index for title, tags, text search, links, and backlinks. Create typed links to note, concept, lesson block, attempt, material passage, and review schedule. Build an explicit context manifest for `@note` mentions so the tutor receives only selected excerpts.

**First useful release.** Notes tab, CRUD, Markdown body, selected-text capture, `@note` whole-note mention, local search, and persistent split/tabs. Defer external editing, sync, note graph, and extensions.

### 6. Materials-grounded learning

**Learner experience.** A learner attaches a syllabus, slides, textbook excerpt, notes, or past paper, then asks “Teach chapter 3 using this.” They can inspect the source supporting a claim or question and see when the system lacks coverage.

**UI.** The Sources workspace tab lists selected materials and passages. Chat responses carry compact source chips; clicking opens the relevant passage. The composer has an attachment picker and a visible material-selection receipt. A “Coverage limited” label appears when a lesson or question has no adequate support.

**Build.** Reuse material ingestion, extraction, ownership controls, passage search, and context manifests. Add retrieval/reranking only after the source policy and evaluation set are in place. Persist source spans used for lessons/questions and make them retrievable from the response or assessment item.

**First useful release.** Attach/select local text and PDF materials, retrieve bounded passages for one Learn request, cite passages in the response, and disclose when deterministic or unverified content is used.

### 7. Learner timeline and review inbox

**Learner experience.** Progress is a story, not a leaderboard: “You learned this, struggled with this variation, made a repair note, then retained it two days later.” The inbox tells the learner what needs attention today and why.

**UI.** A Progress tab has a chronological timeline with filters for Learn, Quiz, Review, Notes, and state changes. The Review tab starts with due work and can show future items without making the learner anxious. Each entry opens its original context.

**Build.** Add an append-only learning activity projection from existing runs, attempts, evidence, schedules, notes, and user actions. Store typed event references rather than duplicated prose. Build a paginated API and a simple local projection first; retain privacy controls and export behavior.

**First useful release.** Show created lessons, completed quiz attempts, accepted evidence, note creation, and due reviews in date order.

### 8. Exam and practice modes

**Learner experience.** Learners choose a mode that matches their real goal: topic drill, timed paper, oral practice, coding practice, worked-solution comparison, or mistake repair. The mode explains the rules before it begins and gives specific next steps after it ends.

**UI.** Add a mode picker inside the existing Quiz tab, not a new unrelated application. Each mode has scope, available materials, length, timer behavior, assistance policy, and outcome. A mistake-note action is always available after feedback.

**Build.** Define `PracticeSession` as a specialization of the current quiz/session workflow with typed configuration and policy. Reuse assessment/evaluation/evidence logic where valid, but keep timer, rubric, output format, and assistance decisions explicit. Code execution requires a sandbox; defer it until an isolated runtime is available.

**First useful release.** Topic drill and timed short quiz using existing question/attempt contracts. Defer coding execution and oral voice mode.

### 9. Typed learning skills

**Learner experience.** Learners see reliable actions with clear outputs: explain, ask a question, give a counterexample, make a revision note, create a quiz, or repair a misconception. They do not need to understand the internal skill system.

**UI.** Expose skills as contextual actions in chat and workspace tabs. A skill action previews what it will use—concept, material, mentioned notes, or attempt feedback—and reports a useful result or failure state.

**Build.** Create a registry with stable skill name, input schema, output schema, authorization/policy, model/provider choice, source requirements, telemetry contract, and evaluator. Skills call shared services through interfaces; no skill gets direct authority to modify canonical learner state except via the evidence-admission flow.

**First useful release.** Formalize existing Learn, Quiz, note-draft, and review-generation paths as typed internal skills before exposing a third-party SDK.

### 10. Evaluation and policy experiments

**Learner experience.** This is mostly invisible. The learner benefits because Forma becomes less likely to ask bad questions, overstate certainty, or repeat ineffective interventions.

**UI.** Offer an unobtrusive “Was this useful?” control and a clear challenge path. Do not expose experimental assignment labels or treat users as data points without disclosure.

**Build.** Maintain versioned offline test fixtures and evaluators for factual accuracy, item ambiguity, answer leakage, rubric agreement, false evidence admission, note-context safety, and delayed-transfer behavior. Persist policy version and anonymized metrics needed for comparisons. Gate policy changes behind test results and reversible feature flags.

**First useful release.** A local evaluation suite for question quality and evidence admission, plus structured feedback events from Learn and Quiz.

### 11. Domain packs

**Learner experience.** Choosing a pack makes Forma immediately useful in a domain without pretending that one generic tutor understands every course. A learner sees bounded content, sources, terminology, learning objectives, and practice formats relevant to their subject.

**UI.** Add a pack chooser when starting a workspace or importing materials. The selected pack appears in the session header and controls available maps, templates, source policy, and terminology. Learners can still use a general mode.

**Build.** A pack is versioned content and configuration: concept-map seed, source manifest, assessment blueprints, rubrics, supported skills, policy configuration, and evaluations. Keep pack data separate from learner notes/evidence and pin sessions to pack version for reproducibility.

**First useful release.** One internally maintained pack for a concrete subject with expert-reviewed sources and a small evaluation set.

### 12. Learner-controlled local and synced data

**Learner experience.** Local-first remains the default. The learner can see where data lives, export it, delete it, back it up, and later decide whether to sync across devices.

**UI.** Keep data controls in **Your workspace**: local data location, export, delete, backup status, and eventually an explicit Sync setup panel. Clearly distinguish local notes/files from canonical learner database data.

**Build.** Continue using app-data directories, encrypted provider keys, local SQLite, and Markdown notes. Before sync, define identity, encryption, conflict behavior, deletion propagation, backup/restore, schema migration, and multi-device ownership. Never add a cloud copy as an invisible side effect.

**First useful release.** Reliable local export/delete plus an automated backup archive option. Sync is a later project.

### 13. Skill and curriculum SDK

**Learner experience.** Eventually, learners can install trusted subject packs or skills and see exactly what those extensions can access. They should never have to guess whether an extension reads their whole vault or calls a paid model.

**UI.** Add an Extensions view only when there are stable internal contracts. Every extension card lists publisher, version, permissions, data access, model usage, local/network behavior, and evaluation status.

**Build.** Publish schemas and a permissioned manifest after internal skills/packs are stable. Sandbox untrusted code, require explicit capability grants, version contracts, and retain revocation/disable paths. Do not run arbitrary third-party code inside the Electron renderer.

**First useful release.** None externally. Validate the internal registry with first-party domain packs and learning skills.

### 14. Hosted edition

**Learner experience.** A hosted edition eventually adds account login, device sync, sharing, billing, and managed model access while preserving a trustworthy local-mode story.

**UI.** Account and sync affordances are separate from the learning workspace. Users see which data is local, synced, shared, or managed by a school/organization.

**Build.** Introduce authenticated ownership, production authorization for every learner/material/note route, encrypted storage, auditability, rate limits, deletion/export controls, billing boundary, and deployment observability. Do not expose the current development identity header to a public service.

**First useful release.** A private hosted pilot with authentication and explicit sync for a small test group, after local export/import and conflict handling are proven.

## Engineering handoff detail

This section is the implementation contract for the feature descriptions above. A coding agent should reuse the current FastAPI, React, SQLite/PostgreSQL, workflow-job, `LearnerStateService`, material, and Electron infrastructure wherever applicable. Do not add a second learner-state store or bypass the existing evidence-admission boundary.

### Shared conventions for every feature

- **Ownership:** Resolve learner ownership server-side. Local desktop may use `local`; hosted routes must require authenticated ownership.
- **Durability:** A user action that starts model work creates an idempotent persisted job. The client polls or subscribes to job status and can safely resume after refresh.
- **Revisions:** Mutable records expose an integer revision. Writes carry `expectedRevision`; conflicts return the newest revision and a clear repair path.
- **UI states:** Every panel needs loading, empty, working, success, error, retry, and offline/local-service-unavailable states. Never discard a chat draft, note draft, or answer due to a failed request.
- **Telemetry:** Record action IDs, policy version, provider/model metadata, latency, cancellation, failure category, and outcome. Do not record raw learner responses or whole notes in broad telemetry.
- **Accessibility:** Keyboard-accessible controls, semantic headings, visible focus, descriptive labels, screen-reader status updates, minimum pane widths, and reduced-motion support are required.
- **Tests:** Add unit tests for service invariants, API tests for authorization/revisions/idempotency, and one browser test for the primary happy path plus one recovery/error path.

### Adaptive planner and next-action recommendations

**Frontend.** Add `NextActionCards` below a completed Learn response and a `NextStepCard` in Progress/Review. Cards render `learn`, `ask`, `quiz`, or `review`, with icon, label, rationale, concept chips, and effort band. Selecting Learn creates/resumes a journey; Ask inserts a draft into the composer without sending it; Quiz opens/focuses a Quiz workspace tab with preselected concept IDs; Review opens the active review activity. “Show other paths” opens a compact list, not a modal dashboard.

**Backend.** Add `next_action_recommendations` with `id`, `learner_id`, `session_id`, `origin_event_id`, `kind`, `target_concept_ids`, `payload`, `rationale`, `rank`, `policy_version`, `status`, and timestamps. Create `RecommendationService.recommend(learner, context)` and `POST /v1/sessions/{id}/recommendations`; return a persisted recommendation set. Candidate sources are active journey route, direct graph neighbors, unresolved prerequisites, due review records, latest evaluated attempts, and material coverage. Begin with deterministic scoring: goal relevance + prerequisite readiness + review urgency + novelty, with explicit hard exclusions for unavailable material or exhausted quiz context.

**Acceptance.** A neural-networks lesson produces exactly 2–4 useful cards, including backpropagation Learn when it is an available neighbor, one Ask draft, and one quiz opportunity. Selecting a card has no hidden model call until the selected flow begins. Dismissal and completion are persisted for later evaluation.

### Evidence-driven review

**Frontend.** Implement `ReviewWorkspace`, `ReviewQueueList`, `ReviewActivityCard`, and `ReviewReasonSheet`. The tab defaults to the first due activity, supports “teach me first,” pause, and close, and makes completion feedback immediate. Future reviews remain visible but secondary.

**Backend.** Extend review records or create `review_activities` linked to schedules with `activity_kind`, `prompt_snapshot`, `rubric_snapshot`, `originating_evidence_id`, `attempt_id`, `status`, and `policy_version`. `POST /v1/reviews/{id}/start` returns a durable activity; answer evaluation flows through the existing assessment/evidence contracts. Avoid creating an activity merely when a reminder appears.

**Acceptance.** A due independent-success review creates a retrieval prompt, stores an attempt, admits only authorized evaluation evidence, marks the prior schedule complete, and creates the next schedule. An assisted or abandoned review does not incorrectly upgrade state.

### Explainable concept state

**Frontend.** Implement `ConceptDetailPanel` with state label, plain-language explanation, evidence timeline, misconception hypotheses, due-review status, related notes, and actions. State labels must map directly from server values; no locally calculated “mastery percentage.” Challenge/reset actions require confirmation and show the impact before execution.

**Backend.** Add `GET /v1/learners/{id}/concepts/{conceptId}/explanation` that joins canonical state, active evidence, schedules, and linked objects into a read projection. Add explicit evidence challenge/invalidation endpoints with reason, revision, and audit event. Recompute via `LearnerStateService`; no direct SQL update from the route.

**Acceptance.** A learner can inspect why a concept is developing, follow evidence to the originating quiz/lesson, challenge an incorrect evaluation, and see the projection update after recomputation.

### Assessment quality pipeline

**Frontend.** Keep assessment rendering shared between inline Learn and Quiz tabs through `AssessmentCard`, `HintPanel`, `EvaluationFeedback`, and `ChallengeAction`. The Quiz tab owns session navigation; it must not duplicate question/feedback logic. Present uncertainty and challenges clearly.

**Backend.** Persist item blueprint, author output, checker output, approval status, rubric version, source manifest ID, exposure counters, and evaluation output separately. Use jobs: `author_item`, `check_item`, `evaluate_attempt`. The checker must receive the prompt, objective, allowed sources, and rubric requirements but not the answer key. Add deterministic guards for duplicate normalized text, unsupported targets, banned answer leakage patterns, and insufficient distractor differences.

**Acceptance.** An unapproved item cannot reach the learner; an evaluator cannot mutate state directly; a challenged item can be withdrawn and supersede affected evidence through the existing state flow.

### Linked notes and workspace panel

**Frontend.** Build a `WorkspacePanel` controlled by local workspace state: `tabs`, `activeTabId`, `splitRatio`, `collapsed`, and per-tab view state. Start with Notes, Quiz, and Sources types. Use a resizable accessible divider and persist layout only after hydration. Implement `NotesTab`, `NoteEditor`, `NoteSearch`, `NoteLinkPicker`, and `ContextReceipt`. Closing a dirty note prompts save/discard/cancel.

**Backend.** Create a `NoteVaultService` separate from legacy anchored-note records. Markdown files live in a local notes directory; SQLite stores a rebuildable index. APIs: `POST /v1/notes`, `GET /v1/notes`, `GET/PATCH/DELETE /v1/notes/{id}`, `GET /v1/notes/search`, `GET /v1/notes/{id}/backlinks`, and `POST /v1/notes/reindex`. Use stable IDs in front matter and optimistic revision checks. Preserve unknown front-matter keys and Markdown bytes as far as the parser safely can.

**Acceptance.** A note survives restart and index rebuild, a split ratio restores, a note can link to a concept and quiz attempt, and closing the tab never loses a dirty draft.

### Materials-grounded learning

**Frontend.** Add `MaterialPicker` in the composer and `SourcesTab` in the workspace. The picker shows selected material count and can remove selections before send. Responses and assessment items use clickable source chips that focus the exact passage in Sources.

**Backend.** Reuse `MaterialService`, material versions, blocks, source spans, and context manifests. Add a `ContextSelectionService` that resolves only session-selected materials, runs bounded retrieval, records passage IDs, and returns support status. Every provider prompt receives a context manifest ID, not arbitrary raw file access.

**Acceptance.** A learner selects a text/PDF material, asks a question, sees the exact supporting passage, and receives an explicit limited-support response when retrieval has no adequate evidence.

### Timeline and review inbox

**Frontend.** Build `LearningTimeline` using cursor pagination and filter chips. Each entry has type, readable sentence, timestamp, and deep link into its original tab/context. The empty state explains how events appear rather than showing a blank chart.

**Backend.** Create a `learning_activity_projection` from existing typed records; it references event IDs rather than copying private payloads. Endpoint: `GET /v1/learners/{id}/timeline?cursor=&types=`. New event writers append a narrow display-safe activity record in the same transaction when feasible.

**Acceptance.** Lessons, quiz outcomes, note creation, evidence admission, and review scheduling appear in correct order and open the appropriate context without exposing another learner’s data.

### Exam and practice modes

**Frontend.** Extend the Quiz setup with `PracticeModePicker` and only show fields meaningful for the selected mode. Timed mode displays a clear clock and pause policy; topic drill shows selected concepts; result view offers repair note and return-to-Learn links.

**Backend.** Add `mode` and typed `mode_config` to quiz/practice records. Validate configurations server-side. Reuse QuizService for author/check/evaluate where semantics match. Create separate adapters for future oral/coding modes; never force them into a multiple-choice schema.

**Acceptance.** Topic drill and timed short quiz resume correctly after refresh and preserve answers, timer state, and evidence behavior.

### Typed learning skills

**Frontend.** No generic “run skill” console is needed. Each stable skill appears through product actions with a preview of context and expected result.

**Backend.** Introduce `SkillDefinition` with name, input Pydantic model, output model, policy function, provider requirements, source requirements, and telemetry name. Create an internal registry and migrate existing journey, quiz, explanation, note-draft, and recommendation calls incrementally. Keep tool invocation behind application services, not arbitrary HTTP endpoints.

**Acceptance.** Registering a skill with invalid schema or missing policy fails at startup/test time. A skill cannot receive full learner notes/materials unless its contract explicitly allows selected context.

### Evaluation and policy experiments

**Frontend.** Add lightweight useful/not-useful feedback and challenge controls only where a learner can understand the action. Avoid exposing hidden experimental branches.

**Backend.** Store fixtures under version control, add an evaluation runner that produces structured JSON, and gate policy changes through versioned configurations. Include tests for question correctness/ambiguity, evaluator agreement cases, source-support labels, recommendation determinism, and false mastery prevention.

**Acceptance.** CI can run the fixture suite without provider secrets using deterministic fixtures; a policy version is present on every recommendation, evaluation, and evidence admission.

### Domain packs

**Frontend.** Add a small `PackPicker` when starting a new topic. The active pack appears as a chip in chat and scope settings; changing it explains whether a new session is required.

**Backend.** Pack manifest contains ID, version, title, graph seed, source manifest, supported skills, assessment templates, and evaluation fixtures. Validate manifests at load time and pin each session to the selected pack/version.

**Acceptance.** A session created under pack version A remains reproducible after pack B exists; a pack cannot silently access materials outside its declared policy.

### Local data, sync, extensions, and hosting

**Local data frontend/backend.** Keep export/delete controls working for notes, materials, learner state, and workspace layout. Add backup archive creation before sync. Exports must contain a documented schema/version and never secrets.

**Sync.** Do not implement until conflict policy is approved. Required design artifacts: identity model, encryption model, file/database conflict behavior, deleted-record behavior, offline queue, recovery/restore, and threat model. Build local import/export compatibility tests first.

**Extensions.** Do not expose public extensions until internal skills/packs are stable. An extension manifest must declare permissions and is executed outside the renderer with constrained APIs. Add enable/disable and revocation before marketplace work.

**Hosted edition.** Replace development identity with authenticated server-derived ownership before any multi-user deployment. Every route, material span, note, context manifest, job, and export checks ownership. Add operational logging, rate limits, retention/deletion, and billing only after core learning workflows are proven locally.
