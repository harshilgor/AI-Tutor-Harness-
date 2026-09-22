from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.graph_generator import GraphGenerator
from backend.app.journey_service import JourneyService
from backend.app.models import TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.session_snapshot_routes import build_session_snapshot_router
from backend.app.storage import Store


def _env(tmp_path):
    path = tmp_path / "session-snapshot.db"
    store = Store(path)
    scope = TopicScope(
        id="scope-snapshot",
        topic="Vectors",
        resolved_meaning="Vectors",
        objective="Learn vectors",
        depth="introductory",
        created_at=utc_now(),
    )
    store.save_scope(scope)
    graph = GraphGenerator().generate(scope)
    store.save_graph(graph)
    concept = graph.concepts[0]
    session = LearningSession(
        id="session-snapshot",
        learner_id="local",
        graph_id=graph.id,
        current_concept_id=concept.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    store.save_session(session)
    app = FastAPI()
    app.include_router(build_session_snapshot_router(lambda: store))
    return path, store, TestClient(app), graph, session, concept


def test_snapshot_restores_committed_journey_without_client_state(tmp_path):
    path, store, client, graph, session, concept = _env(tmp_path)
    try:
        journey = {
            "id": f"journey_{session.id}",
            "sessionId": session.id,
            "mode": "learn",
            "gear": "Guided",
            "goal": session.goal,
            "status": "teaching",
            "steps": [{"conceptId": concept.id, "title": concept.title, "objective": "Understand vectors"}],
            "position": 0,
            "turns": [{
                "question": "Start learning",
                "lesson": {
                    "id": "lesson-snapshot",
                    "sessionId": session.id,
                    "conceptId": concept.id,
                    "graphRevision": graph.version,
                    "gear": "Guided",
                    "title": concept.title,
                    "blocks": [],
                    "status": "qualified",
                    "generatedBy": "test",
                    "createdAt": utc_now().isoformat(),
                },
                "sessionId": session.id,
                "mode": "learn",
            }],
            "revision": 1,
            "persisted": False,
        }
        with store.transaction() as connection:
            JourneyService(store, None).commit(connection, "local", journey)

        response = client.get(f"/v1/sessions/{session.id}/snapshot")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "learn"
        assert body["currentConceptId"] == concept.id
        assert body["currentLessonId"] == "lesson-snapshot"
        assert body["lastCommittedTurn"]["lessonId"] == "lesson-snapshot"
        assert body["revision"] == 2
    finally:
        client.close()
        store.close()

    reopened = Store(path)
    app = FastAPI()
    app.include_router(build_session_snapshot_router(lambda: reopened))
    with TestClient(app) as restarted:
        restored = restarted.get(f"/v1/sessions/{session.id}/snapshot").json()
        assert restored["currentLessonId"] == "lesson-snapshot"
        assert restored["journeyPosition"] == 0
    reopened.close()


def test_snapshot_position_update_is_revision_guarded_and_owner_scoped(tmp_path):
    _, store, client, graph, session, concept = _env(tmp_path)
    try:
        initial = client.get(f"/v1/sessions/{session.id}/snapshot").json()
        updated = client.patch(
            f"/v1/sessions/{session.id}/position",
            json={
                "expectedRevision": initial["revision"],
                "currentConceptId": concept.id,
                "currentLessonId": "lesson-pointer",
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["currentLessonId"] == "lesson-pointer"
        stale = client.patch(
            f"/v1/sessions/{session.id}/position",
            json={"expectedRevision": initial["revision"], "currentLessonId": "stale"},
        )
        assert stale.status_code == 409
        denied = client.get(
            f"/v1/sessions/{session.id}/snapshot",
            headers={"X-Dev-Learner-Id": "other"},
        )
        assert denied.status_code == 404
    finally:
        client.close()
        store.close()
