"""Chat history: list/rename/delete with strict per-learner isolation."""

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "hist_alice"}
BOB = {"X-Dev-Learner-Id": "hist_bob"}


def _create(topic, learner_id, headers):
    response = client.post(
        "/v1/sessions", json={"topic": topic, "learner_id": learner_id}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup(ids, headers):
    for session_id in ids:
        client.delete(f"/v1/sessions/{session_id}", headers=headers)


def test_create_sets_title_from_first_prompt():
    session = _create("Why is the sky blue and how does scattering work", "hist_alice", ALICE)
    try:
        assert session["title"] == "Why is the sky blue and how does scattering work"
    finally:
        _cleanup([session["id"]], ALICE)


def test_long_topic_is_truncated_to_readable_title():
    session = _create(
        "Explain in great detail how gradient descent optimization converges on non-convex loss surfaces",
        "hist_alice",
        ALICE,
    )
    try:
        assert len(session["title"]) <= 61
        assert session["title"].endswith("…")
        assert "gradient" in session["title"].lower()
    finally:
        _cleanup([session["id"]], ALICE)


def test_list_returns_metadata_newest_first():
    first = _create("First chat history topic", "hist_alice", ALICE)
    second = _create("Second chat history topic", "hist_alice", ALICE)
    try:
        payload = client.get("/v1/sessions", headers=ALICE).json()
        ids = [entry["id"] for entry in payload["sessions"]]
        assert first["id"] in ids and second["id"] in ids
        assert ids.index(second["id"]) < ids.index(first["id"])
        entry = next(item for item in payload["sessions"] if item["id"] == second["id"])
        assert entry["title"] == "Second chat history topic"
        assert entry["turnCount"] == 0
        assert set(entry) == {"id", "title", "goal", "updatedAt", "turnCount"}
        assert payload["total"] >= 2
    finally:
        _cleanup([first["id"], second["id"]], ALICE)


def test_list_pagination():
    ids = [_create(f"Pagination topic {index}", "hist_alice", ALICE)["id"] for index in range(3)]
    try:
        page = client.get("/v1/sessions", params={"limit": 2, "offset": 0}, headers=ALICE).json()
        assert len(page["sessions"]) == 2
        assert page["total"] >= 3
        rest = client.get("/v1/sessions", params={"limit": 2, "offset": 2}, headers=ALICE).json()
        assert rest["sessions"]
        assert {entry["id"] for entry in page["sessions"]}.isdisjoint({entry["id"] for entry in rest["sessions"]})
    finally:
        _cleanup(ids, ALICE)


def test_learners_cannot_see_each_other():
    session = _create("Alice private topic", "hist_alice", ALICE)
    try:
        assert all(entry["id"] != session["id"] for entry in client.get("/v1/sessions", headers=BOB).json()["sessions"])
        assert client.patch(f"/v1/sessions/{session['id']}", json={"title": "Bob"}, headers=BOB).status_code == 404
        assert client.delete(f"/v1/sessions/{session['id']}", headers=BOB).status_code == 404
        assert client.get("/v1/sessions", headers=ALICE).json()["total"] >= 1
    finally:
        _cleanup([session["id"]], ALICE)


def test_rename_and_validation():
    session = _create("Rename me topic", "hist_alice", ALICE)
    try:
        renamed = client.patch(f"/v1/sessions/{session['id']}", json={"title": "  My custom title  "}, headers=ALICE)
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "My custom title"
        assert client.patch(f"/v1/sessions/{session['id']}", json={"title": "   "}, headers=ALICE).status_code == 422
        assert client.patch("/v1/sessions/session_missing", json={"title": "Nope"}, headers=ALICE).status_code == 404
    finally:
        _cleanup([session["id"]], ALICE)


def test_delete_removes_conversation_consistently():
    session = _create("Delete me topic", "hist_alice", ALICE)
    assert client.delete(f"/v1/sessions/{session['id']}", headers=ALICE).status_code == 204
    assert client.get(f"/v1/sessions/{session['id']}").status_code == 404
    assert all(entry["id"] != session["id"] for entry in client.get("/v1/sessions", headers=ALICE).json()["sessions"])
    assert client.delete(f"/v1/sessions/{session['id']}", headers=ALICE).status_code == 404
