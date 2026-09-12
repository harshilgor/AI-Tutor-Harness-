# Phase One — Features and Technical Implementation Specification

**Project:** AI Tutor Harness  
**Version:** 1.0 — implementation planning baseline  
**Date:** 11 September 2026  
**Status:** Detailed design; application implementation has not started.  
**Scope authority:** The user's phase-one request and subsequent confirmation that arbitrary-topic graphs, graph trust, teaching behavior, controls, exploration windows, and quality gates belong in phase one.

## 1. Purpose and document hierarchy

This specification describes what phase one should deliver and how its features would be built. It translates the design discussion into components, contracts, workflows, failure behavior, and acceptance criteria.

The five areas discussed are all phase-one responsibilities: graph trust, teaching behavior, teaching controls, contextual windows, and quality gates. Their supporting state, source, verification, and persistence mechanisms are also necessary. This does not bring full exams, course uploads, flashcard scheduling, or institutional features into scope.

The [Product and Technical Brief](AI_Tutor_Harness_Product_and_Technical_Brief.md) remains the broad product reference. [Phase One: Scope and Build Readiness](Phase_One_Scope_and_Build_Readiness.md) records the design reasoning and unresolved decisions. [Future Features and Technical Considerations](Future_Features_and_Technical_Considerations.md) retains deferred work. For the detailed phase-one behavior described here, use this specification; do not combine older alternative proposals into contradictory requirements.

**Requirement** means intended phase-one behavior. **Proposed default** means a concrete implementation choice recommended for the first build, still subject to review or testing. Numerical interface and evaluation targets are initial proposals, not validated guarantees. Provider selection, library versions, deployment, audience, and operating budgets remain unresolved where explicitly noted.

## 2. Phase-one product contract

A learner enters any topic, receives a bounded knowledge map, selects a concept, and learns through an adaptive explanation. They can change the teaching style or explore a selected passage in a side panel, including nested questions, then return without reconstructing the main context. The system preserves progress and distinguishes what was read from what was demonstrated.

### Included features

| ID | Feature | Phase-one result |
|---|---|---|
| G1 | Topic entry and scope resolution | Arbitrary topic input with editable meaning, objective, and depth |
| G2 | Graph generation and expansion | Bounded, versioned map with typed relationships and stable concepts |
| G3 | Graph trust | Source support, dependency justification, uncertainty, validation, correction |
| G4 | Knowledge canvas | Focused graph, semantic zoom, selection, search, accessible outline |
| T1 | Learning kernel | Validated learning actions driven by graph, learner, session, and policy |
| T2 | First-principles teaching | Minimal prerequisite support and purposeful explanation sequencing |
| T3 | Understanding evidence | Small validated checks and conservative learner-state updates |
| C1 | Teaching Gear | Quick, Guided, Deep with explicit instructional differences |
| C2 | Contextual controls | Simpler, Go deeper, Example, Why?, Visualize, Check understanding |
| W1 | Anchored exploration | In-app side panel connected to the selected passage |
| W2 | Nested and saved branches | Breadcrumbs, sibling reopening, drafts, exact return position |
| R1 | Reliability | Persistence, cancellation, retries, versioning, correction lineage |
| Q1 | Quality evaluation | Graph, correctness, pedagogy, controls, usability, state, outcome gates |

### Deferred product scope

Full Practice and Notebook destinations, exam assembly, exam-scale blueprints, flashcard scheduling, course/class workspaces, user uploads, transcription, voice, collaboration, advanced analytics lenses, trained personalization, large-scale graph migration tooling, and distributed multi-agent infrastructure remain deferred.

Save lesson and branch content for resumption now. This is not a full note editor. Keep Learn/Practice/Notebook as the long-term navigation model, but do not render unusable empty destinations merely to match that future layout.

## 3. System architecture and ownership

Retain the proposed Python backend and TypeScript frontend. Use a modular monolith with API and worker processes sharing the same domain contracts. No feature requires a separate service initially.

| Component | Proposed implementation | Owns |
|---|---|---|
| Web experience | React/Next.js and TypeScript | Canvas, lesson blocks, controls, branches, client drafts |
| API boundary | FastAPI and Pydantic | Authentication integration, request validation, command dispatch |
| Topic/graph module | Python | Scope resolution, concepts, edges, graph revisions |
| Retrieval module | Python provider adapter | Search/fetch, source records, scoped evidence packs |
| Learning kernel | Python policy and orchestration modules | Action selection, permissions, budgets, workflow transitions |
| Teaching module | Python capability | Plans and explanation artifacts |
| Verification module | Python tools and validators | Claim checks, calculations, output approval |
| Learner module | Python reducer/estimator | Evidence admission and canonical learner projection |
| Session/branch module | Python | Lesson position, ancestry, branch lifecycle |
| Model adapters | Provider-neutral interface | Structured generation, streaming, errors, usage |
| Durable storage | PostgreSQL | Canonical records, revisions, job state, events |
| Optional supporting storage | Object storage, pgvector, Redis as justified | Permitted source snapshots/assets, retrieval index, ephemeral cache |

Do not make Redis, browser storage, or model context the only copy of learner progress. A vector index helps retrieval but does not establish source truth. A graph database is not required: relational concept/edge tables can support the initial graph.

```text
User gesture or language
  → validated command
  → scoped context snapshot
  → learning action / graph-generation workflow
  → model and permitted tools
  → output verification
  → approved artifact and events
  → optional evidence admission
  → canonical state and UI projection
```

The frontend never chooses a vendor prompt or sets its own mastery value. Models propose plans, explanations, and interpretations. Only the responsible domain module commits its canonical state.

## 4. G1 — Topic entry and scope resolution

### User behavior

Provide a topic input with optional intended outcome and depth. Accept broad subjects, narrow concepts, and questions. Ask for clarification only when different interpretations would materially change the map. For example, an ambiguous “Java” request requires disambiguation unless surrounding context resolves it.

Show a short editable scope statement such as “An introductory map of differentiation, focusing on intuition and basic applications.” Do not invent an exam date, professional qualification goal, or prior knowledge.

### Technical implementation

Create a `TopicScope` record containing original request, normalized title, interpretation, objective, depth, locale/language if supplied, scope boundaries, and revision. The resolver returns either a scope proposal or a clarification requirement. Validate the result before retrieval and generation.

Use different scope templates for a broad subject and a narrow concept. A broad subject starts with clusters; a narrow concept starts with the relevant neighborhood. Proposed visible limits are 5–8 clusters or 8–15 concepts respectively. Make them configuration values and evaluate readability rather than treating them as fixed educational rules.

New unrelated topics create distinct learning scopes. Existing evidence can be reused only through a compatible objective mapping; matching names alone is insufficient.

### Failure and acceptance

Invented or poorly documented topics can receive a clarification or insufficient-support response. “Any topic” means broad input support, not a promise of complete verified knowledge for every request. A failed scope resolution must not publish a graph for a guessed interpretation.

**Acceptance:** broad, narrow, ambiguous, and unsupported inputs each produce the correct bounded state without silently restricting all users to a curated subject.

## 5. G2/G3 — Graph construction, trust, and correction

### 5.1 Concept and edge semantics

Keep clusters, concepts, and assessable objectives distinct. A concept carries identity and meaning; an objective describes what the learner should be able to do with it.

Each concept requires an ID, title, definition, scope, objective references, source bindings, and version. Each edge requires endpoints, type, rationale, and support metadata.

| Edge | Meaning | Can trigger a required bridge? |
|---|---|---|
| `requires` | A foundation needed for a named target objective | Yes, if justified and relevant to the learner gap |
| `recommended_before` | Helpful instructional order | No automatic blocking |
| `part_of` | Organizational containment | No |
| `related_to` | Useful conceptual relationship | No |

Record direction consistently: `A requires B` means B is a foundation for A. Traversal code must not reverse this convention. A dependency for formal derivation must not automatically block an intuitive overview.

### 5.2 Source acquisition

Implement a retrieval adapter that returns candidate references, followed by fetching/inspection of relevant content. Store title, origin URL or identifier, locator, revision/date where available, inspected passage reference, retrieval time, and permitted use metadata. A search snippet alone cannot qualify as checked support.

Apply domain-sensitive authority rules. Official documentation may establish software behavior; educational references can support established foundations; historical or interpretive topics need attribution and may admit several defensible learning routes. Conflicting sources require explicit handling. Repetition of one source across several pages does not constitute independent corroboration.

Keep source support for a definition separate from justification of a prerequisite edge. Co-occurrence is not a dependency proof. Model confidence is diagnostic metadata, not authority.

Treat fetched content as untrusted data. Restrict fetches to permitted protocols and public destinations, bound download size and parsing time, and reject attempts to reach local/private services through source URLs. Page instructions cannot change tool permissions or learner state.

### 5.3 Generation workflow

```text
RESOLVE_SCOPE → RETRIEVE → EXTRACT_CANDIDATES → NORMALIZE_IDENTITIES
→ PROPOSE_EDGES → CHECK_STRUCTURE → CHECK_SUPPORT
→ ACCEPT_SUPPORTED_SUBGRAPH → PUBLISH_REVISION
```

Persist each job and its current stage. Concept normalization considers definition and scope as well as labels. Expansion must compare against the existing graph before inserting new nodes. Avoid building a universal cross-domain ontology before the first release.

Validate missing endpoints, duplicate identities, invalid types, containment defects, required-edge cycles, source bindings, and scope coverage. Allow cycles in general relationships. Correct a prerequisite cycle or explicitly model a jointly taught group; never let traversal recurse indefinitely.

A content validator assesses whether references actually support consequential definitions and whether required edges make sense for the objective. A model critic can assist, but its agreement is not independent proof.

### 5.4 Publication policy

| State | Learner-facing treatment | Teaching consequence |
|---|---|---|
| Supported | Sources available | Teach supported claims under recorded checks |
| Suggested sequence | Suggested learning order | Recommend; do not enforce as required |
| Conflicting | Different interpretations | Attribute alternatives; avoid single-answer checks on unresolved claims |
| Insufficient support | Needs checking | Do not present authoritative teaching or scored evidence from the unsupported claim |

Do not use one undifferentiated “verified” badge. Source status and learner progress must use distinct visual treatment.

Publish a coherent initial subgraph once it passes applicable checks. Hidden clusters need not be fully generated. Expansion creates a new revision and preserves the current lesson anchor. Sessions remain pinned until a controlled revision change; a critical correction should visibly invalidate affected content rather than letting a stale version remain misleading.

### 5.5 Reporting and corrections

Provide “This seems wrong” for a node, edge, or explanation. Store the artifact/version, report, and affected claims. A correction workflow rechecks the issue, records its outcome, publishes a superseding revision when warranted, and finds affected checks/evidence.

Invalid assessment evidence is superseded with a reason. The learner is not marked wrong because the system's item was faulty. Never regenerate the map in place and reset all history.

**Acceptance:** repeated expansion avoids duplicates; questionable ordering is not treated as mandatory; unsupported citations do not pass as inspected sources; corrections preserve valid progress.

## 6. G4 — Knowledge canvas and learning position

### User behavior

Open a focused neighborhood around the current concept. Zoom out to topic clusters and inward to lesson detail. Offer scope search, a legend, and “return to current concept.” Selecting a node opens its learning area without losing the map's spatial context.

Display unassessed, explored, developing, or demonstrated-on-check states. Avoid precise mastery percentages in V1 unless their meaning and uncertainty are established. A related-node color cannot imply mastery of its neighbors.

### Technical implementation

Use React Flow as the initial proposed renderer behind domain-neutral graph data. Store layout coordinates separately from graph semantics. Fetch bounded neighborhoods with a graph revision; do not return the entire possible subject graph on every request.

Use progressive disclosure, stable positions, and zoom thresholds with hysteresis to avoid flickering between representations. Keep lesson selection independent of camera position. Expanding another cluster must not unexpectedly move text being read.

Provide a keyboard-accessible outline backed by the same graph, visible focus, text/icon state labels, reduced-motion behavior, and readable small-screen layouts. A graphical canvas must not be the only way to select a concept.

**Acceptance:** the learner can distinguish relationship types, locate the active lesson, navigate without a mouse, and return after graph expansion without losing their place.

## 7. T1/T2 — Learning kernel and teaching policy

### 7.1 Canonical context

For each action, assemble the active objective, relevant graph slice, learner evidence summary, current lesson/branch, resolved teaching profile, source policy, source pack, permissions, and budget. Obtain identity on the server. Do not trust client-supplied mastery or access claims.

Bound the model context to the task. Retrieve relevant historical artifacts by reference rather than copying every conversation into each prompt. Branch summaries are context, not new evidence.

### 7.2 First-principles action selection

| Condition | Action |
|---|---|
| Required foundation demonstrated | Teach the target |
| A term needs a brief definition | Define inline and continue |
| Uncertain foundation materially affects the lesson | Offer one targeted diagnostic or bridge |
| A supported misconception blocks reasoning | Contrast examples and offer a fresh check |
| Many substantial gaps appear | Present an overview and optional deeper path |
| Learner declines assessment | Continue with understanding marked unassessed |

Traverse only objective-relevant `requires` edges with cycle detection and a bounded depth. Proposed interaction limits are one diagnostic before the first useful explanation and one active bridge at a time. If another major gap emerges, expose the proposed route rather than silently starting an endless prerequisite chain.

Preserve the original lesson step and objective before entering a bridge. Completion returns to that anchor. Necessary assumptions remain explicit even if the learner chooses an overview.

### 7.3 Teaching plan and response contract

The planner proposes target objective, identified gap, known foundations, representation, depth, abstraction, examples, step size, derivation intent, source references, concepts to avoid, and next possible check. Deterministic policy validates scope and permissions.

The tutor generates structured blocks: paragraphs, equations, examples, diagrams, concept links, and claim references. Verification runs before consequential claims or check items are presented as approved. Check for unsupported jargon and accidental objective changes.

A useful default sequence is explanation → example where useful → response opportunity → targeted feedback. It is not a mandatory essay structure. Simple factual questions can receive a direct concise answer. Repeated confusion should trigger a different representation or a question locating the failing step.

### 7.4 Verification

Use inspected sources for factual claims, independent calculation for numerical examples, and suitable execution/symbolic checks only where implemented. Record the method and its limits. Do not claim a symbolic proof or code test was performed merely because a model described one.

Buffer content that requires whole-answer checking. Approved independent blocks may stream incrementally when the verification policy supports that. Partial interrupted output stays visibly incomplete and cannot become evidence.

If verification fails, repair within a bounded retry budget, narrow the claim, or return a clear limited result. Never skip verification to meet a latency target.

**Acceptance:** known foundations are not routinely retaught; missing foundations receive proportionate help; an incorrect example is repaired or withheld; a skipped check never becomes assumed mastery.

## 8. T3 — Understanding checks and learner state

Phase one needs small checks because adaptation depends on evidence. It does not need a complete exam engine.

### Check workflow

```text
Select objective → draft item and private rubric → validate answer/ambiguity
→ deliver prompt → collect response and assistance → evaluate
→ admit evidence → update learner projection → offer feedback
```

For arbitrary topics, runtime checks require validation; curated items alone cannot cover the product. Use reviewed reusable checks where available, and withhold unreliable generated checks. Keep expected answers and rubrics out of the learner payload before the appropriate feedback stage.

Capture response, task/objective version, assistance, recent answer exposure, correctness or rubric coverage, and interpretation uncertainty. A conversational claim can inform planning without qualifying as independent success. Immediately repeating a worked example does not establish transfer.

Only the learner module admits evidence. Validate scope, item status, duplicate identifiers, and assistance. Apply a versioned conservative update policy. Store evidence and the new projection transactionally. Several near-identical attempts should not masquerade as varied proof.

Initial labels should express observations, such as “demonstrated on this check,” rather than claiming broad latent mastery. A more sophisticated estimator is replaceable later. Store probability and uncertainty separately if an estimator is introduced; forgetting behavior is a separate explicit model choice.

Learner disagreement with a grade triggers review or clarification. Invalidated checks supersede their evidence and produce an explained recalculation.

**Acceptance:** reading alone cannot upgrade demonstrated understanding; assisted work is labeled; retries count once; unverified or ambiguous items do not change canonical mastery.

## 9. C1/C2 — Teaching controls

### 9.1 Persistent gear

| Gear | Intended behavior |
|---|---|
| Quick | Essential explanation, compact structure, only necessary bridges |
| Guided | Intuition, concrete example, manageable steps, optional understanding check |
| Deep | Mechanism, assumptions, derivation where appropriate, meaningful connections |

Gear does not lower the correctness floor or silently change the objective. Depth is distinct from abstraction and support. A learner may request Deep plus Simpler.

### 9.2 Contextual actions

| Action | Plan change | Output requirement |
|---|---|---|
| Simpler | Lower abstraction, define terms, reduce step size | Preserve meaning and important reasoning |
| Go deeper | Expand selected mechanism or assumption | Address the anchor without restarting the topic |
| Example | Add concrete illustration | Valid inputs, assumptions, and checked result |
| Why? | Explain selected justification | Answer the exact claim's reasoning |
| Visualize | Choose supported representation | Relevant, accurate, labeled, text-accessible |
| Check understanding | Create a validated small task | Preserve independent-response opportunity |

Implement a control resolver that compiles preset plus local overrides into a typed profile. Precedence: correctness/permissions → objective → explicit local request → gear defaults → inferred presentation preference.

### 9.3 Timing and persistence

- Changing gear affects the next response; the current generation retains its original profile.
- Provide an explicit “Apply to this explanation” action to regenerate existing content.
- An explicit replacement action supersedes in-progress work for that same passage. Late tokens from the canceled action are discarded.
- Keep prior explanation versions so branch anchors remain meaningful.
- Child branches inherit the resolved parent profile. Local branch overrides do not modify the main lesson.
- Repeated local requests may prompt a reversible preference change, not silently establish a permanent learner label.

### 9.4 Visualize implementation

Support a bounded set of diagrams, tables, number lines, and suitable plots. Generate a structured representation that a controlled renderer validates. Check numeric inputs and function domains for plots. Sanitize any markup; do not execute arbitrary model-generated browser code.

If a request needs a simulation or visual type not supported in phase one, explain the limitation and provide a useful text/table alternative. Decorative imagery does not satisfy a request to explain a relationship visually.

### 9.5 Verification of controls

Maintain paired examples for the same objective and learner state. Judge whether each control changes its intended dimension, retains correct content, and remains in scope. Test combinations, especially Deep + Simpler and branch-local overrides. Word count differences alone are not evidence that controls work.

**Acceptance:** controls produce observable instructional differences; changes apply at the documented time; old streams cannot overwrite new explanations; local requests do not unexpectedly alter session defaults.

## 10. W1/W2 — Contextual exploration windows

### 10.1 Interaction model

Use one resizable non-modal exploration panel beside the desktop lesson. Keep the main lesson readable and operable. Support saved sibling branches and nested breadcrumbs within that panel. Multiple simultaneous floating panes are not required for V1.

Proposed desktop starting split is approximately 60/40 within the learning area, respecting minimum text widths. Collapse secondary graph chrome before squeezing both reading areas. On narrow screens, use a focused exploration view retaining the quoted anchor, breadcrumb, and return action.

### 10.2 Anchoring

Support linked terms, arbitrary selected text, and selectable content blocks such as equations. Each branch stores source artifact ID/version, block ID, selected quote or block snapshot, optional range, parent branch ID, objective references, and return location.

Raw character offsets alone are insufficient after content regeneration. Use immutable artifact versions and snapshots. If an anchor has been superseded, show that status and offer the updated context without silently retargeting the original branch.

### 10.3 Context isolation

Build a branch context from the anchor, relevant parent summary, objective, sources, learner snapshot, and teaching profile. It does not receive unrestricted unrelated history. A branch can propose scoped evidence through the same admission path; it cannot directly edit the graph or learner state.

An unrelated tangent remains local unless the learner explicitly starts a new scope or requests graph expansion. New concepts do not appear in the primary graph simply because a branch mentions them.

### 10.4 Lifecycle

```text
CREATED → GENERATING → READY
             ↓           ↓
           FAILED      COLLAPSED → REOPENED
             ↓
           RETRY
```

Generation status and panel visibility should be separate fields. Closing cancels active generation and collapses the panel, retaining committed content. A canceled partial response is marked incomplete. Deletion is a separate explicit operation.

Back restores parent branch position and draft; closing restores the main selection and keyboard focus. Store panel scroll, lesson scroll/anchor, breadcrumb, and draft. Debounce draft persistence, with local recovery where appropriate; display saving failures honestly. Do not expose one user's locally cached content after account switching.

Reopening the same anchor should offer its existing branch by default, with a deliberate option for a separate question. Switching main topics displays that topic's branch collection while preserving previous branches under their original scope.

Optional return summaries should be short, grounded connections to the main lesson. They must not rewrite lesson history or award mastery.

### 10.5 Accessibility

Use a labeled non-modal region on desktop, with predictable focus movement and a return control. Do not trap focus while claiming the main lesson remains usable. If the small-screen presentation uses a modal, implement actual modal focus behavior and return focus on dismissal. Keyboard users need the same selection/explain path as pointer users.

**Acceptance:** main → branch → child → parent → main preserves each location; reload restores committed context; cancellation blocks stale mutations; an unrelated branch never silently changes the active curriculum.

## 11. Data contracts

### Core entities

| Entity | Key fields |
|---|---|
| TopicScope | Owner, request, resolved meaning, objective, depth, revision |
| GraphGenerationJob | Scope, stage, status, budget, attempts, cancellation |
| GraphVersion | Scope, parent revision, publication state, source/config references |
| Concept | Stable identity, meaning, cluster, objectives, source bindings |
| Edge | Endpoints, type, target objective, justification, support status |
| SourceReference | Origin, locator, inspected passage reference, revision, access metadata |
| LearnerConceptState | Owner/objective, observed state, uncertainty, evidence IDs, version |
| Session | Scope/version, current concept, lesson position, gear, revision |
| TeachingPlan | Objective, gap, strategy, resolved controls, sources, action ID |
| LessonArtifact | Immutable version, typed blocks, claims, verification, provenance |
| Branch | Parent, anchor snapshot, local profile, position, draft, visibility |
| UnderstandingCheck | Objective, private rubric, item version, validation |
| Evidence | Observation, assistance, item/rubric, interpretation, admission status |
| Action/Event | IDs, scope, correlation, schema version, state, timestamps |
| VerificationResult | Artifact/claim, method, supporting reference/tool result, outcome |
| Correction | Affected versions, report, resolution, superseded evidence |

### Illustrative action envelope

```json
{
  "schema_version": 1,
  "action_id": "action_123",
  "kind": "EXPLAIN_SELECTION",
  "session_id": "session_12",
  "branch_id": "branch_8",
  "expected_session_revision": 7,
  "graph_version_id": "graph_v3",
  "anchor": {
    "artifact_id": "lesson_9",
    "artifact_version": 2,
    "block_id": "block_4"
  },
  "local_request": "simpler",
  "idempotency_key": "request_456"
}
```

The server derives owner, permissions, policy, sources, and the resolved profile. Persist the configuration identifiers for prompts, models, policies, verifiers, and graph versions with each consequential artifact.

Use foreign keys and uniqueness constraints for identity and evidence deduplication. Keep UI layout separate from semantic state. Do not expose private rubric columns through generic entity serialization.

## 12. API and streaming design

Proposed routes are contracts to refine during implementation, not existing endpoints.

| Endpoint | Responsibility |
|---|---|
| `POST /v1/topic-scopes` | Resolve topic/goal and return scope or clarification |
| `POST /v1/topic-scopes/{id}/graph-jobs` | Generate or expand a scoped graph |
| `GET /v1/graph-jobs/{id}` | Job progress and failure state |
| `GET /v1/graphs/{id}` | Versioned bounded neighborhood |
| `POST /v1/sessions` | Create or resume authorized context |
| `POST /v1/commands` | Typed teaching, selection, control, and branch actions |
| `GET /v1/sessions/{id}` | Committed session/branch projection |
| `GET /v1/actions/{id}/events` | Authorized resumable progress/content stream |
| `POST /v1/actions/{id}/cancel` | Cancel future publication/state effects |
| `POST /v1/checks/{id}/responses` | Submit answer with attempt identity |
| `POST /v1/artifacts/{id}/reports` | Report a suspected content defect |

Use request validation, ownership checks, idempotency keys, stable error codes, and revision checks. Long jobs return an action/job ID instead of blocking indefinitely. Streams carry sequence numbers and artifact/action identity so reconnects can deduplicate and resume.

Possible errors include clarification required, source support insufficient, scope mismatch, revision conflict, validation failed, budget exceeded, and provider unavailable. Preserve input and committed progress. An HTTP success must not imply that verification passed if the job is still pending.

## 13. Models, tools, and workflow execution

One initial provider is sufficient, behind an adapter. Do not scatter vendor-specific SDK calls across domain modules. Normalize structured output, streaming, cancellation, usage, and errors while recording capability differences.

Separate task roles—scope resolver, graph proposer, teaching planner, tutor, and verifier—without requiring a different model or separate call for every role. Combine lightweight work where quality permits. Do not implement complex cost routing before basic quality is measured.

Persist workflow states such as pending, running, awaiting verification, completed, failed, and canceled. Use worker leases/heartbeats and bounded retries. Persist checkpoints between expensive stages. A retry resumes from a valid checkpoint and must not duplicate graph nodes or evidence.

Use an outbox or equivalent recoverable transaction boundary for state changes and event delivery. Consumers must tolerate repeated delivery. Revalidate scope/version before committing late results. Cancellation tokens reduce wasted work, while commit checks prevent stale mutation even if a provider cannot stop generation immediately.

Track the critical path: resolve scope → retrieve context → plan → generate → verify → publish. Parallelize only independent authorized reads/checks. Keep background graph expansion from exhausting interactive worker capacity. Define numerical latency and cost ceilings after measuring selected providers on the evaluation set.

## 14. Persistence, privacy, and operational reliability

Choose local single-user prototype or hosted multi-user pilot before implementation. A hosted pilot requires authenticated ownership checks on every record, source result, and stream. A local prototype should still avoid hard-coding a shared anonymous identity that later makes records inseparable.

Define retention for learner responses, drafts, source excerpts, and generation traces. Store only source material permitted by access/usage policy. Do not promise exact reproduction of nondeterministic model outputs; retain actual artifacts and configuration references.

Protect secrets server-side. Restrict retrieval and any executable verification. Sanitize rendered content. Logs should identify actions and failures without unnecessarily copying sensitive learner text. Test backup/restore for canonical state before relying on persistent pilot usage.

Cached drafts and source content must respect account changes and deletion. Immutable versioning is an audit technique, not an excuse to ignore deletion requirements. Define appropriate removal/supersession behavior for each data class.

## 15. Q1 — Quality gates and evaluation implementation

### 15.1 Fixtures and review tools

Create a versioned evaluation directory with topic requests, source packs, expected constraints, learner snapshots, control variants, branch sequences, and known failure cases. Save configuration IDs and results for each run. Keep evaluation-only answer material separate from live tutor context.

Proposed starting set: at least 30 topic/scope cases spanning mathematics, science, programming, history, and conceptual/humanities topics. Include broad/narrow scope, ambiguity, sparse sources, conflicts, and cross-domain labels. This is a regression sample, not certification of every possible subject.

For selected cases, compare beginner, known-foundation, and specific-gap profiles across Quick/Guided/Deep and contextual overrides. Review dependency reasons as well as factual definitions. Calibrated model judges may assist triage; domain review and deterministic checks remain necessary where available.

### 15.2 Release gates

| Gate | Proposed pilot criterion |
|---|---|
| Integrity | All critical ownership, deduplication, cancellation, and recovery scenarios pass |
| Graph structure | No broken references, invalid required-edge cycles, or silent history loss in the evaluated set |
| Correctness | Zero unresolved critical teaching errors or fabricated citations in reviewed release cases |
| Support labeling | Sampled consequential claims marked supported have actual relevant inspected evidence/tool checks |
| Teaching/controls | At least 90% of paired reviewed cases satisfy applicable behavioral criteria; no critical truth loss |
| Branch usability | Initial 5–8-person formative sessions complete open/nest/back/return after onboarding; repeated disorientation blocks expansion |
| Reliability | Defined reload, timeout, retry, and cancellation scenarios preserve committed state |

Thresholds are proposals to review against actual test quality. Report counts, denominators, domain-specific failures, exclusions, and reviewer disagreements. A zero-known-critical-error result does not prove zero real-world errors.

### 15.3 Required adversarial and failure scenarios

- A source attempts to instruct the system to ignore policy.
- A model invents a reference or misrepresents a passage.
- Graph expansion repeats an alias or creates a required-edge cycle.
- A learner changes concepts while a branch response is arriving.
- Simpler supersedes an explanation while the old stream continues.
- A duplicated answer request arrives after a network retry.
- A faulty check is corrected after evidence was admitted.
- A user closes a branch with an unsaved draft or an incomplete response.
- An unavailable source or model exhausts the allowed retry budget.
- Keyboard and small-screen navigation must return to the original context.

### 15.4 Learning effectiveness

Usability evaluation cannot prove improved learning. Separately design a comparison with a reasonable baseline, comparable starting knowledge and time, independent application tasks, and delayed follow-up. Determine sample size from the study design. Do not use the harness's own mastery estimate as primary proof of effectiveness.

Track context-reconstruction prompts, unnecessary detours, and learning time alongside independent performance. Fewer prompts are useful only if understanding is preserved or improved. Until evidence exists, describe the result as a pilot, not a validated superior tutor.

## 16. Implementation work packages

| Package | Build outputs | Dependency | Completion evidence |
|---|---|---|---|
| P0: design fixtures | Topic examples, source policy, gear examples, annotated branch wireframes | Audience/depth decisions | Reviewed examples and agreed expected behaviors |
| P1: state/contracts | Schemas, ownership, commands, revisions, jobs | Deployment choice | Integrity fixtures pass |
| P2: topic graphs | Resolver, retrieval, graph proposer, validators, expansion | P1 and source/tool choices | Representative supported maps and safe failure outcomes |
| P3: learning view | Canvas, outline, lesson selection, persisted position | P2 graph contract | Navigation/accessibility walkthrough |
| P4: teaching loop | Planner, prerequisite policy, tutor, verification, minimal checks | P1/P2 | Reviewed known/gap/unknown learner scenarios |
| P5: controls | Resolver, gear UI, contextual actions, visual renderer boundary | P4 | Paired control cases pass |
| P6: branches | Anchors, panel, nested path, drafts, cancellation, resumption | P3/P4 | Main-to-child-to-main recovery scenarios pass |
| P7: correction/recovery | Reporting, supersession, trace inspection, backup/retry checks | Prior packages | Fault injection and correction scenarios pass |
| P8: pilot gate | Full evaluation report and usability review | All required features | Explicit release decision with remaining risks |

Do not postpone quality work until P8: each package includes its own checks. Design graph and teaching contracts together. Avoid polishing a standalone graph visualization that the tutor cannot actually use.

## 17. Decisions remaining before application implementation

1. Initial learner audience and default depth, without restricting topic input to one discipline.
2. Local prototype versus hosted pilot, and the corresponding identity/persistence model.
3. Retrieval provider, source authority rules by domain, and permitted source storage.
4. Initial model/tool choices selected through representative trials.
5. Latency, retry, concurrency, and cost limits for graph and teaching actions.
6. Review of actual sample maps, paired teaching outputs, and desktop/mobile wireframes.
7. Final pilot criteria, reviewer responsibilities, and learning-study expectations.

The user has included these five feature areas in phase one. That does not mean every proposed numeric default, UI proportion, or implementation library has been separately validated. Resolve choices through concrete examples and measured trials rather than silently treating them as settled.

## 18. Reference basis and limitations

This is an implementation specification derived from the project discussion, not a fresh review of current library APIs or vendor pricing. Verify those details when selecting dependencies.

- Worked examples and retrieval activities inform the proposed teaching loop; they do not validate our exact product behavior: [IES learning practice guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/1).
- Modal focus restrictions inform the distinction between an interactive desktop side panel and a modal small-screen presentation: [W3C dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
- Confabulation and information-integrity concerns motivate explicit support and failure checks; project thresholds are our proposed gates: [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf).

No feature, quality threshold, or learning outcome is claimed to be implemented or passed by the existence of this document.
