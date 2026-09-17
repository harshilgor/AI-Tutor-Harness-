"""Display-safe contracts for deterministic next-action recommendations."""
from datetime import datetime
from typing import Literal
from pydantic import Field
from .session_models import ApiModel

RecommendationAction = Literal["learn", "ask", "quiz", "review"]
InteractionType = Literal["impression", "selection", "dismissal", "completion", "failure"]


class NextActionRecommendation(ApiModel):
    id: str
    action_kind: RecommendationAction
    title: str = Field(min_length=1, max_length=180)
    rationale: str = Field(min_length=1, max_length=500)
    concept_id: str | None = None
    concept_title: str | None = None
    effort_minutes: int = Field(ge=1, le=60)
    context: dict[str, str] = Field(default_factory=dict)
    score: int = Field(ge=0, le=100)


class RecommendationSet(ApiModel):
    id: str
    session_id: str
    policy_version: str
    created_at: datetime
    recommendations: list[NextActionRecommendation] = Field(min_length=1, max_length=4)


class RecommendationInteractionCreate(ApiModel):
    event_type: InteractionType
    # A small UI-only reason may be retained for dismissals; never note text,
    # answers, source passages, or model prompts.
    reason: str | None = Field(default=None, max_length=240)
