from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.adaptive_observability import (
    IMMEDIATE_ADAPTATION_POLICY_VERSION,
    POLICY_SCENARIOS,
)
from backend.app.graph_generator import GraphGenerator
from backend.app.learner_graph import LearnerGraphRepository
from backend.app.models import TopicScope, utc_now
from backend.app.session_models import ActionStatus, LearningSession, RunStatus
from backend.app.state_models import EvidenceCreate, StateEventCreate
from backend.app.state_routes import build_state_router
from backend.app.state_service import LearnerStateService
from backend.app.storage import Store


def _environment(tmp_path):
    store = Store(tmp_path / "adaptive-observability.db")
    scope = TopicScope(
        id="scope-adaptive",
        topic="Derivatives",
        resolved_meaning="Derivatives",
        objective="Understand derivatives",
        depth="introductory",
        created_at=utc_now(),
    )
    store.save_scope(scope)
    graph = GraphGenerator().generate(scope)
    store.save_graph(graph)
    concept_id = graph.concepts[0].id
    session = LearningSession(
        id="session-adaptive",
        learner_id="local",
        graph_id=graph.id,
        current_concept_id=concept_id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    store.save_session(session)
    LearnerGraphRepository(store).import_topic_graph("local", graph)
    app = FastAPI()
    app.include_router(build_state_router(lambda: store))
    return store, TestClient(app), graph, session, concept_id


def test_policy_scenarios_define_the_approved_immediate_boundary():
    assert IMMEDIATE_ADAPTATION_POLICY_VERSION == "immediate-adaptation-contract-v1"
    assert {scenario.expected_action for scenario in POLICY_SCENARIOS} == {"teach", "check", "repair"}
    assert {scenario.id for scenario in POLICY_SCENARIOS} == {
        "new-concept",
        "taught-without-check",
        "first-independent-miss",
        "repeated-distinct-miss",
        "assisted-success",
        "fresh-independent-success-after-repair",
    }
    assert all("review" not in scenario.expected_action for scenario in POLICY_SCENARIOS)


def test_policy_input_projects_bounded_raw_evidence_without_changing_state(tmp_path):
    store, client, graph, session, concept_id = _environment(tmp_path)
    try:
        admitted = LearnerStateService(store).admit_evidence("local", EvidenceCreate(
            evidence_key="adaptive-evidence-1",
            concept_id=concept_id,
            graph_id=graph.id,
            graph_version=graph.version,
            kind="assessment",
            outcome="correct",
            condition="assisted",
            score=1.0,
            evaluator="test",
            reliability=0.4,
            provenance={
                "itemId": "item-1",
                "itemFamily": "family-derivative-definition",
                "hintIds": ["hint-1"],
            },
        ))
        state_version = admitted.learner_state.version

        response = client.get(
            "/v1/learners/local/adaptive/policy-input",
            params={"sessionId": session.id, "conceptId": concept_id},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["policyVersion"] == IMMEDIATE_ADAPTATION_POLICY_VERSION
        assert body["sessionId"] == session.id
        assert body["conceptState"] == "developing"
        assert body["conceptStateVersion"] == state_version
        assert body["evidence"][0]["id"] == admitted.evidence.id
        assert body["evidence"][0]["itemId"] == "item-1"
        assert body["evidence"][0]["itemFamily"] == "family-derivative-definition"
        assert body["evidence"][0]["assistanceExposed"] is True
        current = LearnerStateService(store).get_state("local").states[0]
        assert current.version == state_version
    finally:
        client.close()
        store.close()


def test_concept_sources_remain_separate_and_report_raw_divergence(tmp_path):
    store, client, graph, session, concept_id = _environment(tmp_path)
    try:
        LearnerStateService(store).admit_evidence("local", EvidenceCreate(
            evidence_key="adaptive-evidence-2",
            concept_id=concept_id,
            graph_id=graph.id,
            graph_version=graph.version,
            kind="assessment",
            outcome="correct",
            condition="independent",
            score=1.0,
            evaluator="test",
            reliability=0.4,
        ))

        response = client.get(f"/v1/learners/local/adaptive/concepts/{concept_id}/sources")

        assert response.status_code == 200, response.text
        body = response.json()
        values = {source["source"]: source["rawValue"] for source in body["sources"]}
        assert values["canonical_state"] == "developing"
        assert values["review_memory"] == "developing"
        assert values["learner_graph"] == "unexplored"
        assert body["rawValuesDiffer"] is True
    finally:
        client.close()
        store.close()


def test_activity_correlations_classify_resolved_ambiguous_and_orphaned(tmp_path):
    store, client, graph, session, concept_id = _environment(tmp_path)
    try:
        other_session = session.model_copy(update={
            "id": "session-other",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })
        store.save_session(other_session)
        action = RunStatus(
            run_id="run-other",
            session_id=other_session.id,
            status=ActionStatus.received,
            progress=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        store.save_action(action)
        state = LearnerStateService(store)
        resolved, _ = state.append_event("local", StateEventCreate(
            kind="lesson.completed",
            concept_id=concept_id,
            session_id=session.id,
        ))
        ambiguous, _ = state.append_event("local", StateEventCreate(
            kind="activity.observed",
            concept_id=concept_id,
            session_id=session.id,
            action_id=action.run_id,
        ))
        orphaned, _ = state.append_event("local", StateEventCreate(
            kind="activity.observed",
            concept_id=concept_id,
        ))
        linked_evidence = state.admit_evidence("local", EvidenceCreate(
            evidence_key="correlation-linked",
            concept_id=concept_id,
            graph_id=graph.id,
            graph_version=graph.version,
            kind="assessment",
            outcome="incorrect",
            condition="independent",
            evaluator="test",
            reliability=0.4,
            source_event_id=resolved.id,
        )).evidence
        orphaned_evidence = state.admit_evidence("local", EvidenceCreate(
            evidence_key="correlation-orphaned",
            concept_id=concept_id,
            graph_id=graph.id,
            graph_version=graph.version,
            kind="assessment",
            outcome="incorrect",
            condition="independent",
            evaluator="test",
            reliability=0.4,
        )).evidence
        now = utc_now()
        with store.transaction() as conn:
            conn.execute(text("""
                INSERT INTO recommendation_sets(
                    id, owner_id, session_id, context_key, policy_version, payload, created_at
                ) VALUES(
                    'set-correlation', 'local', :session, 'context-correlation', 'test-policy', '{}', :now
                )
            """), {"session": session.id, "now": now})
            conn.execute(text("""
                INSERT INTO next_action_recommendations(
                    id, set_id, owner_id, action_kind, concept_id, rank, payload
                ) VALUES(
                    'recommendation-correlation', 'set-correlation', 'local', 'learn', :concept, 1, '{}'
                )
            """), {"concept": concept_id})
            conn.execute(text("""
                INSERT INTO recommendation_interactions(
                    id, owner_id, recommendation_id, event_type, idempotency_key, payload, created_at
                ) VALUES(
                    'interaction-correlation', 'local', 'recommendation-correlation',
                    'selection', 'interaction-correlation-key', '{}', :now
                )
            """), {"now": now})

        response = client.get("/v1/learners/local/adaptive/activity-correlations")

        assert response.status_code == 200, response.text
        body = response.json()
        by_id = {item["entityId"]: item for item in body["diagnostics"]}
        assert by_id[resolved.id]["entityKind"] == "state_event"
        assert by_id[resolved.id]["status"] == "resolved"
        assert by_id[resolved.id]["sessionIds"] == [session.id]
        assert by_id[ambiguous.id]["status"] == "ambiguous"
        assert set(by_id[ambiguous.id]["sessionIds"]) == {session.id, other_session.id}
        assert by_id[orphaned.id]["status"] == "orphaned"
        assert by_id[linked_evidence.id]["entityKind"] == "evidence"
        assert by_id[linked_evidence.id]["status"] == "resolved"
        assert by_id[orphaned_evidence.id]["status"] == "orphaned"
        assert by_id["interaction-correlation"]["entityKind"] == "recommendation_interaction"
        assert by_id["interaction-correlation"]["status"] == "resolved"
        assert body["resolvedCount"] >= 1
        assert body["ambiguousCount"] >= 1
        assert body["orphanedCount"] >= 1
    finally:
        client.close()
        store.close()


def test_adaptive_diagnostics_are_owner_scoped(tmp_path):
    store, client, graph, session, concept_id = _environment(tmp_path)
    try:
        response = client.get(
            "/v1/learners/local/adaptive/policy-input",
            params={"sessionId": session.id},
            headers={"X-Dev-Learner-Id": "other"},
        )
        assert response.status_code == 403
    finally:
        client.close()
        store.close()
