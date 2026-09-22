"""Read-only contracts and diagnostics for the immediate-adaptation slice."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field
from sqlalchemy import bindparam, text

from .session_models import ApiModel

IMMEDIATE_ADAPTATION_POLICY_VERSION = "immediate-adaptation-contract-v1"


class AdaptiveObservabilityError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PolicyScenario(ApiModel):
    id: str
    description: str
    expected_action: Literal["teach", "check", "repair"]
    must_not: list[str] = Field(default_factory=list)


POLICY_SCENARIOS: tuple[PolicyScenario, ...] = (
    PolicyScenario(
        id="new-concept",
        description="A new concept with no lesson exposure is introduced.",
        expected_action="teach",
        must_not=["claim_mastery", "repair_without_evidence"],
    ),
    PolicyScenario(
        id="taught-without-check",
        description="A lesson exists but no fresh assessment evidence exists.",
        expected_action="check",
        must_not=["continue_without_evidence"],
    ),
    PolicyScenario(
        id="first-independent-miss",
        description="One valid independent miss needs a distinct diagnostic check.",
        expected_action="check",
        must_not=["confirm_misconception", "repair_from_single_miss"],
    ),
    PolicyScenario(
        id="repeated-distinct-miss",
        description="Consistent misses across distinct item families support targeted repair.",
        expected_action="repair",
        must_not=["claim_permanent_deficit"],
    ),
    PolicyScenario(
        id="assisted-success",
        description="Success after hints, reveal, retry, or remediation needs a fresh independent check.",
        expected_action="check",
        must_not=["claim_independent_demonstration", "continue_route"],
    ),
    PolicyScenario(
        id="fresh-independent-success-after-repair",
        description="A fresh independent success after repair permits route continuation.",
        expected_action="teach",
        must_not=["claim_calibrated_mastery"],
    ),
)


class PolicyEvidenceObservation(ApiModel):
    id: str
    kind: str
    outcome: str
    condition: str
    reliability: float
    occurred_at: datetime
    item_id: str | None = None
    item_family: str | None = None
    misconception_code: str | None = None
    assistance_exposed: bool


class ImmediateAdaptationInput(ApiModel):
    policy_version: str = IMMEDIATE_ADAPTATION_POLICY_VERSION
    learner_id: str
    session_id: str
    session_revision: int
    graph_id: str
    graph_version: int
    concept_id: str
    concept_state: str | None = None
    concept_state_version: int | None = None
    lesson_exposed: bool = False
    latest_lesson_completed_at: datetime | None = None
    evidence: list[PolicyEvidenceObservation] = Field(default_factory=list)
    active_misconception_codes: list[str] = Field(default_factory=list)


class ConceptSourceSnapshot(ApiModel):
    source: Literal["canonical_state", "review_memory", "learner_graph"]
    present: bool
    raw_value: str | None = None
    revision: int | None = None
    updated_at: datetime | None = None


class ConceptSourceComparison(ApiModel):
    learner_id: str
    concept_id: str
    sources: list[ConceptSourceSnapshot]
    raw_values_differ: bool


class ActivityCorrelationDiagnostic(ApiModel):
    entity_kind: Literal["state_event", "evidence", "recommendation_interaction"]
    entity_id: str
    kind: str
    status: Literal["resolved", "ambiguous", "orphaned"]
    session_ids: list[str] = Field(default_factory=list)
    unresolved_references: list[str] = Field(default_factory=list)


class ActivityCorrelationReport(ApiModel):
    learner_id: str
    resolved_count: int
    ambiguous_count: int
    orphaned_count: int
    diagnostics: list[ActivityCorrelationDiagnostic] = Field(default_factory=list)


class ClosedLoopLink(ApiModel):
    """One hop in the adaptive decision → outcome chain."""

    kind: Literal[
        "recommendation_set",
        "recommendation",
        "presentation",
        "attempt",
        "evidence",
        "state_transition",
        "schedule",
        "next_recommendation_set",
    ]
    id: str
    label: str
    details: dict[str, Any] = Field(default_factory=dict)


class ClosedLoopChain(ApiModel):
    learner_id: str
    session_id: str
    concept_id: str | None = None
    links: list[ClosedLoopLink] = Field(default_factory=list)
    complete: bool = False


def _object(value: str | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    return json.loads(value) if isinstance(value, str) else value


class AdaptiveObservabilityService:
    """Read existing stores without mutating or synthesizing learner state."""

    def __init__(self, store: Any):
        self.store = store

    def closed_loop_chain(
        self,
        learner_id: str,
        session_id: str,
        concept_id: str | None = None,
    ) -> ClosedLoopChain:
        """Project recommendation → evidence → state → schedule → next decision."""
        session = self.store.get_session(session_id)
        if session is None or session.learner_id != learner_id:
            raise AdaptiveObservabilityError(
                "session_not_found",
                "The learning session is not available.",
                404,
            )
        target = concept_id or session.current_concept_id
        links: list[ClosedLoopLink] = []
        with self.store.engine.connect() as connection:
            sets = connection.execute(text("""
                SELECT id, status, input_digest, fulfilled_evidence_id, superseded_by_set_id, payload, created_at
                FROM recommendation_sets
                WHERE owner_id=:owner AND session_id=:session
                ORDER BY created_at ASC, id ASC
            """), {"owner": learner_id, "session": session_id}).mappings().all()
            for row in sets:
                payload = _object(row["payload"])
                primary = next(
                    (
                        item for item in payload.get("recommendations") or []
                        if item.get("isPrimary") or item.get("is_primary")
                    ),
                    (payload.get("recommendations") or [None])[0],
                )
                if target and primary and primary.get("conceptId") not in {None, target}:
                    continue
                links.append(ClosedLoopLink(
                    kind="recommendation_set",
                    id=row["id"],
                    label=row["status"],
                    details={
                        "inputDigest": row["input_digest"],
                        "fulfilledEvidenceId": row["fulfilled_evidence_id"],
                        "supersededBySetId": row["superseded_by_set_id"],
                        "pedagogicalAction": (primary or {}).get("pedagogicalAction") or (primary or {}).get("pedagogical_action"),
                        "whyCode": (primary or {}).get("whyCode") or (primary or {}).get("why_code"),
                    },
                ))
                if primary and primary.get("id"):
                    links.append(ClosedLoopLink(
                        kind="recommendation",
                        id=str(primary["id"]),
                        label=str((primary or {}).get("pedagogicalAction") or (primary or {}).get("pedagogical_action") or "action"),
                        details={"setId": row["id"], "conceptId": primary.get("conceptId")},
                    ))
                if row["fulfilled_evidence_id"]:
                    evidence = connection.execute(text("""
                        SELECT id, kind, outcome, condition, concept_id, provenance_json
                        FROM evidence WHERE id=:id AND learner_id=:owner
                    """), {"id": row["fulfilled_evidence_id"], "owner": learner_id}).mappings().first()
                    if evidence:
                        provenance = _object(evidence["provenance_json"])
                        links.append(ClosedLoopLink(
                            kind="evidence",
                            id=evidence["id"],
                            label=f"{evidence['outcome']}:{evidence['condition']}",
                            details={
                                "kind": evidence["kind"],
                                "conceptId": evidence["concept_id"],
                                "presentationId": provenance.get("presentationId"),
                                "itemId": provenance.get("itemId"),
                                "itemFamily": provenance.get("itemFamily"),
                            },
                        ))
                        if provenance.get("presentationId"):
                            links.append(ClosedLoopLink(
                                kind="presentation",
                                id=str(provenance["presentationId"]),
                                label="presentation",
                                details={"itemId": provenance.get("itemId")},
                            ))
                        if provenance.get("attemptId"):
                            links.append(ClosedLoopLink(
                                kind="attempt",
                                id=str(provenance["attemptId"]),
                                label="attempt",
                                details={},
                            ))
                        transition = connection.execute(text("""
                            SELECT id, kind, payload_json FROM state_events
                            WHERE learner_id=:owner AND kind='state.transition'
                              AND payload_json LIKE :needle
                            ORDER BY recorded_at DESC LIMIT 1
                        """), {"owner": learner_id, "needle": f"%{evidence['id']}%"}).mappings().first()
                        if transition:
                            links.append(ClosedLoopLink(
                                kind="state_transition",
                                id=transition["id"],
                                label="state.transition",
                                details=_object(transition["payload_json"]),
                            ))
                        schedule = connection.execute(text("""
                            SELECT id, status, due_at, originating_evidence_id
                            FROM review_schedules
                            WHERE learner_id=:owner AND concept_id=:concept
                              AND originating_evidence_id=:evidence
                            ORDER BY updated_at DESC LIMIT 1
                        """), {
                            "owner": learner_id,
                            "concept": evidence["concept_id"],
                            "evidence": evidence["id"],
                        }).mappings().first()
                        if schedule:
                            due = schedule["due_at"]
                            due_at = due.isoformat() if hasattr(due, "isoformat") else (str(due) if due else None)
                            links.append(ClosedLoopLink(
                                kind="schedule",
                                id=schedule["id"],
                                label=schedule["status"],
                                details={"dueAt": due_at},
                            ))
            current = next((row for row in sets if row["status"] == "current"), None)
            if current and (not links or links[-1].id != current["id"]):
                links.append(ClosedLoopLink(
                    kind="next_recommendation_set",
                    id=current["id"],
                    label="current",
                    details={"inputDigest": current["input_digest"]},
                ))
        kinds = {link.kind for link in links}
        complete = {"recommendation_set", "evidence"}.issubset(kinds) and (
            "next_recommendation_set" in kinds or any(link.label == "current" for link in links if link.kind == "recommendation_set")
        )
        return ClosedLoopChain(
            learner_id=learner_id,
            session_id=session_id,
            concept_id=target,
            links=links,
            complete=complete,
        )

    def policy_input(
        self,
        learner_id: str,
        session_id: str,
        concept_id: str | None = None,
    ) -> ImmediateAdaptationInput:
        session = self.store.get_session(session_id)
        if session is None or session.learner_id != learner_id:
            raise AdaptiveObservabilityError(
                "session_not_found",
                "The learning session is not available.",
                404,
            )
        target = concept_id or session.current_concept_id
        if target is None:
            raise AdaptiveObservabilityError(
                "concept_required",
                "Choose a concept before inspecting adaptive policy inputs.",
                409,
            )
        graph = self.store.get_graph(session.graph_id)
        if graph is None or target not in {concept.id for concept in graph.concepts}:
            raise AdaptiveObservabilityError(
                "concept_not_in_session",
                "The concept is not part of this learning session.",
                404,
            )

        with self.store.engine.connect() as connection:
            state = connection.execute(text("""
                SELECT status, version FROM learner_concept_states
                WHERE learner_id=:owner AND concept_id=:concept
            """), {"owner": learner_id, "concept": target}).mappings().first()
            rows = connection.execute(text("""
                SELECT id, kind, outcome, condition, reliability, occurred_at,
                       provenance_json
                FROM evidence
                WHERE learner_id=:owner AND concept_id=:concept
                  AND graph_id=:graph AND admission_status='accepted'
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT 20
            """), {"owner": learner_id, "concept": target, "graph": session.graph_id}).mappings().all()
            misconceptions = connection.execute(text("""
                SELECT code FROM misconception_hypotheses
                WHERE learner_id=:owner AND concept_id=:concept AND status='active'
                ORDER BY code
            """), {"owner": learner_id, "concept": target}).scalars().all()
            lesson_event = connection.execute(text("""
                SELECT occurred_at FROM state_events
                WHERE learner_id=:owner AND session_id=:session
                  AND concept_id=:concept AND kind='lesson.completed'
                ORDER BY occurred_at DESC, recorded_at DESC
                LIMIT 1
            """), {
                "owner": learner_id,
                "session": session.id,
                "concept": target,
            }).mappings().first()

        evidence: list[PolicyEvidenceObservation] = []
        for row in rows:
            provenance = _object(row["provenance_json"])
            item_id = (
                provenance.get("itemId")
                or provenance.get("reviewItemId")
                or provenance.get("presentationId")
            )
            item_family = (
                provenance.get("itemFamily")
                or provenance.get("family")
                or provenance.get("semanticClusterId")
            )
            assistance_exposed = row["condition"] == "assisted" or bool(
                provenance.get("hintIds")
                or provenance.get("answerRevealed")
                or provenance.get("retryOf")
                or provenance.get("remediationId")
            )
            evidence.append(PolicyEvidenceObservation(
                id=row["id"],
                kind=row["kind"],
                outcome=row["outcome"],
                condition=row["condition"],
                reliability=float(row["reliability"]),
                occurred_at=row["occurred_at"],
                item_id=str(item_id) if item_id is not None else None,
                item_family=str(item_family) if item_family is not None else None,
                misconception_code=(
                    str(provenance["misconceptionCode"])
                    if provenance.get("misconceptionCode") is not None
                    else None
                ),
                assistance_exposed=assistance_exposed,
            ))

        return ImmediateAdaptationInput(
            learner_id=learner_id,
            session_id=session.id,
            session_revision=session.state_version,
            graph_id=session.graph_id,
            graph_version=session.graph_revision,
            concept_id=target,
            concept_state=state["status"] if state else None,
            concept_state_version=int(state["version"]) if state else None,
            lesson_exposed=lesson_event is not None,
            latest_lesson_completed_at=lesson_event["occurred_at"] if lesson_event else None,
            evidence=evidence,
            active_misconception_codes=list(misconceptions),
        )

    def compare_concept_sources(
        self,
        learner_id: str,
        concept_id: str,
    ) -> ConceptSourceComparison:
        with self.store.engine.connect() as connection:
            canonical = connection.execute(text("""
                SELECT status, version, updated_at FROM learner_concept_states
                WHERE learner_id=:owner AND concept_id=:concept
            """), {"owner": learner_id, "concept": concept_id}).mappings().first()
            review = connection.execute(text("""
                SELECT mastery_estimate, updated_at FROM concept_memory_states
                WHERE learner_id=:owner AND concept_id=:concept
            """), {"owner": learner_id, "concept": concept_id}).mappings().first()
            graph_rows = connection.execute(text("""
                SELECT payload FROM learner_graph_concepts WHERE learner_id=:owner
            """), {"owner": learner_id}).scalars().all()

        learner_graph = None
        for payload in graph_rows:
            candidate = _object(payload)
            if concept_id in (candidate.get("source_concept_ids") or candidate.get("sourceConceptIds") or []):
                learner_graph = candidate
                break

        graph_updated = None
        if learner_graph:
            graph_updated = learner_graph.get("updated_at") or learner_graph.get("updatedAt")
            if isinstance(graph_updated, str):
                graph_updated = datetime.fromisoformat(graph_updated.replace("Z", "+00:00"))
        sources = [
            ConceptSourceSnapshot(
                source="canonical_state",
                present=canonical is not None,
                raw_value=canonical["status"] if canonical else None,
                revision=int(canonical["version"]) if canonical else None,
                updated_at=canonical["updated_at"] if canonical else None,
            ),
            ConceptSourceSnapshot(
                source="review_memory",
                present=review is not None,
                raw_value=review["mastery_estimate"] if review else None,
                updated_at=review["updated_at"] if review else None,
            ),
            ConceptSourceSnapshot(
                source="learner_graph",
                present=learner_graph is not None,
                raw_value=learner_graph.get("state") if learner_graph else None,
                updated_at=graph_updated,
            ),
        ]
        values = {source.raw_value for source in sources if source.raw_value is not None}
        return ConceptSourceComparison(
            learner_id=learner_id,
            concept_id=concept_id,
            sources=sources,
            raw_values_differ=len(values) > 1,
        )

    def activity_correlations(
        self,
        learner_id: str,
        limit: int = 100,
    ) -> ActivityCorrelationReport:
        with self.store.engine.connect() as connection:
            owned_sessions = set(connection.execute(text("""
                SELECT id FROM learning_sessions WHERE learner_id=:owner
            """), {"owner": learner_id}).scalars().all())
            actions = dict(connection.execute(text("""
                SELECT a.id, a.session_id
                FROM learning_actions a
                JOIN learning_sessions s ON s.id=a.session_id
                WHERE s.learner_id=:owner
            """), {"owner": learner_id}).all())
            practice_rows = connection.execute(text("""
                SELECT id, kind, payload FROM practice_records
                WHERE owner_id=:owner AND kind IN ('quiz', 'review_session')
            """), {"owner": learner_id}).mappings().all()
            evidence_rows = connection.execute(text("""
                SELECT id, kind, source_event_id, provenance_json
                FROM evidence
                WHERE learner_id=:owner
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
            """), {"owner": learner_id, "limit": limit}).mappings().all()
            events = connection.execute(text("""
                SELECT id, kind, session_id, action_id, payload_json
                FROM state_events
                WHERE learner_id=:owner
                ORDER BY recorded_at DESC, id DESC
                LIMIT :limit
            """), {"owner": learner_id, "limit": limit}).mappings().all()
            source_event_ids = sorted({
                str(row["source_event_id"])
                for row in evidence_rows
                if row["source_event_id"]
            })
            referenced_state_events = []
            referenced_action_events = []
            if source_event_ids:
                referenced_state_events = connection.execute(text("""
                    SELECT id, kind, session_id, action_id, payload_json
                    FROM state_events
                    WHERE learner_id=:owner AND id IN :ids
                """).bindparams(bindparam("ids", expanding=True)), {
                    "owner": learner_id,
                    "ids": source_event_ids,
                }).mappings().all()
                referenced_action_events = connection.execute(text("""
                    SELECT ae.id, la.session_id
                    FROM action_events ae
                    JOIN learning_actions la ON la.id=ae.action_id
                    JOIN learning_sessions ls ON ls.id=la.session_id
                    WHERE ls.learner_id=:owner AND ae.id IN :ids
                """).bindparams(bindparam("ids", expanding=True)), {
                    "owner": learner_id,
                    "ids": source_event_ids,
                }).mappings().all()
            interactions = connection.execute(text("""
                SELECT ri.id, ri.event_type, rs.session_id
                FROM recommendation_interactions ri
                JOIN next_action_recommendations nr ON nr.id=ri.recommendation_id
                JOIN recommendation_sets rs ON rs.id=nr.set_id
                WHERE ri.owner_id=:owner AND nr.owner_id=:owner AND rs.owner_id=:owner
                ORDER BY ri.created_at DESC, ri.id DESC
                LIMIT :limit
            """), {"owner": learner_id, "limit": limit}).mappings().all()

        activity_sessions: dict[str, str | None] = {}
        for row in practice_rows:
            payload = _object(row["payload"])
            activity_sessions[row["id"]] = (
                payload.get("sessionId")
                if row["kind"] == "quiz"
                else payload.get("learnSessionId")
            )

        def resolve_references(
            *,
            direct_session: Any = None,
            action_id: Any = None,
            payload: dict[str, Any] | None = None,
        ) -> tuple[set[str], set[str]]:
            candidates: set[str] = set()
            unresolved: set[str] = set()

            def add_session(reference: Any, label: str) -> None:
                if not reference:
                    return
                value = str(reference)
                if value in owned_sessions:
                    candidates.add(value)
                elif value in activity_sessions:
                    linked = activity_sessions[value]
                    if linked in owned_sessions:
                        candidates.add(str(linked))
                    else:
                        unresolved.add(f"{label}:{value}")
                else:
                    unresolved.add(f"{label}:{value}")

            add_session(direct_session, "session")
            if action_id:
                action_session = actions.get(str(action_id))
                if action_session:
                    candidates.add(action_session)
                else:
                    unresolved.add(f"action:{action_id}")
            for key in ("sessionId", "learnSessionId", "reviewSessionId", "quizId"):
                add_session((payload or {}).get(key), key)
            return candidates, unresolved

        def classification(candidates: set[str]) -> Literal["resolved", "ambiguous", "orphaned"]:
            status: Literal["resolved", "ambiguous", "orphaned"]
            if len(candidates) == 1:
                status = "resolved"
            elif len(candidates) > 1:
                status = "ambiguous"
            else:
                status = "orphaned"
            return status

        diagnostics: list[ActivityCorrelationDiagnostic] = []
        state_event_sessions: dict[str, set[str]] = {}
        state_event_rows = {row["id"]: row for row in [*events, *referenced_state_events]}
        for row in state_event_rows.values():
            candidates, unresolved = resolve_references(
                direct_session=row["session_id"],
                action_id=row["action_id"],
                payload=_object(row["payload_json"]),
            )
            state_event_sessions[row["id"]] = candidates
            if row["id"] not in {event["id"] for event in events}:
                continue
            diagnostics.append(ActivityCorrelationDiagnostic(
                entity_kind="state_event",
                entity_id=row["id"],
                kind=row["kind"],
                status=classification(candidates),
                session_ids=sorted(candidates),
                unresolved_references=sorted(unresolved),
            ))

        action_event_sessions = {
            row["id"]: {row["session_id"]}
            for row in referenced_action_events
            if row["session_id"] in owned_sessions
        }
        for row in evidence_rows:
            candidates, unresolved = resolve_references(payload=_object(row["provenance_json"]))
            source_event_id = row["source_event_id"]
            if source_event_id:
                source_id = str(source_event_id)
                matched = False
                if source_id in state_event_sessions:
                    candidates.update(state_event_sessions[source_id])
                    matched = True
                if source_id in action_event_sessions:
                    candidates.update(action_event_sessions[source_id])
                    matched = True
                if not matched:
                    unresolved.add(f"sourceEvent:{source_id}")
            else:
                unresolved.add("sourceEvent:missing")
            diagnostics.append(ActivityCorrelationDiagnostic(
                entity_kind="evidence",
                entity_id=row["id"],
                kind=row["kind"],
                status=classification(candidates),
                session_ids=sorted(candidates),
                unresolved_references=sorted(unresolved),
            ))

        for row in interactions:
            candidates: set[str] = set()
            unresolved: set[str] = set()
            if row["session_id"] in owned_sessions:
                candidates.add(row["session_id"])
            else:
                unresolved.add(f"recommendationSession:{row['session_id']}")
            diagnostics.append(ActivityCorrelationDiagnostic(
                entity_kind="recommendation_interaction",
                entity_id=row["id"],
                kind=row["event_type"],
                status=classification(candidates),
                session_ids=sorted(candidates),
                unresolved_references=sorted(unresolved),
            ))

        return ActivityCorrelationReport(
            learner_id=learner_id,
            resolved_count=sum(item.status == "resolved" for item in diagnostics),
            ambiguous_count=sum(item.status == "ambiguous" for item in diagnostics),
            orphaned_count=sum(item.status == "orphaned" for item in diagnostics),
            diagnostics=diagnostics,
        )
