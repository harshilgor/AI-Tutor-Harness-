"""Persistence helpers for concept_memory_states and relationships."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, text

from ..models import utc_now
from .scheduler import MemorySnapshot, ScheduleDecision, schedule_initial


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _object(value: str | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    return json.loads(value) if isinstance(value, str) else value


def ensure_learner(connection: Connection, learner_id: str) -> None:
    now = utc_now()
    exists = connection.execute(text("SELECT 1 FROM learners WHERE id=:id"), {"id": learner_id}).first()
    if exists:
        connection.execute(text("UPDATE learners SET updated_at=:now WHERE id=:id"), {"now": now, "id": learner_id})
    else:
        connection.execute(text("""
            INSERT INTO learners(id, identity_kind, display_name, created_at, updated_at)
            VALUES (:id, 'development_local', NULL, :now, :now)
        """), {"id": learner_id, "now": now})


def memory_from_row(row: Any) -> dict[str, Any]:
    return {
        "learnerId": row["learner_id"],
        "conceptId": row["concept_id"],
        "graphId": row["graph_id"],
        "graphVersion": row["graph_version"],
        "firstLearnedAt": row["first_learned_at"],
        "lastReviewedAt": row["last_reviewed_at"],
        "nextReviewAt": row["next_review_at"],
        "reviewCount": row["review_count"],
        "successfulRecallCount": row["successful_recall_count"],
        "failedRecallCount": row["failed_recall_count"],
        "partialRecallCount": row["partial_recall_count"],
        "skipCount": row["skip_count"],
        "currentStreak": row["current_streak"],
        "consecutiveSuccesses": row["consecutive_successes"],
        "consecutiveFailures": row["consecutive_failures"],
        "difficultyEstimate": row["difficulty_estimate"],
        "lastScore": row["last_score"],
        "lastConfidence": row["last_confidence"],
        "lastOutcome": row["last_outcome"],
        "lastQuestionType": row["last_question_type"],
        "masteryEstimate": row["mastery_estimate"],
        "needsRemediation": bool(row["needs_remediation"]),
        "sourceLessonId": row["source_lesson_id"],
        "sourceSessionId": row["source_session_id"],
        "sourceSectionId": row["source_section_id"],
        "provenance": _object(row["provenance_json"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "lastIntervalDays": float((_object(row["provenance_json"]).get("lastIntervalDays") or 1.0)),
    }


def get_memory(connection: Connection, learner_id: str, concept_id: str) -> dict[str, Any] | None:
    row = connection.execute(text("""
        SELECT * FROM concept_memory_states WHERE learner_id=:learner AND concept_id=:concept
    """), {"learner": learner_id, "concept": concept_id}).mappings().first()
    return memory_from_row(row) if row else None


def snapshot_from_memory(memory: dict[str, Any] | None) -> MemorySnapshot:
    if not memory:
        return MemorySnapshot()
    return MemorySnapshot(
        review_count=int(memory["reviewCount"]),
        consecutive_successes=int(memory["consecutiveSuccesses"]),
        consecutive_failures=int(memory["consecutiveFailures"]),
        last_interval_days=float(memory.get("lastIntervalDays") or 1.0),
        difficulty_estimate=float(memory["difficultyEstimate"]),
        mastery_estimate=memory["masteryEstimate"],
        needs_remediation=bool(memory["needsRemediation"]),
    )


def seed_memory(
    connection: Connection,
    *,
    learner_id: str,
    concept_id: str,
    graph_id: str,
    graph_version: int,
    source_lesson_id: str | None = None,
    source_session_id: str | None = None,
    source_section_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Idempotent initial memory + schedule seed without claiming mastery."""
    ensure_learner(connection, learner_id)
    existing = get_memory(connection, learner_id, concept_id)
    if existing:
        return existing
    moment = now or utc_now()
    decision = schedule_initial(now=moment)
    provenance = {"lastIntervalDays": decision.interval_days, "scheduler": decision.scheduler_version, "seed": True}
    connection.execute(text("""
        INSERT INTO concept_memory_states(
            learner_id, concept_id, graph_id, graph_version, first_learned_at, last_reviewed_at, next_review_at,
            review_count, successful_recall_count, failed_recall_count, partial_recall_count, skip_count,
            current_streak, consecutive_successes, consecutive_failures, difficulty_estimate, last_score,
            last_confidence, last_outcome, last_question_type, mastery_estimate, needs_remediation,
            source_lesson_id, source_session_id, source_section_id, provenance_json, created_at, updated_at)
        VALUES (
            :learner, :concept, :graph, :version, :first, NULL, :next,
            0, 0, 0, 0, 0, 0, 0, 0, :difficulty, NULL, NULL, NULL, NULL, :mastery, false,
            :lesson, :session, :section, :provenance, :now, :now)
    """), {
        "learner": learner_id, "concept": concept_id, "graph": graph_id, "version": graph_version,
        "first": moment, "next": decision.due_at, "difficulty": decision.difficulty_estimate,
        "mastery": decision.mastery_estimate, "lesson": source_lesson_id, "session": source_session_id,
        "section": source_section_id, "provenance": _json(provenance), "now": moment,
    })
    return get_memory(connection, learner_id, concept_id)  # type: ignore[return-value]


def apply_schedule_decision(
    connection: Connection,
    *,
    learner_id: str,
    concept_id: str,
    decision: ScheduleDecision,
    outcome: str | None,
    confidence: str | None,
    score: float | None,
    question_type: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    moment = now or utc_now()
    memory = get_memory(connection, learner_id, concept_id)
    if memory is None:
        raise ValueError("concept_memory_missing")
    review_count = int(memory["reviewCount"]) + (0 if outcome == "skip" else 1)
    success = int(memory["successfulRecallCount"]) + (1 if outcome == "correct" else 0)
    failed = int(memory["failedRecallCount"]) + (1 if outcome == "incorrect" else 0)
    partial = int(memory["partialRecallCount"]) + (1 if outcome == "partial" else 0)
    skips = int(memory["skipCount"]) + (1 if outcome == "skip" else 0)
    streak = int(memory["currentStreak"]) + 1 if outcome == "correct" else 0
    provenance = {**memory.get("provenance", {}), "lastIntervalDays": decision.interval_days, "scheduler": decision.scheduler_version, "dueReason": decision.due_reason}
    connection.execute(text("""
        UPDATE concept_memory_states SET
            last_reviewed_at=:reviewed, next_review_at=:next, review_count=:reviews,
            successful_recall_count=:success, failed_recall_count=:failed, partial_recall_count=:partial,
            skip_count=:skips, current_streak=:streak, consecutive_successes=:cs, consecutive_failures=:cf,
            difficulty_estimate=:difficulty, last_score=:score, last_confidence=:confidence,
            last_outcome=:outcome, last_question_type=:qtype, mastery_estimate=:mastery,
            needs_remediation=:remediation, provenance_json=:provenance, updated_at=:now
        WHERE learner_id=:learner AND concept_id=:concept
    """), {
        "reviewed": moment, "next": decision.due_at, "reviews": review_count, "success": success,
        "failed": failed, "partial": partial, "skips": skips, "streak": streak,
        "cs": decision.consecutive_successes, "cf": decision.consecutive_failures,
        "difficulty": decision.difficulty_estimate, "score": score, "confidence": confidence,
        "outcome": outcome, "qtype": question_type, "mastery": decision.mastery_estimate,
        "remediation": decision.needs_remediation, "provenance": _json(provenance), "now": moment,
        "learner": learner_id, "concept": concept_id,
    })
    return get_memory(connection, learner_id, concept_id)  # type: ignore[return-value]


def upsert_relationship(
    connection: Connection,
    *,
    learner_id: str,
    source_concept_id: str,
    target_concept_id: str,
    relationship_type: str,
    provenance: dict[str, Any] | None = None,
) -> None:
    ensure_learner(connection, learner_id)
    now = utc_now()
    exists = connection.execute(text("""
        SELECT 1 FROM concept_relationships
        WHERE learner_id=:learner AND source_concept_id=:source AND target_concept_id=:target AND relationship_type=:rtype
    """), {"learner": learner_id, "source": source_concept_id, "target": target_concept_id, "rtype": relationship_type}).first()
    if exists:
        return
    connection.execute(text("""
        INSERT INTO concept_relationships(id, learner_id, source_concept_id, target_concept_id, relationship_type, provenance_json, created_at)
        VALUES (:id, :learner, :source, :target, :rtype, :provenance, :now)
    """), {
        "id": f"crel_{uuid4().hex}", "learner": learner_id, "source": source_concept_id,
        "target": target_concept_id, "rtype": relationship_type,
        "provenance": _json(provenance or {}), "now": now,
    })


def list_memories(connection: Connection, learner_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(text("""
        SELECT * FROM concept_memory_states WHERE learner_id=:learner ORDER BY next_review_at ASC
    """), {"learner": learner_id}).mappings().all()
    return [memory_from_row(row) for row in rows]
