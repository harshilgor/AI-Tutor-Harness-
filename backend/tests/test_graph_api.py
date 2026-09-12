from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)


def test_any_topic_produces_limited_graph():
    scope_response = client.post("/v1/topic-scopes", json={"topic": "probability"})
    assert scope_response.status_code == 201
    scope = scope_response.json()
    job_response = client.post(f"/v1/topic-scopes/{scope['id']}/graph-jobs")
    assert job_response.status_code == 202
    payload = job_response.json()
    assert payload["job"]["status"] == "completed"
    assert payload["graph"]["publication_state"] == "limited_unverified"
    assert len(payload["graph"]["concepts"]) == 7
    assert all(edge["support_status"] == "inferred" for edge in payload["graph"]["edges"])


def test_job_and_graph_are_retrievable():
    scope = client.post("/v1/topic-scopes", json={"topic": "linear algebra"}).json()
    payload = client.post(f"/v1/topic-scopes/{scope['id']}/graph-jobs").json()
    job_id = payload["job"]["id"]
    graph_id = payload["job"]["graph_id"]
    assert client.get(f"/v1/graph-jobs/{job_id}").status_code == 200
    graph_response = client.get(f"/v1/graphs/{graph_id}")
    assert graph_response.status_code == 200
    assert graph_response.json()["scope_id"] == scope["id"]


def test_missing_scope_is_recoverable_error():
    response = client.post("/v1/topic-scopes/missing/graph-jobs")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "scope_not_found"
