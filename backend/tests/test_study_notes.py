"""Living study notes: linkage, insights, proposals, ownership, isolation."""

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
    from backend.app.storage import Store
    from backend.app.session_models import LearningSession
    from backend.app.models import utc_now
    from backend.app.study_note_models import ProposalCreate
    from backend.app.study_note_service import StudyNoteService
    from backend.app.workflow_store import WorkflowStore
    from backend.app.workspace_note_models import WorkspaceNoteUpdate
except ModuleNotFoundError:
    from app.main import app
    from app.storage import Store
    from app.session_models import LearningSession
    from app.models import utc_now
    from app.study_note_models import ProposalCreate
    from app.study_note_service import StudyNoteService
    from app.workflow_store import WorkflowStore
    from app.workspace_note_models import WorkspaceNoteUpdate


client = TestClient(app)

ALICE = {"X-Dev-Learner-Id": "study_alice"}
BOB = {"X-Dev-Learner-Id": "study_bob"}


class StubProvider:
    provider_name = "stub"

    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt, max_tokens=4000, **kwargs):
        return dict(self.payload)


def _make_store(tmp_path):
    return Store(str(tmp_path / "study.db"))


def _seed_graph(store):
    try:
        from backend.app.models import Concept, GraphVersion, TopicScope
    except ModuleNotFoundError:
        from app.models import Concept, GraphVersion, TopicScope
    from sqlalchemy import text as _text
    now = utc_now()
    scope = TopicScope(id="scope_study", topic="photosynthesis", resolved_meaning="photosynthesis",
                       objective="Learn photosynthesis.", depth="introductory", created_at=now)
    graph = GraphVersion(id="graph_x", scope_id="scope_study", title="Photosynthesis",
                         description="Seeded test graph.", publication_state="limited_unverified",
                         trust_summary="test", concepts=[Concept(id="concept_a", title="Chlorophyll",
                         label="pigment", summary="Absorbs light.", objective="Understand chlorophyll.",
                         source_ids=[], support_status="unverified")],
                         edges=[], sources=[], generated_by="test", created_at=now)
    with store.transaction() as conn:
        if store.engine.dialect.name == "postgresql":
            conn.execute(_text("INSERT INTO topic_scopes(id, payload) VALUES('scope_study', :p) ON CONFLICT(id) DO NOTHING"),
                         {"p": scope.model_dump_json()})
            conn.execute(_text("INSERT INTO graph_versions(id, scope_id, payload) VALUES('graph_x', 'scope_study', :p) ON CONFLICT(id) DO NOTHING"),
                         {"p": graph.model_dump_json()})
        else:
            conn.execute(_text("INSERT OR IGNORE INTO topic_scopes(id, payload) VALUES('scope_study', :p)"),
                         {"p": scope.model_dump_json()})
            conn.execute(_text("INSERT OR IGNORE INTO graph_versions(id, scope_id, payload) VALUES('graph_x', 'scope_study', :p)"),
                         {"p": graph.model_dump_json()})


def _make_session(store, owner, sid, goal="Learn photosynthesis"):
    _seed_graph(store)
    now = utc_now()
    session = LearningSession(id=sid, learner_id=owner, graph_id="graph_x", goal=goal,
                              title="Learn photosynthesis", created_at=now, updated_at=now)
    store.save_session(session)
    return session


def _make_journey(store, owner, sid, questions=("What is chlorophyll?",)):
    service = StudyNoteService(store, None)
    turns = [{"question": q,
              "lesson": {"id": f"lesson_{i}", "sessionId": sid, "conceptId": "concept_a",
                         "blocks": [{"heading": "Core idea", "body": "Chlorophyll absorbs light."}]},
              "sessionId": sid} for i, q in enumerate(questions)]
    with store.transaction() as conn:
        service.records.put(conn, owner, "journey",
                            {"id": f"journey_{sid}", "sessionId": sid, "mode": "learn", "gear": "Guided",
                             "goal": "Learn photosynthesis", "status": "teaching", "steps": [],
                             "position": 0, "turns": turns, "revision": 1, "persisted": True}, sid)


def _service(store):
    return StudyNoteService(store, StubProvider({"heading": "Chlorophyll", "body": "Absorbs light.", "concept_title": None}))


def test_study_note_link_and_insight_roundtrip(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_link")
    service = _service(store)
    assert service.find_note("study_alice", "session_link") is None
    note = service.get_or_create_note("study_alice", "session_link")
    assert note.frontmatter["session_ids"] == ["session_link"]
    assert service.tutor_updates_mode(note) == "auto"
    assert service.get_or_create_note("study_alice", "session_link").id == note.id
    saved = service.save_insight("study_alice", "session_link", "My take", "Light is food.")
    assert "## My take" in service.notes.get("study_alice", note.id).body
    rows = service.list_sections("study_alice", note.id)
    assert len(rows) == 1 and rows[0]["owner_kind"] == "user" and not rows[0]["tombstoned"]
    _make_session(store, "study_alice", "session_other", goal="Learn mitosis")
    other = service.save_insight("study_alice", "session_other", None, "Second session.")
    assert other["noteId"] != note.id


def test_turn_proposal_prepare_commit_accept(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_turn")
    _make_journey(store, "study_alice", "session_turn")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_turn")
    service.set_tutor_updates("study_alice", note.id, "ask", note.revision)
    note = service.notes.get("study_alice", note.id)
    prepared = service.prepare("study_alice", "session_turn", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "proposed"
    proposals = service.list_proposals("study_alice", "session_turn")
    assert len(proposals) == 1 and proposals[0]["heading"] == "Chlorophyll"
    accepted = service.accept("study_alice", proposals[0]["id"], expected_revision=note.revision)
    assert accepted["status"] == "applied"
    body = service.notes.get("study_alice", note.id).body
    assert "## Chlorophyll" in body and "Absorbs light." in body
    rows = service.list_sections("study_alice", note.id)
    assert rows[0]["owner_kind"] == "tutor"
    # Second accept is rejected as closed.
    from fastapi import HTTPException
    try:
        service.accept("study_alice", proposals[0]["id"])
        raise AssertionError("expected closed")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_turn_synthesis_can_skip_and_refine(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_refine")
    _make_journey(store, "study_alice", "session_refine", questions=("What is chlorophyll?", "Why does it look green?"))
    # First turn adds a section.
    service = StudyNoteService(store, StubProvider({
        "action": "add", "heading": "Chlorophyll", "body": "Absorbs light.", "concept_title": None,
    }))
    note = service.get_or_create_note("study_alice", "session_refine")
    prepared = service.prepare("study_alice", "session_refine", ProposalCreate(origin="turn", turn_index=0))
    with store.transaction() as conn:
        first = service.commit(conn, "study_alice", prepared)
    assert first["status"] == "applied" and first["applyKind"] == "added"
    assert "## Chlorophyll" in service.notes.get("study_alice", note.id).body
    # Shallow follow-up is skipped.
    service.provider = StubProvider({"action": "skip", "heading": "", "body": ""})
    skipped = service.prepare("study_alice", "session_refine", ProposalCreate(origin="turn", turn_index=1))
    assert skipped.get("skipped") == "no_durable_content"
    with store.transaction() as conn:
        skip_result = service.commit(conn, "study_alice", skipped)
    assert skip_result["status"] == "skipped"
    # Deeper follow-up refines the existing section in place.
    service.provider = StubProvider({
        "action": "refine", "heading": "Chlorophyll", "match_heading": "Chlorophyll",
        "body": "Absorbs red and blue light; green is reflected.", "concept_title": None,
    })
    note = service.notes.get("study_alice", note.id)
    prepared2 = service.prepare("study_alice", "session_refine",
                                ProposalCreate(origin="turn", turn_index=1, expected_note_revision=note.revision))
    assert prepared2["proposal"].section_id is not None
    with store.transaction() as conn:
        refined = service.commit(conn, "study_alice", prepared2)
    assert refined["status"] == "applied" and refined["applyKind"] == "refined"
    body = service.notes.get("study_alice", note.id).body
    assert body.count("## Chlorophyll") == 1
    assert "green is reflected" in body
    assert "Absorbs light." not in body


def test_tombstone_blocks_readd(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_tomb")
    _make_journey(store, "study_alice", "session_tomb")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_tomb")
    service.set_tutor_updates("study_alice", note.id, "ask", note.revision)
    note = service.notes.get("study_alice", note.id)
    prepared = service.prepare("study_alice", "session_tomb", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        service.commit(conn, "study_alice", prepared)
    pid = service.list_proposals("study_alice", "session_tomb")[0]["id"]
    service.accept("study_alice", pid, expected_revision=note.revision)
    # Learner deletes the applied section by hand.
    current = service.notes.get("study_alice", note.id)
    pruned = current.body.replace("## Chlorophyll", "## Removed").replace("Absorbs light.", "gone.")
    service.notes.update("study_alice", note.id, WorkspaceNoteUpdate(expected_revision=current.revision, body=pruned))
    # Re-synthesizing the same turn tombstones instead of re-adding.
    prepared2 = service.prepare("study_alice", "session_tomb", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared2)
    assert result["status"] == "proposed"
    pid2 = [p for p in service.list_proposals("study_alice", "session_tomb") if p["id"] != pid][0]["id"]
    from fastapi import HTTPException
    try:
        service.accept("study_alice", pid2)
        raise AssertionError("expected blocked")
    except HTTPException as exc:
        assert exc.status_code == 409
    rows = service.list_sections("study_alice", note.id)
    assert any(row["tombstoned"] for row in rows)


def test_auto_mode_applies_without_accept(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_auto")
    _make_journey(store, "study_alice", "session_auto")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_auto")
    # Default is already auto; keep the explicit set for clarity.
    service.set_tutor_updates("study_alice", note.id, "auto", note.revision)
    prepared = service.prepare("study_alice", "session_auto", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "applied"
    assert "## Chlorophyll" in service.notes.get("study_alice", note.id).body


def test_user_edit_flips_section_to_shared(tmp_path):
    from fastapi import HTTPException
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_shared")
    _make_journey(store, "study_alice", "session_shared")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_shared")
    service.set_tutor_updates("study_alice", note.id, "ask", note.revision)
    note = service.notes.get("study_alice", note.id)
    prepared = service.prepare("study_alice", "session_shared", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        service.commit(conn, "study_alice", prepared)
    pid = service.list_proposals("study_alice", "session_shared")[0]["id"]
    service.accept("study_alice", pid, expected_revision=note.revision)
    section_id = service.list_sections("study_alice", note.id)[0]["section_id"]
    # Learner rewrites the tutor section by hand.
    current = service.notes.get("study_alice", note.id)
    edited = current.body.replace("Absorbs light.", "Absorbs light, mostly red and blue.")
    service.notes.update("study_alice", note.id, WorkspaceNoteUpdate(expected_revision=current.revision, body=edited))
    # A refresh proposal for the same section stays open and flips it to shared.
    prepared2 = service.prepare("study_alice", "session_shared", ProposalCreate(origin="turn", section_id=section_id))
    with store.transaction() as conn:
        service.commit(conn, "study_alice", prepared2)
    pid2 = [p for p in service.list_proposals("study_alice", "session_shared") if p["id"] != pid][0]["id"]
    try:
        service.accept("study_alice", pid2)
        raise AssertionError("expected blocked")
    except HTTPException as exc:
        assert exc.status_code == 409
    rows = service.list_sections("study_alice", note.id)
    assert rows[0]["owner_kind"] == "shared"
    assert "mostly red and blue" in service.notes.get("study_alice", note.id).body


def test_api_endpoints_and_isolation():
    first = client.post("/v1/sessions", json={"topic": "Mitosis overview", "learner_id": "study_alice"})
    assert first.status_code == 201, first.text
    sid = first.json()["id"]
    try:
        assert client.get(f"/v1/sessions/{sid}/study-note", headers=BOB).status_code == 404
        missing = client.get(f"/v1/sessions/{sid}/study-note", headers=ALICE)
        assert missing.status_code == 404
        created = client.post(f"/v1/sessions/{sid}/study-note", headers=ALICE)
        assert created.status_code == 201, created.text
        note_id = created.json()["noteId"]
        assert "Mitosis" in created.json()["title"]
        bad = client.patch(f"/v1/study-notes/{note_id}/settings",
                           json={"tutorUpdates": "sometimes", "expectedRevision": created.json()["revision"]},
                           headers=ALICE)
        assert bad.status_code == 422
        ok = client.patch(f"/v1/study-notes/{note_id}/settings",
                          json={"tutorUpdates": "never", "expectedRevision": created.json()["revision"]},
                          headers=ALICE)
        assert ok.status_code == 200 and ok.json()["tutorUpdates"] == "never"
        insight = client.post(f"/v1/sessions/{sid}/study-note/insights", headers=ALICE,
                              json={"heading": "Remember", "body": "Spindle fibers pull chromatids."})
        assert insight.status_code == 201, insight.text
        proposals = client.get(f"/v1/sessions/{sid}/note-proposals", headers=ALICE).json()
        assert proposals == {"proposals": []}
        assert client.get(f"/v1/sessions/{sid}/note-proposals", headers=BOB).status_code == 404
    finally:
        assert client.delete(f"/v1/sessions/{sid}", headers=ALICE).status_code == 204


def test_delete_session_removes_proposals(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_gone")
    _make_journey(store, "study_alice", "session_gone")
    service = _service(store)
    service.get_or_create_note("study_alice", "session_gone")
    prepared = service.prepare("study_alice", "session_gone", ProposalCreate(origin="turn"))
    with store.transaction() as conn:
        service.commit(conn, "study_alice", prepared)
    assert len(service.list_proposals("study_alice", "session_gone")) == 1
    assert store.delete_session("session_gone", "study_alice") is True
    assert service.list_proposals("study_alice", "session_gone") == []


def test_note_creation_is_idempotent_and_restorable():
    first = client.post("/v1/sessions", json={"topic": "Photosynthesis basics", "learner_id": "study_alice"})
    assert first.status_code == 201, first.text
    sid = first.json()["id"]
    try:
        assert client.get(f"/v1/sessions/{sid}/study-note", headers=ALICE).status_code == 404
        one = client.post(f"/v1/sessions/{sid}/study-note", headers=ALICE)
        two = client.post(f"/v1/sessions/{sid}/study-note", headers=ALICE)
        assert one.status_code == 201 and two.status_code == 201
        assert one.json()["noteId"] == two.json()["noteId"]
        assert one.json()["revision"] == two.json()["revision"]
        # A reopened session finds the same living note.
        found = client.get(f"/v1/sessions/{sid}/study-note", headers=ALICE).json()
        assert found["noteId"] == one.json()["noteId"]
        assert found["sessionIds"] == [sid]
        # Unknown sessions fail cleanly instead of creating orphans.
        assert client.post("/v1/sessions/session_missing/study-note", headers=ALICE).status_code == 404
        assert client.post("/v1/sessions/session_missing/study-note/insights", headers=ALICE,
                           json={"body": "x"}).status_code == 404
    finally:
        assert client.delete(f"/v1/sessions/{sid}", headers=ALICE).status_code == 204


def test_insight_proposal_distills_branch_text(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_branch")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_branch")
    service.set_tutor_updates("study_alice", note.id, "ask", note.revision)
    note = service.notes.get("study_alice", note.id)
    prepared = service.prepare("study_alice", "session_branch", ProposalCreate(
        origin="insight", source_text="Why do we need Query? It represents what the token looks for.",
        source_label="Attention exploration"))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "proposed"
    proposals = service.list_proposals("study_alice", "session_branch")
    assert len(proposals) == 1 and proposals[0]["origin"] == "insight"
    assert proposals[0]["source"]["createdFrom"].startswith("insight:")
    accepted = service.accept("study_alice", proposals[0]["id"], expected_revision=note.revision)
    assert accepted["status"] == "applied"
    assert "Why do we need Query" not in service.notes.get("study_alice", note.id).body
    # Same text twice opens a second proposal, but accepting it cannot
    # duplicate the section body (idempotency guard).
    prepared2 = service.prepare("study_alice", "session_branch", ProposalCreate(
        origin="insight", source_text="Why do we need Query? It represents what the token looks for."))
    with store.transaction() as conn:
        result2 = service.commit(conn, "study_alice", prepared2)
    assert result2["status"] == "proposed"
    pid2 = result2["proposalId"]
    assert pid2 != accepted["proposalId"]
    latest = service.notes.get("study_alice", note.id)
    service.accept("study_alice", pid2, expected_revision=latest.revision)
    body = service.notes.get("study_alice", note.id).body
    assert body.count("## Chlorophyll") == 1


def test_revision_gate_defers_stale_auto_apply(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_gate")
    _make_journey(store, "study_alice", "session_gate")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_gate")
    service.set_tutor_updates("study_alice", note.id, "auto", note.revision)
    stale_revision = service.notes.get("study_alice", note.id).revision
    # Learner edits before the background job commits.
    service.save_insight("study_alice", "session_gate", "My words", "Do not overwrite.")
    prepared = service.prepare("study_alice", "session_gate",
                               ProposalCreate(origin="turn", expected_note_revision=stale_revision))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "proposed"
    body = service.notes.get("study_alice", note.id).body
    assert "Do not overwrite." in body
    assert "Absorbs light." not in body


def test_quiz_origin_builds_review_checklist(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_quiz")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_quiz")
    service.set_tutor_updates("study_alice", note.id, "ask", note.revision)
    note = service.notes.get("study_alice", note.id)
    with store.transaction() as conn:
        service.records.put(conn, "study_alice", "attempt",
                            {"id": "attempt_weak", "conceptId": "concept_a", "score": 0.2,
                             "outcome": "incorrect", "feedback": "Confused book and market weights."},
                            "quiz_1")
        service.records.put(conn, "study_alice", "attempt",
                            {"id": "attempt_strong", "conceptId": "concept_a", "score": 1.0,
                             "outcome": "correct", "feedback": "Solid."},
                            "quiz_1")
    prepared = service.prepare("study_alice", "session_quiz",
                               ProposalCreate(origin="quiz", attempt_ids=["attempt_weak", "attempt_strong"]))
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "proposed"
    proposals = service.list_proposals("study_alice", "session_quiz")
    assert len(proposals) == 1 and proposals[0]["origin"] == "quiz"
    accepted = service.accept("study_alice", proposals[0]["id"], expected_revision=note.revision)
    assert accepted["status"] == "applied"
    assert "Chlorophyll" in service.notes.get("study_alice", note.id).body


def test_never_mode_skips_synthesis(tmp_path):
    store = _make_store(tmp_path)
    _make_session(store, "study_alice", "session_never")
    _make_journey(store, "study_alice", "session_never")
    service = _service(store)
    note = service.get_or_create_note("study_alice", "session_never")
    service.set_tutor_updates("study_alice", note.id, "never", note.revision)
    prepared = service.prepare("study_alice", "session_never", ProposalCreate(origin="turn"))
    assert prepared.get("skipped") == "tutor_updates_never"
    with store.transaction() as conn:
        result = service.commit(conn, "study_alice", prepared)
    assert result["status"] == "skipped"
    assert service.list_proposals("study_alice", "session_never") == []
    assert "## Chlorophyll" not in service.notes.get("study_alice", note.id).body
