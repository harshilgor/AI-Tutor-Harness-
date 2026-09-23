from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.storage import Store
from backend.app.models import Concept, Edge, GraphVersion, TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.mode_transition_service import ModeTransitionService
from backend.app.mode_transition_models import ModeTransitionInteraction
from backend.app.learning_routes import build_learning_router


def _setup_test_db(tmp_path):
    store = Store(tmp_path / "test_mode_transition.db")
    scope = TopicScope(
        id="scope-ai",
        topic="Machine Learning",
        resolved_meaning="Machine Learning",
        objective="Learn",
        depth="introductory",
        created_at=utc_now(),
    )
    store.save_scope(scope)
    graph = GraphVersion(
        id="graph-ai",
        scope_id=scope.id,
        title="Machine Learning",
        description="Core concepts",
        publication_state="published",
        trust_summary="",
        generated_by="test",
        created_at=utc_now(),
        concepts=[
            Concept(id="attention", title="Attention Mechanism", label="", summary="", objective=""),
            Concept(id="backprop", title="Backpropagation", label="", summary="", objective=""),
        ],
        edges=[],
    )
    store.save_graph(graph)
    session = LearningSession(
        id="session-trans-1",
        learner_id="local",
        graph_id=graph.id,
        current_concept_id="attention",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    store.save_session(session)
    return store, session


def test_explicit_learn_signals(tmp_path):
    store, session = _setup_test_db(tmp_path)
    service = ModeTransitionService(store)

    learn_prompts = [
        "Teach me this from the beginning.",
        "I want to actually understand this.",
        "Can you build this up step by step?",
        "Can you teach me backpropagation from the beginning and make sure I understand it?",
        "I don't want just an answer; I want to understand it.",
    ]

    for prompt in learn_prompts:
        result = service.evaluate_intent(
            current_message=prompt,
            recent_turns=[],
            current_mode="ask",
            session_id=session.id,
            concept_title="Attention Mechanism",
            concept_id="attention",
        )
        assert result.intent == "learn", f"Failed for: {prompt}"
        assert result.confidence >= 0.85, f"Low confidence for: {prompt}"
        assert result.target_mode == "learn", f"Wrong target for: {prompt}"
        assert result.suggestion is not None
        assert result.suggestion.action_label == "Continue in Learn"

    store.close()


def test_explicit_quiz_signals(tmp_path):
    store, session = _setup_test_db(tmp_path)
    service = ModeTransitionService(store)

    quiz_prompts = [
        "Quiz me on this.",
        "Test my understanding.",
        "Can you give me practice questions?",
        "Don't tell me the answer; ask me questions.",
        "I want to see if I actually remember this.",
    ]

    for prompt in quiz_prompts:
        result = service.evaluate_intent(
            current_message=prompt,
            recent_turns=[],
            current_mode="ask",
            session_id=session.id,
            concept_title="Attention Mechanism",
            concept_id="attention",
        )
        assert result.intent == "quiz", f"Failed for: {prompt}"
        assert result.confidence >= 0.85, f"Low confidence for: {prompt}"
        assert result.target_mode == "quiz", f"Wrong target for: {prompt}"
        assert result.suggestion is not None
        assert "Quiz" in result.suggestion.action_label

    store.close()


def test_anti_signals_do_not_trigger_learn_or_quiz(tmp_path):
    store, session = _setup_test_db(tmp_path)
    service = ModeTransitionService(store)

    anti_prompts = [
        "Why?",
        "Why does this happen?",
        "Can you explain that?",
        "Can you give me an example?",
        "I'm confused about this one part.",
        "Can you go deeper?",
        "Can you explain it more simply?",
        "What does this term mean?",
        "Just give me the answer.",
        "Keep it quick.",
    ]

    for prompt in anti_prompts:
        result = service.evaluate_intent(
            current_message=prompt,
            recent_turns=[],
            current_mode="ask",
            session_id=session.id,
            concept_title="Attention Mechanism",
            concept_id="attention",
        )
        assert result.target_mode is None, f"Should NOT trigger mode change for: {prompt}"
        assert result.suggestion is None, f"Should NOT have suggestion for: {prompt}"

    store.close()


def test_cooldown_and_dismissal_suppression(tmp_path):
    store, session = _setup_test_db(tmp_path)
    service = ModeTransitionService(store)

    # First request triggers Learn suggestion
    result = service.evaluate_intent(
        current_message="Teach me this from the beginning.",
        recent_turns=[],
        current_mode="ask",
        session_id=session.id,
        concept_title="Attention Mechanism",
    )
    assert result.suggestion is not None

    # User dismisses suggestion
    service.record_interaction(
        owner="local",
        interaction=ModeTransitionInteraction(
            suggestion_id=result.suggestion.id,
            action="dismiss",
            target_mode="learn",
            session_id=session.id,
        ),
    )

    # Next attempt with strong Learn intent is suppressed by cooldown
    second_result = service.evaluate_intent(
        current_message="Teach me this from the beginning.",
        recent_turns=[],
        current_mode="ask",
        session_id=session.id,
        concept_title="Attention Mechanism",
    )
    assert second_result.suggestion is None
    assert second_result.reason == "learn_suppressed_by_cooldown"

    store.close()


def test_quiz_to_learn_gap_evaluation(tmp_path):
    store, session = _setup_test_db(tmp_path)
    service = ModeTransitionService(store)

    # 1 miss should NOT trigger suggestion
    sugg_1 = service.evaluate_quiz_gap(
        owner="local",
        session_id=session.id,
        concept_id="backprop",
        concept_title="Backpropagation",
        consecutive_misses=1,
    )
    assert sugg_1 is None

    # 2 misses should trigger suggestion
    sugg_2 = service.evaluate_quiz_gap(
        owner="local",
        session_id=session.id,
        concept_id="backprop",
        concept_title="Backpropagation",
        consecutive_misses=2,
    )
    assert sugg_2 is not None
    assert sugg_2.target_mode == "learn"
    assert "Backpropagation" in sugg_2.description
    assert sugg_2.action_label == "Continue in Learn"

    store.close()


def test_transition_api_endpoints(tmp_path):
    store, session = _setup_test_db(tmp_path)
    app = FastAPI()
    app.include_router(build_learning_router(lambda: store, lambda: None))
    client = TestClient(app)

    # 1. Test transition-gap endpoint
    resp = client.get(f"/v1/sessions/{session.id}/transition-gap?concept_id=attention&concept_title=Attention&consecutive_misses=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggestion"] is not None
    assert data["suggestion"]["targetMode"] == "learn"

    # 2. Test transition-interaction endpoint (dismiss)
    sugg_id = data["suggestion"]["id"]
    dismiss_resp = client.post(
        f"/v1/sessions/{session.id}/transition-interaction",
        json={
            "suggestionId": sugg_id,
            "action": "dismiss",
            "targetMode": "learn",
        },
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json() == {"status": "ok"}

    # 3. Verify that further gap suggestions for learn are now suppressed
    suppressed_resp = client.get(f"/v1/sessions/{session.id}/transition-gap?concept_id=attention&concept_title=Attention&consecutive_misses=3")
    assert suppressed_resp.status_code == 200
    assert suppressed_resp.json()["suggestion"] is None

    store.close()
