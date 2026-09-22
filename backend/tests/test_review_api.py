"""API tests for Review sessions, ownership, and memory updates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.graph_generator import GraphGenerator
from backend.app.models import TopicScope, utc_now
from backend.app.review.concept_sync import ConceptSyncService
from backend.app.review_routes import build_review_router
from backend.app.session_models import LearningSession
from backend.app.state_routes import build_state_router
from backend.app.storage import Store


class ReviewProvider:
    provider_name = "test-review"

    def complete_json(self, prompt, max_tokens=4000):
        if "Identify 3 to 8" in prompt or "atomic" in prompt.lower():
            return {"concepts": [
                {"title": "Chain rule", "description": "Multiply local derivatives.", "related_to": []},
                {"title": "Backward pass", "description": "Propagates gradients.", "related_to": ["Chain rule"]},
            ]}
        if "Generate ONE retrieval" in prompt or "active recall" in prompt.lower():
            return {
                "question_type": "free_recall",
                "prompt": "What does the backward pass compute?",
                "expected_answer": "Gradients via the chain rule.",
                "options": [],
                "difficulty": "standard",
            }
        if "Evaluate the learner" in prompt:
            return {
                "correctness": "partial",
                "score": 0.5,
                "confidence_assessment": "medium",
                "missing_concepts": ["chain rule"],
                "misconceptions": [],
                "feedback": "You mentioned gradients but missed the chain rule connection.",
                "ideal_answer": "The backward pass computes gradients using the chain rule.",
                "needs_remediation": True,
                "certain": True,
            }
        if "2-minute refresher" in prompt or "mini-lesson" in prompt.lower():
            return {
                "heading": "Chain rule refresher",
                "body": "The chain rule multiplies local derivatives along a composed function.",
                "follow_up_prompt": "How does the chain rule help backpropagation?",
            }
        return {"concepts": []}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ENV", "development")
    monkeypatch.setenv("AI_TUTOR_DEV_IDENTITY", "true")
    store = Store(tmp_path / "review.db")
    scope = TopicScope(
        id="scope-review", topic="backprop", resolved_meaning="backprop",
        objective="gradients", depth="introductory", created_at=utc_now(),
    )
    store.save_scope(scope)
    graph = GraphGenerator().generate(scope)
    store.save_graph(graph)
    session = LearningSession(
        id="session-review", learner_id="local", graph_id=graph.id,
        goal="backprop", created_at=utc_now(), updated_at=utc_now(),
    )
    store.save_session(session)
    provider = ReviewProvider()
    # Seed a few concepts as recently learned / due.
    sync = ConceptSyncService(store, provider)
    sync.sync_from_text(
        "local",
        source_key="lesson:seed",
        text_value="## Chain rule\n\nMultiply local derivatives.\n\n## Backward pass\n\nComputes gradients.",
        graph_id=graph.id,
        graph_version=graph.version,
        source_session_id=session.id,
        parent_concept_id=graph.concepts[0].id,
    )
    # Make concepts due now.
    with store.transaction() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "UPDATE concept_memory_states SET next_review_at=:past WHERE learner_id='local'"
            ),
            {"past": utc_now() - timedelta(days=1)},
        )
    app = FastAPI()
    app.include_router(build_review_router(lambda: store, lambda: provider))
    app.include_router(build_state_router(lambda: store))
    with TestClient(app) as client:
        yield client, store, graph, session
    store.close()


def test_dashboard_and_cross_user_isolation(env):
    client, store, graph, session = env
    ok = client.get("/v1/learners/local/review", headers={"X-Dev-Learner-Id": "local"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["totalConcepts"] >= 1
    assert body["empty"] is False
    denied = client.get("/v1/learners/local/review", headers={"X-Dev-Learner-Id": "other"})
    assert denied.status_code == 403


def test_review_session_answer_confidence_and_resume(env):
    client, store, graph, session = env
    created = client.post("/v1/review/sessions", json={"length": "quick", "sessionId": session.id})
    assert created.status_code == 201
    session_id = created.json()["sessionId"]

    again = client.post("/v1/review/sessions", json={"length": "quick", "resumeSessionId": session_id})
    assert again.json()["sessionId"] == session_id

    public = client.get(f"/v1/review/sessions/{session_id}").json()
    assert public["itemCount"] >= 1
    item = public["items"][0]
    revision = public["revision"]

    job = client.post(
        f"/v1/review/sessions/{session_id}/items/{item['id']}/answer",
        json={"response": "It computes gradients", "selectedIds": [], "expectedRevision": revision},
        headers={"Idempotency-Key": f"answer-{uuid4().hex}"},
    )
    assert job.status_code == 202
    job_id = job.json()["id"]
    from backend.app.review_routes import run_review_job
    run_review_job(store, ReviewProvider(), job_id)
    refreshed = client.get(f"/v1/review/sessions/{session_id}").json()
    current = next(i for i in refreshed["items"] if i["id"] == item["id"])
    assert current["attempt"] is not None
    assert current["attempt"]["correctness"] in {"correct", "partial", "incorrect"}
    revision = refreshed["revision"]
    conf = client.post(
        f"/v1/review/sessions/{session_id}/items/{item['id']}/confidence",
        json={"confidence": "somewhat", "expectedRevision": revision},
    )
    assert conf.status_code == 200

    other = client.get(f"/v1/review/sessions/{session_id}", headers={"X-Dev-Learner-Id": "intruder"})
    assert other.status_code in {403, 404}


def test_evaluation_failure_does_not_corrupt_memory(env, monkeypatch):
    client, store, graph, session = env

    class BrokenProvider(ReviewProvider):
        def complete_json(self, prompt, max_tokens=4000):
            if "Evaluate" in prompt:
                raise RuntimeError("timeout")
            return super().complete_json(prompt, max_tokens)

    created = client.post("/v1/review/sessions", json={"length": "quick"})
    session_id = created.json()["sessionId"]
    public = client.get(f"/v1/review/sessions/{session_id}").json()
    item = public["items"][0]

    from backend.app.review.session_service import ReviewSessionService
    from backend.app.review.models import ReviewAnswerCommand

    service = ReviewSessionService(store, BrokenProvider())
    # Force evaluate_answer to return None by using BrokenProvider path that fails eval
    # Heuristic still runs when provider raises in evaluate_answer — monkeypatch evaluate to None
    import backend.app.review.evaluation_service as ev

    monkeypatch.setattr(ev, "evaluate_answer", lambda *a, **k: None)
    graded = service.grade(
        "local", session_id, item["id"],
        ReviewAnswerCommand(response="something", selected_ids=[], expected_revision=public["revision"]),
    )
    with store.transaction() as conn:
        result = service.commit_grade(conn, "local", graded)
    assert result["attemptId"]
    refreshed = service.public("local", session_id)
    attempt = next(i for i in refreshed.items if i.id == item["id"]).attempt
    assert attempt["status"] == "evaluation_failed"
    assert attempt["correctness"] is None


def test_generated_review_multiple_choice_is_replaced_with_free_response():
    from backend.app.review.question_service import generate_question

    class MultipleChoiceProvider:
        provider_name = "unsafe-review-mc"

        def complete_json(self, prompt, max_tokens=4000):
            return {
                "question_type": "multiple_choice",
                "prompt": "Which option describes the chain rule?",
                "expected_answer": "Multiply local derivatives.",
                "options": [
                    {"id": "wrong", "label": "Add unrelated values."},
                    {"id": "right", "label": "Multiply local derivatives."},
                ],
                "difficulty": "standard",
            }

    generated = generate_question(
        MultipleChoiceProvider(),
        concept_title="Chain rule",
        concept_summary="Multiply local derivatives.",
        source_excerpt="The chain rule multiplies local derivatives.",
    )

    assert generated.question_type == "short_answer"
    assert generated.options == []


def test_legacy_review_multiple_choice_cannot_admit_evidence(env):
    from sqlalchemy import text

    from backend.app.review.models import ReviewAnswerCommand, ReviewSessionCreate
    from backend.app.review.session_service import ReviewSessionService

    client, store, graph, session = env
    service = ReviewSessionService(store, ReviewProvider())
    session_id = service.create("local", ReviewSessionCreate(length="quick", session_id=session.id))["sessionId"]
    public = service.public("local", session_id)
    item = service.records.read("local", public.items[0].id, "review_item")
    item.update({
        "questionType": "multiple_choice",
        "options": [{"id": "a", "label": "Assumed answer"}, {"id": "b", "label": "Other"}],
        "correctOptionIds": ["a"],
    })
    with store.transaction() as conn:
        service.records.put(conn, "local", "review_item", item, session_id, expected=item["revision"])
    with store.engine.connect() as conn:
        evidence_before = conn.execute(text("SELECT COUNT(*) FROM evidence WHERE learner_id='local'")).scalar_one()

    graded = service.grade(
        "local",
        session_id,
        item["id"],
        ReviewAnswerCommand(response="", selected_ids=["a"], expected_revision=public.revision),
    )
    with store.transaction() as conn:
        service.commit_grade(conn, "local", graded)

    with store.engine.connect() as conn:
        evidence_after = conn.execute(text("SELECT COUNT(*) FROM evidence WHERE learner_id='local'")).scalar_one()
    refreshed = service.public("local", session_id)
    attempt = next(candidate for candidate in refreshed.items if candidate.id == item["id"]).attempt
    assert attempt["status"] == "evaluation_failed"
    assert attempt["correctness"] is None
    assert evidence_after == evidence_before


def test_concept_sync_idempotent(env):
    client, store, graph, session = env
    sync = ConceptSyncService(store, ReviewProvider())
    first = sync.sync_from_text(
        "local", source_key="lesson:idem", text_value="## Gradients\n\nDirection of steepest ascent.",
        graph_id=graph.id, graph_version=graph.version, source_session_id=session.id,
    )
    second = sync.sync_from_text(
        "local", source_key="lesson:idem", text_value="## Gradients\n\nDirection of steepest ascent.",
        graph_id=graph.id, graph_version=graph.version, source_session_id=session.id,
    )
    assert first["status"] == "completed"
    assert second == first


def test_backfill_seeds_from_evidence(env):
    client, store, graph, session = env
    concept_id = graph.concepts[0].id
    # Admit assessment evidence via state service
    from backend.app.state_models import EvidenceCreate
    from backend.app.state_service import LearnerStateService

    LearnerStateService(store).admit_evidence("local", EvidenceCreate(
        evidence_key=f"ev-{uuid4().hex}", concept_id=concept_id, graph_id=graph.id,
        graph_version=graph.version, kind="assessment", outcome="correct",
        condition="independent", score=1.0, evaluator="test", reliability=0.4,
    ))
    job = client.post(
        "/v1/learners/local/review/backfill",
        headers={"X-Dev-Learner-Id": "local", "Idempotency-Key": f"backfill-{uuid4().hex}"},
    )
    assert job.status_code == 202
    from backend.app.review_routes import run_review_job
    run_review_job(store, ReviewProvider(), job.json()["id"])
    dash = client.get("/v1/learners/local/review", headers={"X-Dev-Learner-Id": "local"}).json()
    assert dash["totalConcepts"] >= 1
