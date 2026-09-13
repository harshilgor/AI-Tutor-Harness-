from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)


def _headers(learner_id: str) -> dict[str, str]:
    return {"X-Dev-Learner-Id": learner_id}


def _graph(topic: str | None = None) -> dict:
    scope = client.post("/v1/topic-scopes", json={"topic": topic or f"state-{uuid4().hex[:8]}"}).json()
    return client.post(f"/v1/topic-scopes/{scope['id']}/graph-jobs").json()["graph"]


def _evidence(learner_id: str, graph: dict, concept_id: str, key: str, **overrides) -> dict:
    payload = {
        "evidenceKey": key,
        "conceptId": concept_id,
        "graphId": graph["id"],
        "graphVersion": graph["version"],
        "kind": "understanding_check",
        "outcome": "correct",
        "condition": "independent",
        "evaluator": "deterministic-test-rubric-v1",
        "reliability": 0.9,
        "policyVersion": "learner-reducer-v1",
        "provenance": {"fixture": "persistent-state"},
    }
    payload.update(overrides)
    response = client.post(f"/v1/learners/{learner_id}/evidence", headers=_headers(learner_id), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_independent_evidence_can_demonstrate_but_assisted_evidence_cannot():
    graph = _graph()
    concept_id = graph["concepts"][0]["id"]
    independent = f"independent-{uuid4().hex}"
    assisted = f"assisted-{uuid4().hex}"

    independent_result = _evidence(independent, graph, concept_id, "attempt-1")
    assisted_result = _evidence(assisted, graph, concept_id, "attempt-1", condition="assisted")

    assert independent_result["learnerState"]["status"] == "demonstrated"
    assert assisted_result["learnerState"]["status"] == "developing"
    assert assisted_result["learnerState"]["uncertainty"] > independent_result["learnerState"]["uncertainty"]


def test_lesson_reading_records_activity_but_never_awards_canonical_state():
    learner_id = f"reader-{uuid4().hex}"
    graph = _graph()
    session = client.post("/v1/sessions", json={"graphId": graph["id"], "learnerId": learner_id}).json()
    action = client.post(f"/v1/sessions/{session['id']}/actions", json={"intent": "teach"})
    assert action.status_code == 202

    state = client.get(f"/v1/learners/{learner_id}/state", headers=_headers(learner_id)).json()
    events = client.get(f"/v1/learners/{learner_id}/events", headers=_headers(learner_id)).json()
    assert state["states"] == []
    assert {event["kind"] for event in events} >= {"session.started", "lesson.completed"}


def test_evidence_retry_is_idempotent_and_does_not_reschedule_or_reincrement():
    learner_id = f"retry-{uuid4().hex}"
    graph = _graph()
    concept_id = graph["concepts"][0]["id"]
    first = _evidence(learner_id, graph, concept_id, "stable-attempt")
    second = _evidence(learner_id, graph, concept_id, "stable-attempt", reliability=0.1)

    assert second["idempotentReplay"] is True
    assert second["evidence"]["id"] == first["evidence"]["id"]
    assert second["learnerState"]["version"] == 1
    queue = client.get(
        f"/v1/learners/{learner_id}/review-queue?include_future=true", headers=_headers(learner_id)
    ).json()
    assert len(queue) == 1


def test_evidence_supersession_rebuilds_state_and_cancels_origin_review():
    learner_id = f"supersede-{uuid4().hex}"
    graph = _graph()
    concept_id = graph["concepts"][0]["id"]
    original = _evidence(learner_id, graph, concept_id, "original")
    corrected = _evidence(
        learner_id,
        graph,
        concept_id,
        "corrected",
        outcome="incorrect",
        supersedesEvidenceId=original["evidence"]["id"],
    )
    records = client.get(f"/v1/learners/{learner_id}/evidence", headers=_headers(learner_id)).json()

    assert corrected["learnerState"]["status"] == "developing"
    assert corrected["learnerState"]["lastEvidenceId"] == corrected["evidence"]["id"]
    assert {item["admissionStatus"] for item in records} == {"accepted", "superseded"}
    queue = client.get(
        f"/v1/learners/{learner_id}/review-queue?include_future=true", headers=_headers(learner_id)
    ).json()
    assert queue == []


def test_learner_ownership_and_curriculum_compatibility_are_enforced():
    graph = _graph()
    concept_id = graph["concepts"][0]["id"]
    learner_a = f"owner-a-{uuid4().hex}"
    learner_b = f"owner-b-{uuid4().hex}"
    accepted = _evidence(learner_a, graph, concept_id, "compatible")
    rejected = _evidence(learner_b, graph, concept_id, "incompatible", graphVersion=graph["version"] + 1)

    assert accepted["evidence"]["admissionStatus"] == "accepted"
    assert rejected["evidence"]["admissionStatus"] == "rejected"
    assert rejected["evidence"]["admissionReason"] == "incompatible_curriculum_version"
    assert rejected["learnerState"] is None
    forbidden = client.get(f"/v1/learners/{learner_a}/state", headers=_headers(learner_b))
    assert forbidden.status_code == 403
    isolated = client.get(f"/v1/learners/{learner_b}/state", headers=_headers(learner_b)).json()
    assert isolated["states"] == []


def test_nested_branch_preserves_anchor_and_return_position_and_closes_safely():
    learner_id = f"branch-owner-{uuid4().hex}"
    graph = _graph()
    session = client.post("/v1/sessions", json={"graphId": graph["id"], "learnerId": learner_id}).json()
    parent = client.post(
        f"/v1/learners/{learner_id}/branches",
        headers=_headers(learner_id),
        json={
            "sessionId": session["id"],
            "anchor": {"conceptId": graph["concepts"][0]["id"], "blockId": "block-a", "selectedText": "why?"},
            "returnPosition": {"conceptId": graph["concepts"][0]["id"], "lessonId": "lesson-a", "offset": 9},
            "localGear": "Quick",
        },
    ).json()
    child_response = client.post(
        f"/v1/learners/{learner_id}/branches",
        headers=_headers(learner_id),
        json={
            "sessionId": session["id"],
            "parentBranchId": parent["id"],
            "anchor": {"conceptId": graph["concepts"][1]["id"]},
            "returnPosition": {"lessonId": "lesson-child", "blockId": "block-child"},
        },
    )
    assert child_response.status_code == 201
    child = child_response.json()
    assert child["parentBranchId"] == parent["id"]
    assert parent["returnPosition"]["offset"] == 9

    updated = client.patch(
        f"/v1/learners/{learner_id}/branches/{child['id']}",
        headers=_headers(learner_id),
        json={"expectedRevision": 1, "returnPosition": {"lessonId": "lesson-child", "offset": 22}, "summary": "bounded detour"},
    ).json()
    closed = client.post(f"/v1/learners/{learner_id}/branches/{child['id']}/close", headers=_headers(learner_id)).json()
    assert updated["returnPosition"]["offset"] == 22
    assert closed["lifecycle"] == "closed"
    assert closed["returnPosition"] == updated["returnPosition"]


def test_anchored_note_keeps_revisions_and_soft_delete_is_learner_scoped():
    learner_id = f"note-owner-{uuid4().hex}"
    graph = _graph()
    concept_id = graph["concepts"][0]["id"]
    created = client.post(
        f"/v1/learners/{learner_id}/notes",
        headers=_headers(learner_id),
        json={"scope": "private", "body": "first version", "conceptId": concept_id, "provenance": {"author": "learner"}},
    )
    assert created.status_code == 201
    note = created.json()
    revised = client.patch(
        f"/v1/learners/{learner_id}/notes/{note['id']}",
        headers=_headers(learner_id),
        json={"expectedRevision": 1, "body": "second version", "provenance": {"author": "learner"}},
    ).json()
    revisions = client.get(
        f"/v1/learners/{learner_id}/notes/{note['id']}/revisions", headers=_headers(learner_id)
    ).json()
    assert revised["revision"] == 2
    assert revised["conceptId"] == concept_id
    assert [item["body"] for item in revisions] == ["first version", "second version"]
    assert client.delete(f"/v1/learners/{learner_id}/notes/{note['id']}", headers=_headers(learner_id)).status_code == 204
    assert client.get(f"/v1/learners/{learner_id}/notes/{note['id']}", headers=_headers(learner_id)).status_code == 404


def test_review_queue_becomes_due_from_originating_evidence():
    learner_id = f"review-{uuid4().hex}"
    graph = _graph()
    result = _evidence(learner_id, graph, graph["concepts"][0]["id"], "review-origin", condition="assisted")
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    queue = client.get(
        f"/v1/learners/{learner_id}/review-queue", headers=_headers(learner_id), params={"as_of": future}
    ).json()
    assert len(queue) == 1
    assert queue[0]["status"] == "due"
    assert queue[0]["originatingEvidenceId"] == result["evidence"]["id"]
