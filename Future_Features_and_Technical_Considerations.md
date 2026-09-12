# Future Features and Technical Considerations

> Do not expand scope merely because a feature is useful. The present focus is the core learning loop: infer learner state, teach the right concept with minimum friction, verify understanding, update mastery, and select the next best learning action.

**Project:** AI Tutor Harness  
**Date:** 11 September 2026  
**Status:** Future design reference; not an implementation claim or an instruction to expand the MVP.  
**Companion:** [Main Product and Technical Brief](AI_Tutor_Harness_Product_and_Technical_Brief.md). The main brief and README remain separate and unchanged.

This document consolidates the most recent architectural and feature discussion in **Design AI Learning Harness** (conversation `6aa40f8e-5c34-83eb-9032-27125ee20248`), including the complete retrieved reply on additional technical considerations and the subsequent request to defer courses/classes. Schemas, numerical budgets, failure handling, rollout gates, and acceptance examples below are proposed engineering elaborations, not previously validated specifications. This is a design record, not a new research review.

The central technical direction is to model the learning process as explicit state transitions across concepts, learners, goals, sessions, assessments, and evidence. Models participate inside that system; conversational text does not become its database or its authority.

## How to use this document

| Category | What it means today | What it does not authorize |
|---|---|---|
| Core infrastructure we should architect for now | Preserve contracts, identifiers, ownership boundaries, and essential correctness checks in the core loop. | Building a distributed platform, full migration console, or every operational tool before validating learning value. |
| Future product features | Record the experience, dependencies, and success criteria so it can be added coherently. | Adding every button, dashboard, or workflow to the MVP. |
| Deferred workspace/course features | Reserve compatibility with source collections and versioned curricula. | Building uploads, course management, collaboration, or institutional administration now. |

The smallest implementation can remain a modular monolith using the proposed Python backend and TypeScript frontend. Logical planes and capabilities need not be separate services or separate model calls. Where the main brief already contains a basic version of a capability, this document describes its future extension; it does not remove necessary core-loop behavior.

# Core infrastructure we should architect for now

## 1. Learning Control Plane vs Execution Plane

The **Learning Control Plane** decides what should happen, within which constraints, and why. It reads canonical learner estimates, the curriculum graph, the active goal, session permissions, source policy, and pedagogical policy. Its output is a bounded Learning Action: for example, teach market-value weighting with an intuitive example, then obtain an independent understanding check.

The **Execution Plane** performs authorized work: retrieval, explanation generation, calculation, rendering, assessment creation, and verification. It returns artifacts, execution status, and candidate evidence. It cannot independently broaden the curriculum, change exam permissions, or write mastery.

```text
Goal + curriculum + learner snapshot + session + policy
                         |
                  Learning Control Plane
                         |
                  Validated Learning Action
                         |
                  Execution Plane
                         |
               Artifact + candidate evidence
                         |
              Validation and state reducer
                         |
           New canonical state + transition record
```

**Architect now:** define ownership and interfaces in code, even if all components run in one process. A planner may use a model to propose an action, but deterministic validation enforces scope, permissions, and preconditions. Keep model routing behind the capability boundary.

**Acceptance example:** changing the explanation model must not change the rules for whether an assisted answer counts as independent evidence. A failed generation leaves learner state intact and yields a retryable or terminal execution result.

## 2. Internal Learning Action protocol / intermediate representation

A stable intermediate representation separates user language and interface gestures from execution details. “I still do not understand why WACC uses market values” and a click on **Why?** can compile to the same action. Models, prompts, and interface layouts can evolve without rewriting every capability.

Illustrative contract:

```json
{
  "schema_version": "1",
  "action_id": "action_123",
  "idempotency_key": "session_4:request_8",
  "kind": "TEACH",
  "goal_id": "goal_7",
  "session_id": "session_4",
  "branch_id": null,
  "curriculum_version": "finance_v1",
  "learner_state_revision": 42,
  "concept_ids": ["market_value_weighting"],
  "objective": "explain_why_market_values_are_used",
  "representation": "intuition_then_example",
  "scaffolding": "guided",
  "source_policy_id": "general_v1",
  "policy_bundle_id": "teaching_v1",
  "allowed_capabilities": ["retrieve", "explain", "verify"],
  "evidence_scope": ["market_value_weighting"],
  "verification_policy_id": "conceptual_v1",
  "deadline_ms": 8000,
  "follow_up": "PROPOSE_UNDERSTANDING_CHECK"
}
```

Action families can include `TEACH`, `DIAGNOSE`, `ASSESS`, `REVIEW`, `EXPLAIN_PREREQUISITE`, and `SUMMARIZE_BRANCH`. Use typed, versioned fields rather than relying on instructions embedded in free text. Persist the resolved action, not only the original user utterance.

Validate required inputs, concept existence, active versions, tool permissions, evidence scope, and output schema before dispatch. Reject unsupported action versions explicitly. A follow-up is a proposal subject to a fresh policy check; it does not grant the executor authority to start arbitrary workflows.

**Architect now:** a minimal action envelope and capability registry. Later add richer compilation, compatibility adapters, and visual workflow inspection. Avoid making the first version a universal workflow language.

## 3. Evidence-only agent outputs and canonical learner-state mutation

“Evidence-only” describes an agent's authority over learner state: agents can also produce lessons, notes, and question artifacts, but all claims that could change mastery must enter as candidate evidence. Only the Learner State engine may commit canonical changes.

An evidence record should carry an immutable ID, learner and concept IDs, action/session/branch references, observed response, rubric and item versions, assistance level, assessment conditions, time, source provenance, and confidence in the interpretation. Distinguish the observation (“answer chose book values”) from an inferred misconception (“may confuse book and market value”).

Proposed commit path:

1. Authenticate the originating capability and validate the record against the authorized concept and session scope.
2. Check item validity, exposure to hints or solutions, provenance, and duplicate evidence IDs.
3. Apply a versioned reducer or estimator using the current revision; reject or recompute stale writes.
4. Atomically persist accepted evidence, the new learner projection, and a transition reason.
5. Publish the committed event to recommendations and UI projections through a recoverable delivery mechanism.

An explanation read, a saved note, and an “I understand” click are not independent demonstration. A correct self-explanation may be informative, but its weight depends on assistance, rubric coverage, and verification. Independent transfer evidence often deserves greater weight than a conversational claim; the exact weights need calibration.

Do not use last-writer-wins to resolve contradictory evidence. Preserve both observations and their conditions. Avoid counting a tutor's interpretation and an assessor's interpretation of the same answer as two independent demonstrations. Corrections should supersede invalid evidence with an audit trail rather than silently rewriting history.

**Acceptance example:** retrying a submission cannot increase mastery twice; an out-of-scope sidecar cannot mutate the main curriculum; a late response from a canceled action cannot overwrite a newer state revision.

## 4. Explainable state transitions

Persist the previous and resulting state revisions, triggering evidence IDs, estimator version, applicable policy, timestamp, and a structured reason code with supporting facts. This enables both debugging and learner trust.

Example visible explanation: “Your estimate for beta decreased after two independent transfer questions showed difficulty distinguishing systematic risk from total risk.” The explanation should link to those questions when accessible. It must not claim a particular cause when the change actually came from a time-based retention estimate or a recalibration.

Separate evidence-driven updates, retention forecasts, graph migrations, and estimator-version recalculations. A historical replay should label whether it shows the estimate recorded then or a later recalculation using a newer estimator.

**Architect now:** transition records and concise reason templates. Defer rich history visualizations. Explanations come from recorded decisions and evidence, not invented retrospective reasoning or hidden model chain-of-thought.

## 5. Curriculum/course versioning and graph migration

Use stable concept identities and immutable graph versions. A concept title is not its identity. Each graph version records concept definitions, prerequisite edges, learning objectives, source bindings, and the migration from its predecessor.

| Change | Proposed treatment of history |
|---|---|
| Rename or move without semantic change | Preserve identity and evidence; update presentation metadata. |
| Add a concept | Start as unassessed; do not infer mastery merely from nearby nodes. |
| Remove a concept from current scope | Retain historical identity and evidence; omit it from current coverage. |
| Split a concept | Reattribute only evidence that actually covers each new concept; flag remaining uncertainty. |
| Merge concepts | Preserve evidence lineage and deduplicate overlapping observations; do not blindly average mastery. |
| Change definition or prerequisites | Review evidence compatibility and recompute readiness without pretending the learner failed. |

Migrations should be explicit mapping artifacts with change type, justification, confidence, and review status. Pin active lessons and assessment sessions to a graph version; choose a controlled upgrade boundary. Validate missing references, duplicate identities, and cycles in prerequisite relationships before publication. Other relationship types need not be acyclic.

**Architect now:** stable IDs, version references, and evidence independent of graph display structure. Build migration automation and review tools when curricula actually change at scale. A migration must never destroy the learner's prior work.

## 6. Prompt, policy, model, source, and verifier provenance

Every consequential artifact and decision should reference a reproducible configuration bundle: action schema, resolved prompt/template version, model/provider identifier and available revision, generation settings, policy bundle, curriculum version, source revision and locator, retrieval configuration, tool version, and verification result/policy.

Keep artifact IDs and trace IDs so a faulty explanation can be traced to its inputs and downstream evidence. Store hashes or immutable references where appropriate; protect raw learner content with access and retention controls. Provider aliases can change, and nondeterministic generations may not replay exactly. Record those limits rather than promising byte-for-byte reproduction.

Version changes independently. A prompt edit should not masquerade as an unchanged release. A source update should not rewrite the citations attached to an old explanation. Verification means a specific check passed under recorded conditions, not that all statements are guaranteed true.

**Architect now:** a compact provenance envelope shared across capabilities. Defer a full provenance explorer. This also supplies the metadata required by evaluations, shadow comparisons, and targeted correction workflows.

## 7. Branch/sidecar isolation and mutation scopes

A sidecar inherits only the relevant parent context: selected passage, active concept, goal, source policy, and a learner-state snapshot. It has its own branch ID, local conversation, parent pointer, permitted capabilities, evidence scope, and lifecycle status.

Branch agents still cannot directly mutate canonical state. Their scoped evidence may be admitted by the Learner State engine. A WACC branch can propose evidence about market-value weighting; a tangent about quantum mechanics should remain local or propose a separate learning scope. It must not silently alter the finance graph.

Returning to the lesson preserves scroll position, active problem, and teaching stage. A branch summary is contextual material, not mastery evidence. Nested branches retain a visible path and bounded context. Revise or discard stale proposals when the parent session or policy changes.

**Architect now:** explicit scope and parent/session IDs. Later add richer branch trees and optional promotion of out-of-scope discoveries. Test that closing or canceling a branch prevents unauthorized late actions while preserving already committed, valid evidence.

## 8. Assessment-session capability isolation

Exam integrity must be enforced server-side, not by hiding a Tutor button. A session policy grants only approved capabilities, such as question rendering, permitted calculator use, answer submission, and timing. Tutor explanations, hints, notes lookup, answer keys, and branch tools are denied unless the assessment explicitly permits them.

The policy applies across tabs, resumed sessions, API calls, and delegated capabilities. Answer keys and private grading material must not enter client payloads or retrievable tutor context. Version the item set, rubric, accommodations, allowed tools, and mode at session start.

Practice and closed-book exams can have different policies. If assistance is legitimately enabled, label the attempt as assisted; do not preserve an independent-exam classification. Closing an interface panel cannot itself end the backend restrictions.

**Architect now:** capability checks wherever assessment endpoints exist. Later add richer exam administration. Backend restrictions protect the product's own assessment conditions; they cannot establish that a learner used no outside resources on another device.

## 9. Pedagogy policy hierarchy and conflict resolution

Proposed precedence from strongest to weakest:

1. Safety and correctness requirements.
2. Assessment integrity and session permissions.
3. Active learning goal and explicit scope constraints.
4. Necessary prerequisite requirements.
5. Pedagogical strategy, including retrieval and scaffolding.
6. Learner preferences.
7. Presentation preferences.

Separate hard constraints from soft priorities. An exam tool restriction is hard. Whether to interrupt a lesson for a prerequisite is usually a contextual decision based on severity and expected learning value. In Learn mode, “just explain it” can be respected without awarding mastery; during a closed-book assessment it cannot expose the answer.

Resolve hard constraints first, then rank feasible actions. Use deterministic tie-breakers and log conflicts, selected rules, and rejected alternatives. If no action is valid, return a clear constrained outcome rather than improvising an exception. Avoid repeatedly interrupting the learner for low-impact gaps: a short inline prerequisite explanation or later review may be sufficient.

**Architect now:** one policy owner and a versioned decision contract. Defer a configurable policy editor. Do not scatter competing pedagogical rules across prompts and interface components.

## 10. Latency DAGs and orchestration

Design each action as a directed acyclic graph of dependencies. The key question is which work blocks useful learning and which can proceed concurrently.

```text
Request + authorization
          |
          +--> intent proposal ---------+
          +--> learner snapshot --------+--> validated teaching plan
          +--> scoped source retrieval -+              |
                                              tutor generation
                                                      |
                                            required verification
                                                      |
                                             useful learner output
                                                      |
                                  optional summaries / analytics
```

Only start retrieval concurrently when the known request and authorized scope are sufficient. Otherwise perform a bounded preliminary step and retrieve after scope resolution. Avoid a false parallel design that searches unauthorized sources or must discard most of its work.

The critical path is the longest dependency path, not the sum of every task. Parallelize independent reads and tool checks, limit fan-out, propagate deadlines, cancel obsolete work, and reserve capacity for interactive requests. Slow course ingestion or exam generation must not occupy all interactive workers.

Stream useful output when the verification policy permits it. Check self-contained segments incrementally where possible; hold answer keys, scored items, and claims requiring whole-answer verification until checks complete. Do not present unverified output as verified. Optional diagrams or summaries can arrive later, but never delay the state commit required for the next decision without handling the pending state explicitly.

### Proposed per-capability latency budgets

These are initial engineering targets for measurement, not performance promises. Measure end-to-end p50/p95, time to first useful content, validated completion time, and timeout rate under realistic load.

| Capability | Illustrative p95 target | Orchestration and fallback |
|---|---|---|
| Simple definition | First useful content within 2 seconds | Small bounded plan; minimal necessary retrieval/checks; qualify unavailable verification. |
| Concept explanation | First useful content within 4 seconds; short response complete within 12 seconds | Parallel input reads; incremental delivery where allowed; optional visuals later. |
| Sidecar question | First useful content within 3 seconds | Narrow inherited scope and context; cancel superseded requests. |
| Assessment submission | Receipt within 1 second; validated short-item feedback within 6 seconds | Persist receipt first; deterministic grading where appropriate; expose pending grading for complex answers. |
| Small graph generation | Progress within 2 seconds; draft within 30 seconds | Parallel extraction of independent units, followed by graph reconciliation and validation. |
| Mock exam creation | Progress within 2 seconds; small validated exam within 90 seconds | Parallel candidate generation; bounded verification queue; global coverage and duplication checks before release. |
| Full course ingestion, deferred | Job receipt within 2 seconds; completion depends on volume | Durable background workflow, staged progress, resumable per-source processing. |

Each capability declares timeout, cancellation behavior, concurrency ceiling, quality floor, and fallback. Timeouts must not weaken assessment integrity or invent sources. A latency trace should reveal queueing, model time, tool time, verification time, and dependency waits. Prefer fewer necessary stages to indiscriminate multi-agent fan-out.

## 11. Evaluation framework: tutor, assessments, and learning outcomes

Build an evaluation boundary before broad release. Correct answers alone do not establish good teaching. Maintain versioned test sets with known concepts, learner contexts, source policies, rubrics, and expected constraints.

| Layer | What to evaluate | How to inspect it |
|---|---|---|
| Tutor | Correctness, unsupported claims, prerequisite violations, clarity, completeness, unnecessary information, learner-level fit, strategy adherence | Expert-scored examples, source/tool checks, and calibrated rubric-based judging. |
| Assessment | Solvability, answer correctness, ambiguity, novelty, concept coverage, transfer distance, difficulty, structural duplication, unintended prerequisites, answer leakage | Independent solution validation, item metadata review, adversarial attempts, and observed learner responses. |
| System | Next-action quality, state consistency, unnecessary detours, recovery, friction, retention, transfer, time to verified understanding | End-to-end scenario tests and real-learner studies with comparable starting knowledge. |

Define transfer distance operationally through changes in context, representation, and reasoning requirements. A model's label of “hard” or “novel” is a hypothesis until checked. Judge models can help triage, but agreement between models is not independent proof; use expert review and deterministic checks where available.

Primary outcome candidates are learning gain per focused minute, delayed retention, and performance on unseen transfer tasks. Track assistance level and starting knowledge. Avoid optimizing message count, session duration, or the learner estimator's own score as substitutes for external learning outcomes.

Use held-out tasks separated by concept structure or item family to reduce leakage. Report uncertainty, sample sizes, and performance across relevant learner groups. Version any launch thresholds and treat critical integrity failures as blockers. Real-world outcome comparisons require a defined baseline, appropriate consent, and sufficient observation time; do not infer causation from an attractive progress graph.

**Architect now:** a small representative evaluation set and traceable results for the core loop. Expand studies and automation after the first domain and learner population are defined.

## 12. Synthetic learner regression testing

Create repeatable simulated learner profiles with known knowledge, missing prerequisites, misconceptions, answer tendencies, fatigue or time constraints, and response preferences. Preferences such as example-first are hypotheses about presentation, not fixed scientific learning-style categories.

Example: knows TVM and NPV, does not know CAPM, and confuses all risk with volatility. A scenario asks for WACC. Check whether the system recognizes the missing dependency, provides only the necessary prerequisite support, avoids assuming CAPM, and tests the misconception independently.

Combine scripted responses for exact regression checks with constrained model-based simulations for broader coverage. Fix scenario versions and random seeds where possible. Include contradictory answers, hint use, ambiguous self-explanations, source changes, branch tangents, and interrupted sessions.

Assert both pedagogical behavior and system invariants: no state changes without admitted evidence, no answer leakage, no infinite prerequisite loop, and no unsupported mastery promotion. Compare planner/policy versions against the same starting snapshots.

**Architect now:** a few deterministic core-loop scenarios. Defer thousands of generated profiles until the evaluation machinery is reliable. Synthetic learners reveal regressions; they cannot prove that real people learn faster.

## 13. Shadow-mode deployments for model, prompt, and policy changes

Run a candidate configuration against the same authorized input snapshot as the production configuration. The production version remains the only version whose decisions reach the learner and whose evidence can change canonical state. Candidate outputs go to an isolated comparison store.

Disable candidate writes, messages, assessment mutations, and other side effects through permissions, not prompt requests. Use recorded or read-only tool results when feasible. Apply the same privacy and source-access constraints as the live path, with separate cost and concurrency limits so shadow work does not delay learners.

Compare action selection, source grounding, prerequisite detours, rubric results, estimated cost, and latency. Investigate meaningful disagreements with expert review. A candidate's different teaching action cannot reveal the learner's counterfactual response; shadow mode alone cannot establish improved learning outcomes.

Proposed rollout: offline evaluation → isolated shadow comparison → reviewed small rollout → measured expansion. Define rollback conditions before promotion. Pin active assessment configurations across a rollout. Retain the old bundle and ensure evidence interpretation remains versioned.

**Architect now:** configuration IDs and side-effect boundaries. Defer live shadow infrastructure until traffic and release cadence justify it.

## 14. Mastery uncertainty vs mastery probability

Define what the estimate predicts. One possible target is the probability of independent success on a specified class of concept tasks under defined conditions. That is different from confidence in the estimate, which reflects how much and how varied the supporting evidence is.

Two learners can both have an estimated success probability of 0.80 while one has answered only one narrow question and the other has completed varied independent tasks over time. The first estimate should remain much more uncertain. Repeated near-duplicate questions do not supply the same information as varied evidence.

Store evidence coverage, recency, assistance, task type, and an uncertainty representation such as a posterior distribution or calibrated interval. Distinguish current knowledge estimates from future retention forecasts and from source uncertainty. Do not invent confidence percentages merely to populate the UI.

Recommendation implications: high uncertainty can justify a brief diagnostic; credible low mastery can justify teaching; credible strong performance can justify transfer or delayed review. Uncertainty is not failure. The interface can say “promising, needs confirmation” instead of giving every estimate a precise percentage or a red label.

**Architect now:** separate estimate and uncertainty fields, with honest unknown states. Select and calibrate the estimator against observed outcomes later.

## 15. Source hierarchy and truth policies

Source policy decides which references establish scope, definitions, and expected answers. It should be explicit in actions, retrieval, verification, and assessment generation.

**Proposed Course Mode hierarchy:** current instructor-approved materials and corrections → assigned textbook edition → approved course references → trusted external references → ungrounded model prior. A specific course may configure exceptions, such as a syllabus designating the textbook as definitive for a particular topic.

**General Mode:** prioritize appropriate authoritative evidence for the subject, including recency when material can change. Do not carry a course-specific convention into general teaching without labeling it. General Mode is not permission to treat model memory as verified evidence.

Priority sets the teaching frame; it does not make a demonstrably incorrect source correct. Surface contradictions: “The course uses convention X; reference Y uses convention Z.” For an actual error or unresolved conflict, label it, cite the relevant locations, and avoid silently manufacturing agreement. Assessments should specify the intended convention and avoid disputed items until resolved.

**Architect now:** source-policy references, source locators, and an explicit mode field compatible with a simple initial trusted source set. The full Course Mode workspace and user-managed hierarchy remain deferred.

## 16. Cross-cutting contracts for future extensibility

These engineering elaborations support the discussion's state-transition architecture:

- **Separate state domains:** distinguish learner estimates, goal progress, curriculum definitions, session state, assessment state, and generated artifacts. Each needs an owner and revision rules.
- **Durable execution:** represent pending, running, awaiting verification, completed, failed, and canceled work explicitly. Resume interrupted jobs without duplicating evidence.
- **Projection consistency:** derive progress badges, graph colors, and recommendations from a known committed state revision. A UI should label pending grading instead of implying immediate mastery.
- **Verification by content type:** use calculation or symbolic checks for suitable mathematics, execution/tests for suitable code, and cited evidence for factual claims. Multiple agreeing models are not a universal verifier.
- **Capability contracts:** declare inputs, outputs, permissions, side effects, evidence eligibility, verification requirements, version, and latency policy. New features plug into these contracts.
- **Correction paths:** identify artifacts affected by a faulty source, prompt, item, or rubric; supersede invalid evidence and explain recalculations. Keep historical claims distinguishable from current corrected estimates.

Keep these contracts small. A generic event platform, distributed agent fleet, or full administrative console is not a prerequisite for the first useful learning loop.

# Future product features

## 17. Goal Compiler

Translate a natural-language objective into a bounded goal object: outcome, deadline, time available, target depth, coverage, assessment conditions, retention horizon, and known constraints. “Prepare for tomorrow's lecture,” “pass an exam in 21 days,” and “become strong at valuation” should not produce identical learning sequences.

Compile the goal into a selected concept subgraph, minimum prerequisite closure, coverage priorities, and an initial action plan. Show inferred assumptions for lightweight correction. Ask only for missing information that materially changes the plan; never invent exam weights or available study time.

Version the goal as constraints change. Replan from current evidence instead of discarding progress. If the time budget is insufficient, show a narrower achievable scope and the coverage tradeoff rather than promising completion.

**Depends on:** action protocol, graph IDs, learner uncertainty, and policy hierarchy. **Future validation:** less setup friction and better goal-relevant independent performance. The MVP may use a simple explicit goal; the full compiler and planning UI are future work.

## 18. “Why this?” explainability

Attach an unobtrusive explanation action to recommendations, reviews, mastery changes, and prerequisite detours. “Terminal value is the remaining prerequisite for DCF” should come from graph edges and the recorded planner decision. Exam-weight claims require an actual source for those weights.

Use progressive disclosure: a one-sentence reason first, then evidence, source links, and goal dependencies. Allow “study something else” or a corrected goal where policy permits. Explain uncertain recommendations honestly: “A short check would help us decide whether you need this lesson.”

**Depends on:** transition and decision records. **Future validation:** fewer manual requests for justification and fewer unwanted detours without reduced learning outcomes. Store rationale data now; defer an explanation control on every surface.

## 19. Mistake Replay and misconception clustering

Within Practice, group past mistakes by likely underlying misconception, not simply incorrect-answer count. A cluster might connect book-value weighting errors across WACC questions while keeping arithmetic slips separate.

Store each mistake with concept, item/rubric version, learner response, assistance level, proposed misconception, and confidence. Combine rule-based tags and semantic comparison; allow uncertain or overlapping clusters. Never treat an inferred misconception as a permanent label about the person.

“Fix this” opens a short targeted explanation, contrasting example, and fresh independent check. Preserve the original attempt for review but use a new task to assess repair. Resolution should depend on varied or delayed evidence, not merely rereading the correction.

**UI:** recurring issue card, examples, last occurrence, repair action, and outcome. **Future validation:** reduced recurrence on unseen problems. **Depends on:** evidence lineage, misconception taxonomy, and assessment generation.

## 20. Knowledge Frontier

Show concepts the learner is ready to approach because prerequisite evidence is sufficient for the intended task. Distinguish **ready now**, **needs a brief diagnostic**, **one prerequisite to repair**, and **outside the active goal**.

Compute the frontier from the current graph version, learner uncertainty, and goal. Rank feasible concepts by expected usefulness, retention needs, and effort; do not equate every unexplored node with the next useful lesson. Use minimum prerequisite closure to avoid restarting from fundamentals unnecessarily.

The frontier is a recommendation, not a hard prohibition on curiosity. Explain blockers and offer a small bridge or diagnostic. A graph migration can change readiness without meaning the learner has forgotten something.

**Depends on:** graph semantics, uncertainty, and policy. **Future validation:** fewer unnecessary prerequisite lessons and sustained independent performance. Basic next-concept selection belongs in the loop; rich frontier visualization is deferred.

## 21. Challenge Mode and scaffolding fade

Make growing independence visible: explanation and worked example → guided problem → partially supported problem → independent problem → novel transfer scenario. Move between stages based on evidence, not time spent or clicks.

A support indicator can show the current level and offer a request for help. Taking a hint is legitimate learning behavior, but the resulting evidence must be marked assisted. Restore support when the learner struggles; fading is reversible and should not feel punitive.

Challenge Mode requires separate control over difficulty, transfer distance, and scaffolding. Removing hints does not automatically make an item a valid transfer task. Coordinate with Teaching Gear so a manual support preference cannot silently change evidence classification.

**Depends on:** assistance metadata, action parameters, and assessment policies. **Future validation:** improved unassisted transfer without excessive frustration or dropout.

## 22. Teach-back

Invite a short written or spoken explanation and evaluate conceptual coverage against versioned invariants, not grammar, eloquence, or accent. A WACC rubric might check weighted financing costs, market-value weights, the debt tax adjustment, and opportunity-cost interpretation within the course definition.

Return a concise coverage view: demonstrated, unclear, or missing, with a targeted follow-up. Spoken answers require transcription confidence and an opportunity to correct material transcription errors. Distinguish missing mention from evidence of misunderstanding.

Teach-back can produce useful evidence, but its strength depends on independence, rubric quality, and whether the learner just saw the answer. Do not automatically classify every fluent explanation as strong mastery. Follow with application or delayed transfer where needed.

**Depends on:** rubrics, evidence ingestion, and optionally transcription. **Future validation:** agreement with expert conceptual scoring and prediction of independent performance. Text-first implementation can precede audio.

## 23. Learning Replay and history lenses

Show what changed over a selected period: newly demonstrated concepts, strengthened retention evidence, repaired misconceptions, new uncertainty, and remaining blockers. Build the view from evidence and transition records rather than a model-generated summary of chat history alone.

Let learners open an event to see the task and why it affected the estimate. Label recalibration, time-based forecasts, and curriculum migration separately from new performance. A score increasing from one value to another is an estimate change, not proof of an equivalent percentage increase in knowledge.

Offer a short weekly recap and a deeper historical graph overlay without adding a mandatory analytics destination. Avoid rankings or streaks that incentivize easy repeated questions.

**Depends on:** versioned projections and transition reasons. **Future validation:** learners can accurately explain their progress and choose a useful next action with less effort.

## 24. UI lenses, overlays, and navigation

Keep persistent navigation as **Learn | Practice | Notebook**. Introduce additional detail within the existing workspace rather than adding a top-level tab for every feature.

| Surface | Future elements and behavior |
|---|---|
| Learn | Knowledge canvas, active concept/lesson card, contextual sidecar, Teaching Gear, command box, source indicator, Why this?, frontier markers, scaffolding status, breadcrumbs, and contextual quick actions. |
| Practice | One mode switcher: Review, Flashcards, Quiz, Exam. Scope choices: Recommended, Current concept, Current module, Past mistakes, Custom; Whole course only once course workspaces exist. |
| Exam | Clean focused interface with allowed tools, timer where relevant, submission state, and accessible navigation governed by the backend session policy. |
| Notebook | Personal notes, saved explanations, worked examples, bookmarks, cited excerpts, and concept backlinks; optional split view highlights related nodes. |

Quick actions can include **Simpler, Example, Visualize, Go deeper, Practice, Teach back**. Show the few relevant actions in context rather than displaying the entire set permanently. Preserve lesson position and branch breadcrumbs across exploration.

| Lens / overlay | Meaning |
|---|---|
| Progress | Demonstrated mastery with uncertainty, distinct from mere exposure. |
| Readiness | Goal coverage, prerequisite blockers, and sourced exam importance where available. |
| Memory | Fragility and review forecasts, labeled as predictions. |
| Source | Source-to-concept links, revisions, coverage gaps, and conflicts. |
| History | Evidence-backed changes over time, including migrations and recalibrations. |

Use the same graph and state underneath all lenses. Each lens needs a legend and a consistent revision, with text or symbols as alternatives to color. Prefer Focus view around the current concept by default; Roadmap and broader Map views can support planning and exploration. Ensure keyboard navigation, small-screen alternatives, and readable list views for dense graphs.

**Future validation:** faster resumption and fewer navigation actions per useful learning step. Do not ship all lenses together merely because the shared graph makes them feasible.

## 25. Additional connected future capabilities

### Multiple representations / “Explain from another world”

Maintain ways to express the same conceptual invariant: formal explanation, visual intuition, simple language, derivation, worked example, analogy, counterexample, and misconception analysis. Select a representation from observed outcomes and current task demands, not a fixed learner label. Record which representation preceded later independent success. Analogies should state their limits and pass the same correctness checks as other teaching.

### Purpose and prerequisite pathways

Extend Why this? into a small local map: what a concept depends on, what it enables, and how it connects to the active goal. Prefer a few relevant edges over an entire domain graph. Links and weights need provenance; absent exam weights should remain absent.

### Notebook as a concept-linked learning artifact store

Preserve saved explanations, source excerpts, and worked examples with concept backlinks and original provenance. Personal edits remain distinguishable from generated or quoted material. Notes can inform context and review selection, but creating or reading a note must not award mastery.

### Outcome-informed teaching adaptation

Over time, compare interventions such as intuition-first or example-first against later independent performance. Account for concept difficulty, prior knowledge, and assistance before attributing success to presentation. This is a future evaluation capability, not a reason to build a complex personalization engine before the basic teaching loop works.

# Deferred workspace/course features

## 26. FUTURE FEATURE — Courses / Classes Workspace

**Explicitly deferred. This is not MVP scope.** Creating and managing courses could become a large product in its own right. It is intentionally postponed so the current product stays focused on maximizing learning value and minimizing learning friction. Preserve source and curriculum compatibility today; do not build the workspace, upload pipeline, collaboration system, or course administration merely to make the architecture feel complete.

### 26.1 Purpose and learner experience

A learner could create a named class/course workspace, such as “Corporate Finance — Autumn 2026,” and attach the materials that define what they are learning. The workspace supplies a bounded source collection, curriculum context, goals, and truth policy to the existing Learn, Practice, and Notebook experiences.

Supported material types could include lecture slides, PDFs, books or selected chapters, personal notes, web references, audio recordings and transcripts, assignments, syllabus, worked solutions where access is authorized, reading lists, and other learning materials. Store role and status explicitly: instructor slide deck, required textbook, personal note, optional reference, or assessment artifact are not interchangeable.

Proposed flow: create workspace → attach a small set of materials → classify their roles → review extracted scope and conflicts → publish a curriculum version → enter the existing learning loop. Allow useful learning once sufficient approved material is ready; do not force a learner to organize every file first.

### 26.2 Proposed domain objects

| Object | Responsibility |
|---|---|
| Workspace | Course identity, owner/members, access rules, active curriculum and source policy. |
| Source and SourceRevision | Material identity plus immutable content revisions, origin, rights/access metadata, type, and processing state. |
| SourceSegment | Page, slide, section, paragraph, or timestamp range with extracted content and confidence. |
| SourcePolicy | Ordered authority rules, topic-specific overrides, conflict handling, and external fallback policy. |
| CurriculumVersion | Approved concept set, prerequisites, objectives, scope, and graph migration reference. |
| ConceptSourceLink | Segment-to-concept association with relationship type, confidence, and revision. |
| IngestionJob | Processing stages, retries, errors, cancellation, and resulting draft artifacts. |
| Membership / Grant | Permission to view, edit, publish, retrieve, or use particular material. |

Learner evidence stays owned by the learner-state system, linked to workspace/curriculum context. Shared course material must not imply shared personal mastery records. A general concept identity can be reused while course-specific definitions and mappings remain explicit.

### 26.3 Source hierarchy inside a course

Offer sensible defaults: instructor-approved corrections and current teaching materials, required textbook edition, approved supplementary references, trusted external sources, then model prior. Let authorized users classify materials and resolve topic-specific precedence. A personal note or automatically generated transcript should not become instructor authority simply because it was uploaded most recently.

The syllabus may govern coverage and grading expectations while a textbook governs a concept definition. Record such distinctions rather than forcing every decision through a single global ranking. Show unresolved contradictions and missing source coverage before generating scored items.

Keep answer keys, unpublished assessment material, and instructor-only documents in separate access scopes. Retrieval permission must reflect the active assessment session as well as workspace membership.

### 26.4 Ingestion and transcription

Use a staged, resumable pipeline:

1. Check upload access, supported type, size, content identity, and document safety; retain original provenance.
2. Extract text and layout from slides/PDFs; use OCR for scans with explicit confidence flags.
3. Preserve equations, tables, diagrams, headings, page numbers, and slide boundaries where possible. Route uncertain extraction for review instead of silently losing important structure.
4. Transcribe audio with timestamps and optional speaker labels; preserve alignment to the original recording and allow transcript corrections.
5. Segment content into retrievable units, attach metadata and permissions, and identify duplicate or overlapping material.
6. Propose concepts, objectives, source links, and prerequisite edges in a draft graph.
7. Validate structure and source coverage; surface ambiguity and publish only the approved result.

Show per-material states such as uploaded, extracting, needs review, ready, or failed. Support retries without duplicate sources or graph nodes. An audio transcript is derived material with an error rate; mathematical notation and speaker attribution require particular care. Do not overwrite the recording or original extraction when a transcript is corrected.

Treat all ingested content as source data, never as executable instructions to the tutor or tools. Permission checks must occur before retrieval results reach a model. Long-running ingestion belongs in a background queue with cancellation and resource limits.

### 26.5 Concept graph generation from attached materials

Generate candidate nodes from learning objectives, definitions, worked problems, syllabus structure, and assignments. Separate **prerequisite**, **part of**, **related to**, and **appears in assessment** relationships. Mere co-occurrence does not establish a prerequisite.

Resolve aliases and duplicate concepts across slides, textbook chapters, and notes. Preserve course-specific meaning where apparently identical terms differ. Every proposed node should have supporting material or an explicit inferred/external label. Flag weakly supported nodes and inferred edges for review.

Use the syllabus to bound coverage; use authorized assessment descriptions to infer required task types. Do not invent topic weighting from document length. Run graph integrity checks and permit review before the graph becomes the active learning specification.

### 26.6 Linking sources to concept nodes

Maintain many-to-many links with source revision, page/slide/timestamp locator, relationship type, extraction confidence, and access scope. A concept can be defined in a textbook, illustrated in a lecture, and exercised in an assignment.

Selecting a citation should open the exact relevant location. The Source lens can distinguish authoritative definitions, examples, exercises, conflicting statements, and uncovered concepts. Generated lessons and questions should retain the specific segments that supported them, not just a filename.

Deleting or replacing a material must not silently redirect old citations to unrelated new text. Show withdrawn or unavailable sources honestly while applying the appropriate retention and deletion rules.

### 26.7 Versioning when files change

A changed file creates a new source revision. Identify changes at meaningful segments, then propose their impact on concepts, graph edges, lessons, and assessment items. A filename staying the same does not mean content is unchanged; a new filename does not necessarily mean a new conceptual source.

Produce a draft curriculum update and an explicit migration report: added topics, removed scope, renames, splits/merges, definition changes, and stale source bindings. Do not regenerate the graph in place or reset the learner's history.

Pin active assessments and learning artifacts to their original versions. New sessions can use the published update after review. Preserve evidence that still applies; flag uncertain mappings for diagnostic confirmation. Rollback selects a previous valid version rather than deleting the intervening history.

### 26.8 Permissions, provenance, and privacy

Start future workspace design with clear ownership. Possible later roles include owner, editor/instructor, and learner/viewer, but collaboration is not required for the first personal workspace release. Enforce least privilege for each source, derived segment, generated artifact, and retrieval request.

Record uploader, origin, upload time, revision hash, material role, applicable use/access restrictions, and extraction/transcription lineage. Audio recordings may involve other people; support appropriate access, consent handling, and retention choices. Do not assume that uploading a book grants redistribution rights or makes it available to other workspaces.

Permission changes must propagate to retrieval indexes and derived previews. Never expose one learner's notes, recordings, or mastery to another through shared retrieval. Deletion should cover original and derived material as required; retain only permitted audit metadata rather than treating “immutable history” as a reason to keep prohibited content forever.

### 26.9 Course Mode vs General Mode behavior

When **Course Mode** is active, the planner, retriever, tutor, verifier, and assessor all receive the workspace's versioned source policy and curriculum scope. Retrieve relevant course material first, teach its terminology and expected conventions, and cite it precisely.

If course coverage is insufficient, make external supplementation explicit and follow the configured fallback rule. If external evidence contradicts the course, distinguish a convention difference from a factual error. Show both where useful and avoid presenting a known error as universally true. Generate course assessments only from sufficiently resolved expectations.

When **General Mode** is active, broaden the teaching frame to suitable authoritative general sources. Preserve the learner's course history and source links; switching modes does not rewrite old evidence or automatically transfer course-specific mastery into every broader interpretation.

Display a compact active-mode/source indicator. Mode changes should take effect at a coherent session boundary, with active exams remaining pinned to their assessment policy. A mode toggle must never act as a bypass for exam restrictions or source permissions.

### 26.10 Workspace UI, staged delivery, and deferral gates

Future UI could include a workspace selector, create/edit dialog, material library, attach control, source-role editor, ingestion status, transcript review, graph-change preview, source-conflict notice, and Course/General Mode indicator. Integrate these into the existing learning environment; avoid turning routine learning into file administration.

Possible later increments, subject to evidence of need:

1. Personal workspace with a small set of text/PDF sources and explicit source hierarchy.
2. Reliable source revisions, citations, graph review, and curriculum migration.
3. Audio/transcription and richer media extraction.
4. Sharing, instructor review, and institutional controls only after separate product validation.

Revisit this feature when the core loop demonstrates useful learning outcomes, users repeatedly need bounded source collections, and the team can support ingestion correctness and permissions without weakening the learning experience. These are decision gates, not a promised schedule.

**Acceptance scenarios for a future release:** a revised syllabus preserves valid progress; correcting a transcript updates affected draft links; revoked material becomes inaccessible to retrieval; Course Mode cites the selected course revision; a source conflict is surfaced; an interrupted upload resumes without duplicates; private assignment solutions cannot leak into a closed-book exam.

## 27. Architecture decisions to preserve now; work to postpone

| Preserve in today's core design | Postpone until justified |
|---|---|
| Typed actions and explicit capability permissions | Full Goal Compiler and workflow editor |
| Evidence admission and one canonical state owner | Large-scale learner simulation infrastructure |
| Stable concept IDs and version references | Automated course graph migration console |
| Provenance, transition reasons, and uncertainty | Full History/Source/Readiness overlays |
| Source-policy field and scoped retrieval contracts | User-managed Courses / Classes Workspace |
| Assessment restrictions and assistance metadata | Institutional assessment administration |
| Critical-path traces and bounded concurrent execution | Large distributed orchestration platform |
| Small, meaningful core-loop evaluations | Broad personalization experiments and live shadow fleet |

Before implementing a future feature, name the learner problem, the expected reduction in friction or improvement in verified understanding, the dependencies, and the evidence that would justify keeping it. Preserve room for future capabilities through sound boundaries; keep present delivery centered on the learning loop.
