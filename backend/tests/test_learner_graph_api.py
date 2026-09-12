from uuid import uuid4

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)


def _topic_graph() -> dict:
    scope = client.post("/v1/topic-scopes", json={"topic": f"topic-{uuid4().hex[:8]}"}).json()
    response = client.post(f"/v1/topic-scopes/{scope['id']}/graph-jobs")
    assert response.status_code == 202
    return response.json()["graph"]


def test_learner_graph_import_is_cross_topic_and_idempotent_for_same_graph():
    learner_id = f"learner-{uuid4().hex}"
    first_graph = _topic_graph()
    second_graph = _topic_graph()

    first = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/import",
        json={"graph_id": first_graph["id"]},
    )
    assert first.status_code == 202
    assert first.json()["graph"]["revision"] == 1
    assert len(first.json()["graph"]["concepts"]) == 7

    repeated = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/import",
        json={"graph_id": first_graph["id"]},
    )
    assert repeated.status_code == 202
    assert len(repeated.json()["graph"]["concepts"]) == 7
    assert repeated.json()["graph"]["revision"] == 1

    second = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/import",
        json={"graph_id": second_graph["id"]},
    )
    assert second.status_code == 202
    assert len(second.json()["graph"]["concepts"]) == 14
    events = client.get(f"/v1/learners/{learner_id}/knowledge-graph/events")
    assert events.status_code == 200
    assert len(events.json()) == 3
    assert all(event["event_type"] == "topic_graph_imported" for event in events.json())


def test_learner_graph_event_projects_overlay_state_and_persists():
    learner_id = f"learner-{uuid4().hex}"
    graph = _topic_graph()
    imported = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/import",
        json={"graph_id": graph["id"]},
    ).json()["graph"]
    concept_id = imported["concepts"][0]["id"]

    response = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/events",
        json={
            "event_type": "concept_demonstrated",
            "concept_id": concept_id,
            "evidence_id": "attempt_123",
            "metadata": {"independence": "none"},
        },
    )
    assert response.status_code == 201
    projected = response.json()["graph"]["concepts"][0]
    assert projected["state"] == "demonstrated"
    assert projected["evidence_count"] == 1
    assert response.json()["event"]["evidence_id"] == "attempt_123"

    persisted = client.get(f"/v1/learners/{learner_id}/knowledge-graph").json()
    assert persisted["state_version"] == 2
    assert persisted["concepts"][0]["state"] == "demonstrated"
    assert client.get(f"/v1/learners/{learner_id}/knowledge-graph/events").json()[0]["event_type"] == "concept_demonstrated"


def test_learner_graph_rejects_unknown_concept_and_missing_source_graph():
    learner_id = f"learner-{uuid4().hex}"
    missing_import = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/import",
        json={"graph_id": "graph_missing"},
    )
    assert missing_import.status_code == 404
    assert missing_import.json()["detail"]["code"] == "graph_not_found"

    missing_concept = client.post(
        f"/v1/learners/{learner_id}/knowledge-graph/events",
        json={"event_type": "concept_explored", "concept_id": "concept_missing"},
    )
    assert missing_concept.status_code == 404
    assert missing_concept.json()["detail"]["code"] == "learner_concept_not_found"


def test_session_creation_imports_topic_graph_into_learner_projection():
    learner_id = f"learner-{uuid4().hex}"
    graph = _topic_graph()
    session_response = client.post(
        "/v1/sessions",
        json={"graph_id": graph["id"], "learner_id": learner_id, "goal": "Understand the topic"},
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["learnerId"] == learner_id

    projection = client.get(f"/v1/learners/{learner_id}/knowledge-graph")
    assert projection.status_code == 200
    assert len(projection.json()["concepts"]) == 7
    events = client.get(f"/v1/learners/{learner_id}/knowledge-graph/events").json()
    assert events[0]["event_type"] == "topic_graph_imported"
