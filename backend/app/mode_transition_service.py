"""Intent-aware mode transition evaluation and cooldown policy.

The tutor only suggests a mode change when the learner's intent genuinely calls
for it. Difficulty, conversation length, and normal exploratory follow-ups are
never treated as evidence for a mode transition.
"""
from __future__ import annotations

import re
from typing import Any, Literal
from uuid import uuid4

from .mode_transition_models import (
    IntentEvaluationResult,
    ModeTransitionInteraction,
    ModeTransitionSuggestion,
    ModeType,
)
from .models import utc_now
from .workflow_store import WorkflowStore

CONFIDENCE_THRESHOLD = 0.85
COOLDOWN_TURN_WINDOW = 5

# --- REGEX RULES FOR EXPLICIT DIRECTIVES ---

# Directives that strictly suppress any mode transition suggestion
_EXPLICIT_SUPPRESSION_PATTERNS = [
    r"\bjust (give me )?(the )?answer\b",
    r"\b(don'?t|do not) (teach|quiz|test|lecture)\b",
    r"\bno quiz\b",
    r"\bkeep it (quick|short|brief|simple)\b",
    r"\bshort answer (only|please)\b",
    r"\bdirect answer\b",
    r"\bonly answer the question\b",
]

# Directives that explicitly request a structured teaching journey (Learn)
_EXPLICIT_LEARN_PATTERNS = [
    r"\bteach me (this|that|about|how|from the beginning|properly|step by step)\b",
    r"\bcan you teach me\b",
    r"\bi want to (actually|truly|properly) understand\b",
    r"\bwalk me through this (from the beginning|step by step)\b",
    r"\bbuild this up (step by step|from (the )?prerequisites|from scratch|from first principles)\b",
    r"\bstart from the prerequisites\b",
    r"\bi want to learn this (properly|deeply|from first principles)\b",
    r"\b(don'?t|do not) want just an answer\b",
    r"\blet'?s spend some time learning this\b",
    r"\bmake sure i (actually|really) understand\b",
    r"\bstructured lesson\b",
]

# Directives that explicitly request testing, active recall, or assessment (Quiz)
_EXPLICIT_QUIZ_PATTERNS = [
    r"\bquiz me\b",
    r"\btest my understanding\b",
    r"\btest me on (this|what i just learned|these concepts)\b",
    r"\bcan you give me (practice|test) questions\b",
    r"\bgive me practice questions\b",
    r"\b(don'?t|do not) tell me the answer[,;]? ask me questions\b",
    r"\bsee if i (actually|really) remember\b",
    r"\bgive me an exam\b",
    r"\bpractice questions\b",
    r"\bask me (a )?question(s)? to test me\b",
]

# Anti-signals that represent completely valid Ask interactions and must NOT trigger Learn
_ANTI_LEARN_PATTERNS = [
    r"^why\??$",
    r"^why does this happen\??$",
    r"^can you explain that\??$",
    r"^can you give me an example\??$",
    r"^i'?m confused about this (one )?part\??$",
    r"^can you go deeper\??$",
    r"^can you explain it more simply\??$",
    r"^what does this (term|word|sentence) mean\??$",
    r"^simplify that\??$",
]


class ModeTransitionService:
    def __init__(self, store):
        self.store = store
        self.records = WorkflowStore(store) if store else None

    @staticmethod
    def _matches_any(text: str, patterns: list[str]) -> bool:
        lowered = text.lower().strip()
        return any(re.search(pattern, lowered) for pattern in patterns)

    def evaluate_intent(
        self,
        current_message: str,
        recent_turns: list[dict[str, Any]],
        current_mode: ModeType,
        session_id: str | None = None,
        owner: str = "local",
        concept_title: str | None = None,
        concept_id: str | None = None,
        course_id: str | None = None,
    ) -> IntentEvaluationResult:
        """Evaluate learner intent across current message, recent turns, and current mode."""
        msg = (current_message or "").strip()
        if not msg:
            return IntentEvaluationResult(intent="none", confidence=0.0, reason="empty_message")

        # 1. Explicit suppression check: "just give me the answer"
        if self._matches_any(msg, _EXPLICIT_SUPPRESSION_PATTERNS):
            return IntentEvaluationResult(
                intent="ask",
                confidence=0.99,
                reason="explicit_suppression_directive",
                target_mode=None,
            )

        # 2. Check cooldowns / dismissals if session is provided
        dismissed_modes, last_turn_suggested = self._get_session_cooldown(owner, session_id)
        current_turn_index = len(recent_turns)

        # 3. Explicit Quiz directive: "quiz me"
        if self._matches_any(msg, _EXPLICIT_QUIZ_PATTERNS):
            if "quiz" in dismissed_modes:
                return IntentEvaluationResult(intent="quiz", confidence=0.95, reason="quiz_suppressed_by_cooldown")
            if current_mode != "quiz":
                suggestion = self._build_quiz_suggestion(
                    source_mode=current_mode,
                    concept_title=concept_title or "this topic",
                    concept_id=concept_id,
                    confidence=0.95,
                    reason="explicit_quiz_request",
                    session_id=session_id,
                    course_id=course_id,
                )
                return IntentEvaluationResult(
                    intent="quiz",
                    confidence=0.95,
                    reason="explicit_quiz_request",
                    target_mode="quiz",
                    suggestion=suggestion,
                )
            return IntentEvaluationResult(intent="quiz", confidence=0.95, reason="already_in_quiz")

        # 4. Explicit Learn directive: "teach me from the beginning"
        if self._matches_any(msg, _EXPLICIT_LEARN_PATTERNS):
            if "learn" in dismissed_modes:
                return IntentEvaluationResult(intent="learn", confidence=0.95, reason="learn_suppressed_by_cooldown")
            if current_mode != "learn":
                suggestion = self._build_learn_suggestion(
                    source_mode=current_mode,
                    concept_title=concept_title or "this topic",
                    concept_id=concept_id,
                    confidence=0.95,
                    reason="explicit_teaching_request",
                    session_id=session_id,
                    course_id=course_id,
                    seed_prompt=msg,
                )
                return IntentEvaluationResult(
                    intent="learn",
                    confidence=0.95,
                    reason="explicit_teaching_request",
                    target_mode="learn",
                    suggestion=suggestion,
                )
            return IntentEvaluationResult(intent="learn", confidence=0.95, reason="already_in_learn")

        # 5. Anti-signals: normal Ask clarification queries
        if self._matches_any(msg, _ANTI_LEARN_PATTERNS):
            return IntentEvaluationResult(
                intent="ask",
                confidence=0.90,
                reason="normal_exploratory_clarification",
                target_mode=None,
            )

        # 6. Multi-turn conversational intent analysis
        # Check if the user signaled understanding after an explanation and wants testing
        # e.g., "I think I get it now" or "Okay I understand" + recent explanation
        if current_mode == "ask" and recent_turns and "quiz" not in dismissed_modes:
            if re.search(r"\b(i think i (get|understand) it( now)?|makes sense now|got it now)\b", msg.lower()):
                # User understood the explanation; this is a prime opportunity for Quiz
                suggestion = self._build_quiz_suggestion(
                    source_mode=current_mode,
                    concept_title=concept_title or "this topic",
                    concept_id=concept_id,
                    confidence=0.86,
                    reason="readiness_for_testing",
                    session_id=session_id,
                    course_id=course_id,
                )
                return IntentEvaluationResult(
                    intent="quiz",
                    confidence=0.86,
                    reason="readiness_for_testing",
                    target_mode="quiz",
                    suggestion=suggestion,
                )

        # Check if 1 suggestion per cooldown window rule is met
        if last_turn_suggested is not None and (current_turn_index - last_turn_suggested) < COOLDOWN_TURN_WINDOW:
            return IntentEvaluationResult(intent="none", confidence=0.0, reason="frequency_cap_cooldown")

        return IntentEvaluationResult(intent="none", confidence=0.0, reason="no_strong_intent_signal")

    def evaluate_quiz_gap(
        self,
        owner: str,
        session_id: str,
        concept_id: str,
        concept_title: str,
        consecutive_misses: int,
        course_id: str | None = None,
    ) -> ModeTransitionSuggestion | None:
        """Suggest transitioning from Quiz to Learn only after persistent concept gaps (2+ misses)."""
        if consecutive_misses < 2:
            return None

        dismissed_modes, _ = self._get_session_cooldown(owner, session_id)
        if "learn" in dismissed_modes:
            return None

        return ModeTransitionSuggestion(
            id=f"trans-{uuid4().hex[:12]}",
            source_mode="quiz",
            target_mode="learn",
            reason="persistent_concept_gap",
            confidence=0.88,
            title="Review this concept in Learn?",
            description=f"You've encountered difficulty with {concept_title}. Want to work through it step by step in Learn?",
            action_label="Continue in Learn",
            dismiss_label="Not now",
            context={
                "sessionId": session_id,
                "conceptId": concept_id,
                "conceptTitle": concept_title,
                "courseId": course_id,
                "consecutiveMisses": consecutive_misses,
            },
            created_at=utc_now(),
        )

    def record_interaction(
        self,
        owner: str,
        interaction: ModeTransitionInteraction,
    ) -> None:
        """Persist a learner's dismissal or acceptance of a suggestion."""
        if not self.store or not interaction.session_id:
            return
        with self.store.transaction() as conn:
            from sqlalchemy import text
            conn.execute(text("""
                INSERT INTO practice_records(id, owner_id, kind, parent_id, revision, payload)
                VALUES(:id, :owner, 'transition_interaction', :parent, 1, :payload)
            """), {
                "id": f"trans_act_{interaction.suggestion_id}",
                "owner": owner,
                "parent": interaction.session_id,
                "payload": interaction.model_dump_json(),
            })

    def _get_session_cooldown(self, owner: str, session_id: str | None) -> tuple[set[str], int | None]:
        """Query dismissed modes and turn index of the most recent suggestion."""
        if not self.store or not session_id:
            return set(), None
        try:
            with self.store.engine.connect() as conn:
                from sqlalchemy import text
                rows = conn.execute(text("""
                    SELECT payload FROM practice_records
                    WHERE owner_id=:owner AND parent_id=:sid AND kind='transition_interaction'
                """), {"owner": owner, "sid": session_id}).fetchall()
                dismissed = set()
                for row in rows:
                    import json
                    data = json.loads(row[0])
                    if data.get("action") == "dismiss" and data.get("target_mode"):
                        dismissed.add(data["target_mode"])
                return dismissed, None
        except Exception:
            return set(), None

    def _build_learn_suggestion(
        self,
        source_mode: ModeType,
        concept_title: str,
        concept_id: str | None,
        confidence: float,
        reason: str,
        session_id: str | None,
        course_id: str | None,
        seed_prompt: str,
    ) -> ModeTransitionSuggestion:
        return ModeTransitionSuggestion(
            id=f"trans-{uuid4().hex[:12]}",
            source_mode=source_mode,
            target_mode="learn",
            reason=reason,
            confidence=confidence,
            title="Continue in Learn?",
            description=(
                f"I can teach {concept_title} step by step, build from concepts you already know, "
                "and check your understanding along the way."
            ),
            action_label="Continue in Learn",
            dismiss_label="Not now",
            context={
                "sessionId": session_id,
                "conceptId": concept_id,
                "conceptTitle": concept_title,
                "courseId": course_id,
                "seedPrompt": seed_prompt,
                "originSummary": f"Started from your conversation about {concept_title}",
            },
            created_at=utc_now(),
        )

    def _build_quiz_suggestion(
        self,
        source_mode: ModeType,
        concept_title: str,
        concept_id: str | None,
        confidence: float,
        reason: str,
        session_id: str | None,
        course_id: str | None,
    ) -> ModeTransitionSuggestion:
        is_explicit = reason == "explicit_quiz_request"
        return ModeTransitionSuggestion(
            id=f"trans-{uuid4().hex[:12]}",
            source_mode=source_mode,
            target_mode="quiz",
            reason=reason,
            confidence=confidence,
            title="Ready for a quiz?" if is_explicit else "Test yourself on this?",
            description=(
                f"Test your recall on {concept_title} with practice questions."
                if is_explicit
                else f"Practice active recall on {concept_title} to strengthen your understanding."
            ),
            action_label="Start Quiz" if is_explicit else "Continue in Quiz",
            dismiss_label="Not now",
            context={
                "sessionId": session_id,
                "conceptId": concept_id,
                "conceptTitle": concept_title,
                "courseId": course_id,
                "questionCount": 5,
            },
            created_at=utc_now(),
        )
