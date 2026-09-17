from backend.app.storage import Store
from backend.app.models import TopicScope, utc_now
from backend.app.graph_generator import GraphGenerator
from backend.app.session_models import LearningSession, LessonArtifact, LessonBlock
from backend.app.note_draft_models import CreateNoteDraft, NoteDraftReplacement
from backend.app.note_draft_service import NoteDraftService
from backend.app.workspace_note_models import WorkspaceNoteCreate, WorkspaceNoteUpdate
from backend.app.workspace_note_service import WorkspaceNoteService
from backend.app.material_service import problem
import pytest

class DraftProvider:
    provider_name = "test-drafts"
    def complete_json(self, prompt, max_tokens=4000):
        return {"title": "Probability revision", "body": "# Key idea\nConditioning restricts the population.", "tags": ["probability"], "included": "lesson"}

def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_NOTE_VAULT_DIR", str(tmp_path / "vault"))
    store = Store(tmp_path / "drafts.db")
    scope = TopicScope(id="scope-draft", topic="probability", resolved_meaning="probability", objective="learn", depth="introductory", created_at=utc_now())
    store.save_scope(scope); graph = GraphGenerator().generate(scope); store.save_graph(graph)
    session = LearningSession(id="session-draft", learner_id="local", graph_id=graph.id, created_at=utc_now(), updated_at=utc_now())
    store.save_session(session)
    lesson = LessonArtifact(id="lesson-draft", session_id=session.id, concept_id=graph.concepts[0].id, gear="Guided", title="Conditional probability", blocks=[LessonBlock(id="block-draft", kind="explanation", heading="Population", body="Conditioning restricts the population.", order=0)])
    store.save_artifact(lesson)
    return store, session, lesson

def test_draft_uses_only_authorized_lesson_anchor_and_never_writes_vault(tmp_path, monkeypatch):
    store, session, lesson = env(tmp_path, monkeypatch)
    try:
        service = NoteDraftService(store, DraftProvider())
        draft = service.prepare("local", session.id, CreateNoteDraft(origin_kind="lesson", lesson_id=lesson.id))
        assert draft.source_anchors[0].id == f"{lesson.id}:block-draft"
        assert WorkspaceNoteService(store).list("local") == []
        with pytest.raises(Exception) as denied:
            service.prepare("local", session.id, CreateNoteDraft(origin_kind="selection", lesson_id=lesson.id, block_id="block-draft", selected_text="not in the lesson"))
        assert getattr(denied.value, "detail", {}).get("code") == "unapproved_source_anchor"
    finally: store.close()

def test_stale_replacement_conflicts_and_provider_failure_saves_nothing(tmp_path, monkeypatch):
    store, session, lesson = env(tmp_path, monkeypatch)
    try:
        notes = WorkspaceNoteService(store)
        note = notes.create("local", WorkspaceNoteCreate(title="Existing", body="Original section."))
        service = NoteDraftService(store, DraftProvider())
        draft = service.prepare("local", session.id, CreateNoteDraft(origin_kind="lesson", lesson_id=lesson.id, replacement=NoteDraftReplacement(note_id=note.id, expected_revision=1, start_offset=0, end_offset=8)))
        with store.transaction() as conn: service.commit(conn, "local", draft)
        notes.update("local", note.id, WorkspaceNoteUpdate(expected_revision=1, body="Changed section."))
        with pytest.raises(Exception) as stale: service.replace("local", draft.id, 1, 0, 8)
        assert getattr(stale.value, "detail", {}).get("code") == "revision_conflict"
        assert notes.get("local", note.id).body == "Changed section."
        failing = NoteDraftService(store, None)
        with pytest.raises(Exception): failing.prepare("local", session.id, CreateNoteDraft(origin_kind="lesson", lesson_id=lesson.id))
        assert WorkspaceNoteService(store).list("local")[0].id == note.id
    finally: store.close()

def test_quiz_feedback_uses_feedback_only_and_material_origin_is_not_a_contract(tmp_path, monkeypatch):
    store, session, _ = env(tmp_path, monkeypatch)
    try:
        from backend.app.workflow_store import WorkflowStore
        records = WorkflowStore(store)
        with store.transaction() as connection:
            records.put(connection, "local", "attempt", {"id": "attempt-feedback", "feedback": "Use the conditioning event.", "response": "private answer"}, "quiz")
        class FeedbackProvider(DraftProvider):
            def complete_json(self, prompt, max_tokens=4000):
                assert "Use the conditioning event." in prompt
                assert "private answer" not in prompt
                return super().complete_json(prompt, max_tokens)
        draft = NoteDraftService(store, FeedbackProvider()).prepare("local", session.id, CreateNoteDraft(origin_kind="quiz_feedback", quiz_attempt_id="attempt-feedback"))
        assert draft.source_anchors[0].id == "attempt-feedback"
        with pytest.raises(Exception):
            CreateNoteDraft(origin_kind="material")
    finally: store.close()
