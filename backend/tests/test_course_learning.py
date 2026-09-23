"""Tests for Phase 2: Course-Aware Learning, Tutoring Prompt Injection, and Course-Inherited Notes."""

from fastapi.testclient import TestClient

try:
    from backend.app.main import app, get_store
    from backend.app.journey_service import JourneyService
    from backend.app.assessment_models import JourneyCommand
    from backend.app.session_models import TeachingGear
    from backend.app.study_note_service import StudyNoteService
    from backend.app.course_service import CourseService
except ModuleNotFoundError:
    from app.main import app, get_store
    from app.journey_service import JourneyService
    from app.assessment_models import JourneyCommand
    from app.session_models import TeachingGear
    from app.study_note_service import StudyNoteService
    from app.course_service import CourseService


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "learn_alice"}


def test_course_context_in_prompt_and_inherited_notes():
    # 1. Create a Course with specific preferences
    course_res = client.post(
        "/v1/courses",
        json={
            "name": "Distributed Consensus",
            "goal": "Master Raft and Paxos from first principles",
            "teaching_preferences": {
                "depth": "deep",
                "pace": "thorough",
                "math_level": "rigorous",
            },
        },
        headers=ALICE,
    )
    assert course_res.status_code == 201, course_res.text
    course = course_res.json()
    course_id = course["id"]

    session_id = None
    try:
        # 2. Create a session linked to the course
        sess_res = client.post(
            "/v1/sessions",
            json={
                "topic": "State Machine Replication",
                "course_id": course_id,
                "gear": "Deep",
            },
            headers=ALICE,
        )
        assert sess_res.status_code == 201, sess_res.text
        session = sess_res.json()
        session_id = session["id"]
        assert session.get("courseId") == course_id

        # 3. Test prepare_stream on JourneyService
        store = get_store()
        from unittest.mock import MagicMock
        provider = MagicMock(provider_name="test_provider")
        journey_svc = JourneyService(store, provider)
        cmd = JourneyCommand(action="start", mode="learn", gear=TeachingGear.deep, expected_revision=1)
        prepared = journey_svc.prepare_stream("learn_alice", session_id, cmd)

        assert prepared.get("courseContext") is not None
        ctx = prepared["courseContext"]
        assert ctx["courseId"] == course_id
        assert ctx["courseName"] == "Distributed Consensus"
        assert ctx["courseGoal"] == "Master Raft and Paxos from first principles"
        assert ctx["teachingPreferences"]["depth"] == "deep"
        assert ctx["teachingPreferences"]["mathLevel"] == "rigorous"
        assert ctx["activeRoadmapNode"] is not None

        # Verify prompt text has course context
        prompt = prepared["prompt"]
        assert "Distributed Consensus" in prompt
        assert "Master Raft and Paxos from first principles" in prompt
        assert "depth=deep" in prompt
        assert "math=rigorous" in prompt

        # 4. Test note creation inherits course_id
        note_svc = StudyNoteService(store, None)
        note = note_svc.ensure_learn_lesson("learn_alice", session_id)
        assert note.frontmatter.get("course_id") == course_id

        # 5. Test CourseService.list_course_notes returns the note
        course_svc = CourseService(store)
        course_notes = course_svc.list_course_notes("learn_alice", course_id)
        assert any(n.id == note.id for n in course_notes)

    finally:
        if session_id:
            client.delete(f"/v1/sessions/{session_id}", headers=ALICE)
        client.delete(f"/v1/courses/{course_id}", headers=ALICE)


def test_standalone_session_has_no_course_context():
    sess_res = client.post(
        "/v1/sessions",
        json={"topic": "General Relativity"},
        headers=ALICE,
    )
    assert sess_res.status_code == 201
    session = sess_res.json()
    session_id = session["id"]
    try:
        store = get_store()
        from unittest.mock import MagicMock
        provider = MagicMock(provider_name="test_provider")
        journey_svc = JourneyService(store, provider)
        cmd = JourneyCommand(action="start", mode="learn", gear=TeachingGear.guided, expected_revision=1)
        prepared = journey_svc.prepare_stream("learn_alice", session_id, cmd)

        assert prepared.get("courseContext") is None
        assert "This session is part of the course" not in prepared["prompt"]

        note_svc = StudyNoteService(store, None)
        note = note_svc.ensure_learn_lesson("learn_alice", session_id)
        assert "course_id" not in note.frontmatter
    finally:
        client.delete(f"/v1/sessions/{session_id}", headers=ALICE)
