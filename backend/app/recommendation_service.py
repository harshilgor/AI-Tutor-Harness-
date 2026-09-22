"""Deterministic, owner-scoped next-action recommendation policy.

Recommendations are planning projections. They record no learning evidence and
never call LearnerStateService's mutation APIs.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError

from .adaptive_observability import AdaptiveObservabilityService
from .immediate_adaptation_policy import (
    IMMEDIATE_ADAPTATION_POLICY_VERSION,
    decide_immediate_action,
    policy_input_digest,
)
from .journey_service import JourneyService
from .material_service import MaterialService, problem
from .models import utc_now
from .recommendation_models import NextActionRecommendation, RecommendationSet
from .workflow_store import encoded

POLICY_VERSION = IMMEDIATE_ADAPTATION_POLICY_VERSION


class RecommendationService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _context_key(
        journey: dict,
        graph_id: str,
        material_version_ids: list[str],
        input_digest: str | None = None,
    ) -> str:
        # No learner text is retained in a recommendation context key.
        stable = {
            "graph": graph_id,
            "position": journey.get("position", 0),
            "steps": [step.get("conceptId") for step in journey.get("steps", [])],
            "status": journey.get("status"),
            "adaptiveInput": input_digest,
            "policyVersion": POLICY_VERSION,
            # Material versions affect the quiz hard exclusion. Keep only IDs,
            # never learner material content, in the idempotency fingerprint.
            "materialVersions": sorted(material_version_ids),
        }
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:40]

    def _due_review(self, owner: str, concept_ids: set[str]) -> tuple[str, datetime] | None:
        if not concept_ids:
            return None
        with self.store.engine.connect() as conn:
            row = conn.execute(text("""
                SELECT concept_id, due_at FROM review_schedules
                WHERE learner_id=:owner AND status='due' AND concept_id IN :concept_ids
                ORDER BY due_at ASC LIMIT 1
            """).bindparams(bindparam("concept_ids", expanding=True)), {"owner": owner, "concept_ids": list(concept_ids)}).mappings().first()
        return (row["concept_id"], row["due_at"]) if row else None

    def _candidate(self, *, action: str, concept, score: int, rationale: str, effort: int, session_id: str) -> dict:
        return {
            "action_kind": action,
            "title": {"learn": f"Learn {concept.title}", "ask": f"Ask about {concept.title}", "quiz": f"Quiz {concept.title}", "review": f"Review {concept.title}"}[action],
            "rationale": rationale,
            "concept_id": concept.id,
            "concept_title": concept.title,
            "effort_minutes": effort,
            "context": {"sessionId": session_id, "conceptId": concept.id},
            "score": score,
        }

    def _generate(
        self,
        owner: str,
        session_id: str,
        material_version_ids: list[str],
    ) -> tuple[list[dict], str]:
        session = MaterialService(self.store).session(owner, session_id)
        graph = self.store.get_graph(session.graph_id)
        if not graph:
            problem("graph_not_found", "This learning map is unavailable.", 404)
        journey = JourneyService(self.store, None).get(owner, session_id)
        by_id = {concept.id: concept for concept in graph.concepts}
        steps = journey.get("steps") or []
        position = min(journey.get("position", 0), max(0, len(steps) - 1))
        current_id = (steps[position].get("conceptId") if steps else None) or session.current_concept_id or graph.concepts[0].id
        current = by_id.get(current_id, graph.concepts[0])
        policy_input = AdaptiveObservabilityService(self.store).policy_input(owner, session_id, current.id)
        decision = decide_immediate_action(policy_input)
        input_digest = policy_input_digest(policy_input)
        next_step = steps[position + 1] if position + 1 < len(steps) else None
        next_id = next_step.get("conceptId") if next_step else None
        if next_id not in by_id:
            next_id = next((
                edge.target for edge in graph.edges
                if edge.type == "requires" and edge.source == current.id and edge.target in by_id
            ), None)
        target = by_id[next_id] if decision.action == "teach" and decision.reason_code == "fresh_independent_success" and next_id else current
        action_kind = {"teach": "learn", "check": "quiz", "repair": "learn"}[decision.action]
        journey_action = (
            "repair" if decision.action == "repair"
            else "start" if journey.get("status") in {"new", "proposed"} and decision.action == "teach"
            else "next"
        )
        primary = self._candidate(
            action=action_kind,
            concept=target,
            score=100,
            effort=6 if decision.action == "check" else 12,
            session_id=session_id,
            rationale=decision.rationale,
        )
        primary.update({
            "pedagogical_action": decision.action,
            "why_code": decision.reason_code,
            "evidence_ids": decision.evidence_ids,
            "input_digest": input_digest,
            "is_primary": True,
            "context": {
                **primary["context"],
                "journeyAction": journey_action,
                "policyVersion": decision.policy_version,
            },
        })
        candidates: list[dict] = []
        # Due schedules surface as review recommendations once the review runner is available.
        due = self._due_review(owner, set(by_id))
        if due:
            concept_id, due_at = due
            concept = by_id.get(concept_id)
            if concept:
                candidates.append(self._candidate(
                    action="review", concept=concept, score=95, effort=6, session_id=session_id,
                    rationale="This concept is due for a short retrieval check.",
                ))

        # Route continuation is preferred, then graph neighbours that depend on
        # the current concept. Hard exclusions happen before scoring.
        if next_id in by_id and next_id != current.id:
            candidates.append(self._candidate(action="learn", concept=by_id[next_id], score=92, effort=12, session_id=session_id, rationale="This is the next concept in your current learning route."))
        else:
            neighbours = [edge.target for edge in graph.edges if edge.type == "requires" and edge.source == current.id and edge.target in by_id and edge.target != current.id]
            for index, concept_id in enumerate(neighbours[:2]):
                candidates.append(self._candidate(action="learn", concept=by_id[concept_id], score=88 - index, effort=12, session_id=session_id, rationale=f"It builds directly on {current.title}."))

        candidates.append(self._candidate(action="ask", concept=current, score=70, effort=3, session_id=session_id, rationale="Use a focused question to clarify the concept you are working on."))
        if material_version_ids:
            candidates.append(self._candidate(action="quiz", concept=current, score=74, effort=6, session_id=session_id, rationale="Your attached material can support a short concept check."))

        # One action per action/concept pair, then score and cap.
        unique: dict[tuple[str, str | None], dict] = {}
        for candidate in candidates:
            unique.setdefault((candidate["action_kind"], candidate["concept_id"]), candidate)
        alternates = sorted(unique.values(), key=lambda item: (-item["score"], item["action_kind"]))
        filtered = [
            item for item in alternates
            if (item["action_kind"], item["concept_id"]) != (primary["action_kind"], primary["concept_id"])
        ]
        return [primary, *filtered[:3]], input_digest

    def get_or_create(self, owner: str, session_id: str) -> RecommendationSet:
        session = MaterialService(self.store).session(owner, session_id)
        journey = JourneyService(self.store, None).get(owner, session_id)
        material_version_ids = MaterialService(self.store).attachments(owner, session_id)
        generated, input_digest = self._generate(owner, session_id, material_version_ids)
        context_key = self._context_key(journey, session.graph_id, material_version_ids, input_digest)
        with self.store.engine.connect() as conn:
            row = conn.execute(text("""SELECT id,payload,status,superseded_by_set_id,fulfilled_evidence_id FROM recommendation_sets
                WHERE owner_id=:owner AND session_id=:session AND context_key=:context AND policy_version=:policy"""),
                {"owner": owner, "session": session_id, "context": context_key, "policy": POLICY_VERSION}).mappings().first()
        if row:
            if row["status"] != "current":
                with self.store.transaction() as conn:
                    conn.execute(text("""
                        UPDATE recommendation_sets
                        SET status='superseded', superseded_by_set_id=:current
                        WHERE owner_id=:owner AND session_id=:session AND status='current' AND id<>:current
                    """), {"current": row["id"], "owner": owner, "session": session_id})
                    conn.execute(text("""
                        UPDATE recommendation_sets
                        SET status='current', superseded_by_set_id=NULL
                        WHERE id=:current AND owner_id=:owner
                    """), {"current": row["id"], "owner": owner})
            return RecommendationSet.model_validate_json(row["payload"]).model_copy(update={
                "status": "current",
                "superseded_by_set_id": None,
                "fulfilled_evidence_id": row["fulfilled_evidence_id"],
            })
        now = utc_now()
        recommendation_set = RecommendationSet(id=f"recommendation_set_{uuid4().hex}", session_id=session_id, policy_version=POLICY_VERSION, input_digest=input_digest, created_at=now,
            recommendations=[NextActionRecommendation(id=f"recommendation_{uuid4().hex}", **candidate) for candidate in generated])
        try:
            with self.store.transaction() as conn:
                conn.execute(text("""
                    UPDATE recommendation_sets
                    SET status='superseded', superseded_by_set_id=:current
                    WHERE owner_id=:owner AND session_id=:session AND status='current'
                """), {"current": recommendation_set.id, "owner": owner, "session": session_id})
                conn.execute(text("""INSERT INTO recommendation_sets(
                        id,owner_id,session_id,context_key,policy_version,payload,created_at,
                        status,input_digest,superseded_by_set_id,fulfilled_evidence_id
                    ) VALUES(
                        :id,:owner,:session,:context,:policy,:payload,:created,
                        'current',:digest,NULL,NULL
                    )"""),
                    {"id": recommendation_set.id, "owner": owner, "session": session_id, "context": context_key, "policy": POLICY_VERSION, "payload": recommendation_set.model_dump_json(), "created": now, "digest": input_digest})
                conn.execute(text("""INSERT INTO next_action_recommendations(id,set_id,owner_id,action_kind,concept_id,rank,payload)
                    VALUES(:id,:set_id,:owner,:action,:concept,:rank,:payload)"""),
                    [{"id": item.id, "set_id": recommendation_set.id, "owner": owner, "action": item.action_kind, "concept": item.concept_id, "rank": rank, "payload": item.model_dump_json()} for rank, item in enumerate(recommendation_set.recommendations, 1)])
        except IntegrityError:
            return self.get_or_create(owner, session_id)
        return recommendation_set

    def record_interaction(
        self,
        owner: str,
        recommendation_id: str,
        event_type: str,
        reason: str | None,
        idempotency_key: str | None,
        evidence_id: str | None = None,
    ) -> None:
        with self.store.transaction() as conn:
            record = conn.execute(text("""
                SELECT recommendation.id, recommendation.set_id, recommendation_set.status
                FROM next_action_recommendations recommendation
                JOIN recommendation_sets recommendation_set ON recommendation_set.id=recommendation.set_id
                WHERE recommendation.id=:id AND recommendation.owner_id=:owner
                  AND recommendation_set.owner_id=:owner
            """), {"id": recommendation_id, "owner": owner}).mappings().first()
            if not record:
                problem("recommendation_not_found", "This recommendation is not available.", 404)
            if event_type in {"selection", "completion"} and record["status"] != "current":
                problem("stale_recommendation", "This next step changed. Reload the current recommendation.", 409)
            if evidence_id:
                evidence = conn.execute(text("""
                    SELECT 1 FROM evidence
                    WHERE id=:evidence AND learner_id=:owner AND admission_status='accepted'
                """), {"evidence": evidence_id, "owner": owner}).first()
                if evidence is None:
                    problem("evidence_not_found", "The completion evidence is not available.", 404)
            try:
                conn.execute(text("""INSERT INTO recommendation_interactions(id,owner_id,recommendation_id,event_type,idempotency_key,payload,created_at)
                    VALUES(:id,:owner,:recommendation,:event,:key,:payload,:created)"""),
                    {"id": f"recommendation_interaction_{uuid4().hex}", "owner": owner, "recommendation": recommendation_id, "event": event_type,
                     "key": idempotency_key, "payload": encoded({"reason": reason, "evidenceId": evidence_id}), "created": utc_now()})
                if event_type == "completion" and evidence_id:
                    conn.execute(text("""
                        UPDATE recommendation_sets
                        SET fulfilled_evidence_id=:evidence
                        WHERE id=:set_id AND owner_id=:owner AND status='current'
                    """), {"evidence": evidence_id, "set_id": record["set_id"], "owner": owner})
            except IntegrityError:
                # Same event/key is idempotent, and writes no learner state.
                return





