from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text

from test_persistent_state_api import client, _headers, _graph, _evidence
from backend.app.main import store


def test_state_explanation_only_lists_admitted_evidence_and_challenge_recomputes():
    learner = f"projection-{uuid4().hex}"
    graph = _graph()
    concept = graph["concepts"][0]["id"]
    first = _evidence(learner, graph, concept, "first")
    explanation = client.get(f"/v1/learners/{learner}/state/{concept}/explanation", headers=_headers(learner))
    assert explanation.status_code == 200
    assert [item["id"] for item in explanation.json()["admittedEvidence"]] == [first["evidence"]["id"]]
    challenged = client.post(f"/v1/learners/{learner}/evidence/{first['evidence']['id']}/challenge", headers=_headers(learner), json={"reason": "The answer key did not match the question."})
    assert challenged.status_code == 201
    refreshed = client.get(f"/v1/learners/{learner}/state/{concept}/explanation", headers=_headers(learner))
    assert refreshed.status_code == 200
    assert refreshed.json()["state"]["status"] == "unexplored"
    assert refreshed.json()["admittedEvidence"] == []
    evidence = client.get(f"/v1/learners/{learner}/evidence", headers=_headers(learner)).json()
    assert evidence[0]["admissionStatus"] == "rejected"


def test_timeline_cursor_is_learner_scoped_and_has_deep_links():
    learner = f"timeline-{uuid4().hex}"
    graph = _graph()
    concept = graph["concepts"][0]["id"]
    _evidence(learner, graph, concept, "timeline")
    page = client.get(f"/v1/learners/{learner}/timeline?limit=1", headers=_headers(learner))
    assert page.status_code == 200
    assert len(page.json()["entries"]) == 1
    assert page.json()["entries"][0]["deepLink"]["kind"] == "evidence"
    denied = client.get(f"/v1/learners/{learner}/timeline", headers=_headers("another"))
    assert denied.status_code == 403


def test_timeline_cursor_keeps_equal_timestamp_entries_and_rejects_invalid_cursor():
    learner = f"timeline-cursor-{uuid4().hex}"
    headers = _headers(learner)
    first = client.post(f"/v1/learners/{learner}/events", headers=headers, json={"kind": "lesson.completed", "payload": {"lessonId": "lesson-one"}}).json()
    second = client.post(f"/v1/learners/{learner}/events", headers=headers, json={"kind": "lesson.completed", "payload": {"lessonId": "lesson-two"}}).json()
    shared_time = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with store.transaction() as connection:
        connection.execute(text("UPDATE state_events SET recorded_at=:time WHERE id IN (:first, :second)"), {"time": shared_time, "first": first["id"], "second": second["id"]})
    first_page = client.get(f"/v1/learners/{learner}/timeline?limit=1", headers=headers).json()
    response = client.get(f"/v1/learners/{learner}/timeline", params={"limit": 1, "cursor": first_page["nextCursor"]}, headers=headers)
    assert response.status_code == 200, response.text
    second_page = response.json()
    assert {first_page["entries"][0]["id"], second_page["entries"][0]["id"]} == {first["id"], second["id"]}
    invalid = client.get(f"/v1/learners/{learner}/timeline?cursor=not-a-cursor", headers=headers)
    assert invalid.status_code == 422
