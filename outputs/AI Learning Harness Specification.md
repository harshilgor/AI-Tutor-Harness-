# AI Learning Harness

## Product and Technical Specification

Version 0.1 | 11 September 2026 | Product definition and proposed implementation baseline

## 1 Executive summary

Build a learning environment that maintains an evidence-backed model of what a person knows, identifies the smallest useful next learning action, and teaches from that person's current knowledge frontier. The environment combines a bounded curriculum graph, persistent learner state, teaching policy, grounded tutoring, assessment, notes, and contextual branches in one workspace.

The primary outcome is durable, independently demonstrated understanding gained per unit of learning time. Reduce the work of repeatedly asking for simpler explanations, definitions, examples, and a return to the original topic. Preserve productive effort: recall, reasoning, prediction, problem solving, and transfer to unfamiliar situations.

The central design rule is that conversation history is not the source of truth. The curriculum defines the territory; assessment provides evidence; the learner-state service interprets that evidence; the planner chooses an action; and the tutor renders a lesson under those constraints. The graph is operational: it controls sequencing, prerequisite repair, review, and explanations of progress.

Start with one bounded, assessable course. Deliver a complete loop from course materials through diagnostic, prerequisite bridge, lesson, independent assessment, graph update, and later review. Keep the architecture modular without requiring every logical role to run as a separate model or service. Specific model vendors, deployment providers, commercial packaging, licensing, and performance thresholds remain decisions to validate.

## 2 Product intent and decision status

### 2.1 Established product direction

The product should accelerate learning and reduce prompting friction; expose known and unexplored territory; adapt explanations to learner knowledge; support inline contextual exploration without losing the parent lesson; connect personal notes to concepts; and offer a simple teaching control. The user's preferred interface integrates roadmap, map, and focus into a shared spatial system rather than three disconnected destinations.

The Codex analogy describes an environment around a model. A curriculum serves as a specification, the graph as structured working context, assessments as tests, verification tools as correctness checks, and learner state as persistent memory. This analogy is a product explanation, not an equivalence between educational understanding and passing software tests.

### 2.2 Working design proposals

Quick, Guided, and Deep teaching gears; semantic zoom; six logical roles; minimum prerequisite closure; probabilistic knowledge tracing; source and tool verification; event-driven orchestration; and a relational database with graph edges are working proposals developed in the discussion. The technical contracts and acceptance criteria below make those proposals reviewable. They are not claims that an implementation already exists.

### 2.3 Revisions preserved from the discussion

The initial three-view proposal evolved into a single canvas with semantic zoom. An initial five-role architecture evolved to six roles by separating the teaching planner from the tutor. Teaching from first principles became teaching only missing prerequisites. Multiple agreeing agents were rejected as sufficient proof of correctness. A simple percentage or an acknowledgement of understanding was replaced by evidence of independent performance and retention.

The discussion suggested varying verification effort with teaching gear. The implementation should retain a correctness floor across all gears: a shorter lesson must not receive weaker required checks. More complex content may trigger more verification regardless of gear. The original multiplicative next-action score is retained as an idea, with a more robust starting policy proposed in Section 8.

### 2.4 Scope and boundaries

The first product serves an individual learner studying a bounded course toward a stated goal. Candidate domains discussed include introductory finance, school mathematics, calculus, statistics, and introductory programming. Finance is the running illustration, not a selected launch market. Initially exclude universal curriculum coverage, training a foundation model, guaranteed misinformation elimination, institutional grade certification, and autonomous high-stakes advice.

## 3 Learner journeys and feature inventory

### 3.1 Begin a course

The learner supplies a goal, optionally an exam date, and course materials such as a syllabus, lecture slides, or textbook extracts. The system proposes a bounded curriculum and identifies missing or ambiguous source coverage. A short adaptive diagnostic seeds the learner overlay. The discussion suggested about ten minutes; this is a user experience hypothesis, not a required duration. Learners may skip diagnostics, in which case untested knowledge stays unknown.

Acceptance: the learner can inspect and edit scope, start without a long questionnaire, see why the proposed first concept was selected, and distinguish assessed knowledge from self-reported familiarity. Failed ingestion must leave usable uploaded files and a recoverable job status.

### 3.2 Learn from the frontier

A learner requesting DCF valuation may already know time value of money, discounting, and free cash flow but lack WACC and terminal value. The planner chooses a small missing prerequisite, teaches it, checks understanding, then resumes DCF. It does not restart from elementary definitions or assume all advanced terms are familiar.

Acceptance: the next action references a graph version and learner-state snapshot; known prerequisites are not routinely retaught; unresolved prerequisites produce a bridge, diagnostic, or explicit learner override. The return position survives refresh and navigation.

### 3.3 Explore without derailment

Selecting a term or sentence exposes Explain, Why, Example, Analogy, Prerequisites, and Go deeper. A contextual sidecar opens beside the relevant lesson. It already knows the selected passage, target concept, learner state, current goal, sources, and explanations already shown. Nested branches allow exploration from DCF to WACC, cost of equity, CAPM, and beta, then back to the original lesson.

Acceptance: opening and closing branches preserves lesson position and unsent work. A branch cannot silently change the parent goal. Multiple perspectives can be requested without creating inconsistent learner memories. Section 12 specifies concurrency and retention.

### 3.4 Demonstrate and retain understanding

The learner explains, solves, identifies when a concept applies, and transfers it to a new context. Later review checks retention. The graph answers what is known now, what may be forgotten, what is ready next, what blocks the goal, and what remains uncovered.

Acceptance: reading or clicking “I understand” does not mark mastery. A hinted answer is recorded as assisted. A delayed assessment can lower confidence in retained mastery without erasing the historical evidence.

### 3.5 Return before an exam

The home state summarizes strong topics, fragile topics, misconceptions, uncovered topics, review due, and the next useful action. Examples discussed included WACC, working-capital adjustments, APV, and bond valuation. “73 percent ready” and “three modules remaining” were illustrative interface copy. Production readiness estimates require a defined scope, coverage weights, uncertainty, and validation; they must not imply a calibrated probability of passing an exam.

## 4 Unified workspace and semantic zoom

### 4.1 Spatial information architecture

At far zoom, show subject clusters such as Finance, Corporate Finance, and Valuation. At medium zoom, expose the goal-relevant route and blockers. At close zoom, expand the active concept into its lesson, examples, assessment, notes, misconceptions, and branches. Zoom changes meaning and detail, not merely magnification.

The map is the shared context. A fixed left-map, center-lesson, right-sidecar layout was an early scaffold; the later direction uses anchored cards around concepts. Prototype this behavior before committing to unrestricted floating windows. Preserve stable placement and reading order so that the learner need not manage a visual desktop while studying.

### 4.2 Visible states

- Green with a check: demonstrated mastery under the current policy.
- Yellow with a partial-fill marker: developing or fragile understanding.
- Red with an alert marker: an active misconception supported by assessment evidence.
- Grey with an empty marker: unexplored or unassessed, with those meanings distinguished in details.
- Faded green with a review marker: previously demonstrated mastery with retention review due.
- A focus ring: the current concept, independent of its mastery state.
- A readiness marker: prerequisites satisfied and relevant to the goal.

Color must be redundant with labels, icons, fill, or border treatment. Screen-reader and keyboard users need a structured outline presenting the same concepts, relations, statuses, and actions. Mobile should use an anchored sheet and breadcrumb trail rather than tiny floating panels. Reduced motion must preserve navigation meaning.

### 4.3 Graph rendering brief

Load bounded neighborhoods and aggregate distant clusters. Persist concept positions separately from curriculum semantics. Avoid full relayout after every state update. Use stable concept IDs, viewport queries, virtualized cards, cancellation of obsolete requests, and a selected-node URL for restoration. Graph layout is presentation state and must not alter prerequisite relationships.

Acceptance: the learner can traverse all zoom levels without losing selection; keyboard focus returns to the originating term after closing a sidecar; all progress information is available outside the canvas; and large-course performance is measured against an agreed node and device budget. Determine those budgets during the UX prototype.

### 4.4 Purpose and progress

Every node should explain “Why am I learning this?” through prerequisites, downstream concepts it enables, and relevance to the learner's goal. WACC may enable DCF and company valuation; any numerical exam weighting must come from the syllabus or explicit user input. Show coverage separately from mastery. Do not imply that all nodes have equal educational weight.

## 5 Teaching gears and adaptive representations

### 5.1 One primary control

Expose Quick, Guided, and Deep. Quick offers concise explanation and a minimal useful example or check. Guided adapts support, usually with intuition and a concrete example. Deep offers derivation, multiple perspectives, connections, and transfer tasks when appropriate. Gear changes affect the current or next teaching action through an explicit interaction; they should not erase assessment work.

Internally, gear controls depth, abstraction, examples, derivations, scaffolding, questioning, connection density, and assessment scope. The original discussion proposed zero to one examples in Quick, one to two in Guided, and multiple in Deep; these are defaults, not inflexible quotas. First-principles detail should depend on actual gaps. Quick still defines necessary terms and meets verification policy.

### 5.2 Contextual adaptation

Provide Simpler, Go deeper, Example, Why, Show visually, and Test me beneath lesson content. Translate each click into a typed action rather than a new freeform prompt. Retain explicit preferences separately from inferred tendencies. Repeated Simpler signals may lower initial abstraction for that topic; a single click must not redefine the learner's general ability.

Representation options include formal explanation, visual intuition, an accessible elementary explanation, mathematical derivation, worked example, real-world analogy, counterexample, and common misconception. “Explain from another world” maps an unfamiliar idea into a familiar domain. Analogies need a statement of their limits so the mapping does not become a misconception.

### 5.3 Learning from preferences

Store topic-specific evidence that a sequence such as intuition, example, then equation is effective. Judge effectiveness through subsequent independent understanding and retention, alongside stated preference. Avoid permanent learning-style labels or claims to know how a person's brain works. Learners can inspect, reset, and override adaptation. Fade scaffolding when evidence supports independence.

Acceptance: a gear change produces observable differences without changing factual conclusions; user overrides win over inferred preferences; feedback records the lesson and strategy that prompted it; personalization can be disabled without losing notes or mastery evidence.

## 6 Curriculum graph and compiler

### 6.1 Graph semantics

The domain graph describes the course independently of a learner. Nodes represent assessable concepts or skills at a useful granularity. Edges distinguish requires, part of, related to, enables, and example of. Only the requires relation drives prerequisite closure. Hierarchy and conceptual association must not be mistaken for hard teaching dependencies.

Each concept contains a stable ID, course and version, title, aliases, definition, learning objectives, scope, prerequisite references, representations, known misconceptions, assessment blueprint, source references, review status, and optional goal weights. Prerequisites may depend on the objective: intuitive understanding of an options formula requires less background than deriving it.

### 6.2 Compilation pipeline

Ingest authorized materials; extract text and page or slide locations; identify course objectives; propose concepts and relations; normalize aliases and duplicates; attach supporting source spans; validate structure; and publish an approved graph version. The curriculum compiler may use models to propose structure, but generated relationships remain candidates until validated.

Checks include missing endpoints, self-links, duplicate IDs, cycles in hard prerequisites, disconnected required objectives, unsupported edges, overly broad concepts, and assessment coverage. Source order is a useful clue, not proof of dependency. Break legitimate mutually dependent topics into teachable stages rather than accepting an unresolvable prerequisite cycle.

### 6.3 Versioning and change

Pin active sessions to a curriculum version. Publish revisions with explicit old-to-new concept mappings. Preserve historical assessment references. A renamed concept can keep its ID; splitting one concept into several requires a migration rule that does not copy full mastery to every child. Learners should see relevant scope changes, and progress summaries should name the current course version.

Acceptance: a course can be rebuilt reproducibly from versioned sources and configuration; graph validation rejects cycles; an educator can correct an edge; and changes do not silently rewrite past attempts. A relational concepts and concept_edges model is sufficient for the proposed MVP; a dedicated graph database remains an alternative to benchmark when traversal demands justify it.

## 7 Learner state and three memory layers

### 7.1 Curriculum memory

This stores what exists in the bounded course, how concepts relate, and what evidence supports teaching them. It is shared course structure. It does not contain a learner's mastery.

### 7.2 Learner memory

Maintain one record per learner and concept with an estimated mastery probability, uncertainty or confidence descriptor, evidence count, independent successes, last assessed and last verified times, active misconceptions, retention estimate, review due time, exposure history, and state-policy version. Store preferred representation evidence and explicit settings separately from mastery.

Unknown is not zero mastery. Self-report is not an independent assessment. A high estimated probability supported by one weak item is not equivalent to a well-supported estimate. Confidence labels should reflect evidence quality and calibration; do not display spurious precision such as 94 percent confidence without a defined interpretation.

Only the learner-state service writes canonical mastery and misconception state. Tutor, assessor, and verifier produce observations or proposals. State changes reference accepted evidence and can be reconstructed. Corrections invalidate evidence through an audit event rather than silently editing history.

### 7.3 Session memory

Persist the immediate goal, current concept, lesson block, branch path, original return anchor, active confusion, teaching gear, unfinished response, and compact context summary. A DCF session can retain “Step 3, WACC, why market-value weights, confusion about book versus market value” without sending its entire transcript to every model.

Closing a sidecar removes it from active context. Retain useful summaries, notes, and evidence according to a transparent retention policy; closing is not automatically a destructive deletion of the transcript. Explicit deletion must propagate through stored content and derived indexes as specified in Section 18.

### 7.4 Context assembly

Build a bounded context package containing the goal, target objective, relevant graph neighborhood, learner snapshot, active misconceptions, preferences, source pack, current lesson excerpt, and recent relevant actions. Set token budgets per component. When compressing context, preserve identifiers, unresolved questions, evidence pointers, and the return anchor. Never let a narrative summary override canonical state.

## 8 Minimum prerequisite closure and teaching planner

### 8.1 Closure algorithm

Given a target objective and graph version, walk backward over applicable hard prerequisite edges. Classify each prerequisite as sufficiently supported, uncertain, weak, or actively misconceived using current learner evidence. Continue through missing prerequisites until reaching a teachable frontier. Return an ordered repair plan and the saved target continuation.

“Minimum” means the smallest justified bridge within the chosen graph and policy, not a mathematically optimal global curriculum. Alternative prerequisites, diagnostic costs, and uncertain mastery make this a decision problem. Limit traversal depth and bridge time, detect cycles, and explain when a target requires a larger learning path than expected.

A sample Black-Scholes request in the discussion assumed options, normal distributions, and volatility were sufficiently known while continuous compounding was weak. The proposed bridge was a three-minute compounding lesson, then a check and return. These probabilities and duration were illustrative; actual prerequisites depend on whether the objective is intuition, application, or derivation.

### 8.2 Handling uncertainty and learner control

If state is unknown, choose a low-cost diagnostic or brief explanation based on the cost of assuming incorrectly. Do not test every ancestor. Learners may skip a bridge; record the override, keep the prerequisite unresolved, and adapt the target lesson accordingly. If the bridge reveals deeper gaps, replan with an explicit explanation and maintain the return anchor.

### 8.3 Choosing the next action

Candidate actions include teach, review, assess, remediate a misconception, open a bridge, present another representation, and resume the parent. The discussion proposed expected learning gain multiplied by goal relevance, unlock value, and forgetting risk, divided by expected time. Treat that as an intuitive prioritization sketch: a zero forgetting-risk factor could otherwise suppress every new concept.

A proposed MVP policy first filters actions for prerequisite readiness, then combines normalized expected gain, goal relevance, downstream unlock value, review urgency, and misconception importance with configurable weights, divided by estimated duration with a positive floor. Keep review urgency distinct from learning new material. Begin with transparent heuristics and log why an action wins. Learn better estimates only after collecting suitable outcome data.

### 8.4 Planner contract

Input: goal ID, curriculum version, learner-state version, session anchor, gear, time budget, candidate concepts, and evidence availability. Output: target objective, action type, missing prerequisites, strategy sequence, allowed concepts, concepts to avoid, representation, support level, source requirements, assessment intent, expected duration, and return anchor.

For the WACC example, the plan may target market versus book value, use intuition then one company example then a transfer question, and explicitly avoid reteaching CAPM or introducing enterprise value. The tutor has not generated prose at this stage.

Acceptance: the same versioned inputs and deterministic policy produce an explainable action; missing evidence prevents unsupported mastery assumptions; the learner can override the recommendation; and a successful bridge returns to the saved target without reentering context manually.

## 9 Tutor contracts and output validation

### 9.1 Prompt composition

Construct tutor instructions from a stable role contract plus the plan and evidence package. Tell the tutor to teach the specified objective, respect the learner's demonstrated prerequisites, use the selected strategy, define unfamiliar terms, avoid out-of-scope derivations, and return structured content. Treat uploaded text and notes as quoted data, never as system instructions.

A representative Guided prompt asks for intuition, one example, no CAPM derivation, source-backed claims, and one diagnostic question. The discussion used a 180-word limit as an example. Choose content budgets by action rather than imposing a global length rule. An advanced derivation may require multiple staged blocks.

### 9.2 Structured response

Return content blocks with stable IDs and types such as explanation, example, equation, visual specification, question, and source reference. Include concepts used, new concepts introduced, claim records, source or tool evidence IDs, and an assessment proposal. Each selected term has a concept ID and a stable block anchor for sidecars.

Validate schema and permitted block types before display. Check referenced concepts and sources exist. Scan for newly introduced prerequisites. If the tutor introduces opportunity cost of capital to a learner who has not encountered it, either define it inline, use simpler language, or offer an appropriately labeled branch. Merely making a blocking term clickable is insufficient when understanding the main lesson depends on it.

### 9.3 Active teaching

Prefer short explanation, example, learner reasoning, and feedback cycles. Do not expose a worked answer while claiming to assess independent recall. Maintain multiple representations of a concept, but validate that every variant preserves its assumptions and conclusion. Visual content must receive the same correctness review as prose, including labels and units.

Acceptance: malformed output never becomes broken UI; unsupported source IDs are rejected; a new blocking term triggers repair; an assessment question has a separate answer key; and all displayed claims retain their verification status.

## 10 Assessor and mastery evidence

### 10.1 Assessment blueprint

For each objective define observable evidence: explain in one's own words, solve a problem, discriminate between applicable and inapplicable cases, identify a misconception, or transfer knowledge to an unfamiliar context. Include delayed tasks to assess retention. The discussion's CAPM example moves from explanation through calculation and recognition to later use inside WACC.

Generate or select items independently of the just-shown worked example. Store item version, targeted concepts, difficulty estimate, answer key or rubric, source references, and verification result. Separate learner-facing question text from private grading material. Verify generated answer keys before using items to update state.

### 10.2 Attempt evidence

Capture response, correctness or rubric dimensions, assistance level, hints, retries, time, item exposure, misconception candidates, grader confidence, and verification artifacts. Timing is contextual evidence, not a proxy for ability. A wrong answer may reflect ambiguous wording or arithmetic rather than a conceptual misconception.

For numeric and code tasks, use deterministic checking when feasible. For open responses, use a rubric and evidence excerpts; route uncertain or consequential judgments to another method or review. A learner can challenge a grade. Confirmed grader error invalidates affected evidence and triggers recomputation.

### 10.3 Mastery transition policy

Require sufficient independent evidence across distinct items before labeling demonstrated mastery. Include transfer and delayed evidence when claiming durable mastery. Thresholds, required item diversity, and minimum counts are proposed policy parameters to calibrate. Acknowledgement, reading time, copied notes, and exact repetition of a worked answer cannot independently establish mastery.

Acceptance: hints reduce or disqualify independence evidence; duplicate attempts do not double-count; rejected or unverified items do not update mastery; and the learner can inspect a concise explanation of why a concept changed state.

## 11 Knowledge tracing and retention

### 11.1 Interpretable baseline

Use a probabilistic baseline before considering a learned sequence model. A Bayesian Knowledge Tracing style model estimates latent knowledge from responses using prior knowledge, guessing, slipping, and learning-transition parameters. It is a model of evidence, not direct access to understanding. Parameter fitting, item validity, and evaluation are essential.

For a prior p, slip s, and guess g, the posterior after a correct response is p times (1 minus s), divided by p times (1 minus s) plus (1 minus p) times g. After an incorrect response it is p times s, divided by p times s plus (1 minus p) times (1 minus g). A learning transition t can then update posterior q to q plus (1 minus q) times t. Keep parameters bounded and handle numerical extremes.

These equations describe a simple binary single-skill baseline. The parameterization follows Corbett and Anderson's knowledge-tracing formulation, with a primary-paper copy available at https://perso.liris.cnrs.fr/pierre-antoine.champin/2014/m2iade-ia2/_static/893CorbettAnderson1995.pdf. Partial credit, assisted attempts, multi-skill items, and misconception diagnosis need explicit policies or richer models. Do not attribute an incorrect multi-step DCF response equally to every prerequisite. Avoid double-counting highly correlated retries.

### 11.2 Forgetting and uncertainty

Classic simple BKT does not automatically model elapsed-time forgetting. Add an explicit retention model or review policy, versioned separately, and validate it against delayed performance. Distinguish historical demonstrated mastery from estimated current retention. A due-for-review marker can be used before a reliable decay probability is available.

### 11.3 Future modeling

Compare the baseline with logistic, recurrent, or transformer knowledge-tracing approaches only when data quality and volume support a fair evaluation. The relevant prediction is success on an independent future task, especially transfer and delayed retention. Evaluate calibration and subgroup errors, not only ranking accuracy. Keep state transitions auditable even if a learned model later replaces the baseline.

## 12 Inline branches sidecars and notes

### 12.1 Branch contract

A branch stores its ID, parent branch or lesson ID, selected block and text span, source content version, target concepts, intent, return anchor, learner-state snapshot, source pack, compact summary, and status. The selected text must remain resolvable even if a newer lesson version exists. If it cannot be resolved, show the historical passage rather than attaching to the wrong sentence.

Nested branches form a session tree, distinct from curriculum prerequisites. Set a configurable depth and simultaneous-generation budget. A learner may explore several perspectives, but the interface should prioritize one active reading surface. An analogy branch and a derivation branch share canonical state and source policy, not their full private conversations.

### 12.2 Merge and return

On collapse, summarize unresolved questions, useful explanations, saved notes, and assessment evidence. Only validated assessment evidence can propose mastery changes. A branch summary may inform future explanation selection but cannot certify understanding. Parent lesson position and draft answer remain intact. Reopening retrieves the relevant branch history under the retention policy.

Acceptance: concurrent branch results cannot overwrite newer learner state; closing a branch cancels unnecessary generation; summaries retain source pointers; and returning to a parent requires no manual “go back to what we were doing” prompt.

### 12.3 Concept-linked notes

Notes attach to one or more concepts and optionally a lesson block, selected source span, or branch. Support user-authored notes, one-click Save to notes from AI material, editing, backlinks, search, and portable export. Label AI-generated notes and preserve source provenance. A personal paraphrase is useful memory material, not a verified source by default.

The intended loop is learn, ask, save a note, demonstrate understanding, update the graph, and use relevant notes in future teaching. Retrieve notes as personal context, with conflicts against verified sources surfaced. Never silently rewrite a user's note. Suggested corrections should be reviewable.

Acceptance: notes survive course navigation and refresh; source links remain traceable after version changes; export includes concept IDs and citations; deletion removes retrieval copies; and saving a note does not increase mastery.

## 13 Evidence and verification architecture

### 13.1 Verification by claim type

Use source grounding for factual material; calculation and symbolic checks for mathematics; isolated execution and tests for code; structured references plus calculations for suitable scientific content; and current-source retrieval for changing facts. For contested interpretations, preserve competing views and uncertainty. Independent tool or source evidence is stronger than model agreement alone.

Course materials have priority for course scope, notation, and expected conventions. This does not make an erroneous slide universally authoritative. A conflict between course convention and external evidence should be shown and resolved explicitly. Source quality, age, authority, and relevance must be recorded separately.

### 13.2 Evidence objects

A source document has an immutable version, content hash, origin, access rights, extraction status, and locator scheme. A source chunk carries page, slide, section, or timestamp plus exact span. A claim links a lesson block to supporting, contradicting, or contextual evidence. A tool artifact records inputs, environment or engine version, outputs, and checker result.

Verification results should distinguish source-supported, tool-checked, qualified interpretation, unresolved, and rejected. “Verified” must name what was checked: a correct calculation does not validate every assumption in the surrounding explanation. Citation existence is not citation entailment. Track claim coverage and evidence relevance.

### 13.3 Delivery gate

Classify claims, retrieve evidence, generate content, run applicable checks, repair failures within a bounded budget, then publish approved blocks. Essential unresolved claims require a qualified response or a narrower explanation. Never invent citations when retrieval fails. Stream progress or already-cleared blocks; do not stream unchecked substantive claims and later call the entire lesson verified.

For a discovered post-publication error, version the correction, mark affected lessons and items, notify learners who received materially wrong teaching, invalidate contaminated assessment evidence where warranted, and recompute affected state. Preserve an audit trail.

### 13.4 Evidence quality and ingestion

Validate extraction quality, particularly equations, tables, and diagrams. Preserve original pages for inspection. Enforce source access controls at retrieval time, not just upload. Record conflicts and missing coverage rather than treating a full vector-search result set as a complete curriculum. Citation display should let the learner reach the exact supporting location.

Acceptance: fabricated citations fail validation; failed calculations block the relevant block; code runs without production credentials in an isolated environment; contradictory sources remain visible; and a source withdrawal identifies downstream content that depended on it.

## 14 System architecture and role boundaries

### 14.1 Proposed architecture

Client workspace sends typed actions to an authenticated orchestration API. The orchestrator loads curriculum, learner state, session context, and source evidence; requests a teaching plan; calls the tutor; gates content through verification; and returns structured blocks. Assessment responses go to the assessor, then accepted evidence goes to the learner-state service. Committed state emits graph and review updates.

The proposed initial implementation has a web client, a modular backend, a background job worker, a relational database, object storage, a vector index, and an event outbox. Modules can share a deployment initially. Independent services are justified by scaling or isolation requirements, not by the number of logical agents.

### 14.2 Logical roles

- Curriculum compiler: proposes and validates the domain graph from bounded materials.
- Teaching planner: selects what to do next and specifies instructional strategy.
- Tutor: generates lesson content under the plan and evidence constraints.
- Assessor: generates or selects valid tasks and evaluates learner responses.
- Verifier: checks claims, answer keys, calculations, and executable artifacts.
- Learner model: interprets accepted evidence and updates canonical state.

The orchestrator coordinates these roles and enforces budgets, transitions, authorization, and cancellation. The learner model can initially be ordinary deterministic and probabilistic code rather than an LLM. Logical agents need not have separate vendors or perpetual conversational memory.

### 14.3 Event-driven invocation

An explanation request invokes planning as needed, tutoring, and applicable verification. Finishing a lesson can invoke assessment and then state update. Building a roadmap invokes compilation and validation; learner overlay initialization follows without asserting mastery. A note save normally needs no model. Independent evidence retrieval and tool checks may run concurrently, but canonical state writes remain serialized or version-checked.

Do not use an unbounded verifier-of-verifier chain. Set a finite repair count, deadline, and spend budget. Escalate uncertain judgments to a stronger method or explicit uncertainty, not simply more agreeing agents.

## 15 Orchestration lifecycle and reliability

### 15.1 Teaching state machine

RECEIVED proceeds to AUTHORIZED, CONTEXT_READY, PLANNED, GENERATED, VERIFIED, and DELIVERED. A generation or verification failure may enter REPAIRING and retry within limits. Terminal states include CANCELLED, FAILED, and QUALIFIED_RESPONSE. Persist the run ID and current transition so a refresh or worker restart can resume safely.

### 15.2 Assessment state machine

ITEM_VALIDATED proceeds to PRESENTED, ATTEMPT_RECEIVED, GRADED, EVIDENCE_ACCEPTED, STATE_COMMITTED, and REVIEW_UPDATED. Invalid or disputed evidence enters REVIEW_REQUIRED. The grader cannot bypass the evidence gate. The UI must not show final mastery until the canonical commit succeeds.

### 15.3 Consistency and replay

Use idempotency keys on commands and unique attempt IDs on evidence. Commit learner-state changes and an outbox event in one transaction. Consumers deduplicate event IDs. Per-learner and concept sequence numbers or optimistic versions detect concurrent updates. Retry from the latest snapshot when needed; do not apply an old proposed mastery value over a newer state.

Capture graph, prompt, model, rubric, source, and mastery-policy versions. Replaying an event should reproduce state calculation from stored grading evidence; it should not rerun a nondeterministic model and pretend the output is identical. Regrading is a new versioned operation.

### 15.4 Failure behavior

On provider timeout, resume from a checkpoint or use an eligible fallback within the remaining budget. On retrieval failure, narrow the answer or explain the evidence gap. On invalid tutor JSON, attempt bounded repair. On a state-write failure, retain the attempt and show progress as pending. On cancellation, discard obsolete generation but retain explicitly saved notes and committed evidence.

Acceptance: duplicate delivery cannot double-count mastery; crash recovery does not lose submitted attempts; late sidecar results cannot replace the active lesson; and all terminal states provide a useful user-facing outcome.

## 16 Data model

### 16.1 Identity and curriculum records

users and workspaces define ownership. courses store scope and goal context. curriculum_versions record publication and source snapshots. concepts contain stable identity and objective metadata. concept_edges contain relation type, endpoints, applicability, provenance, and review status. goals link learners to scoped objectives, deadlines, and explicit importance weights.

### 16.2 Learning and session records

learner_concept_states are keyed by learner, concept, and relevant policy or curriculum identity; include state version, probability estimate, evidence summary, misconception state, and review fields. learner_preferences separate explicit settings from inferred strategy evidence. sessions store the goal and continuation. lessons and lesson_blocks store approved content and versions. branches store the parent tree and return anchors.

### 16.3 Evidence and knowledge records

assessment_items store objective mappings, rubric, private key, and validation status. assessment_attempts store the learner response, assistance, item version, and status. assessment_evidence stores accepted observations with grading provenance. sources and source_chunks preserve exact references. claims, claim_evidence_links, verification_runs, and tool_artifacts form the correctness audit trail. notes and note_concept_links preserve personal knowledge.

### 16.4 Operations records

learning_events form the immutable logical history subject to privacy deletion policy. orchestration_runs record states and budgets. model_calls record route, model version, tokens, latency, and outcome without logging unnecessary personal text. outbox_events support reliable delivery. review_schedule stores due actions and the policy that produced them.

### 16.5 Constraints and indexes

Enforce foreign keys, tenant ownership, unique event and attempt IDs, and probability bounds. Index learner plus concept, course plus graph version, branch parent, review due time, and source hash. Restrict access to answer keys. Store large files and tool output in object storage with database references. Treat vectors and summaries as rebuildable derived data, with tenant and source filters applied during retrieval.

Do not place raw transcripts in a single evolving learner-profile field. Keep immutable observations distinct from mutable projections so errors can be corrected without losing provenance.

## 17 API and event contracts

### 17.1 Proposed API surface

- POST /v1/courses creates a scoped course; POST /v1/courses/{id}/sources registers uploads and returns an ingestion job.
- POST /v1/courses/{id}/compile proposes a curriculum version; POST /v1/curricula/{id}/publish publishes a validated version.
- GET /v1/courses/{id}/graph accepts version, focus, and depth parameters and returns a bounded graph plus learner overlay.
- POST /v1/sessions creates a goal-bound session; POST /v1/sessions/{id}/actions accepts teach, simplify, example, assess, review, or resume intent.
- POST /v1/branches creates a sidecar from a versioned block anchor; PATCH /v1/branches/{id} collapses or updates it.
- POST /v1/attempts submits an assessment response; GET /v1/attempts/{id} reports grading and commit status.
- GET /v1/learner/concepts/{id} returns canonical state and evidence summary; it does not expose a client-writable mastery field.
- POST and PATCH /v1/notes save or edit concept-linked notes; GET /v1/exports returns a requested portable export job.

### 17.2 Shared command fields

Commands include request_id, idempotency_key, session_id where applicable, expected_state_version, curriculum_version, and typed payload. Identity is derived from the authenticated session, not trusted from a learner_id supplied in JSON. Return a run_id and pending status for longer actions, with an event stream or polling endpoint. Use explicit conflict, invalid-input, unauthorized, evidence-unavailable, and budget-exceeded errors.

### 17.3 Example teaching action

An action specifies intent “explain_why”, concept “market_value_weights”, parent lesson and block IDs, the selected text range, gear “guided”, curriculum version, and expected learner-state version. The server resolves the actual passage and authorized source pack. The response contains a run ID followed by approved lesson blocks, evidence status, branch context, and a proposed next action.

### 17.4 Event envelope

Every event carries event_id, event_type, schema_version, occurred_at, aggregate_id, aggregate_version, correlation_id, causation_id, authenticated ownership metadata, and a typed payload. Useful events include SourceIngested, CurriculumPublished, TeachingActionPlanned, LessonVerified, BranchOpened, BranchCollapsed, NoteSaved, AttemptSubmitted, AssessmentGraded, EvidenceAccepted, LearnerStateUpdated, ReviewScheduled, and VerificationFailed.

An AssessmentGraded event records attempt ID, item and rubric versions, target concepts, result, assistance, and evidence references. LearnerStateUpdated records old and new projection versions and accepted evidence IDs. Avoid sending raw student responses on broadly subscribed analytics topics.

### 17.5 Streaming contract

Use ordered event sequence numbers and resumable cursors. Separate progress events from approved content. A reconnect receives missing events without repeating side effects. Include completed, failed, and cancelled markers. The UI reconciles versions before applying state changes, and ignores content for cancelled or superseded runs.

## 18 Privacy security and operational boundaries

Apply per-user or tenant authorization to courses, notes, attempts, sources, vectors, exports, and tool artifacts. Minimize model context and redact sensitive content from operational logs. Uploaded documents can contain malicious instructions; parsing and retrieval must treat them as data. Tools require allowlisted capabilities and must not receive unnecessary credentials.

For execution-based verification, use time and resource limits, network restrictions, isolated filesystems, and no production secrets. Validate structured visual or code outputs before rendering. Do not execute arbitrary HTML or script embedded in a lesson in the application origin.

Define retention for transcripts, source files, attempts, derived embeddings, and analytics before launch. Export and deletion must cover derived copies and backup expiry rules. Explain which data supports personalization and whether any data may be used for model improvement. Training reuse should be a separate explicit decision. Determine age range, regional obligations, institutional requirements, and content rights with appropriate review before expanding to minors or institutions.

## 19 Model routing latency and cost

### 19.1 Route by task

Use deterministic code for graph checks, state updates, idempotency, and simple numeric validation. Consider a lower-cost capable model for intent classification, summaries, and straightforward grounded transformations. Use a stronger reasoning route for ambiguous prerequisite planning, difficult explanations, complex grading, or source conflict. Verification often needs retrieval or a tool rather than a larger language model.

No exact provider, model name, price, or quality ranking is selected here. Evaluate candidates on the course benchmark at implementation time. A model registry should record capabilities, supported schemas, context limits, measured quality, latency, cost, and data-handling eligibility.

### 19.2 Router contract

Inputs include role, task difficulty, evidence availability, risk category, required tools, context size, budget remaining, and latency deadline. Output includes model route, verification requirements, timeout, retry allowance, and eligible fallback. Log route reason and measured outcome. A cheaper fallback must meet the same minimum correctness and privacy conditions; otherwise return a qualified result.

### 19.3 Cost controls

Cache source extraction, stable graph neighborhoods, and approved reusable explanations by content, graph, prompt, and model version. Keep personalized material isolated by learner and relevant state version. Avoid running six roles on every request. Parallelize only independent work. Bound nested sidecars, context size, retries, and generated lesson length. Batch offline compilation and item validation where appropriate.

Measure cost per successful learning loop and retained mastered concept, not only per response. More inexpensive answers can cost more if they cause confusion and repeated prompts. Track the sum of input and output token costs, retrieval, tool execution, storage, and repair calls. Use measured prices at the time of planning rather than fixed assumptions.

### 19.4 Latency design

Show action acknowledgement immediately, then meaningful progress. Deliver approved blocks incrementally when safe. Keep heavy graph compilation and source ingestion asynchronous. Define latency objectives separately for simple explanation, verified calculation, assessment, and compilation after a pilot benchmark. Track median and tail latency, cancellation, and time to first useful verified content.

## 20 Metrics and experimental validation

### 20.1 Primary learning outcome

Measure independently demonstrated mastery gain per active learning minute, with delayed retention as a companion outcome. Use held-out tasks and a predeclared objective set. Self-estimated mastery changes alone cannot validate the product because the system controls both teaching and scoring.

### 20.2 Friction and experience

Track manual pedagogy corrections per independently mastered concept, repeated requests for definitions or examples, time to resume after a branch, abandoned bridges, session completion, and learner control satisfaction. Separate corrective “simpler” clicks from intentional deeper exploration. A reduction in messages is beneficial only when learning outcomes are maintained or improved.

### 20.3 Correctness and calibration

Measure material teaching-error rate on reviewed samples, unsupported-claim rate, citation entailment, tool-check coverage, false mastery labels, grading agreement against expert rubrics, and calibration of predicted independent success. Report sample sizes and uncertainty. Zero observed errors in a sample is not a guarantee of zero misinformation.

### 20.4 Operational measures

Track verified-content latency, model and tool failure rates, duplicate event handling, state-commit lag, cost per completed loop, repair rate, ingestion success, and graph-validation failures. Segment results by concept, difficulty, gear, assistance, and route while protecting privacy.

### 20.5 Evaluation plan

Build an expert-reviewed benchmark for the chosen course: concepts, prerequisites, source-grounded lessons, assessment items, misconception cases, and transfer questions. Compare the harness with a baseline tutoring conversation under the same material and time conditions. Hold out assessment items and avoid leakage from practice examples. Randomize or counterbalance where feasible and use delayed follow-up.

Evaluate ablations for structured learner state, prerequisite repair, sidecars, and adaptation to determine which components help. Test the model router separately against a stronger-route baseline. Set numerical success thresholds before the pilot based on feasibility and acceptable error, rather than choosing thresholds after seeing results.

## 21 MVP sequencing and release gates

### 21.1 Stage 0 Define the pilot

Choose one audience, course, goal, source set, and assessment standard. Secure usable material rights and prepare a reviewed graph and item set. Decide how correctness failures are handled. Exit when course scope and evaluation protocol are concrete enough to test a complete learning loop.

### 21.2 Stage 1 Build the state and evidence foundation

Implement source ingestion, versioned concepts and edges, learner state, item and attempt storage, verification records, and the event outbox. Use a curated graph before automating arbitrary compilation. Exit when an accepted attempt updates state exactly once and can be replayed, challenged, and corrected.

### 21.3 Stage 2 Complete one learning loop

Implement diagnostics, prerequisite closure, a transparent planner, grounded tutor blocks, verified assessment, and a review-due policy. Provide a simple graph neighborhood and lesson surface. Exit when a learner can bridge a gap, resume the parent, demonstrate independent understanding, and see an evidence-backed state change.

### 21.4 Stage 3 Reduce interface friction

Add one-level sidecars, saved return anchors, teaching gear, reaction controls, and concept-linked notes. Prototype semantic zoom with curriculum, route, and lesson detail. Exit when the learner completes representative tasks without reexplaining context and when keyboard and mobile paths work.

### 21.5 Stage 4 Validate learning and economics

Run the bounded pilot and delayed assessments. Evaluate grading, factual errors, friction, latency, and cost. Add routing only where benchmark evidence supports it. Exit when predeclared learning and correctness gates pass and failures have a defined correction process.

### 21.6 Later expansion

Expand nested branches, multiple simultaneous perspectives, automated curriculum compilation, richer retention modeling, cross-course concept mapping, and learned strategy selection. Consider institutional features, collaboration, integrations, and advanced graph storage only after demonstrated demand. Do not let a sophisticated canvas postpone the complete assessment loop.

## 22 Risks and alternatives

Incorrect tutoring can propagate into notes and mastery evidence; mitigate through typed verification, source provenance, correction propagation, and reviewed assessment keys. Incorrect prerequisite graphs can block capable learners or overwhelm beginners; mitigate with objective-specific edges, diagnostics, and overrides.

False mastery can create misplaced confidence; require independent evidence, show uncertainty, and evaluate delayed transfer. Excessive remediation can feel patronizing; bound bridges and allow informed skipping. Preference adaptation can overfit; keep user control and measure outcomes rather than inferring fixed learning styles.

A dense canvas can increase cognitive load; use semantic aggregation, stable layout, and accessible outlines. Multiple agents can add latency and correlated errors; use role-based invocation, finite budgets, and independent evidence. Source ingestion can distort equations; retain original locators and flag low-quality extraction. Longitudinal data can become sensitive; minimize collection and make export and deletion real product capabilities.

Alternatives considered include a single long-chat tutor, separate roadmap and map tabs, a dedicated graph database from day one, unrestricted agent conversations, and early custom knowledge-tracing training. Each can be useful in some circumstances, but the proposed baseline favors structured state, a shared workspace, relational storage, bounded orchestration, and interpretable mastery rules until evidence justifies added complexity.

## 23 Commercial strategy and defensibility

Open source, closed source, and open core remain unresolved. An open approach could expose schemas, orchestration, adapters, and evaluation tools while building trust and portability. A closed service could focus on managed reliability, course quality, and convenience. An open-core approach needs a clear boundary that does not trap learners' notes or evidence.

The discussion identified the longitudinal learner model, effective teaching policy, prerequisite repair, and mastery evidence as potential differentiators. Treat defensibility as a hypothesis. A graph visualization or prompt collection alone is unlikely to establish durable differentiation. Claims that an algorithm is protectable intellectual property require separate review; no patentability or exclusivity is asserted here.

Compare business options using adoption, trust, distribution, support cost, source licensing, data portability, and measurable learning advantage. Private learner data should not be treated as a moat that overrides user rights. Decide monetization after measuring actual inference and support costs for the intended audience.

## 24 Open questions and next brainstorming roadmap

### 24.1 Product and audience workshop

Choose the first learner group, domain, goal horizon, and definition of success. Decide whether the initial product is exam preparation, conceptual learning, or ongoing professional development. Deliver a one-page pilot brief and a bounded course inventory.

### 24.2 Interface workshop

Design the semantic zoom transitions, card placement, branch navigation, notes interaction, gear behavior, progress language, mobile layout, and accessible alternative. Deliver an interactive prototype covering one diagnostic-to-review journey. Resolve how much spatial freedom helps rather than distracts.

### 24.3 Orchestration workshop

Specify state machines, role contracts, context budgets, cancellation, retries, concurrency, and state ownership. Deliver sequence diagrams and failure scenarios for teach, branch, assess, and correct-error flows. Decide which modules share a deployment.

### 24.4 Models and economics workshop

Benchmark candidate planner, tutor, grader, and extraction routes. Measure quality, latency, and cost on the same tasks; define escalation and fallback policy. Deliver a routing matrix and cost model with current verified provider inputs. Select exact models only after that comparison.

### 24.5 Graph evidence and mastery workshop

Define concept granularity, edge validation, curriculum migration, source conflict handling, item quality, mastery thresholds, review policy, and assessment challenges. Deliver versioned schemas, an annotated course graph, and an expert-reviewed test set.

### 24.6 Ownership and launch workshop

Compare open, closed, and open-core options; decide hosting, data portability, course rights, and support expectations. Deliver a decision record, MVP backlog, release gates, and owners. Only then turn the specification into an implementation schedule and budget.

## 25 Discussion coverage register

The initial vision of a Codex-like environment, reduced prompting, and persistent knowledge state is covered in Sections 1 to 3. The two graphs, known and unexplored territory, and operational progress are covered in Sections 4, 6, and 7. First-principles teaching refined into minimum prerequisite closure is covered in Section 8.

Popup chats, selected text context, nested branches, multiple perspectives, and lossless return are covered in Sections 3 and 12. Teaching knobs, reactions, preference adaptation, and alternative representations are covered in Section 5. The shift from three views and rigid columns toward a zoomable shared canvas is covered in Section 4.

The three memory layers, compact structured context, planner prompt, structured tutor output, jargon repair, and next-action scoring are covered in Sections 7 to 9. Assessment, probabilistic mastery, misconceptions, forgetting, exam readiness, and delayed review are covered in Sections 3, 10, 11, and 20.

The five-to-six-role evolution, single canonical state writer, event-driven agents, cost-conscious invocation, source grounding, math and code checks, course-material priority, and limits of verification are covered in Sections 13 to 19. The initial relational and vector storage proposal, narrow-domain MVP, model selection, routing, open-source decisions, and next brainstorming stages are covered in Sections 14 to 24.

## 26 Reference and research followup

Primary product reference: Design AI Learning Harness, conversation dated 11 September 2026, conversation identifier 6aa40f8e-5c34-83eb-9032-27125ee20248. This specification consolidates the design direction and adds proposed implementation contracts and validation criteria.

The discussion mentioned Khanmigo, ChatGPT Study Mode, NotebookLM mind maps, retrieval practice, spaced review, graph-based retrieval, knowledge tracing, and emerging multi-agent tutoring research. These are background research leads, not dependencies or validated performance evidence for this product. The discussion's reported Khanmigo improvements of 3.4 percent and a further 2.7 percent require checking the original study, population, metric, and whether the units are relative percentages or percentage points before reuse in a pitch or business case.

Research followup should retrieve the original primary sources, distinguish educational evidence from product marketing, and test transfer to the chosen audience. No external numerical efficacy claim is used as a release assumption. Technical examples throughout this document are proposed contracts and illustrative scenarios, not existing production behavior.
