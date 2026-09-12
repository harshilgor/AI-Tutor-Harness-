# Phase One: Scope and Build Readiness

**Date:** 11 September 2026  
**Status:** Planning only. Implementation is not authorized by this document.  
**Basis:** The current phase-one request, the Product and Technical Brief, and Future Features and Technical Considerations.

**Detailed implementation companion:** [Phase One — Features and Technical Implementation Specification](Phase_One_Features_and_Technical_Implementation_Spec.md). The user has confirmed that the five reviewed areas belong in phase one; the companion consolidates their feature and technical build requirements. Individual proposed defaults still require validation.

## 1. Phase-one objective

Create a connected learning experience in which a learner can see a knowledge graph, receive first-principles teaching adapted to their needs, and explore any confusing passage in a contextual window without losing the main lesson.

The three user-confirmed priorities are:

1. **Knowledge graph:** the structure that organizes concepts, dependencies, and the learner's relationship to them.
2. **Learning harness:** the system that decides what to explain, checks prerequisites, teaches accurately, and responds meaningfully to teaching controls.
3. **Contextual exploration:** anchored windows for questions and deeper explanations, with a reliable return to the original context.

This is the current phase-one scope baseline. Details labeled **proposed** remain design recommendations, not user-approved choices. Previously documented product breadth is not automatically phase-one scope.

**Confirmed during this review:** Users can enter **any topic from day one** and generate a knowledge graph. A single curated subject is not the phase-one product boundary. Bounded benchmark subjects may still be used for quality testing.

We cannot eliminate every possible implementation mistake through planning. Readiness means that important behaviors, boundaries, failure cases, and validation criteria are explicit. Teaching effectiveness and interface usability remain hypotheses until tested with people.

## 2. Review findings and conflicts to resolve

| Finding in existing documents | Phase-one treatment |
|---|---|
| Strong coverage of kernel, evidence, graphs, policies, and provider boundaries | Reuse these foundations; avoid another architecture rewrite. |
| Original rollout includes course ingestion; later document explicitly defers it | Keep user-managed courses, uploads, transcription, and source administration deferred. A graph still needs an explicit content/source strategy. |
| Learn/Practice/Notebook describes the full product | Phase one centers on Learn. Do not build full exams, flashcards, or Notebook merely to populate navigation. |
| Semantic zoom and later Focus/Roadmap/Map descriptions could imply competing navigation | Proposed resolution: one graph, focused by default, with progressive detail. Any outline is an accessibility alternative, not a second curriculum. |
| Gear exists conceptually but exact behavior is unspecified | Define control-to-plan-to-output behavior and observable tests before implementation. |
| Branch isolation is described technically, but window interaction is unfinished | Specify placement, nesting, persistence, cancellation, selection anchors, and return behavior. |
| Mastery and quality are described in broad terms | Define a modest evidence policy and reviewed examples; avoid unsupported percentage precision. |

The principal gap is operational specificity, not a shortage of future feature ideas.

## 3. Scope boundary

### Required product experience

- Enter any topic, generate an initial bounded graph, and understand each visible relationship.
- Select a concept and start or resume a lesson without losing position.
- Identify a missing foundation and receive a minimal explanation or diagnostic.
- Use Quick, Guided, and Deep teaching plus contextual adjustments.
- Select a term or passage and open an anchored exploration panel.
- Ask follow-ups, explore another concept, and return to the main lesson.
- Retain session state and distinguish exposure from demonstrated understanding.

### Necessary supporting behavior

- Stable concept IDs, typed edges, source references, and graph versions.
- A bounded teaching plan, source-aware output checks, and error handling.
- Small inline understanding checks, because the tutor cannot infer understanding reliably from reading alone. This is a proposed supporting scope, not a full assessment product.
- Canonical learner-state ownership and assistance metadata.
- Durable lesson/branch state, explicit cancellations, and retry deduplication.
- Basic operational traces and a small representative quality evaluation set.

### Deferred unless explicitly added

Full exams, assessment blueprints at exam scale, flashcard scheduling, Practice dashboards, a complete Notebook, course/class management, user uploads, audio/voice, collaboration, advanced history lenses, automated graph migration consoles, learned personalization, live shadow infrastructure, and multi-provider optimization.

Preserve interfaces for these features. Do not build their complete infrastructure in advance. A simple saved branch and resumable lesson do not require a full Notebook product.

## 4. Knowledge graph: decisions and specification

### 4.1 Confirmed decision: arbitrary-topic graph generation

Two materially different products are possible:

| Approach | Phase-one implication |
|---|---|
| One checked subject or small subject pack | Curate a graph, verify sources and dependencies, and evaluate the teaching loop within that scope. |
| Generate a graph for any user-entered topic | Also build topic scoping, retrieval, concept extraction, alias resolution, dependency proposals, validation, and honest handling of incomplete or unsupported graphs. |

The user selected the second approach: **generate a graph for any user-entered topic from day one**. This adds graph generation and validation to phase one. It does not require a Courses/Classes workspace, and it does not imply that an unlimited, complete curriculum can be generated and verified instantly.

Finance remains an illustrative example, not a launch-domain restriction. Initial depth and intended outcome should come from the request or an editable default. Ask a short clarification only when ambiguity materially changes the graph, such as “Java” meaning a programming language or an island.

### 4.1a Required topic-to-graph workflow

```text
Topic request → resolve meaning and intended depth → propose bounded scope
→ retrieve suitable references → propose concepts/objectives
→ resolve aliases → propose typed dependencies → validate structure/content
→ publish supported initial map → teach a selected node
```

Proposed entry experience: one topic box, an optional goal/depth choice, and an editable scope summary. For “physics,” begin with major clusters and a bounded starting path; do not attempt to generate every physics concept. For a narrow topic, use a local concept neighborhood. Show meaningful progress while generation runs and allow cancellation.

Graph generation requires a distinct capability and persisted job. The generator proposes graph data; a validator checks its schema, references, dependencies, and evidence. The published result must distinguish supported content from inferred or unresolved relationships. Search ranking and model confidence alone cannot certify an edge.

Phase-one source acquisition can use suitable external references and curated reference catalogs without user uploads. The exact retrieval provider and authority policy remain decisions. Scientific, historical, mathematical, and interpretive subjects require different validation criteria; prerequisite order in a humanities topic must not be presented as uniquely objective when several teaching paths are defensible.

### 4.1b On-demand expansion and graph identity

Proposed behavior: publish a useful bounded initial map, then expand selected clusters on demand. Reuse existing concept IDs and detect aliases before adding nodes. Attach expansion to a graph revision and preserve the active lesson position. Do not replace the whole graph each time the learner asks a question.

A new unrelated topic creates a new learning scope by default. Cross-topic connections can be proposed explicitly. Reuse learner evidence only when objective meaning and assessment conditions are compatible; matching a concept name is insufficient.

An accepted topic request may still produce “needs clarification,” “insufficient reliable sources,” or a limited map. Handle invented terms, extremely specialized subjects, disputed claims, and requests requiring professional judgment with explicit limitations. Do not fill missing evidence with confident graph structure merely to report success.

### 4.1c Additional graph-generation acceptance cases

- A broad topic produces readable clusters and a bounded path rather than thousands of unreviewable nodes.
- An ambiguous term is resolved before publishing a graph about the wrong subject.
- A narrow topic produces relevant foundations without a full unrelated curriculum.
- Repeated expansion does not duplicate aliases or erase progress.
- Unsupported or conflicting claims are labeled and cannot silently become verified lesson foundations.
- Failed retrieval or partial generation yields a clear recoverable state.
- A new scope cannot inherit unrelated mastery just because labels overlap.
- Evaluation covers varied domains, not only the finance examples used in earlier documents.

### 4.2 What the graph represents

Separate three things:

- **Concept structure:** what exists and how concepts relate.
- **Learner overlay:** what has been explored, checked, or remains uncertain.
- **Session position:** what is currently open and where the learner came from.

A node needs an ID, title, short definition, scope, observable learning objective, source reference, and version. Prerequisite edges need direction and a reason. `requires`, `part_of`, and `related_to` are different relationships; only required dependencies should drive prerequisite traversal.

Define node granularity through a concrete sample graph before coding. “Finance” is a cluster; “identify appropriate weights in a weighted average” may be an assessable objective. Avoid a flat mixture of entire subjects and atomic skills with identical visual meaning.

### 4.3 Graph quality and publication

Proposed process: draft → structural validation → content/dependency review → published version. Generated relationships remain proposals until the chosen validation policy accepts them. Store provenance separately from confidence: a high model confidence score is not evidence.

Required cases: duplicate labels, aliases, disconnected required concepts, missing references, prerequisite cycles, conflicting definitions, and unsupported edges. General relationship cycles are allowed. A dependency cycle requires correction or an explicitly modeled jointly taught group.

### 4.4 Graph interaction

Proposed first experience: focused neighborhood around the active concept, with zooming outward to topic groups and inward to learning detail. The active lesson stays readable; layout changes do not pull it away while the learner is reading.

Support selection, search within the supported scope, pan/zoom, “return to current concept,” a relationship legend, and an accessible ordered outline. Use text or icons alongside color. Do not represent every unexplored concept as a failure.

Minimum states: unassessed, explored, developing, and demonstrated on a defined check. A misconception marker should indicate supported evidence or an explicit hypothesis. Add numerical mastery only once its meaning and uncertainty are defined.

### 4.5 Scope changes

If a branch mentions a new concept, it must not silently edit the published graph. Resolve it to an existing concept, label it as an external tangent, or propose an explicit scope expansion. A learner can ask about something outside the map without having that topic automatically added to their curriculum.

## 5. Learning harness: observable behavior

### 5.1 First principles without endless prerequisites

For each target objective, the harness reads relevant prerequisites and learner evidence, then chooses among explaining directly, embedding a short definition, asking a targeted diagnostic, or opening a short prerequisite bridge.

Unknown is neither mastered nor failed. Self-report can guide where to start, but does not establish independent mastery. Let the learner request a direct explanation; label knowledge as unassessed rather than forcing a quiz before every lesson.

Bound prerequisite exploration by relevance, depth, and time. If a topic is far beyond the current foundations, explain the proposed learning path instead of recursively opening many lessons. Bridge completion must restore the original objective and position.

### 5.2 Teaching plan

Before generation, resolve: target objective, current gap, known foundations, representation, explanation depth, examples, support level, forbidden unnecessary concepts, source pack, and next possible check.

The output contract should contain display blocks, concept references, source/claim references, and verification status. The UI must not infer canonical state by parsing prose. Unsupported terminology triggers simplification, a short definition, or an explicit explanation link.

### 5.3 Understanding and adaptation

Use a small set of reviewed checks for the first learning slice. A learner's answer, hint exposure, and evaluation result become evidence. One state owner decides any update. No mastery increase follows merely from opening a node, reading a lesson, or closing a sidecar.

When a learner remains confused, change the representation or address a specific gap. Rephrasing the same abstract explanation repeatedly is a failure case. Distinguish conceptual confusion, arithmetic mistakes, ambiguous answers, and absent evidence.

Repeated Simpler requests can inform a suggested default change. Proposed initial behavior: preserve the explicit gear, adapt within the current lesson, and offer a reversible preference update rather than silently learning a permanent profile.

### 5.4 Correctness boundaries

Select a concrete source policy that can handle user-entered topics, including authority, recency, disputed interpretations, and unavailable evidence. Record which claims are checked and how. Use suitable independent calculation checks for numerical examples. Avoid using a second model's agreement as the sole correctness criterion.

When evidence is inadequate, narrow the explanation, acknowledge uncertainty, or withhold the unsupported claim. A failed model call does not advance the lesson or change learner state. Verification requirements must apply equally in a branch and in the main lesson.

## 6. Teaching controls: functional contract

Proposed persistent control: **Teaching Gear — Quick / Guided / Deep**. It changes the teaching plan, not merely a label or response length. Contextual buttons provide local overrides without forcing a settings visit.

| Control | Required change | Must preserve | Validation example |
|---|---|---|---|
| Quick | Compact explanation and only essential examples/bridges | Correctness, objective, necessary definitions | Same objective explained briefly without unexplained key terms. |
| Guided | Intuition, useful example, manageable steps, optional check | Learner's demonstrated prerequisites | Supports the missing foundation without reteaching known material. |
| Deep | Mechanism, assumptions, derivation where useful, meaningful connections | Scope and reader orientation | Explains why the method works, not just a longer introduction. |
| Simpler | Lower abstraction and define unfamiliar terms | Conceptual truth | Removes jargon while retaining the key relationship. |
| Go deeper | Expand the selected reasoning step or mechanism | Selected anchor | Answers the missing “why” without restarting the lesson. |
| Example | Add a concrete, checked illustration | Same concept and assumptions | Provides an actual worked case, not only an analogy label. |
| Why? | Explain the causal/logical justification | Exact claim under discussion | Justifies the selected statement rather than summarizing the topic. |
| Visualize | Use a suitable supported diagram/representation | Accuracy and text accessibility | Shows a relevant relationship and an equivalent textual explanation. |
| Check understanding | Offer a short suitable check | Honest assistance classification | Does not reveal its answer before an independent response. |

“Visualize” needs a supported-format boundary before build: proposed V1 uses a small set of reliable diagrams, tables, and worked visual structures, not arbitrary generated interactive simulations. Unsupported requests must have an honest fallback.

Proposed control rules:

- Gear changes apply to the next response; they do not rewrite old lessons automatically.
- Provide an explicit action if the learner wants the current explanation regenerated.
- A contextual adjustment affects the selected explanation; it does not silently change global settings.
- A new branch inherits the gear at creation and may hold a local override.
- A control pressed during generation cancels/supersedes the pending action or queues a clearly identified next action. Do not merge incompatible streams.
- Scaffolding and exam difficulty remain distinct concepts; phase one does not need exam difficulty sliders.

Before implementation, review the same concept under all three gears and each contextual action. Agree on observable differences using a few concrete examples. Token counts alone cannot certify that a knob works.

## 7. Exploration windows: proposed interaction contract

### 7.1 Desktop layout

Use an in-app side panel beside the main lesson. This is a proposed layout to review, not a finalized UI. The main lesson remains visible and retains its scroll position. Keep graph context available in the same workspace, without forcing three equally wide columns at all times.

```text
Active concept / Teaching Gear / return controls
┌──────────────────────────────┬──────────────────────────┐
│ Main lesson                  │ Exploration              │
│                              │ Selected passage         │
│ WACC explanation             │ “market values”          │
│ ... selected passage ...     │                          │
│                              │ Why are these used?      │
│ Original position preserved  │ Explanation + follow-up  │
└──────────────────────────────┴──────────────────────────┘
Graph neighborhood remains accessible in the workspace.
```

Avoid browser pop-up windows as the default: the desired behavior is a contextual panel within the learning experience. On small screens, use a focused panel with the selected passage, breadcrumb, and a reliable return button. Simultaneous full visibility is a desktop goal; a narrow screen needs an explicit context-preserving alternative.

### 7.2 Opening and anchoring

Support clicking linked terms and selecting arbitrary text, including non-linked phrases. Offer Explain, Why?, Example, or a custom question. Keyboard users must have an equivalent action.

Store the lesson artifact/version, block ID, selected range or quote, parent branch ID, concept references, and return position. Anchoring by raw character offset alone is fragile if the lesson is regenerated. Preserve the original quoted snapshot and label an old anchor when its source is superseded.

### 7.3 Context and nesting

A branch receives the selected passage, relevant parent summary, current goal, sources, learner snapshot, and local gear. It does not copy every preceding conversation into every request.

Proposed V1: one active exploration panel, multiple saved branches, and a breadcrumb path for nested exploration. Opening a child replaces the content inside the exploration panel while keeping the main lesson visible. Parent and child remain resumable. This supports repeated dives without an uncontrolled cascade of floating windows.

The number of simultaneously visible panels is an explicit design decision. The current requirement calls for contextual dives, not necessarily several independent desktop windows at once.

### 7.4 Returning, saving, and late results

- Back returns to the parent branch; close returns focus to the main lesson.
- Closing hides the branch and cancels active work by default; retained content can reopen.
- Already committed valid evidence remains valid after close. An uncommitted late response cannot mutate the session after cancellation.
- A short branch summary may be available on return, but must not rewrite the main lesson or assert mastery.
- Reload restores the main anchor and saved branch path. Unsaved input behavior must be specified and tested.
- Deletion, if offered, is distinct from close and must be explicit.

## 8. Minimal state and command boundaries

Retain the existing Python/TypeScript direction as a proposed stack, without selecting dependency versions in this planning review.

Minimal records: TopicScope, GraphGenerationJob, GraphVersion, Concept, Edge, LearningObjective, LearnerConceptState, Session, LessonArtifact, TeachingPlan, Branch, LearningAction, Evidence, SourceReference, and VerificationResult. Sources need external topic-appropriate acquisition as well as any curated references; this does not require a user-facing upload system.

Minimal commands: GenerateTopicGraph, ClarifyTopicScope, ExpandGraphCluster, SelectConcept, AskQuestion, SetTeachingGear, AdjustExplanation, OpenBranch, AskInBranch, ReturnToParent, CloseBranch, ResumeSession, and SubmitUnderstandingCheck.

Each action carries a unique ID, scope, session/branch reference, expected revision, and policy/version references. Keep authorization, planning, generation, verification, and evidence admission separate even within one application. Stale outputs cannot replace a newer selection. Repeated submissions cannot duplicate evidence.

Decide before implementation whether this is a local single-user prototype or a hosted multi-user pilot. The latter requires authenticated ownership and access isolation from the beginning; it cannot be safely added after mixing learner records.

## 9. Failure and edge-case checklist

| Situation | Expected result |
|---|---|
| Graph is empty or generation fails | Explain the state and provide a scoped retry; never show fabricated completed progress. |
| Dependency is unknown | Offer a targeted check or short bridge; do not mark failure. |
| Prerequisite traversal loops | Stop with a controlled outcome and flag the graph defect. |
| Learner asks outside supported scope | Explain boundary and offer a bounded tangent or scope choice. |
| Learner repeatedly requests simpler explanations | Change strategy or identify a gap; avoid repeated paraphrases. |
| Main concept changes while a branch is generating | Keep output attached to its original branch; do not insert into the new lesson. |
| Gear changes during generation | Apply the documented cancellation/next-action behavior. |
| User opens the same passage twice | Reopen or clearly create a separate branch; avoid accidental duplicates. |
| A generated explanation is corrected | Preserve revision and anchors; supersede invalid evidence if needed. |
| Source is missing or contradictory | Show a limited/uncertain result; do not claim verification. |
| Network/model failure | Preserve learner input and position; offer retry without duplicate state changes. |
| Reload or application restart | Restore committed session/branch state. |
| Keyboard navigation or narrow screen | Preserve access to actions and an unambiguous return path. |

## 10. Acceptance scenarios

These are specifications for future verification, not tests that have already passed.

1. **Graph meaning:** A learner can distinguish prerequisite from related-to edges and identify the active concept without relying on color.
2. **Known foundation:** A learner with supporting evidence is taught the target without unnecessary elementary detours.
3. **Missing foundation:** A learner lacking one dependency receives that bridge and returns to the original lesson.
4. **Unknown foundation:** The system stays honest about uncertainty and does not preemptively mark failure.
5. **Controls:** Quick, Guided, Deep, and contextual actions produce the specified pedagogical changes on the same objective.
6. **Anchored confusion:** Selecting an arbitrary sentence opens a relevant explanation alongside the desktop lesson, not a generic topic response.
7. **Nested exploration:** Main lesson → branch → child branch → parent → main lesson preserves each position and context.
8. **Evidence integrity:** Reading and self-report do not count as independent success; a retry cannot count a response twice.
9. **Failure recovery:** Cancellation, timeout, and reload preserve position and prevent stale output from replacing current content.
10. **Correctness:** A deliberately faulty numerical example or unsupported source claim is detected or withheld under the defined verification policy.
11. **Scope isolation:** An unrelated tangent cannot silently mutate the primary graph or learner scope.
12. **Usability:** A real learner can explore and return without having to reconstruct context in a new prompt.

Use deterministic fixtures for state and routing rules, domain-reviewed examples for teaching correctness, and human walkthroughs for usability. Model-based judging can assist review, but does not prove educational effectiveness.

## 11. Decisions needed before coding

| ID | Decision | Status / proposed next action |
|---|---|---|
| D1 | Reviewed initial subject versus arbitrary-topic graph generation | **Resolved: any user-entered topic from day one.** |
| D2 | Initial learner audience, default depth, and benchmark topic set | Define without restricting users to a single subject. |
| D3 | Graph/source authority and review process | Produce a sample graph and source policy; inspect actual edges. |
| D4 | Node granularity and initial graph boundary | Review representative cluster, concept, skill, and edge examples. |
| D5 | Desktop panel behavior and mobile alternative | Review wireframes for main, branch, nested branch, and return states. |
| D6 | Gear and contextual action semantics | Review contrasting output examples and accept functional contract. |
| D7 | Initial learner evidence and understanding-check policy | Choose an honest small baseline with explicit uncertainty. |
| D8 | Local prototype versus hosted pilot | Determines identity, persistence, and access requirements. |
| D9 | Provider, verification tools, response latency, and cost envelope | Evaluate candidates on selected examples; do not infer from popularity. |
| D10 | Quality acceptance and release audience | Agree on reviewed teaching cases, critical failures, and pilot expectations. |

Model routing optimization, large-scale migration tooling, advanced mastery estimation, and commercial/open-source strategy need not all be finalized to build the first controlled learning slice. Keep them recorded without pretending they block every implementation task.

## 12. Planning completion gate

Before implementation begins, prepare and review:

- A bounded initial-map policy with D2/D8 resolved; D1 is confirmed.
- Representative generated graphs across several topic types, with definitions, typed dependencies, objectives, and source references.
- Four learner journeys: first visit, prerequisite gap, teaching adjustment, nested exploration and return.
- Annotated desktop and small-screen wireframes, including loading and failure states.
- Side-by-side examples proving the intended differences between teaching controls.
- A minimal state/command contract and explicit source/evidence policies.
- A small domain-reviewed teaching and correctness evaluation set.
- A build sequence with acceptance scenarios, operational budgets, and known residual risks.

**Current readiness:** direction is clear; detailed phase-one design is incomplete. The artifacts above have not yet been approved or validated. Do not confuse this checklist with completion of those artifacts.

After those decisions, the proposed implementation order is graph/state foundation → topic scoping, retrieval, generation, and validation → one source-grounded teaching path → controls → anchored/nested exploration → recovery and complete-loop evaluation. Graph and teaching contracts should be designed together so the graph is useful to the tutor from the first slice.

## 13. Document relationship

- The Product and Technical Brief remains the broad product/architecture reference.
- Future Features and Technical Considerations remains the expansion and deferral reference.
- This document records the current phase-one scope, missing decisions, and build-readiness gate.

New design decisions should update this record rather than introducing incompatible requirements in several files. No application implementation was started as part of this review.

## 14. Recommended resolution: graph trust

**Recommendation:** treat each generated graph as a versioned learning proposal with evidence attached to individual concepts and relationships. Publish a useful, checked initial neighborhood; expand it progressively. Accept any topic, while making support limits explicit.

### Source and relationship policy

Separate three kinds of judgment:

1. **Content support:** does a reference substantiate the concept definition or claim?
2. **Dependency justification:** is skill A actually needed to perform the selected objective B?
3. **Teaching preference:** might A make B easier to learn even if it is not necessary?

A source supporting two concepts does not establish a prerequisite between them. Each `requires` edge must name the objective and a dependency reason. Use `recommended_before` for a helpful sequence and `related_to` for a connection. Only a justified required edge can trigger a blocking prerequisite intervention.

For example, a qualitative explanation of a derivative can use slope and change; deriving differentiation rules has a different prerequisite set. A graph must not require calculus before allowing an intuitive discussion of a concept that uses calculus formally.

Proposed source selection is domain-sensitive: authoritative educational references for established foundations, official versioned documentation for software behavior, primary material plus reputable scholarly interpretation for historical claims, and attributable perspectives for contested questions. Use source diversity for contested or consequential claims; a fixed two-source rule does not guarantee independent support. Ten pages repeating one source are not ten independent confirmations.

Preserve source title, locator, revision/date where available, supported claim, and actual inspected content reference. A search snippet or an invented citation cannot qualify as checked support. Retrieved pages are data and must never override system permissions or tool policy.

### Publish and teach rules

| Internal status | UI wording | Permitted behavior |
|---|---|---|
| Supported content | Sources available | Teach supported claims under the recorded checks; no universal “true” badge. |
| Inferred pedagogical relationship | Suggested learning order | Offer a route; do not claim a sourced necessity or lock progression. |
| Material conflict | Different interpretations | Show attributed alternatives; hold any check that assumes one disputed answer. |
| Insufficient support | Needs checking | Show a candidate only if clearly labeled; withhold unsupported authoritative teaching or grading. |

Do not paint source status with the same colors used for learner progress. Keep an unobtrusive source indicator, with detail on selection. Learner mastery and content confidence are unrelated axes.

Validation has three layers: deterministic graph integrity, claim/reference matching, and dependency/content critique. The critique is a check, not proof. Automated publication is necessary for arbitrary topics; human review should audit representative cases and resolve flagged defects, not block every user request.

Proposed generation budget for initial experiments: roughly 5–8 visible clusters for a broad topic, or 8–15 visible concepts for a narrow one. These are interface trial settings, not evidence-based universal limits. Avoid fully generating hidden subgraphs before the first useful lesson. Expand through deduplicated additions to a new revision, with the current lesson pinned until an appropriate transition.

### Corrections

Provide “This seems wrong” on concepts, edges, and explanations. Preserve the reported artifact, recheck it, and mark confirmed defects. Correct the graph through a new revision. Locate affected lessons and evidence; supersede evidence from invalid checks rather than treating it as a learner failure. Never silently reset all progress after a graph regeneration.

**Residual risk:** coverage and correctness cannot be certified across all possible topics. Evaluate many topic types, report supported scope honestly, and return a limited map when necessary.

## 15. Recommended resolution: teaching behavior

**Recommendation:** use a small policy-driven teaching loop with a choice of next actions. A model drafts the teaching plan, but the harness checks its scope, prerequisite burden, and evidence rules before execution.

### Next-action policy

| Learner/context condition | Preferred action |
|---|---|
| Relevant prerequisite demonstrated | Teach the target directly. |
| An unfamiliar term can be explained briefly | Define it inline and continue. |
| Uncertain prerequisite materially changes the lesson | Offer one focused diagnostic or a short bridge. |
| Evidence indicates a blocking misconception | Contrast the mistaken and correct idea, then obtain a fresh check. |
| Target is far beyond available foundations | Offer an intuitive overview and a proposed deeper path; do not launch a long forced detour. |
| Learner asks to skip the check | Continue explaining with state marked unassessed. |
| Repeated confusion after a changed explanation | Ask which step fails or use a concrete case to localize the gap. |

Proposed default interaction is **short explanation → worked example when useful → opportunity to respond → targeted feedback**. Use this as an adaptable sequence, not a mandatory four-part response to every question. A request for a definition should not automatically trigger an exercise.

The IES practice guide supports alternating worked examples with problem solving and using retrieval activities. It does not establish that our exact loop or numerical defaults are optimal for every learner or domain. [IES learning practice guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/1).

### Bound interventions

As an initial policy, offer at most one diagnostic before the first useful explanation and one active prerequisite bridge at a time. If another substantial gap appears, show the proposed path and let the learner choose depth. These are tunable friction limits, not learning-science constants. Correctness still takes precedence over presenting an advanced result without its essential assumptions.

Distinguish changing representation from reducing the learning objective. An analogy should state its limits. An intuition-only explanation must not be labeled a completed derivation. The learner can choose Deep and still need simple language: depth and abstraction are separate.

### Evidence baseline for phase one

Track explored, supported during practice, and demonstrated on a specific independent check. Preserve uncertainty rather than declaring global mastery from one response. Generate checks for arbitrary topics through a bounded item/answer/rubric validation path; curated checks are evaluation fixtures and reusable assets, not the only supported runtime topics.

Capture hints and recent exposure. After showing a worked answer, test with a changed case rather than immediate verbatim recall if the aim is independent application. Reject ambiguous or insufficiently verified checks from learner-state updates. A graded disagreement has a correction path.

Repeated “Simpler” clicks adjust the immediate strategy; persistent personalization remains explicit and reversible. Avoid permanently labeling a learner as unable to handle equations because one explanation failed.

## 16. Recommended resolution: controls

**Recommendation:** keep one persistent gear and contextual actions. Internally compile them into explicit teaching-plan fields and validate the resulting output against those fields.

The plan separates depth, abstraction, example use, step size, derivation, and assistance. Presets set defaults; a local action overrides only its relevant dimensions. This allows **Deep + Simpler**: a thorough explanation in accessible language. It must not collapse to Quick.

### Precedence and timing

1. Correctness and permissions remain mandatory.
2. The selected objective remains fixed unless the learner changes it.
3. An explicit local action overrides the matching gear defaults for that response.
4. Session gear supplies remaining defaults.
5. Inferred preferences only fill unspecified presentation choices.

Changing the persistent gear affects the next response. The active response completes under its original settings; show “applies to next response.” Explicitly requesting a replacement such as Simpler cancels and supersedes an in-progress replacement for the same passage. Each response carries its action ID so late tokens cannot mix into a different response.

Offer “Apply to this explanation” if the learner wants a gear change to regenerate current content. Preserve the previous version and anchors. Child branches inherit the parent's resolved profile at creation; local overrides do not unexpectedly change the main lesson. A session-level gear change applies to future branch requests unless that branch has an explicit local override.

### Concrete contrast example: what is a derivative?

- **Quick:** explain instantaneous rate of change using the slope of a curve at a point.
- **Guided:** start with average change over an interval, use a small numerical example, then shrink the interval and invite a prediction.
- **Deep:** connect average rates to the limiting difference quotient, explain the limit and assumptions, and discuss a point where differentiability fails when foundations permit.
- **Deep + Simpler:** retain the limit mechanism and its limitations, introduce notation gradually, and explain each step in familiar language.

These are proposed output characteristics, not final lesson content. Evaluate each control using paired outputs for identical learner state, objective, and sources. Review whether the intended dimension changed and whether key meaning survived. Extra words alone do not count as passing.

For Visualize, select among a validated relationship diagram, table, number line, or suitable plot. Numerical plots require checked data/functions and clear labels. If no reliable visual form is supported, say so and provide a useful textual structure; never return unrelated artwork just to make the button appear functional.

## 17. Recommended resolution: windows

**Recommendation:** one non-modal, resizable exploration panel on desktop, with saved sibling branches and nested breadcrumbs. Keep the main lesson visible and operable. Avoid a stack of modal pop-ups.

W3C's modal-dialog pattern intentionally confines keyboard focus and makes underlying content unavailable for interaction. That conflicts with a simultaneously usable main lesson. The desktop exploration should therefore behave as a labeled non-modal region, with deliberate focus movement and return. If a narrow-screen presentation is modal, use the proper modal behavior there. [W3C dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

### Interaction sequence

1. Select text, a linked term, or a content block such as an equation; activate Explain/Why/Example or enter a question.
2. Preserve an immutable anchor and main return position, then focus the exploration heading or input.
3. Display the selected quote and breadcrumb permanently within the panel header.
4. Selecting content inside the panel opens a child branch within that same panel.
5. Back restores the parent's draft and scroll position. Close restores the triggering main-lesson location and keyboard focus.
6. Saved branch markers let the learner reopen earlier explanations without regenerating them.

Proposed desktop sizing starts near a 60/40 lesson/exploration split within the learning area, adjusted to minimum readable widths. Collapse graph chrome before squeezing text excessively. This is a wireframe trial, not a final pixel specification. On mobile, show the anchor and breadcrumb above the focused exploration and return to the exact lesson location.

Drafts should save locally while typing and sync according to the chosen deployment model; display failure if remote saving fails. Clearing a draft is separate from closing a branch. Render partial interrupted responses as incomplete, never as a completed lesson.

Entering an unrelated main topic should switch the visible branch collection to that topic. Existing branches remain attached to their original lesson. Do not silently retarget a branch to a new main conversation.

Returning from a useful branch may show an optional one-sentence connection: “This explains why the earlier step uses X.” That connection must remain grounded in the branch and original lesson. Do not insert a long generated recap, rewrite history, or infer mastery from closure.

**Residual design question:** simultaneous comparison of two branches might be useful later. Saved siblings plus one active panel is the recommended phase-one default; validate whether this satisfies real users before adding additional floating panes.

## 18. Recommended resolution: quality gates

**Recommendation:** use separate release gates for integrity, content, teaching, usability, and actual learning. Never average them into one score that allows a polished interface to hide incorrect teaching.

### Proposed initial evaluation set

Create at least 30 topic/scope cases across mathematics, natural science, programming, history, and conceptual/humanities learning. Include broad, narrow, ambiguous, contested, sparse-source, and cross-domain requests. This is an initial regression set, not proof of universal topic coverage.

For a smaller representative subset, exercise three learner conditions (beginner, known foundations, specific gap), three gears, and local overrides. Use held-out examples or task structures for independent checks. Add cancellation, reload, stale responses, unavailable sources, malicious source instructions, and source correction fixtures.

NIST's Generative AI Profile identifies confabulation and information integrity as relevant risks. Our implication is to evaluate evidence and failure handling explicitly, rather than equating fluent output with reliability. The thresholds below are proposed project gates, not NIST-prescribed values. [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf).

| Gate | Proposed pilot requirement | Failure response |
|---|---|---|
| State and permissions | All defined critical scenarios pass; zero known unauthorized writes, duplicate evidence updates, or cross-user leaks. | Block release until fixed. |
| Graph integrity | No broken references, invalid required-edge cycles, or silent loss of learner history in the evaluated set. | Repair or withhold affected graph revision. |
| Content correctness | Zero unresolved critical teaching errors or fabricated citations in reviewed release cases. | Correct, rerun related cases, and inspect shared cause. |
| Source support | Every sampled consequential claim marked supported has an inspected, relevant source or tool result. | Remove unsupported status; repair or withhold claim. |
| Teaching and controls | At least 90% of paired reviewed cases meet all applicable behavior criteria, with no critical truth loss. | Revise plan/prompt/rules; report performance by domain and control. |
| Window usability | In an initial 5–8-person formative study, every participant can complete basic open/back/return after onboarding; repeated disorientation is a blocker. | Revise interaction design before broadening scope. |
| Recovery | Scripted cancellation/reload/retry paths preserve committed content and prevent stale mutation. | Fix persistence/ordering before a pilot. |

Numeric gates are proposed starting thresholds to review against the actual benchmark; 90% of a weak benchmark is not adequate. Record denominators, exclusions, reviewer disagreements, and performance by domain. A zero-known-defect gate does not claim a zero population error rate.

Latency should be measured as time to first useful checked output and complete result, at p50/p95 under a defined load. Do not set provider-independent guarantees before benchmarking. Regardless of timing, acknowledge the action immediately, display an honest work state, allow cancellation, and preserve input on timeout. Establish a per-session and per-generation cost ceiling before pilot use; stop/regenerate within policy rather than silently lowering correctness checks.

### Learning-outcome gate

The formative usability group does not establish better learning. Separately compare the harness with a reasonable baseline using comparable starting knowledge, equal learning time, independent application tasks, and delayed follow-up. Predefine the outcome and study design; determine sample size from that design rather than choosing an attractive small number.

Track whether learners need fewer context-reconstruction prompts, while ensuring that independent performance does not deteriorate. Do not use the harness's own mastery estimate as its primary proof of success. Until outcome data exists, describe the product as a pilot with learning hypotheses, not a validated superior tutor.

## 19. Design position after this analysis

The recommended policy for each of the five areas is now concrete enough to review and prototype. These recommendations do not declare D3–D7 or D10 approved, and no quality gate has been run.

The remaining work before production implementation is to instantiate the policy in actual examples: generated sample maps, source/dependency audits, paired gear outputs, annotated branch wireframes, and the evaluation fixtures. Audience/default depth, deployment model, provider/tool selection, and operating budgets still need decisions.

Use these sections as the proposed detailed resolution of earlier alternatives: gear changes affect future output; explicit replacement actions cancel superseded work; branches have one active panel with saved siblings; arbitrary-topic checks require runtime validation. Existing future-feature deferrals remain in effect.
