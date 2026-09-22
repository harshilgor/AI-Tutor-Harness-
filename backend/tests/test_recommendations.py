from __future__ import annotations
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.storage import Store
from backend.app.models import Concept, Edge, GraphVersion, TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.recommendation_routes import build_recommendation_router
from backend.app.recommendation_service import RecommendationService, POLICY_VERSION


def graph():
    now = utc_now()
    return GraphVersion(id="graph-neural", scope_id="scope-neural", title="Neural networks", description="", publication_state="published", trust_summary="", generated_by="test", created_at=now,
        concepts=[
            Concept(id="intro", title="Neural network introduction", label="", summary="", objective=""),
            Concept(id="backprop", title="Backpropagation", label="", summary="", objective=""),
            Concept(id="gradient", title="Gradient descent", label="", summary="", objective=""),
        ], edges=[Edge(id="e1", source="intro", target="backprop", type="requires", justification="", support_status="supported")])


def _seed(store: Store):
    scope = TopicScope(
        id="scope-neural", topic="Neural networks", resolved_meaning="Neural networks",
        objective="Learn", depth="introductory", created_at=utc_now(),
    )
    store.save_scope(scope)
    item = graph()
    store.save_graph(item)
    session = LearningSession(
        id="session-neural", learner_id="local", graph_id=item.id,
        current_concept_id="intro", created_at=utc_now(), updated_at=utc_now(),
    )
    store.save_session(session)
    return item, session


def test_recommendations_rank_backprop_and_are_idempotent(tmp_path):
    store = Store(tmp_path / "recommendations.db")
    item, session = _seed(store)
    service = RecommendationService(store)
    first = service.get_or_create("local", session.id)
    second = service.get_or_create("local", session.id)
    assert first.id == second.id
    assert first.policy_version == POLICY_VERSION
    assert first.recommendations[0].action_kind == "learn"
    assert first.recommendations[0].concept_id == "intro"
    assert first.recommendations[0].pedagogical_action == "teach"
    assert first.recommendations[0].is_primary is True
    assert len({(item.action_kind, item.concept_id) for item in first.recommendations}) == len(first.recommendations)
    # No due reviews in this fixture, so review actions stay absent.
    assert all(item.action_kind != "review" for item in first.recommendations)
    assert RecommendationService._context_key({"position": 0, "steps": [], "status": "new"}, item.id, []) != RecommendationService._context_key({"position": 0, "steps": [], "status": "new"}, item.id, ["material-version-1"])
    store.close()


def test_due_review_surfaces_as_recommendation(tmp_path):
    from backend.app.state_models import EvidenceCreate
    from backend.app.state_service import LearnerStateService

    store = Store(tmp_path / "recommendations-due.db")
    item, session = _seed(store)
    LearnerStateService(store).admit_evidence("local", EvidenceCreate(
        evidence_key="rec-due-1", concept_id="backprop", graph_id=item.id,
        graph_version=1, kind="assessment", outcome="correct",
        condition="independent", score=1.0, evaluator="test", reliability=0.4,
    ))
    now = utc_now()
    with store.transaction() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            UPDATE review_schedules SET status='due', due_at=:now, updated_at=:now
            WHERE learner_id='local' AND concept_id='backprop'
        """), {"now": now})
    service = RecommendationService(store)
    result = service.get_or_create("local", session.id)
    assert any(candidate.action_kind == "review" and candidate.concept_id == "backprop" for candidate in result.recommendations)
    store.close()


def test_evidence_changes_primary_recommendation_digest_and_repeated_misses_repair(tmp_path):
    from backend.app.state_models import EvidenceCreate
    from backend.app.state_service import LearnerStateService

    store = Store(tmp_path / "recommendations-adaptive.db")
    item, session = _seed(store)
    service = RecommendationService(store)
    initial = service.get_or_create("local", session.id)
    state = LearnerStateService(store)
    for index, family in enumerate(("family-a", "family-b"), 1):
        state.admit_evidence("local", EvidenceCreate(
            evidence_key=f"miss-{index}",
            concept_id="intro",
            graph_id=item.id,
            graph_version=1,
            kind="assessment",
            outcome="incorrect",
            condition="independent",
            score=0,
            evaluator="test",
            reliability=0.4,
            provenance={"itemId": f"item-{index}", "itemFamily": family, "sessionId": session.id},
        ))
    updated = service.get_or_create("local", session.id)
    assert updated.id != initial.id
    assert updated.input_digest != initial.input_digest
    assert updated.recommendations[0].pedagogical_action == "repair"
    assert updated.recommendations[0].why_code == "repeated_distinct_miss"
    assert updated.recommendations[0].context["journeyAction"] == "repair"
    store.close()


def test_recommendation_routes_are_owner_scoped_and_do_not_write_state(tmp_path):
    store = Store(tmp_path / "recommendations.db")
    item, session = _seed(store)
    app = FastAPI(); app.include_router(build_recommendation_router(lambda: store))
    # The route depends on local dev identity through the same material-owner policy.
    with TestClient(app) as client:
        response = client.get(f"/v1/sessions/{session.id}/recommendations")
        assert response.status_code == 200
        payload = response.json()
        recommendation_id = payload["recommendations"][0]["id"]
        first = client.post(f"/v1/recommendations/{recommendation_id}/interactions", json={"eventType": "selection"}, headers={"Idempotency-Key": "same"})
        second = client.post(f"/v1/recommendations/{recommendation_id}/interactions", json={"eventType": "selection"}, headers={"Idempotency-Key": "same"})
        assert first.status_code == second.status_code == 204
        assert client.get(f"/v1/sessions/{session.id}/recommendations", headers={"X-Dev-Learner-Id": "other"}).status_code == 404
    with store.engine.connect() as connection:
        assert connection.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM learner_concept_states")).scalar_one() == 0
        assert connection.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM recommendation_interactions")).scalar_one() == 1
    store.close()


def test_stale_recommendation_is_rejected_and_current_completion_links_evidence(tmp_path):
    from backend.app.state_models import EvidenceCreate
    from backend.app.state_service import LearnerStateService

    store = Store(tmp_path / "recommendation-lifecycle.db")
    item, session = _seed(store)
    app = FastAPI(); app.include_router(build_recommendation_router(lambda: store))
    with TestClient(app) as client:
        first = client.get(f"/v1/sessions/{session.id}/recommendations").json()
        admitted = LearnerStateService(store).admit_evidence("local", EvidenceCreate(
            evidence_key="recommendation-completion",
            concept_id="intro",
            graph_id=item.id,
            graph_version=1,
            kind="assessment",
            outcome="correct",
            condition="independent",
            score=1,
            evaluator="test",
            reliability=0.4,
            provenance={"itemId": "item-completion", "itemFamily": "family-completion", "sessionId": session.id},
        )).evidence
        current = client.get(f"/v1/sessions/{session.id}/recommendations").json()
        assert current["id"] != first["id"]
        stale = client.post(
            f"/v1/recommendations/{first['recommendations'][0]['id']}/interactions",
            json={"eventType": "selection"},
        )
        assert stale.status_code == 409
        completed = client.post(
            f"/v1/recommendations/{current['recommendations'][0]['id']}/interactions",
            json={"eventType": "completion", "evidenceId": admitted.id},
            headers={"Idempotency-Key": "complete-current"},
        )
        assert completed.status_code == 204
    with store.engine.connect() as connection:
        rows = connection.execute(__import__("sqlalchemy").text("""
            SELECT id,status,superseded_by_set_id,fulfilled_evidence_id
            FROM recommendation_sets
            WHERE owner_id='local' AND session_id=:session
            ORDER BY created_at
        """), {"session": session.id}).mappings().all()
    assert sum(row["status"] == "current" for row in rows) == 1
    assert rows[0]["superseded_by_set_id"] == rows[1]["id"]
    assert rows[1]["fulfilled_evidence_id"] == admitted.id
    store.close()
