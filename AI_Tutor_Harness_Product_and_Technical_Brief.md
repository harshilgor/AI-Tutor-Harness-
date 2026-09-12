# AI Tutor Harness

## Product and Technical Brief

**Version:** 0.1 — consolidated design baseline  
**Date:** 11 September 2026  
**Status:** Product direction and proposed architecture; implementation has not been claimed or validated.  
**Project:** `C:\Projects\AI Tutor harness`

## 1. Purpose, provenance, and decision status

This brief consolidates the conversation **Design AI Learning Harness** into an extensible product and engineering reference. It covers the learning experience, persistent state, orchestration, assessment engine, and implementation boundaries. It is intended to support further UI/UX design, engineering planning, and model evaluation.

The source conversation is identified by `6aa40f8e-5c34-83eb-9032-27125ee20248`. All six available turns were retrieved. Two long assistant replies were capped at 20,000 characters by the conversation reader; their unavailable endings are not represented as recovered text. This document covers the available discussion and every topic requested for this brief. Concrete schemas, API routes, failure handling, acceptance criteria, and rollout details below are **proposed implementation notes**, not a verbatim transcript or previously approved specifications.

External research claims, numerical study results, and unresolved citation markers from the conversation have not been reproduced as verified facts. This is a design consolidation, not a fresh literature review or a check of current software versions and vendor pricing.

### Direction to preserve

- Build an execution environment for learning: models operating on structured curriculum, learner evidence, policies, and tools.
- Optimize verified understanding and retention while reducing unnecessary prompting and context switching.
- Use a semantic-zoom knowledge canvas with three primary areas: **Learn, Practice, Notebook**.
- Keep canonical learner state outside model prompts and conversational history.
- Use one small learning kernel with modular capabilities and explicit workflows.
- Start with a Python backend and TypeScript frontend in a modular monolith.
- Assess concepts through varied reasoning demands and transfer, not only number-swapped questions.

### Decisions still open

The first subject and target audience, exact model assignments, mastery thresholds, graph-authoring process, commercial model, open-source boundaries, deployment provider, production budgets, and detailed visual design remain open. Illustrative probabilities, timings, transfer scores, and readiness percentages are not calibrated product promises.

## 2. Product thesis

**The harness continuously selects the smallest useful next teaching action that improves the learner's verified understanding.**

A general chat interface requires learners to manage their own educational process: recognize missing prerequisites, ask for simpler explanations, request examples, remember where they were, and decide when to review. Long conversations accumulate text without necessarily producing a reliable account of what the person knows.

The harness supplies the working environment around the model:

> LLM + learner state + knowledge graph + pedagogy + verification + assessment + memory.

The learner experiences one coherent tutor. Internally, the system selects capabilities, models, and deterministic tools according to the learning objective. The underlying model is replaceable; the persistent learning environment is the product.

The coding-harness analogy is useful: the curriculum supplies the specification, the knowledge graph supplies structured working context, assessments supply tests, verification tools check outputs, and the learner model holds persistent state. The analogy has limits: education involves latent understanding, so a successful answer is evidence rather than absolute proof of mastery.

The potential long-term advantage is a trustworthy longitudinal learner model and evidence about which interventions produce retention and transfer. A graph display or a collection of prompts alone does not establish that advantage.

## 3. First-principles learning goals

1. **Start at the knowledge frontier.** Identify the smallest missing prerequisite instead of assuming understanding or restarting from elementary material.
2. **Preserve productive effort.** Reduce navigation and prompting friction while retaining retrieval, reasoning, and independent problem solving.
3. **Separate exposure from mastery.** Reading an explanation and saying “I understand” do not establish independent competence.
4. **Teach toward a bounded goal.** Use a course, syllabus, task, or exam objective rather than an unlimited graph of an entire field.
5. **Make learning durable.** Revisit knowledge after delays and test it across varied contexts.
6. **Make uncertainty visible.** State estimates, source coverage, and verification limits should be intelligible.
7. **Preserve learner agency.** Recommendations are overridable; the system should explain why a next action matters.

### Core learning loop

```text
Define goal → compile bounded curriculum → diagnose prior knowledge
→ locate frontier → teach actively → assess independently
→ update evidence and learner state → schedule review → choose next action
```

An active teaching segment typically uses intuition, an example, learner reasoning, and feedback. Different representations can include formal explanation, visual intuition, simplified language, derivation, worked example, analogy, counterexample, and misconception analysis.

### Success measures

Primary candidates are verified mastery gained per focused minute, delayed retention, and transfer performance. Supporting measures include manual pedagogy corrections per mastered concept, unnecessary prerequisite detours, time to resume after a branch, repeated misconception rate, and course-goal coverage.

Operational measures include time to first useful response, validated assessment generation latency, cost per learning outcome, verification failure rate, duplicate-item rate, and workflow recovery rate. Do not optimize session length or message count as substitutes for learning. A declining number of “simpler” clicks is meaningful only alongside stable or improved understanding.

## 4. Knowledge graphs, curriculum state, and learner state

### 4.1 Domain and curriculum graph

The domain graph describes what concepts exist and how they relate. A course selects and versions a bounded part of that territory. For example:

```text
DCF depends on WACC, free cash flow, and terminal value
WACC depends on cost of equity, cost of debt, and capital structure
Cost of equity may use CAPM within the selected course model
```

Each concept should carry a stable ID, title, definition, scope, source references, related skill specifications, representations, misconceptions, and curriculum version. Edges must be typed: `requires`, `part_of`, `related_to`, `enables`, or `applies_in`. A topical relationship must not automatically become a prerequisite.

**Implementation notes:** Store concepts and edges in PostgreSQL initially. A specialized graph database is not required for V1. Validate prerequisite cycles, disconnected required skills, duplicate concepts, edge direction, and provenance. Course prerequisites should reflect the intended learning objective: deriving a formula can require more background than applying it. Preserve general related-to cycles while handling dependency cycles explicitly.

Curriculum state also contains course goals, assessment weights where known, material versions, source policy, coverage, and graph review status. AI-proposed graph changes should be distinguished from accepted curriculum revisions.

### 4.2 Learner graph

The learner graph is a person-specific overlay on concepts and skills, not a copy of the curriculum structure. It answers:

- What can this learner demonstrate now?
- What remains uncertain or unexplored?
- Which misconceptions appear in their work?
- What may be fading, and what is ready to learn next?
- What blocks the current goal?

Per-skill state should include estimated mastery, uncertainty, evidence references, last independent assessment, successful attempts, assistance history, misconception hypotheses, forgetting or review state, and estimator version. Keep self-reported confidence separate from the model's confidence in its estimate.

Suggested visual states are unexplored, developing, demonstrated mastery, fragile/due for review, and misconception detected. Use labels, borders, icons, and fill patterns alongside color. A “mastered” state is revisable, not permanent certification.

### 4.3 Session memory

Session state records the current goal, concept, lesson position, branch ancestry, selected text, active confusion, Teaching Gear, and pending task. It lets a learner explore CAPM inside WACC and return to the same DCF step.

Session summaries and branch context are bounded. Closing a branch can release transient model context while retaining notes, evidence, and the return anchor according to retention policy. Closing a panel should not silently delete user-authored material.

### 4.4 Ownership rule

**Only the learner-state module writes canonical mastery state.** Tutor, assessor, exam, simulation, and flashcard modules produce evidence or proposals. A model-generated assertion such as “mastery is now 0.81” cannot directly change the learner record.

## 5. Minimum prerequisite closure and recommendations

Teaching from first principles means grounding the next explanation in what this learner can use; it does not mean reteaching everything from the beginning.

Proposed closure process:

1. Resolve the target skill and intended depth within the active curriculum version.
2. Traverse required prerequisite edges backward, with cycle detection and scope limits.
3. Overlay learner estimates, uncertainty, evidence age, and the independence of past attempts.
4. Identify blocking gaps and uncertain dependencies that warrant a short diagnostic.
5. Select a minimal bridge plan in dependency order.
6. Teach and check the bridge, then restore the original task.

For a Black–Scholes learning objective, the selected course graph might identify continuous compounding as the only blocking gap while options and volatility are sufficiently established. The learner receives a short bridge rather than an entire mathematical curriculum. Exact prerequisites depend on whether the objective is intuition, calculation, or derivation.

**Implementation notes:** “Minimum” is initially a bounded heuristic, not a claim of mathematical optimality. Use relevance, uncertainty, expected time, and dependency depth. An incomplete graph can miss a gap; output checks must also inspect newly introduced terminology. Explicitly handle unavailable prerequisite evidence instead of equating unknown with either mastered or failed.

The recommendation engine ranks learn, review, and practice actions using expected gain, goal relevance, concepts unlocked, forgetting risk, and time. The conversation suggested a multiplicative score divided by expected time. Treat this as an exploratory heuristic: a zero forgetting-risk term would incorrectly suppress new learning. A practical initial scorer should use separate review and new-learning features, explain its choice, and permit override.

## 6. Experience architecture: Learn, Practice, Notebook

| Area | Primary job | Included experiences |
|---|---|---|
| Learn | Build understanding in context | Knowledge canvas, tutor cards, sidecars, contextual actions, inline quick checks |
| Practice | Retrieve and demonstrate understanding | Flashcards, quizzes, exams, past mistakes, due reviews |
| Notebook | Retain and organize personal knowledge | Notes, saved explanations, definitions, examples, bookmarks, sources, AI summaries |

Course switching and settings are secondary controls. A lightweight launch dashboard can offer “continue learning,” due review, and next recommended action without becoming a permanent fourth tab. Progress belongs in graph layers or an optional overlay. The earlier idea of separate Roadmap, Map, and Focus destinations was refined into semantic zoom on one canvas.

### 6.1 Semantic-zoom learning canvas

- **Far zoom:** Course and topic clusters show the territory and goal coverage.
- **Medium zoom:** A readable roadmap shows dependencies, the frontier, and current progress.
- **Near zoom:** An active node expands into explanations, examples, questions, notes, and branches.

Clicking WACC should expand a learning card while preserving spatial orientation. Avoid displaying every node and edge at once. Use clustering, local neighborhoods, progressive disclosure, stable layout, and visible return controls.

**Implementation notes:** React Flow is the initial canvas candidate. Keep curriculum semantics separate from canvas coordinates and UI selection. Fetch graph neighborhoods incrementally; do not ship an entire large graph on each interaction. Define zoom thresholds with hysteresis so small movements do not repeatedly swap representations. Preserve focus across layout changes. Provide keyboard access and an equivalent ordered outline or focused layout on small screens; zoom cannot be the sole means of navigation.

### 6.2 Contextual actions

Below relevant content, expose **Simpler, Go deeper, Example, Why?, Visualize, Test me**. These issue typed commands rather than requiring learners to compose prompts. Inline practice may open a short card and return to the lesson after completion.

### 6.3 Sidecars and branches

A sidecar is a bounded contextual exploration anchored to a concept, sentence, or lesson step. It receives the selected text, parent concept, objective, source pack, relevant learner state, already-seen explanation, and teaching profile.

Branches can nest and offer alternative representations without replacing the main lesson. Each needs a parent ID, anchor, return position, bounded summary, and lifecycle status. Preserve useful notes and independently supported evidence when collapsing it. Multiple perspectives are optional workflow roles, not a requirement to run many model calls for every question.

### 6.4 Notebook

Notes attach to one or more concept IDs and optionally an exact lesson or source span. “Save to notes” captures an explanation with provenance. Distinguish user-authored notes, saved AI text, and generated summaries. Allow editing, backlinks, and return to the concept. Future teaching may retrieve relevant notes, but a personal note is not automatically a verified source or proof of understanding.

### 6.5 Focused assessment modes

Exam mode uses a dedicated question view, progress, optional timer, flagging, and navigation. Suppress answer-revealing tutor assistance during an independent attempt. Enforce this on the backend as well as in the interface. Accommodations can remain available without exposing solutions; assisted attempts must be labeled accurately.

Flashcard mode uses a retrieval prompt, response or recall opportunity, reveal, and review feedback. Self-ratings such as Again/Hard/Good/Easy can guide scheduling, while observable correctness and assistance history remain distinct evidence.

A universal command bar can interpret “Make a 30-minute exam on this week's learning” or “Make flashcards from my mistakes” into validated commands. Voice can later use the same command boundary. Navigation surfaces and backend capabilities are not one-to-one.

## 7. Teaching Gear and adaptive pedagogy

Expose one understandable control: **Quick | Guided | Deep**. It sets defaults for a multidimensional teaching profile.

| Dimension | Quick | Guided | Deep |
|---|---|---|---|
| Explanation depth | Concise | Adaptive | Detailed |
| Examples | Zero or one when sufficient | One or two as useful | Multiple representations |
| Prerequisite exploration | Targeted | Adaptive checks | More thorough exploration |
| Derivations | Usually omitted | When useful | Often included |
| Scaffolding | Focused help | Support that fades | Deliberate reasoning support |
| Concept connections | Essential | Relevant | Broader, goal-aware |
| Understanding checks | Short | Standard | More transfer-oriented |

The original discussion also suggested varying verification effort by gear. **Implementation refinement:** retain a correctness and safety floor for every gear; allocate extra verification according to claim type and risk. Quick must never mean permission to publish unchecked high-risk claims. Deep does not automatically mean harder exams or more model reasoning on every call.

Repeated contextual feedback may adjust default abstraction, examples, and pacing. Store these as revisable preferences or observed intervention outcomes, not fixed “learning style” diagnoses. Separate learner preference from measured effectiveness and allow reset or override. An explanation can become easier to understand without changing the skill being assessed.

## 8. Learning kernel and policy layer

```text
UI action / language intent
          ↓
Validated command + authorization
          ↓
Learning kernel: context, policy, capability selection, workflow
          ↓
Capability → model router / tools → verification
          ↓
User-facing result + events + evidence
          ↓
Canonical learner update → next action
```

The kernel owns shared concepts: learner, curriculum and session state references; policies; permissions; capability registry; model and tool interfaces; workflow execution; events; budgets. Tutoring, exams, notes, and future features remain capabilities above those primitives.

Global learning policy should require prerequisite awareness, prefer demonstrated evidence over self-report, constrain unnecessary concepts, protect independent assessments, ground claims under course source policy, and use retrieval when retention is the objective. Capability policy specializes this for tutoring, exams, flashcards, and notes.

Policy composition is **global policy → capability policy → learner context → task**. Enforceable rules belong in code and permissions as well as prompts. Retrieved documents, learner notes, and model outputs are data, not instructions that may override authorization or exam rules.

### Canonical context contract

```json
{
  "context_version": "1",
  "learner_id": "learner_123",
  "goal_id": "goal_valuation",
  "curriculum_version": "finance_v1",
  "session_id": "session_1",
  "current_concept_id": "wacc",
  "learner_state_version": 12,
  "relevant_skill_states": [],
  "teaching_profile": {"gear": "guided"},
  "source_policy_id": "course_sources_first",
  "source_pack_refs": [],
  "permissions": ["learn", "practice"],
  "model_budget": {"policy_id": "interactive_default"}
}
```

Hydrate context on the server using the authenticated user; never trust a frontend-supplied learner ID or mastery estimate. Send a bounded relevant snapshot to the model, not unrestricted history or every stored record.

## 9. Modular monolith and language stack

| Layer | Proposed technology | Implementation intent |
|---|---|---|
| Learning backend | Python | Own learning logic, orchestration, assessment, and verification |
| API and validation | FastAPI + Pydantic | Typed requests, validated responses, generated OpenAPI contracts |
| Frontend | TypeScript + React / Next.js | Own navigation, canvas, forms, streaming, and focused modes |
| Canvas | React Flow initially | Render interactive concept neighborhoods |
| Primary storage | PostgreSQL | Curriculum, learner state, evidence, notes, workflow records |
| Retrieval index | pgvector initially | Supplement source retrieval with semantic search |
| Ephemeral cache | Redis when justified | Caching and short-lived coordination; never sole canonical storage |
| File storage | S3-compatible storage | Uploaded sources and generated assets |
| Background work | Persisted jobs and simple workers first | Ingestion and assessment generation with recovery |
| Durable workflow option | Temporal later | Consider when long waits, retries, and recovery warrant it |
| Workflow adapter option | LangGraph behind internal contracts | Optional implementation, not the product's domain architecture |
| Deployment | Docker and cloud containers | Provider remains open |
| Schemas | Pydantic / JSON Schema | Versioned contracts; generate compatible TypeScript types |

This is one logical Python application with strong module boundaries, potentially running API and worker processes. It does not require a fleet of microservices, Kubernetes, custom model training, or a specialized graph database at launch.

```text
apps/web/                         TypeScript experience
learning_harness/
  core/                           Shared IDs, contracts, policies
  curriculum/                     Graph, skill specifications, versions
  learner/                        Evidence interpretation and canonical state
  teaching/                       Planning and tutoring
  assessment/                     Blueprints, items, attempts, grading, review
  verification/                   Claims, tools, validation results
  retrieval/                      Source packs and provenance
  orchestration/                  Commands, workflow state, capability registry
  models/                         Provider adapters and routing
  notes/                          Personal knowledge artifacts
  analytics/                      Learning and operational measurement
prompts/                          Versioned task templates
```

Modules expose typed interfaces and own their writes. Avoid reaching directly into another module's tables from capability code. Extract a service only when workload isolation, team ownership, or deployment needs justify it; preserve contracts and avoid promising costless extraction.

## 10. Capability contract and extensibility

Each capability should declare its identifier, version, supported commands, input/output schemas, permissions, dependencies, policy, emitted events, and evidence types. The conceptual lifecycle is:

```text
can_handle(context, command)
→ plan(context, command)
→ execute(plan)
→ evaluate(result)
→ commit approved artifacts/events/evidence
```

Examples include `teaching.tutor`, `teaching.socratic`, `assessment.exam`, `assessment.retrieval_practice`, and `knowledge.notes`. Future proof tutors, coding labs, simulations, and debate modes can reuse the same learner, graph, source, model, and evidence infrastructure.

Explicit UI commands should map deterministically where possible. Free-form language may require intent interpretation, followed by schema validation. Resolve competing capabilities through a stable registry and policy, rather than unconstrained model selection.

### Adding a feature

1. Define its learning purpose, commands, and typed results.
2. Reuse the canonical context and declare required tools and permissions.
3. Specify its workflow and verification gates.
4. Define the evidence it can legitimately produce.
5. Add rendering to an existing surface or a focused mode.
6. Add contract checks, evaluation examples, and observability.

A flashcard feature should not require rewriting the tutor or creating a second mastery database. Provider SDKs and workflow frameworks must stay behind adapters. Version prompts, policies, capabilities, curricula, rubrics, and estimators so regressions can be traced.

## 11. Commands, events, and evidence

| Type | Meaning | Examples |
|---|---|---|
| Command | A request that can be accepted or rejected | `TeachConcept`, `AskQuestion`, `OpenBranch`, `GenerateExam`, `SubmitAnswer`, `CreateFlashcards` |
| Event | A fact recorded after an action | `LessonStarted`, `ExplanationDelivered`, `QuestionAnswered`, `ExamGenerated`, `NoteCreated` |
| Evidence | A structured observation usable for learner inference | Independent transfer success, rubric result, hinted response, misconception hypothesis |

Clicking a concept emits an exposure event; it does not demonstrate mastery. `QuestionAnswered` records a submission; an evaluated evidence record adds rubric outcomes and reliability. `ConceptMasteryUpdated` records the canonical updater's decision. This refinement prevents raw submissions from becoming unvalidated state changes.

```json
{
  "evidence_id": "ev_102",
  "schema_version": 1,
  "learner_id": "learner_123",
  "attempt_id": "attempt_18",
  "skill_id": "wacc.market_value_weighting",
  "observation": "incorrect",
  "assessment_mode": "transfer",
  "assistance": "none",
  "misconception_hypothesis": "book_value_weights",
  "rubric_version": "wacc_r1",
  "item_version": "item_23_v1",
  "validation_status": "accepted",
  "source_event_id": "event_909"
}
```

**Implementation notes:** Add occurrence time, correlation and causation IDs, actor, curriculum version, and provenance. Use idempotency keys for commands and deduplicate evidence by stable identifiers. Persist state updates and outgoing event records transactionally, using an outbox if asynchronous delivery is needed. Consumers should tolerate retries and stale versions. Do not assume exactly-once delivery or build a full event-sourced architecture merely to keep an event log.

Review scheduling and recommendations consume approved state updates. Analytics can consume behavioral events. Notebook retrieval can use saved content without granting it authority over learner state.

## 12. Explicit workflows and orchestration

Logical roles are Curriculum Compiler/Architect, Teaching Planner, Tutor, Assessor, Verifier, and Learner Model. They are responsibilities, not necessarily separate models or processes. Invoke only the roles needed for the current task.

### Teaching

```text
ANALYZE → CHECK_PREREQUISITES → PLAN → GENERATE
→ VERIFY → DELIVER → CHECK_UNDERSTANDING
→ RECORD_EVIDENCE → ADVANCE or REMEDIATE
```

The plan identifies the target skill, detected gap, known prerequisites, representation sequence, scaffolding, concepts to avoid, source pack, and response contract. For WACC market-value weighting, it may use intuition, one company example, then a diagnostic without reteaching CAPM.

The tutor returns structured content blocks, concept references, newly introduced terms, claims with source references, and an optional assessment proposal. Check for unsupported claims and unexplained dependencies. Regenerate, simplify, or add a short bridge when needed.

### Sidecar

```text
OPEN_ANCHOR → BUILD_CONTEXT → PLAN/TEACH/VERIFY
→ optional CHECK → SAVE_USEFUL_ARTIFACTS → RETURN_TO_ANCHOR
```

### Curriculum ingestion

```text
UPLOAD → PARSE → CHUNK → EXTRACT_CONCEPTS/SKILLS
→ PROPOSE_EDGES → VALIDATE → REVIEW → PUBLISH_VERSION
```

### Assessment

```text
BLUEPRINT → GENERATE → SOLVE/CRITIQUE → SIMILARITY_CHECK
→ APPROVE → DELIVER → COLLECT → GRADE → UPDATE_LEARNER → REVIEW_PLAN
```

Every workflow needs persisted status, timeouts, bounded retries, cancellation, and a recoverable failure outcome. If validation cannot succeed within budget, fail clearly or use a previously approved eligible item. Never bypass verification to make the workflow appear successful. Long-running jobs should survive an API restart even before a dedicated durable-workflow platform is introduced.

## 13. Model providers, routing, and prompt management

Capabilities request a task through a provider-neutral interface such as `ModelProvider.generate`, not direct vendor calls scattered throughout the application. Candidate adapters include OpenAI, Anthropic, Gemini, and local models; these are architectural options, not selected deployments.

Normalize messages, structured-output expectations, streaming, tool calls, usage, errors, and cancellation. Maintain an explicit support matrix because providers do not have identical capabilities. Preserve provider-specific features through controlled options rather than assuming complete interchangeability.

Routing inputs include task type, complexity, required quality, source sensitivity, structured-output or tool needs, latency, cost budget, and provider health. Use deterministic calculation or execution where it can establish an answer. Evaluate faster models for simpler extraction or card drafting, and stronger reasoning models for difficult planning, transfer generation, or critique. Model identity and current pricing require later evaluation.

Fallbacks must preserve policy and required capabilities. A cheaper model is not an acceptable fallback if it fails the task's quality gate. Record why escalation occurred and cap retries. Use a narrow source pack, reusable validated material, and background generation to control latency and cost.

Store prompts outside business logic, for example `prompts/assessment/generate_item_v1.yaml`. Each generation trace should identify model/provider, prompt, policy, capability and curriculum versions, source pack, tool results, latency, and cost where available. Store only the learner information needed for debugging under the retention policy.

## 14. Verification and source grounding

The product should promise an evidence-based correctness process, not zero misinformation. Multiple models can share the same error.

| Output type | Preferred evidence |
|---|---|
| Arithmetic and numerical work | Independent calculation, units, tolerances, boundary checks |
| Symbolic mathematics | Symbolic tools where applicable plus explicit domain assumptions |
| Programming | Isolated execution and relevant tests |
| Course factual content | Traceable syllabus, lecture, textbook, or approved source spans |
| Current claims | Current authoritative sources under course policy |
| Contested or interpretive claims | Attributed positions, rubric, and disclosed uncertainty |

Uploaded course materials set the course context and expectations. If they conflict internally or with authoritative corrections, expose the discrepancy rather than silently declaring the course material infallible. Retrieval similarity alone does not establish that a source supports a claim.

Store verification status, method, checked claims, assumptions, source spans, and unresolved issues. A generic checkmark should not imply that every sentence was independently proven. A solver/critic review is useful but does not replace external evidence.

**Streaming note:** verification after unrestricted streaming can reveal an error before it is checked. Gate assessment items and high-risk content before delivery; for ordinary teaching, use validated content blocks or a clearly defined provisional-to-verified flow. Never stream hidden solutions to the assessment client.

## 15. Assessment engine: testing concepts through transfer

The motivating failure is an exam generator that merely changes company names or numbers while preserving the same procedure. Such items can support rehearsal but cannot by themselves establish broad understanding.

Assessment starts with **what skill is being measured**, then selects reasoning demands, then creates a question. Difficulty, transfer distance, scaffolding, and format are separate controls.

### 15.1 Skill specifications

A skill specification includes concept links, observable competencies, conceptual invariants, prerequisites, misconceptions, allowed assumptions, representative tasks, scoring criteria, and sources.

For WACC, competencies may include selecting relevant financing components, choosing market-value weights, using appropriate component costs, accounting for taxes under stated assumptions, calculation, interpreting changes, and excluding irrelevant inputs. Misconceptions include book-value weighting, equal averaging, incorrect tax treatment, and uncritical use of historical financing costs.

An item should preserve the conceptual invariant being tested while changing the observable problem structure. Domain rules need qualified assumptions; a finance example must not imply that one simplified formula applies in every setting.

### 15.2 Assessment blueprints

An exam blueprint specifies scope, learning objectives, skill coverage, duration, item count, families, formats, target difficulty and transfer distributions, scaffolding, scoring, source restrictions, and excluded prior exposures. An item-level entry could be:

```json
{
  "skill_id": "wacc.market_value_weighting",
  "cognitive_operation": "diagnose",
  "item_family": "critique_analyst_method",
  "target_difficulty": 0.65,
  "target_transfer_distance": 0.7,
  "scaffolding": "none",
  "format": "case_analysis",
  "misconception_target": "book_value_weights",
  "requires_calculation": true
}
```

These numbers are authoring targets until calibrated against actual learners. They do not establish measured difficulty or transfer distance.

### 15.3 Transfer distance

| Illustrative level | Change relative to learned examples |
|---|---|
| 0.1 | Same procedure with different numbers; rehearsal |
| 0.3 | Different context, familiar procedure |
| 0.5 | Changed representation; learner selects relevant information |
| 0.7 | Concept embedded in a larger problem |
| 0.9 | Novel situation requiring recognition of the applicable concept |

Transfer is relative to what the learner has already seen. Store that exposure context and assess changes in representation, context, cues, and reasoning path. A numerically tedious calculation can be difficult but low-transfer. Novelty can also introduce unintended background demands; validation must distinguish those from the target skill.

### 15.4 Item families

For one skill, sample across calculation, diagnosis, comparison, information selection, explanation, reverse inference, application, critique, and transfer. WACC examples include:

- Calculate under clearly specified assumptions.
- Diagnose an analyst's use of book-value weights.
- Compare two cases and identify an assumption that explains the difference.
- Select necessary inputs from a larger information set.
- Critique the claim that financing entirely with cheaper debt automatically minimizes financing cost.
- Apply the concept as one stage in a broader valuation problem.

These are item-design examples, not validated exam questions or financial advice. Each needs a complete scenario, defensible answer or rubric, and independent checking.

### 15.5 Hidden item specification

Store item ID/version, skill IDs, prerequisites, invariant, family, expected reasoning steps, accepted answers, tolerances, rubric, common error paths, assumptions, sources, generation trace, and validation results. Keep answer keys and private rubrics server-side until the permitted feedback stage.

If an answer is wrong, distinguish input selection from calculation or interpretation where the response provides enough evidence. Do not infer a specific misconception from a final number alone when several causes are possible.

### 15.6 Similarity guards

Compare candidates with source questions, canonical templates, previous generated items, the current exam, and the learner's exposure history. Combine text or embedding similarity with normalized quantities, task-family labels, expected-step structure, and model-assisted reasoning-path comparison.

High topic similarity is expected. The guard targets repeated solution paths where diversity is required. Two items that both read D and E, compute weights, apply a tax adjustment, and average returns remain structurally similar after renaming the company. A diagnosis task can test the same invariant through a different operation.

Use purpose-specific thresholds. Repetition can be intentional in early practice; an exam blueprint may require broader coverage. Bound regeneration, keep rejection reasons, and audit false positives. An embedding threshold alone cannot guarantee novelty or prevent all memorization.

### 15.7 Solver and critic validation

An independent solver attempts the item without seeing the proposed answer first. Use calculation, symbolic methods, or code where applicable. A critic checks sufficiency of information, ambiguity, assumptions, alignment to skill and blueprint, unintended prerequisites, distractor leakage, and scoring fairness. Open-ended items may have multiple valid answers; require a rubric instead of artificial uniqueness.

If solver and answer key disagree, resolve the discrepancy before delivery. Agreement between two models is not enough for an independently checkable calculation. Accepted items receive a versioned validation record; rejected items are repaired, regenerated, or excluded.

### 15.8 Exam delivery and feedback

Create an immutable attempt snapshot, enforce assessment mode, save responses incrementally, support recovery, and define timing and submission rules. After submission, grade against the validated rubric, emit skill-level evidence, identify supported misconception hypotheses, and propose review or remediation. Keep assisted and independent attempts distinct.

## 16. Flashcards and spaced review

Flashcards are a retrieval-practice capability available from Learn, Practice, or post-exam remediation. Use one atomic retrieval target per card, clear prompts, source-linked answers, and conceptual prompts where appropriate. Avoid relying only on recognition or ambiguous wording.

```text
Select scope/due skills → draft or retrieve cards → validate
→ prompt recall → capture response → reveal/feedback
→ record evidence → schedule review
```

Cards may originate from a concept, a misconception, or a saved note, but note-derived content still requires appropriate validation. A self-rated “Easy” can guide scheduling without becoming strong independent evidence. Capture hints and answer reveal timing. Response time is contextual, not a standalone measure of competence.

Keep review scheduling separate from mastery estimation. The exact scheduling algorithm, intervals, and handling of missed sessions remain open. Retrieval success does not establish far-transfer skill; broader practice remains necessary.

## 17. Mastery and knowledge tracing

Use an interpretable probabilistic baseline before attempting a learned proprietary model. Bayesian Knowledge Tracing was proposed in the conversation; a simple evidence-based model is also an appropriate baseline for evaluation.

**Implementation clarification:** classic BKT models latent knowledge, learning, guessing, and slips; elapsed-time forgetting requires an explicit extension or separate retention model. Do not claim that unmodified BKT automatically handles decay.

The estimator should distinguish independent from hinted work, familiar from novel items, immediate from delayed performance, and observed evidence from self-report. Skill-level estimates feed concept-level summaries; an aggregate percentage must not conceal a crucial missing subskill. Multi-skill problems require cautious credit assignment.

Version the update policy and retain evidence references so changes are explainable and recalculable. Avoid treating several nearly identical questions as independent strong evidence. Calibration should examine predicted versus observed success, delayed retention, transfer, and uncertainty across learner groups.

Course readiness can summarize objective-weighted coverage and independent performance, but it is not automatically the probability of passing an external exam. Label the meaning and uncertainty before displaying a precise percentage. Larger neural knowledge-tracing approaches are later options once data volume, privacy, and measured benefit justify them.

## 18. Proposed APIs and data models

These routes and entities make the architecture concrete; they are proposed contracts to refine during implementation.

### API surface

| Route | Purpose |
|---|---|
| `POST /v1/courses` | Create a bounded course |
| `POST /v1/courses/{id}/sources` | Register/upload source materials and start ingestion |
| `GET /v1/courses/{id}/graph` | Retrieve a versioned graph neighborhood |
| `GET /v1/courses/{id}/learner-state` | Retrieve authorized learner overlay and uncertainty |
| `POST /v1/sessions` | Start/resume learning context |
| `POST /v1/commands` | Dispatch validated learning actions |
| `GET /v1/workflows/{id}` | Retrieve asynchronous progress or failure |
| `GET /v1/sessions/{id}/stream` | Stream authorized workflow/content events |
| `POST /v1/assessment-attempts/{id}/answers` | Save an answer idempotently |
| `POST /v1/assessment-attempts/{id}/submit` | Finalize an attempt under its rules |
| `GET /v1/reviews/due` | Retrieve scheduled review work |
| `POST /v1/notes` | Create a concept-linked note |

Commands include a command type, schema version, session/course references, parameters, and idempotency key. Server-derived identity and permissions govern every action. For example, `StartAssessment` supplies scope and mode, not a vendor prompt. Return a workflow ID for long generation tasks. Define stable error codes, pagination, concurrency/version rules, and stream resumption semantics.

### Core entities

| Entity | Important fields or relationships |
|---|---|
| Course / CurriculumVersion | Goals, scope, source policy, publication status |
| Concept / ConceptEdge | Stable IDs, typed relationships, provenance, version |
| SkillSpecification | Competencies, invariant, prerequisites, misconceptions, rubric references |
| LearnerSkillState | Learner/skill key, estimate, uncertainty, state version, evidence links |
| LearningGoal | Target skills, date where supplied, relevance weights |
| Session / Branch | Current focus, anchor, ancestry, summary, mode |
| Source / SourceChunk | File hash/version, page/span, rights metadata, retrieval references |
| TeachingPlan / LessonArtifact | Strategy, content blocks, concept links, verification |
| AssessmentBlueprint / Item | Coverage, family, private key/rubric, validation version |
| Attempt / Answer / Evidence | Immutable item reference, assistance, rubric outcome, provenance |
| ReviewSchedule | Skill/card link, due time, scheduling policy version |
| Note | Author/type, content, concept links, source and lesson references |
| Workflow / Command / Event | Status, IDs, idempotency, correlation, timestamps |
| GenerationTrace / VerificationResult | Model/prompt versions, tool checks, status, limitations |

Enforce ownership and referential integrity. Version curriculum and items so historical attempts remain interpretable after edits. Store private answer material separately from public item payloads. Use structured artifacts rather than reparsing rendered prose as the primary state interface.

## 19. Reliability, privacy, and operational boundaries

Persist canonical state in PostgreSQL and source files in durable object storage. Cache loss must not erase progress. Define backup, recovery, migration, retention, export, and deletion behavior before broad release. Uploaded educational materials and learner histories may be sensitive or licensed; access and provider-sharing choices need explicit product policy.

Sandbox executable verification, restrict tools, and treat retrieved content as untrusted input. Record workflow failures without logging unnecessary personal text. Add provider timeouts, bounded budgets, and traceable failure outcomes. A model outage should not corrupt an attempt or falsely mark work verified.

Future data use for training or research is a separate consent and governance decision. Avoid framing personal learner data as an unrestricted asset merely because longitudinal evidence may improve the product.

## 20. Implementation sequence and acceptance criteria

### Phase 0 — define the learning contract

Choose one narrow, measurable domain and audience. Select trusted materials, define a small reviewed graph and skill set, author representative assessment families, and establish baseline tutor and grading evaluations. Agree on what “independent,” “verified,” and “mastered” mean operationally.

### Phase 1 — vertical learning slice

Implement curriculum and learner persistence, one teaching workflow, prerequisite bridge, source-grounded output, basic Learn canvas, Teaching Gear, one sidecar, concept-linked notes, and a small independent check. Use a provider adapter even if only one provider is initially configured.

**Acceptance:** A learner can encounter a gap, complete a bridge, return to the original lesson, submit an answer, and see a traceable state update after refresh. Reading alone does not increase demonstrated mastery. Another learner cannot retrieve their records.

### Phase 2 — structured practice

Add blueprints, diverse item families, similarity checks, solver/critic validation, private answer storage, focused exam attempts, flashcards, and review scheduling. Reuse the same evidence pipeline.

**Acceptance:** A number-swapped clone is detected when diversity is required; ambiguous or unsolved items are withheld; answer keys remain unavailable during the attempt; retries do not duplicate evidence; post-exam remediation targets supported gaps.

### Phase 3 — adaptive experience and operations

Refine semantic zoom, recommendation explanations, delayed-retention measurement, profile adaptation, multi-provider routing, budget policies, and workflow recovery. Expand domains only after validating graph and assessment quality.

**Acceptance:** A interrupted background job resumes or fails clearly; model changes can be compared on held-out examples; the UI has accessible navigation alternatives; readiness labels reflect their actual evidence basis.

### Phase 4 — expansion by evidence

Consider simulations, coding labs, proof tutoring, voice, stronger knowledge tracing, durable workflow infrastructure, and selective service extraction. Add complexity only when measured needs support it.

## 21. Evaluation strategy

Evaluate the full learning loop, not only fluent responses. Maintain versioned examples for prerequisite detection, unsupported claims, contradictory sources, item validity, duplicate reasoning paths, grading disagreements, misconception attribution, and accidental answer leakage.

Use domain review for curriculum and rubrics. Compare model/routing changes against a stable evaluation set and track latency and cost alongside quality. Test state invariants such as one evidence update per accepted attempt, restricted exam context, preserved branch return position, and recoverable workflow transitions.

Learning effectiveness requires delayed and transfer-based evaluation with learners. Product metrics alone cannot demonstrate causal improvement. Experimental design, sample sizes, fairness checks, and release thresholds remain to be specified.

## 22. Risks and mitigations

| Risk | Consequence | Design response |
|---|---|---|
| Incorrect or incomplete curriculum graph | Missing foundations or excessive detours | Provenance, review, typed edges, bounded diagnostics |
| False mastery | Learner advances with fragile understanding | Independent varied evidence, uncertainty, delayed checks |
| Shared model errors | Incorrect content appears validated | External sources/tools and explicit verification scope |
| Superficially varied exams | Rehearsal mistaken for transfer | Skill blueprints, item families, exposure-aware similarity guards |
| Excessive novelty | Measures unrelated knowledge | Prerequisite and fairness validation |
| Assessment leakage | Invalid independent evidence | Server-enforced modes and private solutions |
| Graph overload | Higher navigation friction | Clustering, semantic zoom, accessible focused alternative |
| Too many model roles per action | Latency and cost undermine usefulness | Selective roles, deterministic tools, budgeted workflows |
| Corrupted or conflicting state | Inconsistent recommendations | Single canonical updater, version checks, idempotency |
| Vendor/framework coupling | Expensive future changes | Provider and workflow adapters; contract tests |
| Unsupported personalization | Preferences mistaken for effective teaching | Reversible adaptation measured against outcomes |
| Overstated readiness | Misleading confidence before an exam | Clearly defined estimates and calibration |
| Privacy or source-rights failures | Loss of trust and restricted use | Access control, retention policy, rights and consent decisions |
| Scope expansion too early | Broad but unreliable product | Narrow first domain and end-to-end acceptance gates |

## 23. Open questions and next design work

### Product and learning

- Who is the first learner: school student, university student, professional, or self-directed adult?
- Which first domain offers trustworthy sources and measurable correctness?
- How much diagnostic work is acceptable before useful teaching starts?
- Which mastery and retention standards should unlock progression?
- How should learners challenge an incorrect graph, explanation, or grade?
- What does exam readiness mean for the selected course?

### UI/UX

- What are the semantic-zoom thresholds, mobile layout, and branch limits?
- How do learners return from nested branches and compare representations?
- Should saved AI material enter Notebook automatically or only on explicit save?
- How should uncertainty and partial verification appear without overwhelming the lesson?
- Which accommodations belong in independent assessment mode?

### Architecture and operations

- Which model candidates satisfy each task's quality, cost, privacy, and latency requirements?
- What triggers escalation to a stronger model or a second verifier?
- Which workflows need durable scheduling at launch?
- How are course graph revisions reviewed and migrated into learner views?
- What retrieval strategy and source-conflict rules work in the first domain?
- What retry limits, operating budgets, and reliability targets are acceptable?

### Assessment and learner modeling

- How will transfer distance and item difficulty be calibrated?
- How much structural repetition is desirable for each practice mode?
- What evidence is sufficient to identify a misconception?
- Which knowledge-tracing and review-scheduling baselines should be compared?
- How should assistance, partial credit, and multi-skill answers affect estimates?

### Ownership and strategy

- Open source, closed source, or an open core with hosted services?
- Which interfaces, prompts, curricula, and evaluation sets should be public?
- What is defensible beyond general graph and chat functionality?
- Which source licenses, learner-data rights, and export promises shape the product?
- What business model aligns incentives with durable learning rather than time spent?

## 24. Design guardrails

The system should remain understandable as **one learning kernel, many capabilities, replaceable models, and one coherent tutor experience**. Keep learning evidence central, keep the knowledge map operational, and let measured improvements in understanding justify future complexity.

The next concrete design artifacts should be a reviewed first-course skill graph, a Learn-to-Practice interaction prototype, a versioned command/evidence contract, a small assessment benchmark, and a vertical-slice implementation plan with explicit quality gates.
