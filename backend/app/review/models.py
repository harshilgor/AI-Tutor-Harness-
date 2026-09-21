"""Typed contracts for the Review memory and session surface."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from ..session_models import ApiModel

SessionLength = Literal["quick", "standard", "deep"]
QuestionType = Literal[
    "free_recall", "explain", "apply", "compare", "diagnose", "teach", "short_answer", "multiple_choice"
]
ConfidenceLevel = Literal["guessing", "somewhat", "confident", "very"]
Correctness = Literal["correct", "partial", "incorrect"]
MasteryLabel = Literal["recently_learned", "needs_reinforcement", "developing", "strong", "due"]


class ReviewDashboardConcept(ApiModel):
    concept_id: str
    title: str
    reason: str
    mastery_estimate: MasteryLabel
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    source_lesson_id: str | None = None
    source_lesson_title: str | None = None


class ReviewDashboard(ApiModel):
    due_count: int = 0
    weak_count: int = 0
    new_count: int = 0
    total_concepts: int = 0
    estimated_minutes: int = 0
    streak_days: int = 0
    preparing: bool = False
    unfinished_session_id: str | None = None
    needs_attention: list[ReviewDashboardConcept] = Field(default_factory=list)
    recently_strengthened: list[ReviewDashboardConcept] = Field(default_factory=list)
    recently_learned: list[ReviewDashboardConcept] = Field(default_factory=list)
    empty: bool = False
    caught_up: bool = False


class ReviewSessionCreate(ApiModel):
    length: SessionLength = "standard"
    concept_ids: list[str] = Field(default_factory=list, max_length=20)
    resume_session_id: str | None = Field(default=None, max_length=160)
    optional: bool = False
    session_id: str | None = Field(default=None, max_length=160, description="Optional Learn session for graph context")


class ReviewOption(ApiModel):
    id: str
    label: str


class ReviewItemPublic(ApiModel):
    id: str
    concept_id: str
    concept_title: str
    question_type: QuestionType
    prompt: str
    options: list[ReviewOption] = Field(default_factory=list)
    status: Literal["pending", "answered", "evaluated", "skipped", "remediating"]
    due_reason: str | None = None
    source_lesson_id: str | None = None
    source_lesson_title: str | None = None
    attempt: dict[str, Any] | None = None
    remediation: dict[str, Any] | None = None
    reveal_after_answer: bool = True


class ReviewSessionPublic(ApiModel):
    id: str
    status: Literal["ready", "in_progress", "completed", "abandoned"]
    length: SessionLength
    revision: int
    item_count: int
    current_index: int
    estimated_minutes: int
    items: list[ReviewItemPublic] = Field(default_factory=list)
    summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ReviewAnswerCommand(ApiModel):
    response: str = Field(default="", max_length=8000)
    selected_ids: list[str] = Field(default_factory=list, max_length=8)
    expected_revision: int = Field(ge=1)


class ReviewConfidenceCommand(ApiModel):
    confidence: ConfidenceLevel
    expected_revision: int = Field(ge=1)


class ReviewRevisionCommand(ApiModel):
    expected_revision: int = Field(ge=1)


class ReviewEvaluationResult(ApiModel):
    correctness: Correctness
    score: float = Field(ge=0, le=1)
    confidence_assessment: Literal["low", "medium", "high"] = "medium"
    missing_concepts: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    feedback: str
    ideal_answer: str = ""
    needs_remediation: bool = False
    certain: bool = True
    prerequisite_gap: str | None = None


class ReviewAskTutorResponse(ApiModel):
    session_id: str | None = None
    prompt: str
    context: dict[str, Any]
    return_review_session_id: str


class ReviewHistoryEntry(ApiModel):
    reviewed_at: datetime
    outcome: str
    evidence_id: str | None = None


class ReviewConceptHistory(ApiModel):
    concept_id: str
    title: str
    first_learned_at: datetime | None = None
    last_outcome: str | None = None
    next_review_at: datetime | None = None
    mastery_estimate: MasteryLabel | None = None
    reviews: list[ReviewHistoryEntry] = Field(default_factory=list)
