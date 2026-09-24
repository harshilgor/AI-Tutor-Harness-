"""Context planner contract: continuity, isolation, and provider roles."""
from backend.app.context_engine import ContextBlock, ContextEngine
from backend.app.model_provider import OpenRouterLessonProvider
from backend.app.generation_store import GenerationStore
from backend.app.storage import Store
from backend.app.conversation_state import ConversationStateService
from backend.app.assessment_context import select_attempts
from backend.app.context_service import rerank_passages
from fastapi import HTTPException
import pytest
from uuid import uuid4
from pathlib import Path
import json
import copy
from types import SimpleNamespace


def _turn(question: str, answer: str) -> dict:
    return {"question": question, "lesson": {"blocks": [{"body": answer}]}}


def test_short_turns_extend_beyond_four_and_preserve_order():
    turns = [_turn(f"Question {number}", f"Answer {number}") for number in range(8)]
    context = ContextEngine(2000, 1000).build_generation_context(
        instructions="Answer the question.", current_user_message="What was Question 0?",
        candidates=[], turns=turns,
    )
    assert len(context.recent_messages) == 16
    assert context.recent_messages[0]["content"] == "Question 0"
    assert context.recent_messages[-1]["content"] == "Answer 7"


def test_long_turn_is_not_cut_and_lower_priority_context_yields():
    turns = [_turn("old", "old answer"), _turn("new", "x" * 1200)]
    context = ContextEngine(700, 430).build_generation_context(
        instructions="Teach.", current_user_message="Continue",
        candidates=[ContextBlock("sources", "s" * 1600, "source", 5)], turns=turns,
    )
    assert len(context.recent_messages) == 2
    assert context.recent_messages[0]["content"] == "new"
    assert "sources" in context.omitted


def test_explicit_notes_remain_in_context_when_supporting_sources_do_not_fit():
    context = ContextEngine(400, 100).build_generation_context(
        instructions="Teach.", current_user_message="Use my note.",
        candidates=[ContextBlock("learnerNotes", "selected note" * 20, "explicit_note", 5, True),
                    ContextBlock("sources", "other source" * 200, "source", 5)], turns=[],
    )
    assert "selected note" in context.supporting_context()
    assert "sources" in context.omitted


def test_ranked_evidence_keeps_complete_items_that_fit_and_reserves_images():
    context = ContextEngine(900, 100).build_generation_context(
        instructions="Teach.", current_user_message="Explain this figure.",
        candidates=[ContextBlock("sources", [
            {"spanId": "large", "text": "x" * 2000},
            {"spanId": "small", "text": "Relevant passage."},
        ], "attached_material", 5)], turns=[], image_count=1, image_token_reserve=200,
    )
    assert context.estimated_image_tokens == 200
    assert context.estimated_input_tokens <= context.budget_tokens
    assert context.blocks[0].content == [{"spanId": "small", "text": "Relevant passage."}]
    assert "sources_partial" in context.omitted


def test_provider_budget_uses_explicit_model_window(monkeypatch):
    monkeypatch.setenv("AI_TUTOR_MODEL_CONTEXT_WINDOWS", '{"example/model": 6000}')
    monkeypatch.setenv("AI_TUTOR_CONTEXT_INPUT_BUDGET_TOKENS", "12000")
    monkeypatch.setenv("AI_TUTOR_CONTEXT_OUTPUT_RESERVE_TOKENS", "1000")
    monkeypatch.setenv("AI_TUTOR_CONTEXT_SAFETY_TOKENS", "500")
    provider = OpenRouterLessonProvider("key", "example/model", None, None)
    assert provider.context_input_budget_tokens == 4500
    assert OpenRouterLessonProvider("key", "unknown/model", None, None).context_input_budget_tokens == 12000


def test_provider_payload_keeps_current_user_message_distinct():
    context = ContextEngine(2000).build_generation_context(
        instructions="Teach carefully.", current_user_message="Why does it overshoot?",
        candidates=[ContextBlock("lesson", {"topic": "gradient descent"}, "lesson", 1, True)],
        turns=[_turn("Explain gradient descent", "It descends the loss surface.")],
    )
    router = OpenRouterLessonProvider("key", "model", None, None)
    messages = router.streaming_payload(context, 500)["messages"]
    assert messages[-1] == {"role": "user", "content": "Why does it overshoot?"}
    assert messages[-2]["role"] == "assistant"
    assert messages[-3]["content"] == "Explain gradient descent"
    openai = OpenRouterLessonProvider.openai("key", "model")
    payload = openai.streaming_payload(context, 500)
    assert payload["input"][-1] == {"role": "user", "content": "Why does it overshoot?"}


def test_provider_usage_state_is_isolated_per_generation_copy():
    provider = OpenRouterLessonProvider("key", "model", None, None)
    first, second = copy.copy(provider), copy.copy(provider)
    first.last_usage = object()
    assert second.last_usage is None


def test_only_one_active_generation_per_conversation():
    database = Path(__file__).parent / f".context_test_{uuid4().hex}.db"
    store = Store(database)
    try:
        records = GenerationStore(store)
        session = f"session_{uuid4().hex}"
        owner = f"owner_{uuid4().hex}"
        request = {"mode": "ask", "message": "First"}
        first = records.create(owner, session, request, "first", "test", "test")
        assert records.create(owner, session, request, "first", "test", "test")["id"] == first["id"]
        with pytest.raises(HTTPException) as conflict:
            records.create(owner, session, {"mode": "ask", "message": "Second"}, "second", "test", "test")
        assert conflict.value.status_code == 409
        records.transition(first["id"], "failed")
        assert records.create(owner, session, {"mode": "ask", "message": "Second"}, "second", "test", "test")["id"] != first["id"]
    finally:
        store.close()
        database.unlink(missing_ok=True)


def test_compacted_state_persists_and_is_scoped_to_owner():
    class StateProvider:
        def complete_json(self, prompt, max_tokens):
            data = json.loads(prompt.split("\n", 1)[1])
            prior = data["priorState"].get("userFacts", [])
            facts = prior + ([data["turn"]["user"]] if data["turn"]["user"] else [])
            return {"topic": "preferences", "userFacts": facts, "constraints": [], "preferences": [],
                    "decisions": [], "unresolvedQuestions": [], "currentThread": "preferences",
                    "summary": "Preferences stated by the learner."}

    database = Path(__file__).parent / f".context_test_{uuid4().hex}.db"
    store = Store(database)
    try:
        session = f"session_{uuid4().hex}"
        turns = [_turn("My favorite color is orange.", "Noted.")] + [
            _turn(f"Question {index}", f"Answer {index}") for index in range(25)
        ]
        service = ConversationStateService(store, StateProvider())
        result = service.advance("alice", session, turns, 22)
        assert result["compactedTurns"] == 22
        assert "My favorite color is orange." in ConversationStateService(store, StateProvider()).get("alice", session)["state"]["userFacts"]
        context = ContextEngine(1600, 100).build_generation_context(
            instructions="Answer from conversation state.", current_user_message="What color did I say?",
            candidates=[ContextBlock("conversationState", result["state"], "conversation_state", 2)], turns=turns,
        )
        assert "My favorite color is orange." in context.supporting_context()
        assert ConversationStateService(store, StateProvider()).get("bob", session)["state"] == {}
        assert service.advance("alice", session, turns, 22)["version"] == result["version"]
    finally:
        store.close()
        database.unlink(missing_ok=True)


def test_compaction_reads_every_part_of_long_assistant_answer():
    seen = []

    class Provider:
        def complete_json(self, prompt, max_tokens):
            item = json.loads(prompt.split("\n", 1)[1])["turn"]
            seen.append(item)
            return {"topic": "example", "userFacts": [], "constraints": [], "preferences": [],
                    "decisions": [], "unresolvedQuestions": [], "currentThread": "example", "summary": "Summary."}

    database = Path(__file__).parent / f".context_test_{uuid4().hex}.db"
    store = Store(database)
    try:
        answer = "a" * 5300 + "LAST_DETAIL"
        result = ConversationStateService(store, Provider()).advance("alice", "long", [_turn("question", answer)], 1)
        assert result["compactedTurns"] == 1
        assert "LAST_DETAIL" in "".join(item["assistant"] for item in seen)
        assert len(seen) == 2
    finally:
        store.close()
        database.unlink(missing_ok=True)


def test_failed_compaction_does_not_advance_boundary():
    class Provider:
        def complete_json(self, prompt, max_tokens):
            raise RuntimeError("provider failed")

    database = Path(__file__).parent / f".context_test_{uuid4().hex}.db"
    store = Store(database)
    try:
        result = ConversationStateService(store, Provider()).advance("alice", "failed", [_turn("question", "answer")], 1)
        assert result["compactedTurns"] == 0
        assert result["state"] == {}
    finally:
        store.close()
        database.unlink(missing_ok=True)


def test_automatic_notes_respect_course_and_explicit_selection(monkeypatch):
    import backend.app.automatic_note_context as notes

    summaries = [
        SimpleNamespace(id="explicit", title="Gradient descent", frontmatter={"course_id": "course_a"}),
        SimpleNamespace(id="matching", title="Gradient descent", frontmatter={"course_id": "course_a"}),
        SimpleNamespace(id="other_course", title="Gradient descent", frontmatter={"course_id": "course_b"}),
    ]

    class FakeNotes:
        def __init__(self, store):
            pass

        def search(self, owner, term, limit=10):
            return summaries if term == "gradient" else []

        def get(self, owner, note_id):
            return SimpleNamespace(id=note_id, title="Gradient descent", revision=2,
                                   body="A note about gradient descent and overshooting.")

    monkeypatch.setattr(notes, "WorkspaceNoteService", FakeNotes)
    monkeypatch.setattr(notes, "configured_model", lambda: None)
    found = notes.retrieve_relevant_notes(None, "alice", "Explain gradient overshooting", "course_a", {"explicit"})
    assert [item["noteId"] for item in found] == ["matching"]


def test_assessment_context_prefers_current_session_and_concept():
    class Records:
        def listing(self, owner, kind):
            return [
                {"id": "other_concept", "conceptId": "different", "quizId": "current", "createdAt": "2026-09-23T03:00:00"},
                {"id": "other_session", "conceptId": "target", "quizId": "other", "createdAt": "2026-09-23T02:00:00"},
                {"id": "current_session", "conceptId": "target", "quizId": "current", "createdAt": "2026-09-23T01:00:00"},
            ]

        def read(self, owner, record_id, kind):
            return {"sessionId": "active" if record_id == "current" else "elsewhere"}

    assert [item["id"] for item in select_attempts(Records(), "alice", "target", "active")] == [
        "current_session", "other_session",
    ]


def test_assessment_context_prefers_current_weakness_within_session():
    class Records:
        def listing(self, owner, kind):
            return [
                {"id": "recent_success", "conceptId": "target", "quizId": "q", "score": 1,
                 "createdAt": "2026-09-23T03:00:00"},
                {"id": "older_miss", "conceptId": "target", "quizId": "q", "score": 0,
                 "createdAt": "2026-09-23T01:00:00"},
            ]

        def read(self, owner, record_id, kind):
            return {"sessionId": "active"}

    assert [item["id"] for item in select_attempts(Records(), "alice", "target", "active")] == [
        "older_miss", "recent_success",
    ]


def test_assessment_context_prioritizes_active_quiz_and_matching_lesson():
    class Records:
        def listing(self, owner, kind):
            return [
                {"id": "weak", "conceptId": "target", "quizId": "old", "presentationId": "p-old",
                 "score": 0, "createdAt": "2026-09-23T04:00:00"},
                {"id": "active", "conceptId": "target", "quizId": "active-quiz", "presentationId": "p-current",
                 "score": 1, "createdAt": "2026-09-23T03:00:00"},
            ]

        def read(self, owner, record_id, kind):
            return {"sessionId": "active"} if record_id == "active-quiz" else {"lessonId": "lesson-current"}

    ranked = select_attempts(Records(), "alice", "target", "active", active_quiz_id="active-quiz",
                             lesson_id="lesson-current")
    assert [item["id"] for item in ranked] == ["active", "weak"]


def test_passage_reranker_uses_section_metadata_as_second_stage_signal():
    candidates = [
        (0.5, {"id": "body", "text": "A generic discussion of gradients."}, "Course notes"),
        (0.5, {"id": "section", "text": "A short example.", "heading": "Gradient descent convergence"}, "Course notes"),
    ]
    ranked = rerank_passages(candidates, "gradient descent convergence")
    assert ranked[0][1]["id"] == "section"
    assert ranked[0][-1] > ranked[1][-1]


@pytest.mark.parametrize("metadata_key", ["conceptId", "lessonId", "sectionId", "courseId"])
def test_reranker_applies_each_structured_metadata_scope(metadata_key):
    candidates = [
        (0.5, {"id": "unscoped", "text": "A matching passage."}, "Reference"),
        (0.5, {"id": "scoped", "text": "A matching passage.", metadata_key: "target"}, "Reference"),
    ]
    ranked = rerank_passages(candidates, "matching passage", metadata_scope={metadata_key: "target"})
    assert ranked[0][1]["id"] == "scoped"
