"""Integration checks for the shared Learn/Quiz contracts, without paid calls."""
import json
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.storage import Store
from backend.app.graph_generator import GraphGenerator
from backend.app.models import TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.learning_routes import build_learning_router
from backend.app.material_service import MaterialService
from backend.app.material_models import UploadRequest
from backend.app.learner_graph import LearnerGraphRepository
from backend.app.state_service import LearnerStateService
from backend.app.assessment_generation import fingerprint


class Provider:
    provider_name = "test-only"
    def __init__(self):
        self.kind = "single"
        self.certain = True

    def complete_json(self, prompt, max_tokens=4000):
        data = json.loads(prompt.split('\n', 1)[1])
        if prompt.startswith("Propose"):
            return {"steps": [{"conceptId": data["concepts"][0]["id"], "title": "Conditional populations", "objective": "Explain why conditioning changes the population."}]}
        if prompt.startswith("You author"):
            context = data["context"]
            return {"concept_id": context["conceptIds"][0], "kind": self.kind,
                    "stem": "When we condition on an event, which population should we consider?", "reasoning_target": "Distinguish the original population from the conditioning event.",
                    "family": "conditioning_population", "options": [] if self.kind == "short" else [{"id": "a", "label": "The original population"}, {"id": "b", "label": "The conditioning event"}],
                    "correct_ids": [] if self.kind == "short" else ["b"], "solution": "Conditioning restricts the reference population to the given event.",
                    "criteria": [{"id": "population", "description": "Identifies the restricted reference population", "weight": 1}],
                    "hints": ["Which observations remain possible given the condition?"], "source_ids": [context["sources"][0]["spanId"]]}
        if prompt.startswith("Independently"):
            return {"unambiguous": True, "concept_test": True, "novel": True, "supported": True, "correct_ids": [] if self.kind == "short" else ["b"], "solution": "The given event defines the restricted reference population."}
        if prompt.startswith("Compare"):
            return {"agree": True}
        if prompt.startswith("Evaluate"):
            return {"certain": self.certain, "criteria": [{"id": "population", "score": 1}], "feedback": "Your explanation identifies the reference population."}
        return {"blocks": [{"kind": "explanation", "heading": "Conditioning", "body": "Conditioning changes the population we consider. Start with the observations consistent with the given event."}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ENV", "development")
    monkeypatch.setenv("AI_TUTOR_DEV_IDENTITY", "true")
    store = Store(tmp_path / "workflow.db")
    scope = TopicScope(id="scope-test", topic="probability", resolved_meaning="probability", objective="conditional probability", depth="introductory", created_at=utc_now())
    store.save_scope(scope)
    graph = GraphGenerator().generate(scope)
    store.save_graph(graph)
    session = LearningSession(id="session-test", learner_id="local", graph_id=graph.id, goal="conditional probability", created_at=utc_now(), updated_at=utc_now())
    store.save_session(session)
    LearnerGraphRepository(store).import_topic_graph("local", graph)
    material = MaterialService(store)
    content = b"Conditional probability restricts the population to the conditioning event. Probability uses the reference population."
    created = material.create("local", UploadRequest(title="Probability reference", media_type="text/plain", byte_count=len(content)))
    material.upload("local", created["materialId"], created["versionId"], content)
    material.process_one()
    material.attach("local", session.id, created["versionId"])
    provider = Provider()
    app = FastAPI()
    app.include_router(build_learning_router(lambda: store, lambda: provider))
    with TestClient(app) as client:
        yield client, store, provider, session
    store.close()


def command(client, path, payload, key=None):
    response = client.post('/v1' + path, json=payload, headers={"Idempotency-Key": key or uuid4().hex})
    assert response.status_code == 202, response.text
    return client.get('/v1/learning-jobs/' + response.json()["id"]).json()


def quiz_ready(client, session):
    job = command(client, '/quizzes', {"sessionId": session.id, "count": 1})
    assert job["status"] == "completed", job
    qid = job["result"]["quizId"]
    result = command(client, f'/quizzes/{qid}/next', {"expectedRevision": 1})
    assert result["status"] == "completed", result
    return client.get(f'/v1/quizzes/{qid}').json()


def test_private_key_hint_evidence_and_idempotency(env):
    client, store, _, session = env
    quiz = quiz_ready(client, session)
    public = json.dumps(quiz)
    assert 'correct_ids' not in public and 'solution' not in public and 'criteria' not in public
    pid = quiz["current"]["id"]
    hint = command(client, f'/presentations/{pid}/hints', {})
    assert hint["status"] == "completed"
    payload = {"presentationId": pid, "expectedRevision": quiz["revision"], "selectedIds": ["b"]}
    first = command(client, f'/quizzes/{quiz["id"]}/attempts', payload, "same-answer")
    second = command(client, f'/quizzes/{quiz["id"]}/attempts', payload, "same-answer")
    assert first == second and first["status"] == "completed", first
    result = client.get(f'/v1/quizzes/{quiz["id"]}').json()
    assert result["attempts"][0]["assisted"] is True
    assert result["summary"]["score"] == 100
    evidence = LearnerStateService(store).list_evidence("local")
    assert len(evidence) == 1 and evidence[0].condition.value == "assisted"
    assert LearnerStateService(store).get_state("local").states[0].status.value == "developing"


def test_owner_revision_and_malformed_answers(env):
    client, store, _, session = env
    quiz = quiz_ready(client, session)
    assert client.get(f'/v1/quizzes/{quiz["id"]}', headers={"X-Dev-Learner-Id": "other"}).status_code == 404
    invalid = command(client, f'/quizzes/{quiz["id"]}/attempts', {"presentationId": quiz["current"]["id"], "expectedRevision": 1, "selectedIds": ["b"]})
    assert invalid["status"] == "failed"
    assert not LearnerStateService(store).list_evidence("local")


def test_uncertain_written_answer_does_not_award_evidence(env):
    client, store, provider, session = env
    provider.kind, provider.certain = "short", False
    quiz = quiz_ready(client, session)
    result = command(client, f'/quizzes/{quiz["id"]}/attempts', {"presentationId": quiz["current"]["id"], "expectedRevision": quiz["revision"], "response": "Maybe the remaining cases?"})
    assert result["status"] == "completed", result
    assert not LearnerStateService(store).list_evidence("local")
    assert client.get(f'/v1/quizzes/{quiz["id"]}').json()["summary"]["score"] is None


def test_learn_ask_resume_and_no_exposure_mastery(env):
    client, store, _, session = env
    path = f'/sessions/{session.id}/journey'
    result = command(client, path, {"mode": "learn", "message": "Teach probability", "expectedRevision": 1})
    assert result["status"] == "completed", result
    route = client.get('/v1' + path).json()
    assert route["status"] == "proposed" and not route["turns"]
    start = command(client, path, {"mode": "learn", "action": "start", "expectedRevision": route["revision"]})
    assert start["status"] == "completed", start
    saved = client.get('/v1' + path).json()
    assert len(saved["turns"]) == 1
    ask = command(client, path, {"mode": "ask", "message": "What is a sample space?", "expectedRevision": saved["revision"]})
    assert ask["status"] == "completed", ask
    restored = client.get('/v1' + path).json()
    assert restored["steps"] == saved["steps"] and restored["position"] == saved["position"]
    assert not LearnerStateService(store).list_evidence("local")


def test_queued_job_recovery_and_conflicting_key(env):
    client, store, _, session = env
    from backend.app.workflow_store import WorkflowStore
    records = WorkflowStore(store)
    job = records.enqueue("local", session.id, "create", {"session_id": session.id, "count": 1}, "recover")
    client.get('/v1/learning-jobs/' + job["id"])
    assert records.job("local", job["id"])["status"] == "completed"
    response = client.post('/v1/quizzes', json={"sessionId": session.id, "count": 2}, headers={"Idempotency-Key": "recover"})
    assert response.status_code == 409


def test_number_changes_are_not_novel():
    assert fingerprint("There are 20 samples and 5 cases.") == fingerprint("There are 90 samples and 12 cases.")
