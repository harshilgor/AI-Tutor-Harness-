from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)


def make_session(topic: str = "probability") -> dict:
    scope = client.post("/v1/topic-scopes", json={"topic": topic}).json()
    graph_result = client.post(f"/v1/topic-scopes/{scope['id']}/graph-jobs").json()
    return client.post("/v1/sessions", json={"graph_id": graph_result["graph"]["id"], "goal": "Understand the foundations"}).json()


def test_teaching_action_returns_structured_lesson_and_persists_resume_state():
    session = make_session()
    response = client.post(
        f"/v1/sessions/{session['id']}/actions",
        headers={"Idempotency-Key": "action-one"},
        json={"intent": "teach", "message": "Teach me this from first principles", "gear": "Deep"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "qualified_response"
    assert payload["intent"] == "teach"
    assert payload["lesson"]["status"] == "qualified"
    assert len(payload["lesson"]["blocks"]) >= 4
    assert payload["lesson"]["blocks"][-1]["metadata"]["qualified"] is True

    resumed = client.get(f"/v1/sessions/{session['id']}").json()
    assert resumed["currentLessonId"] == payload["lesson"]["id"]
    assert resumed["stateVersion"] == 2

    repeated = client.post(
        f"/v1/sessions/{session['id']}/actions",
        headers={"Idempotency-Key": "action-one"},
        json={"intent": "teach", "message": "should be deduplicated"},
    )
    assert repeated.status_code == 202
    assert repeated.json()["runId"] == payload["runId"]


def test_action_events_are_replayable_as_sse():
    session = make_session("systems thinking")
    action = client.post(
        f"/v1/sessions/{session['id']}/actions",
        json={"intent": "why", "concept_id": "missing-id", "gear": "Guided"},
    ).json()
    events = client.get(f"/v1/actions/{action['runId']}/events")
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: action.started" in events.text
    assert "event: intent.classified" in events.text
    assert "event: lesson.completed" in events.text


def test_session_can_start_directly_from_topic():
    response = client.post("/v1/sessions", json={"topic": "linear algebra"})
    assert response.status_code == 201
    session = response.json()
    assert session["graphId"].startswith("graph_")
