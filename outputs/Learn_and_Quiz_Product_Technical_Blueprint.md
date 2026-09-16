# Learn and Quiz: product and technical blueprint

Version 1.0 · 15 September 2026 · Design proposal for review; no implementation authorized by this document.

## Decisions and scope

Ask and Learn occupy the same chat interface. A composer mode selector changes behavior without discarding conversation, attached material, or learning position. Existing Quick / Guided / Deep controls remain independent of mode. Quiz has a separate navigation destination, while short checks can appear inline in Learn. Review and Library share the underlying records but are outside this implementation scope except for integration boundaries.

The defining outcome is that a learner can study a concept, demonstrate reasoning in a different situation, receive appropriate repair, and return to the same journey later. Completing content is not proof of understanding. Question quality takes priority over question volume.

Sections 1–2 specify experience before technology. Subsequent sections derive capabilities and architecture from that experience. Defaults such as diagnostic length and quiz length below are proposed product policies, not scientifically calibrated constants.

## 1. Learn UX specification

### Entry and layout

The existing chat is the entry point. Its composer contains Ask / Learn, the current teaching gear, attachments, and the message field. Selecting Learn changes the placeholder to “What would you like to understand or be able to do?” Switching modes never creates a separate dashboard or automatically starts a new conversation.

Desktop: existing navigation on the left; conversation in the center; existing contextual exploration panel available on demand. A compact, collapsible journey summary appears within the conversation and can reopen from the session header. Do not introduce another permanent panel. On mobile, contextual exploration opens as a sheet with an explicit return action; the composer remains reachable without obscuring the active question.

New sessions show a topic prompt and access to attached material. Existing sessions show the last interaction and a brief resume card only if useful: current concept, unresolved question, and next action. Unknown learner state is shown as unknown, never silently treated as a beginner or expert.

### Starting a journey

1. Learner states an outcome, topic, or request about attached material.
2. Tutor clarifies only ambiguities that would change the lesson. Goal and available time are optional editable context, not mandatory onboarding fields.
3. Tutor uses existing evidence or offers a short starting-point check. Default budget: up to three probes before proposing a route; offer more diagnosis only when a concrete uncertainty justifies it. A learner can skip and start with assumptions labeled.
4. Tutor proposes a short route with roughly three to five meaningful milestones, starting from relevant prerequisites. “Start” accepts the route; “Adjust” edits the goal or scope. A narrow follow-up within an existing journey needs no new approval screen.
5. The first lesson step begins. The route is editable and advisory, not a gate preventing questions.

### Teaching loop and content

Each meaningful step establishes why the idea matters, explains or elicits the reasoning, connects it to prior concepts, and offers a response opportunity when informative. The tutor does not quiz after every sentence or force a Socratic exchange when the learner explicitly wants an explanation.

Quick emphasizes a small answer and optional check. Guided uses manageable steps and worked examples. Deep adds mechanisms, derivations, assumptions, and boundary cases. These settings do not establish learner ability; a knowledgeable learner can choose Quick and a novice can choose Deep.

Content is presented as readable message blocks:

| Content | Experience |
|---|---|
| Explanation | Short paragraphs with an explicit central idea; longer material unfolds by meaningful step |
| Worked example | Problem, reasoning steps, conclusion, and assumptions; reveal steps on request where useful |
| Question | Inline assessment card, visually distinct from a preference question |
| Equation | Rendered mathematics with symbol definitions and surrounding explanation |
| Code | Highlighted code, language label, copy action, and explanation; execution is not implied |
| Diagram | Labeled relationships with text equivalent and optional enlargement |
| Source | Citation opens the relevant passage and provenance, not just a document title |
| Route | Small ordered list; optional dependency view only when it clarifies relationships |

The learner can ask freely, select text for a contextual question, request Why / Example / Simpler, save a note, change gear, pause, or switch to Ask. These actions preserve the route. A selected passage anchors any exploration and its return position.

### Adaptation and recovery

“I don’t understand” triggers a focused clarification: which step is uncertain, or a short discriminating probe. Repair can change representation, introduce a prerequisite, contrast a misconception with the correct mechanism, or walk through a smaller example. Repeating the same paragraph with synonyms is not adequate repair.

One wrong answer is a hypothesis, not a diagnosis. Distinguish a slip, missing prerequisite, ambiguous item, and systematic misconception through follow-up evidence. Do not invent stable learning-style categories or infer mastery from engagement.

“Go deeper” expands mechanism, assumptions, derivation, or application. If this leaves the original scope, offer a contextual branch and preserve the return point. Switching to Ask suspends the guided flow; switching back offers continuation without replaying onboarding.

### Progress, stopping, and Quiz connection

Display coverage separately from evidence: “3 of 5 steps covered” versus “Independently demonstrated on 2 checks.” Concept labels use unknown / developing / demonstrated, with supporting evidence and recency available. Avoid precise mastery percentages until calibrated.

A lesson ending offers Continue, Quiz this concept, or Finish for now. Quiz this concept carries objective, concept IDs, materials, prior exposure, and return position automatically. An inline diagnostic and a standalone quiz use the same assessment behavior.

Ending or closing the app preserves position and pending questions. A restart resumes the committed state. A stopped generation is labeled incomplete and does not advance the route. Missing sources produce a qualified explanation or a request for material, not fabricated citations. Model failure preserves the request and offers retry without duplicate messages.

### Accessibility

Keyboard-operable controls, visible focus, readable contrast, non-color-only feedback, text equivalents for diagrams, and accessible math descriptions are required. Streaming must not repeatedly announce every token to screen readers. No default timer; diagrams and animations must respect reduced motion.

## 2. Quiz UX specification

### Landing and setup

Quiz landing prioritizes Resume unfinished quiz, Quiz recent learning, and Choose concepts or materials. The default is a short five-question formative session, adjustable before starting. Show purpose, approximate duration, and targeted concepts; never advertise precise duration as guaranteed.

Entering from Learn preselects scope. Difficulty defaults to Adaptive, with optional Foundational / Standard / Stretch selection. These are reasoning-demand labels, not calibrated ability scores. The learner can exclude concepts and choose a shorter session. Lack of evidence starts conservatively and adapts after responses.

### Question quality and generation from the learner's perspective

Questions are prepared and checked before presentation. Preparation shows a simple status and allows cancellation. If only three valid items are available, offer three; never pad a five-item quiz with unverified material.

Every question must test an explicit reasoning objective. A generation blueprint varies context, representation, assumptions, and reasoning demand. Merely changing numbers or names does not qualify as conceptual novelty. Authoring requires the intended answer, a scoring rubric, misconception hypotheses, source basis, and explanations of why distractors are wrong.

Illustrative probability set: predict the effect of changing a conditioning population; diagnose an incorrect independence assumption; explain why a proposed conclusion does not follow; transfer reasoning to a different domain. Difficulty comes from the reasoning required, not obscure wording or irrelevant reading load.

### Presentation and supported formats

One question at a time. Keep problem, response, and subsequent feedback together. Progress reads “Question 2 of 5”; explain any learner-approved extension. A fixed-length adaptive session can choose later items from earlier answers without silently increasing its length.

MVP response formats: single-select, multiple-select with explicit selection instructions, and short written explanation. They support prediction, error diagnosis, comparison, boundary cases, and transfer. Later: numeric responses with units/tolerance, ordering, diagram manipulation, spoken answers, and sandboxed code exercises.

Always offer I don’t know and Flag question. Skip, unanswered, and I don’t know are separate records. Optional confidence is self-report and cannot outweigh actual evidence. Draft responses survive navigation/reload where storage is available; submission status is visible.

### Hints and feedback

Hints progress from a conceptual cue to a targeted nudge to a worked step. Requesting a hint records assistance. Revealing a solution ends the independent attempt; subsequent practice is assisted or a new item, never retroactively independent. Do not deduct points for inaccessible UI or shame help-seeking.

Default formative feedback is immediate. It identifies what is correct, what reasoning is missing, the relevant assumption, and a useful next action. Feedback remains attached to the original response. A retry creates another attempt and preserves the first.

Written answers are evaluated against criteria, including acceptable alternative reasoning. If grading is uncertain, show “Needs clarification” and ask a targeted follow-up or exclude it from scored evidence. Learners can challenge an item or evaluation. Confirmed errors invalidate/supersede affected evidence and trigger state recomputation; they do not leave a permanent false penalty.

### Scoring, gaps, and adaptation

For the MVP, each evaluable item has a normalized rubric score from 0 to 1. Multi-select uses exact-set correctness initially, with diagnostic feedback for individual selections; explain that policy. Short responses use explicit criterion weights summing to 1. Session score is 100 × sum of normalized scores / number of evaluable answered items, with attempted/total, skips, I-don’t-know responses, and assisted responses shown alongside it. I don’t know counts as an answered zero-score item, while preserving its distinct evidence category. Invalid or unresolved grading is excluded and the denominator is visible. A skipped quiz cannot appear fully completed.

This is a practice score, not mastery. First-attempt scores and assisted/retry performance are reported separately. Adaptive quiz scores are not comparable between learners or sessions of different composition. No rankings in MVP.

A misconception is proposed only with evidence, and is labeled tentative until corroborated. Correct guesses, assisted success, and independent transfer carry different evidence conditions. Learning-state admission remains conservative and versioned; no automatic prerequisite mastery propagation.

After a miss, select a targeted discriminating question or offer repair; after clear independent success, vary context or increase reasoning demand. Repeated poor performance offers a return to Learn instead of escalating frustration. The session summary offers a specific repair link and a fresh follow-up quiz; it does not merely say “study harder.”

## 3. Required capabilities

Types: LLM = bounded model task; Logic = deterministic application policy; Retrieval = scoped source selection. Hybrid explicitly combines these, rather than treating every row as an independent agent.

### Learn capabilities

| Capability | Function and necessity | Inputs | Outputs | Owner/type |
|---|---|---|---|---|
| Goal clarification | Resolve ambiguity that changes instruction | Message, session goal, material scope | Goal or focused clarification | LLM + Logic |
| Content decomposition | Build a bounded teachable route | Goal, graph, sources | Ordered concepts and prerequisite references | LLM proposal + graph validation |
| Starting-point diagnosis | Avoid unsupported ability assumptions | Existing evidence, objective, probe budget | Diagnostic request or justified starting point | Logic + shared Quiz |
| Teaching | Choose a pedagogical next step | Goal, position, evidence, gear | Typed teaching plan | Existing policy + bounded LLM proposal |
| Explanation | Communicate a supported concept | Plan, source passages, assumptions | Structured content blocks | LLM + Retrieval |
| Socratic questioning | Elicit reasoning before revealing it | Concept, reachable step, assistance history | Question request with rubric | LLM + shared Quiz |
| Example and transfer | Connect abstraction to application | Concept, known contexts, prior examples | Worked example or novel assessment request | LLM + validation |
| Representation selection | Choose useful math, text, code, or diagram | Concept, request, accessibility needs | Allowed representation sequence | Logic + LLM |
| Misconception repair | Address the specific mistaken model | Accepted evidence, tentative hypothesis | Contrast, bridge, and follow-up check | LLM + Logic |
| Difficulty adaptation | Adjust step size and prerequisites | Evidence, goal, recent assistance | Revised plan, not an arbitrary token count | Logic, later calibrated estimator |
| Personalization | Respect explicit preferences and history | Gear, goals, prior evidence, saved preferences | Compact teaching profile | Logic; LLM wording |
| Branch/resume | Preserve continuity through exploration | Anchor, route position, branch history | Saved branch and return position | Logic |
| Grounding | Support claims and expose missing support | Source versions, scope, query | Relevant spans and support status | Retrieval + validation |
| Progress summary | Separate exposure from demonstration | Activity and accepted evidence | Coverage and evidence summary | Logic + optional LLM wording |

### Quiz capabilities

| Capability | Function and necessity | Inputs | Outputs | Owner/type |
|---|---|---|---|---|
| Blueprint construction | Ensure conceptual coverage | Objectives, concepts, sources, session length | Item specifications and coverage budget | Logic + LLM |
| Question authoring | Produce meaningful reasoning tasks | Blueprint, source spans, excluded prior items | Candidate item, private key/rubric, hints | LLM |
| Correctness checking | Catch wrong or ambiguous items | Candidate and sources; initial solve without author key | Independent solution and quality verdict | LLM + deterministic checks |
| Novelty checking | Reject template-only variation | Candidate, learner exposure, item family | Similarity flags and accept/reject decision | Logic + semantic comparison |
| Difficulty assignment | Label reasoning demand honestly | Blueprint, steps, prerequisites | Provisional difficulty dimensions | Logic + LLM; later empirical calibration |
| Hint construction | Scaffold without premature revelation | Item, rubric, current hint level | Staged hints | LLM authoring + Logic release |
| Presentation | Preserve exact question seen | Approved item version, display permutation | Public question instance | Logic |
| Answer validation | Handle empty, malformed, or unsupported input | Public response schema, response | Valid attempt or correction request | Logic |
| Evaluation | Assess correctness and reasoning | Frozen response, private rubric, assistance | Criterion scores, uncertainty, rationale | Logic for selection; LLM for prose |
| Feedback | Explain the actual error constructively | Evaluation, response, authorized solution | Learner feedback and repair suggestion | LLM + result consistency checks |
| Gap detection | Avoid overdiagnosis from one answer | Evaluation and earlier accepted evidence | Evidence-linked hypothesis | Logic + bounded LLM |
| Adaptive selection | Choose informative next question | Coverage remaining, evidence, exposure | Next blueprint or repair recommendation | Logic |
| Score aggregation | Produce reproducible summaries | Evaluable attempts, scoring policy | Score, denominator, assistance breakdown | Logic |
| Evidence admission | Protect canonical learner state | Evaluation provenance, reliability, concept/version | Accepted/rejected evidence and new state version | Existing LearnerStateService |
| Challenge handling | Correct bad questions and grading | Challenge, item, evaluation, sources | Review result, invalidation/supersession | Logic + reviewer/model assistance |

## 4. System architecture and agent boundaries

Use one modular application backend with two workflows and shared services. The Learn orchestrator coordinates teaching; the Quiz engine coordinates assessment. Neither owns a separate learner-memory store.

The tutor is a bounded action-selection workflow. Allowed actions include clarify_goal, explain_step, request_check, repair, branch, and summarize. Existing deterministic prerequisite policy constrains model proposals. Models generate structured proposals; application code validates permissions, budgets, IDs, and transitions before execution.

Quiz author and checker are separate invocations with different inputs. The checker first solves without seeing the author's key, then compares. Separation reduces a particular source of anchoring but is not proof of independence or correctness. Model diversity is an experiment, not an automatic requirement.

A skill package contains an ID/version, instructions, input/output schema references, allowed tools, applicability rules, resource budgets, and evaluation fixtures. Markdown contains pedagogy; Python enforces contracts. Approved packages ship with the application. User-supplied arbitrary executable plugins are outside MVP.

Tools are narrow services such as retrieve_context, request_item, read_learner_state, and save_position. No model receives raw SQL, unrestricted filesystem access, or a tool that awards mastery. A generation retry budget defaults to two repair attempts, after which the system returns insufficient-quality status. Budgets are configurable and logged.

Learn lifecycle: clarifying → diagnosing → proposing → teaching ↔ awaiting_response → consolidating → paused/completed. Ask pauses the guided flow. Side branches retain a return state. A completed route is not a mastered topic.

Quiz lifecycle: preparing → ready → in_progress → awaiting_evaluation → feedback → next_item/completed. Explicit failed, paused, cancelled, and contested states preserve data. No process stays alive just to wait for learner input.

## 5. Frontend architecture

### Routes and components

Proposed routes, to be adapted to the existing workspace router: `/chat` for entry; `/chat/:sessionId` for the shared Ask/Learn conversation; `/quiz` for landing; `/quiz/:quizId` for a session; `/quiz/:quizId/results` for results. There is deliberately no separate `/learn` destination. Review and Library remain integration links.

Extend existing `learn-chat.tsx`, `chat-composer.tsx`, `rich-content.tsx`, `lesson-reader.tsx`, and contextual workspace behavior. Names are reuse candidates, not claims that these files already implement the specification.

New/shared components: ModeSelector, JourneySummary, AssessmentCard, ResponseInput, HintPanel, EvaluationFeedback, EvidenceSummary, QuizSetup, QuizProgress, QuizResults, SourcePopover, and ChallengeAction. AssessmentCard and feedback render identically inline and in Quiz; surrounding navigation differs.

### State and streaming

Server owns session mode, route position, items, submissions, evaluations, and learner state. Frontend owns unsubmitted text, open panels, selection, and presentation preferences. Use a server-state cache such as TanStack Query for fetch/invalidation; React state/reducers for local interaction. Do not add a second global state framework without a demonstrated need.

Persist mode at the session boundary and snapshot mode/gear on each action. Switching during generation cancels the active run or queues the next action; an old response cannot be attached as if generated under the new mode. Use run IDs and session revisions.

Reuse the existing event-stream pattern. Events carry runId, eventId, sequence, status, and public payload. Stream explanation text into an explicitly provisional message; finalize its validated artifact before marking the step complete. Questions are emitted atomically after validation, never streamed with partial options or answer-key fragments. Feedback waits for evaluation finalization.

Reconnect uses an event cursor and deduplicates events, falling back to a committed snapshot. Submitting twice uses the same idempotency key. Show preparing, awaiting input, evaluating, needs clarification, failed, and reconnecting states. Do not optimistically update mastery.

## 6. Backend architecture

### Existing foundation and proposed additions

Source inspection on 15 September found the following; this was a static inspection, not a runtime validation:

| Existing area | Reuse/extension |
|---|---|
| `learning_kernel.py`, `learning_policy.py`, `policy_models.py` | Extend typed actions into guided lifecycle; preserve prerequisite safeguards |
| `session_models.py`, storage and action events | Add explicit Ask/Learn mode, route checkpoint, pending response and revision checks |
| `state_service.py`, state contract | Preserve sole-writer authority and evidence supersession |
| `model_provider.py` | Extend provider abstraction with public structured generation interfaces rather than relying on a private completion helper |
| `material_service.py`, `context_service.py`, material routes/worker | Reuse material versions, scoped retrieval and manifests; validate quality before broader RAG |
| Material request models | Some practice-related shapes exist; they do not establish a complete quiz pipeline |
| Frontend package | React/TypeScript and Next/vinext tooling exist; retain provisionally rather than forcing a framework migration |

The repository's README descriptions can lag implementation: model adapters and material retrieval exist, although comprehensive claim verification and calibrated mastery remain unestablished.

### API contracts

Retain `/v1/sessions`, session actions, runs, and events. Extend action requests compatibly with mode, expected session revision, and optional assessment response reference. All mutation requests use learner-scoped idempotency keys. Hosted identity is derived server-side, never trusted from a learnerId body field.

Proposed assessment endpoints:

| Endpoint | Input → result |
|---|---|
| `POST /v1/quizzes` | Concepts, objective, material versions, length, origin session → quizId/jobId |
| `GET /v1/quizzes/{id}` | Owned ID → public state, coverage, current presentation |
| `POST /v1/quizzes/{id}/attempts` | Presentation ID, response or don't-know, expected revision → attemptId/evaluation status |
| `POST /v1/presentations/{id}/hints` | Requested next hint level → released hint and assistance event |
| `GET /v1/attempts/{id}/evaluation` | Owned attempt → finalized feedback or pending/uncertain status |
| `GET /v1/quizzes/{id}/results` | Owned quiz → score breakdown, concept evidence, repair links |
| `POST /v1/attempts/{id}/challenges` | Reason → challenge record and review status |
| `POST /v1/quizzes/{id}/pause` | Expected revision → durable checkpoint |

Inline checks create assessment sessions with origin=learn_inline through the same service. Public item DTOs never include answer keys, rubrics, unreleased hints, or author/checker conversation. Authorization applies to every referenced ID, not just the parent quiz.

### Context, retrieval, jobs, and caching

Assemble context from the current message, structured route, canonical learner evidence, recent turns, branch summaries, relevant material spans, and prior item exposure. Summaries support navigation but cannot replace evidence or manufacture new facts. Pin graph, material, skill, and evaluator versions in a context manifest.

Prefer learner-selected materials for scoped instruction. Retrieval must preserve passage IDs and extraction status, exclude private answer keys from ordinary learner-facing context, and label incomplete support. Retrieved text is data, not tool instructions. Begin with the existing retrieval boundary; add embeddings/hybrid retrieval only when a retrieval benchmark shows a benefit.

Generation and evaluation jobs must be durable: persisted state, attempt count, lease/heartbeat, timeout, retry policy, and idempotent finalization. Extend the existing worker pattern. SQLite local mode can use one worker; hosted PostgreSQL workers need transactional claims and expired-lease recovery. Do not rely solely on an in-process post-response callback for critical work. FastAPI documents background-task usage and heavier-work alternatives: [official documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/).

Cache approved items by objective, concept/material versions, blueprint, language, difficulty profile, and generator/checker version. Selection still checks exposure and item family. Private material caches remain owner-scoped. Cache shared source processing only with appropriate ownership. Do not share learner conversations or personalized feedback across users.

### Observability and evaluation

Trace each action through context, plan, model calls, item validation, presentation, evaluation, evidence admission, and next-step selection. Record latency, tokens/cost, versions, retries, rejection reasons, and job outcome. Avoid logging raw learner responses by default; use controlled diagnostic sampling and retention settings.

Offline fixtures need expert-reviewed questions, flawed items, alternative valid answers, misconception examples, and adversarial text. Measure factual correctness, ambiguity, answer leakage, novelty, rubric agreement, false mastery admission, and adaptation behavior. Production metrics include completion/abandonment, hint use, challenges upheld, latency, and cost per completed activity. Learning-effect claims require delayed/transfer assessments; immediate quiz scores alone do not establish effectiveness.

## 7. Database and data model

Use additive migrations. Logical entities below can extend existing records instead of creating duplicate tables. All learner-owned references enforce matching ownership; public curriculum items are explicitly distinguished. Store timestamps in UTC and display in learner timezone.

| Entity | Principal fields and relationships |
|---|---|
| LearningSession (extend) | owner, mode, goal, gear, graphVersion, lifecycle, currentStep, pendingPresentationId, revision |
| LearningRoute / Step | session, version, concept IDs, objective, order, completion activity; no mastery field |
| TeachingAction / Plan (reuse) | session, context manifest, policy/skill versions, chosen action, status |
| ContextManifest (extend) | graph/material versions, evidence IDs/state version, passages, model/skill versions |
| QuizSession | owner, origin session/anchor, objective, length, coverage plan, adaptive policy, revision, lifecycle |
| ItemBlueprint | concept IDs, reasoning target, difficulty dimensions, misconceptions, source constraints |
| ItemVersion | immutable public stem/options, blueprint, item family, source refs, quality status, author/checker versions |
| PrivateItemSolution | itemVersion, correct option IDs, rubric criteria/weights, acceptable alternatives, staged hints; separate API projection |
| ItemQualityReview | itemVersion, independent solution reference, checks, verdict, rejection reasons |
| Presentation | owner, quiz, itemVersion, stable option-ID permutation, shownAt, exposure context |
| Attempt | presentation, immutable response, outcome type, first/retry relation, submittedAt, idempotency key |
| AssistanceEvent | presentation/attempt, hint or solution exposure, timestamp; available to evaluator |
| Evaluation | attempt, rubric/evaluator versions, criterion scores, reliability, uncertainty, status, supersession |
| Evidence (reuse) | evaluation/source event, concept and curriculum version, independence conditions, admission result |
| LearnerConceptState (reuse) | accepted evidence refs, version, conservative status/confidence; sole writer is state service |
| Misconception / ReviewSchedule (reuse) | evidence-linked hypotheses and review history |
| Challenge | owner, item/evaluation, reason, decision, correction references |
| Job / Outbox | owner, task type, payload refs, lease, retries, dedupe key, committed event sequence |

Constraints: unique owner+idempotency keys; immutable item version used by every attempt; foreign keys to exact revisions; one committed evaluation result per evaluation version; optimistic session revisions; reject cross-owner references. Do not keep a database transaction open across a model call. Final evidence admission and canonical state/audit updates occur atomically; outbox events publish after commit. Expired or superseded evaluations cannot overwrite newer state.

Local SQLite stores the same logical records; hosted PostgreSQL supports concurrent accounts. Keep SQLAlchemy/Alembic as canonical learner-data ownership even though the frontend starter includes Drizzle. Hosted authentication remains a release prerequisite: the current development header is not authentication.

## 8. Concrete data flows

### Learn turn

1. Frontend submits sessionId, message, mode=learn, gear, anchor/material references, expected revision, and idempotency key.
2. API resolves owner, validates references, deduplicates, saves an action/run, and returns runId.
3. Context builder reads pinned graph/material versions, accepted concept evidence, recent conversation and route. It saves a manifest containing the IDs and versions used.
4. Policy chooses allowed strategy and relevant skills. Model receives only that bounded context and tool schemas; its proposal cannot bypass graph or budget constraints.
5. Retrieval returns scoped passage references and support status. Generator returns typed content blocks or an assessment request. Validator checks IDs, allowed representations, and provenance; unsupported content is qualified or rejected.
6. Public action events update the conversation. Validated final blocks and checkpoint commit against the expected revision. A concurrent change triggers reconciliation rather than silently advancing the wrong route.
7. Reading/explanation records activity only. If a check is requested, create a shared assessment presentation and wait for the response.
8. Accepted assessment evidence updates canonical state through the flow below. The next Learn action uses that new state version; no mastery is inferred from prose alone.

### Quiz interaction

1. Frontend submits concept IDs, goal, material versions, chosen length/difficulty, origin session and return anchor.
2. Quiz engine reads canonical state and exposure history, then saves a coverage blueprint. It reuses a suitable approved item or creates a generation job.
3. Author receives objective, source spans, reasoning demand, and excluded item families. It returns candidate public content plus a private key, rubric, hints, and misconception mappings.
4. Checker independently solves, compares, validates ambiguity and conceptual novelty, and approves or rejects. Only approved item versions can be presented.
5. Presentation stores the exact option order. API sends presentationId, stem, allowed response schema, public options, and public source context; no solutions.
6. Frontend submits response/don't-know and idempotency key. Server freezes an attempt and records actual assistance exposure. Client assertions cannot erase hint use.
7. Evaluator reads the immutable item/rubric and response. It returns scores, rationale and uncertainty. Feedback is derived from that evaluation; uncertainty can block evidence admission.
8. Admission validates evaluator provenance, concept versions and evidence conditions, then commits evidence, canonical state and audit records. A job cannot call completion twice to double-count evidence.
9. Public feedback and summary reference the evaluation and new state version. Adaptive selection respects coverage, exposure and fixed session budget. Repair links restore the correct Learn anchor with the specific gap.

## 9. Shared infrastructure

Learn and Quiz share identity, sessions, concept graph versions, source ingestion/retrieval, context manifests, model adapters, skill registry, assessment renderer, question bank, attempt/evaluation services, evidence admission, review scheduling hooks, telemetry, and accessibility components.

They do not share one enormous prompt. Learn requests an assessment through a typed contract; Quiz returns evidence and a recommended next action. Both consult the same canonical state. UI coverage, chat summaries, and cached projections remain explicitly non-authoritative.

## 10. Recommended technology stack

Retain React/TypeScript, existing Next-compatible frontend tooling, Python/FastAPI, Pydantic, SQLAlchemy, Alembic, and current model-provider abstraction. Use SQLite for local operation and PostgreSQL for hosted deployment. Preserve rich-content rendering with existing Markdown/math support; allow only validated representations and no arbitrary generated HTML or executable code.

Add a small Python skill registry and explicit workflow transitions, rather than adopting Pi or a general multi-agent framework now. Add TanStack Query for server-state synchronization if accepted during implementation; its documented purpose fits fetch/cache/update responsibilities: [official overview](https://tanstack.com/query/v4/docs/framework/react/overview). Select and pin a compatible current version during implementation; the cited page describes the responsibility rather than prescribing a package version.

Use persisted jobs with a worker and HTTP events for progress. Defer Redis/Celery, a vector database, desktop shell selection, local model serving, and framework migration until measured requirements justify them. These are not prerequisites for the agreed Learn/Quiz experience. Local installation and hosted delivery should reuse the same learning services; neither full offline AI nor multi-device sync is implied.

## 11. MVP and later stages

| MVP | Later |
|---|---|
| Shared Ask/Learn chat; independent teaching gear | Additional teaching policies tested experimentally |
| Short diagnosis, editable route, pause/resume and existing exploration | Long curriculum planning and collaborative journeys |
| Source-scoped text, math, code display, simple accessible diagrams | Interactive simulations, handwriting, voice, code execution |
| Single/multi-select and short explanation assessments | Rich numeric/symbolic and manipulation formats |
| Blueprint, author/checker, stable item versions and private rubrics | Empirically calibrated item bank and expert authoring tools |
| Hints, don't-know, challenge records and conservative evidence | Automated challenge triage and richer learner models |
| Local persistent sessions and replayable runs | Signed desktop installers, hosted accounts/billing, sync |
| Review schedule integration using existing conservative rules | Calibrated forgetting and notification experiments |

For quality validation, use one bounded subject with reviewed materials and an expert-reviewed reference set. The architecture can accept other topics, but MVP validation does not establish reliable teaching in every domain.

## 12. Implementation order and acceptance gates

1. **Experience review:** walkthrough of starting Learn, switching to Ask, misunderstanding/repair, inline check, standalone Quiz, failed grading, and returning to Learn. Gate: all flows preserve context and make the next action clear. No implementation before design review.
2. **Contracts and fixtures:** freeze public/private assessment shapes, state transitions, skill manifests, and conceptual quality rubric. Gate: examples cover valid alternatives, misleading distractors, hint use and ambiguous questions.
3. **Shared durable records:** additive migrations, session mode/checkpoints, item/presentation/attempt/evaluation records, jobs and idempotency. Gate: restart, duplicate submission, stale revision and owner-isolation tests pass without corrupting existing data.
4. **Curated assessment vertical slice:** render reviewed questions, grade selection answers, provide hints/feedback and admit evidence. Gate: no private key in public payloads; shown order replays exactly; hints affect evidence; exposure cannot award mastery.
5. **Learn lifecycle:** mode selection, compact route, teaching/awaiting-response loop, contextual return and inline assessment. Gate: Ask/Learn switching and gear changes preserve the correct checkpoint and pending responses.
6. **Generated question pipeline:** blueprint, author, independent checking, novelty checks and rejection limits. Gate: expert review on a declared test set meets agreed quality thresholds; numerical restyling fails novelty fixtures; unverifiable items are withheld.
7. **Written-response evaluation and repair:** criterion grading, uncertainty handling, challenges and evidence supersession. Gate: valid alternative answers are accepted, ambiguous grading is withheld, and corrections recompute affected state.
8. **Adaptive quiz and polish:** selection policy, source inspection, results, review integration, accessibility and network recovery. Gate: coverage and length constraints hold; quiz repair restores the originating lesson; keyboard and screen-reader flows are usable.
9. **Measured pilot:** report item defects, grading disagreement, false-state updates, response times and cost per completed session. Choose quality and cost thresholds before the pilot; assess delayed transfer before making learning-effect claims.

These gates specify evidence required to advance, not estimated delivery dates. Open product choices for review are the visible Quiz label versus Practice, default short-session length, and initial validation subject. Proposed defaults are Quiz, five questions, and one source-bounded subject selected with the user. Deployment packaging and calibrated mastery remain separate decisions.

## Source and design provenance

Repository inspection: `backend/app/learning_kernel.py`, `policy_models.py`, `session_models.py`, `material_models.py`, `material_routes.py`, `material_service.py`, `material_worker.py`, `backend/STATE_CONTRACT.md`, migrations through `0005_material_context.py`, and frontend component/package listings.

Prior reference: [amosblomqvist/learn](https://github.com/amosblomqvist/learn), particularly its teaching protocol and structured quiz interactions. This blueprint adapts ideas, not source code. It deliberately bounds diagnosis, preserves uncertainty, and separates learner state from conversational claims.

External technical references support narrow implementation choices only. No claim is made that this design, an exact review interval, or its provisional difficulty labels have been empirically validated.
