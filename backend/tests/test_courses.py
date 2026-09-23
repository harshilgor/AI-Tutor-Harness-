"""Tests for Course Foundation (Phase 1): CRUD, roadmap, sessions, notes, isolation."""

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "course_alice"}
BOB = {"X-Dev-Learner-Id": "course_bob"}


def _create_course(name="Distributed Systems", goal="Master consensus algorithms", headers=ALICE):
    response = client.post(
        "/v1/courses",
        json={"name": name, "goal": goal},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup_course(course_id, headers=ALICE):
    client.delete(f"/v1/courses/{course_id}", headers=headers)


def test_create_course():
    course = _create_course(name="Quantum Computing", goal="Understand qubits and superposition")
    try:
        assert course["name"] == "Quantum Computing"
        assert course["goal"] == "Understand qubits and superposition"
        assert "id" in course
        assert len(course["roadmap"]) >= 4
        assert "Core concepts" in course["roadmap"][0]["title"]
        assert course["roadmap"][0]["status"] == "in_progress"
        assert course["roadmap"][1]["status"] == "planned"
    finally:
        _cleanup_course(course["id"])


def test_list_courses_with_isolation():
    alice_course = _create_course(name="Alice Course", headers=ALICE)
    bob_course = _create_course(name="Bob Course", headers=BOB)
    try:
        alice_res = client.get("/v1/courses", headers=ALICE)
        assert alice_res.status_code == 200
        alice_courses = alice_res.json()
        alice_ids = [c["id"] for c in alice_courses]
        assert alice_course["id"] in alice_ids
        assert bob_course["id"] not in alice_ids

        bob_res = client.get("/v1/courses", headers=BOB)
        assert bob_res.status_code == 200
        bob_courses = bob_res.json()
        bob_ids = [c["id"] for c in bob_courses]
        assert bob_course["id"] in bob_ids
        assert alice_course["id"] not in bob_ids
    finally:
        _cleanup_course(alice_course["id"], headers=ALICE)
        _cleanup_course(bob_course["id"], headers=BOB)


def test_get_and_update_course():
    course = _create_course(name="Compilers 101", goal="Build an AST interpreter")
    try:
        # Get course
        res = client.get(f"/v1/courses/{course['id']}", headers=ALICE)
        assert res.status_code == 200
        assert res.json()["name"] == "Compilers 101"

        # Update course
        patch_res = client.patch(
            f"/v1/courses/{course['id']}",
            json={"name": "Compilers & Parsers", "teaching_preferences": {"depth": "deep", "math_level": "rigorous"}},
            headers=ALICE,
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["name"] == "Compilers & Parsers"
        assert updated["teachingPreferences"]["depth"] == "deep"
        assert updated["teachingPreferences"]["mathLevel"] == "rigorous"
    finally:
        _cleanup_course(course["id"])


def test_update_roadmap_node():
    course = _create_course(name="Operating Systems")
    try:
        second_node = course["roadmap"][1]
        node_id = second_node["id"]
        patch_res = client.patch(
            f"/v1/courses/{course['id']}/roadmap/{node_id}",
            json={"status": "in_progress"},
            headers=ALICE,
        )
        assert patch_res.status_code == 200
        updated_node = patch_res.json()
        assert updated_node["status"] == "in_progress"

        # Verify through get roadmap
        roadmap_res = client.get(f"/v1/courses/{course['id']}/roadmap", headers=ALICE)
        assert roadmap_res.status_code == 200
        nodes = roadmap_res.json()
        matched = next(n for n in nodes if n["id"] == node_id)
        assert matched["status"] == "in_progress"
    finally:
        _cleanup_course(course["id"])


def test_course_session_association_and_deletion():
    course = _create_course(name="Linear Algebra")
    session_id = None
    try:
        # Create session attached to course
        session_res = client.post(
            "/v1/sessions",
            json={"topic": "Eigenvalues and Eigenvectors", "course_id": course["id"]},
            headers=ALICE,
        )
        assert session_res.status_code == 201, session_res.text
        session = session_res.json()
        session_id = session["id"]
        assert session.get("courseId") == course["id"]

        # List course sessions
        c_sess_res = client.get(f"/v1/courses/{course['id']}/sessions", headers=ALICE)
        assert c_sess_res.status_code == 200
        course_sessions = c_sess_res.json()["sessions"]
        assert any(s["id"] == session_id for s in course_sessions)

        # Delete the course
        del_res = client.delete(f"/v1/courses/{course['id']}", headers=ALICE)
        assert del_res.status_code == 204

        # Session should still exist, but courseId unlinked
        get_sess = client.get(f"/v1/sessions/{session_id}", headers=ALICE)
        assert get_sess.status_code == 200
        assert get_sess.json().get("courseId") is None
    finally:
        if session_id:
            client.delete(f"/v1/sessions/{session_id}", headers=ALICE)
        _cleanup_course(course["id"])
