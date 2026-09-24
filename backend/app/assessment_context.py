"""Choose assessment evidence relevant to the current concept and session."""
from __future__ import annotations


def select_attempts(records, owner: str, concept_id: str, session_id: str, limit: int = 3,
                    active_quiz_id: str | None = None, lesson_id: str | None = None) -> list[dict]:
    attempts = [attempt for attempt in records.listing(owner, "attempt") if attempt.get("conceptId") == concept_id]
    quiz_sessions: dict[str, str | None] = {}

    def same_session(attempt: dict) -> bool:
        quiz_id = attempt.get("quizId")
        if not quiz_id:
            return False
        if quiz_id not in quiz_sessions:
            try:
                quiz_sessions[quiz_id] = records.read(owner, quiz_id, "quiz").get("sessionId")
            except Exception:
                quiz_sessions[quiz_id] = None
        return quiz_sessions[quiz_id] == session_id

    def weakness(attempt: dict) -> float:
        score = attempt.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            return 0.0
        return max(0.0, min(1.0, 1.0 - float(score)))

    # Resolve the most recently active quiz for this concept/session from
    # durable attempts. This supplements (and never replaces) concept/session
    # filtering, and avoids relying on record listing order or generated IDs.
    quiz_latest: dict[str, str] = {}
    for attempt in attempts:
        quiz_id = attempt.get("quizId")
        created = str(attempt.get("createdAt") or "")
        if quiz_id and (quiz_id not in quiz_latest or created > quiz_latest[quiz_id]):
            quiz_latest[quiz_id] = created
    latest_quiz = max(quiz_latest, key=lambda quiz: (quiz_latest[quiz], quiz), default=None)

    def same_lesson(attempt: dict) -> bool:
        if not lesson_id:
            return False
        presentation_id = attempt.get("presentationId")
        if not presentation_id:
            return False
        try:
            presentation = records.read(owner, presentation_id, "presentation")
        except Exception:
            return False
        return presentation.get("lessonId") == lesson_id or presentation.get("sourceLessonId") == lesson_id

    attempts.sort(key=lambda attempt: (
        bool(active_quiz_id and attempt.get("quizId") == active_quiz_id),
        same_lesson(attempt),
        same_session(attempt),
        weakness(attempt),
        bool(attempt.get("quizId") and attempt.get("quizId") == latest_quiz),
        attempt.get("createdAt") or "", attempt.get("id") or "",
    ), reverse=True)
    return attempts[:limit]
