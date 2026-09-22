"""Phase 5 shared assessment identity and scheduling authority gates."""

from __future__ import annotations

from sqlalchemy import text

from backend.app.assessment_lifecycle import AssessmentLifecycle
from backend.app.assessment_models import Candidate, Criterion, Option
from backend.app.models import Concept, GraphVersion, TopicScope, utc_now
from backend.app.review.scheduling_authority import apply_timing, decide_timing
from backend.app.session_models import LearningSession
from backend.app.state_models import EvidenceCreate
from backend.app.state_service import LearnerStateService
from backend.app.storage import Store


def _seed(store: Store):
    now = utc_now()
    scope = TopicScope(
        id="scope-shared", topic="Shared assessment", resolved_meaning="Shared",
        objective="Learn", depth="introductory", created_at=now,
    )
    store.save_scope(scope)
    graph = GraphVersion(
        id="graph-shared", scope_id=scope.id, title="Shared", description="",
        publication_state="published", trust_summary="", generated_by="test", created_at=now,
        concepts=[Concept(id="c1", title="Concept", label="", summary="", objective="")],
        edges=[],
    )
    store.save_graph(graph)
    session = LearningSession(
        id="session-shared", learner_id="local", graph_id=graph.id,
        current_concept_id="c1", created_at=now, updated_at=now,
    )
    store.save_session(session)
    return graph, session


def test_migration_adds_shared_assessment_identity(tmp_path):
    store = Store(tmp_path / "shared-identity.db")
    with store.engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(assessment_item_exposure)")).all()}
        assert {"item_version", "last_presentation_id", "origin"}.issubset(columns)
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}
        assert "assessment_presentation_links" in tables
    store.close()


def test_lifecycle_commits_presentation_link_and_private_key(tmp_path):
    store = Store(tmp_path / "lifecycle.db")
    _seed(store)
    lifecycle = AssessmentLifecycle(store, provider=None)
    item = Candidate(
        kind="single",
        stem="What is the sum of two and two in basic arithmetic?",
        reasoning_target="Recognize simple addition facts.",
        options=[Option(id="a", label="4"), Option(id="b", label="5")],
        correct_ids=["a"],
        solution="Two plus two equals four by the definition of addition.",
        criteria=[Criterion(id="r1", description="Correct sum from addition facts", weight=1)],
        hints=["Add the numbers carefully."],
        concept_id="c1",
        family="family-add",
        source_ids=["src-1"],
    )
    item_record = {
        "id": "item_shared_1",
        "stem": item.stem,
        "kind": item.kind,
        "options": [option.model_dump() for option in item.options],
        "author": {"status": "drafted"},
        "checker": {"status": "approved"},
        "qualityStatus": "approved",
        "origin": "quiz",
        "itemVersion": 1,
        "contentFingerprint": "fp",
    }
    presentation = {
        "id": "presentation_shared_1",
        "itemId": item_record["id"],
        "quizId": "quiz_shared_1",
        "stem": item.stem,
        "kind": item.kind,
        "options": [option.model_dump() for option in item.options],
        "hints": [],
        "attemptId": None,
        "origin": "quiz",
        "itemVersion": 1,
        "workflowKind": "quiz",
        "workflowId": "quiz_shared_1",
        "hintCount": 1,
        "sources": [],
    }
    with store.transaction() as conn:
        lifecycle.commit_presentation(
            conn, "local",
            item=item,
            item_record=item_record,
            presentation=presentation,
            parent_kind="quiz",
            parent_id="quiz_shared_1",
        )
    loaded_presentation, loaded_item = lifecycle.load_private("local", presentation["id"])
    assert loaded_presentation["id"] == presentation["id"]
    assert loaded_item.correct_ids == ["a"]
    with store.engine.connect() as conn:
        link = conn.execute(text("""
            SELECT workflow_kind, item_id, origin FROM assessment_presentation_links
            WHERE presentation_id=:id
        """), {"id": presentation["id"]}).mappings().one()
        assert link["workflow_kind"] == "quiz"
        assert link["item_id"] == item_record["id"]
        exposure = conn.execute(text("""
            SELECT origin, last_presentation_id FROM assessment_item_exposure
            WHERE owner_id='local'
        """)).mappings().one()
        assert exposure["origin"] == "quiz"
        assert exposure["last_presentation_id"] == presentation["id"]
    store.close()


def test_scheduling_authority_keeps_memory_and_schedule_aligned(tmp_path):
    store = Store(tmp_path / "schedule-align.db")
    graph, _session = _seed(store)
    state = LearnerStateService(store)
    admitted = state.admit_evidence("local", EvidenceCreate(
        evidence_key="schedule-align-1",
        concept_id="c1",
        graph_id=graph.id,
        graph_version=1,
        kind="assessment",
        outcome="correct",
        condition="independent",
        score=1.0,
        evaluator="test",
        reliability=0.4,
    ))
    with store.transaction() as conn:
        memory = conn.execute(text("""
            SELECT next_review_at FROM concept_memory_states
            WHERE learner_id='local' AND concept_id='c1'
        """)).mappings().one()
        schedule = conn.execute(text("""
            SELECT due_at FROM review_schedules
            WHERE learner_id='local' AND originating_evidence_id=:evidence
        """), {"evidence": admitted.evidence.id}).mappings().one()
        assert memory["next_review_at"] is not None
        assert schedule["due_at"] is not None
        assert str(memory["next_review_at"])[:19] == str(schedule["due_at"])[:19]

        decision = decide_timing(outcome="correct", confidence="confident", condition="independent", memory={
            "reviewCount": 1, "consecutiveSuccesses": 1, "consecutiveFailures": 0,
            "lastIntervalDays": 1.0, "difficultyEstimate": 0.5, "masteryEstimate": "developing",
            "needsRemediation": False,
        })
        apply_timing(
            conn,
            learner_id="local",
            concept_id="c1",
            decision=decision,
            outcome="correct",
            confidence="confident",
            evidence_id=admitted.evidence.id,
            apply_memory=True,
            mirror_schedule=True,
            source="memory",
        )
        memory2 = conn.execute(text("""
            SELECT next_review_at FROM concept_memory_states
            WHERE learner_id='local' AND concept_id='c1'
        """)).mappings().one()
        schedule2 = conn.execute(text("""
            SELECT due_at FROM review_schedules
            WHERE learner_id='local' AND originating_evidence_id=:evidence
        """), {"evidence": admitted.evidence.id}).mappings().one()
        assert str(memory2["next_review_at"])[:19] == str(schedule2["due_at"])[:19]
    store.close()
