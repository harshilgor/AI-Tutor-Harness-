"""Contracts for intent-aware mode transition suggestions and interactions."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import Field

from .models import utc_now
from .session_models import ApiModel

ModeType = Literal["ask", "learn", "quiz"]
TransitionAction = Literal["accept", "dismiss"]


class ModeTransitionSuggestion(ApiModel):
    """Display-safe, structured recommendation to transition between learning modes."""

    id: str
    source_mode: ModeType
    target_mode: ModeType
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=500)
    action_label: str = Field(min_length=1, max_length=60)
    dismiss_label: str = Field(default="Not now", max_length=60)
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ModeTransitionInteraction(ApiModel):
    """Learner interaction with an inline transition suggestion."""

    suggestion_id: str
    action: TransitionAction
    target_mode: ModeType
    session_id: str | None = None
    reason: str | None = Field(default=None, max_length=240)


class IntentEvaluationResult(ApiModel):
    """Internal result of multi-turn intent evaluation."""

    intent: ModeType | Literal["none"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    target_mode: ModeType | None = None
    suggestion: ModeTransitionSuggestion | None = None
