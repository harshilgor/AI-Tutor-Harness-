"""Provider-neutral contracts for durable streamed teaching generations."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import Field

from .assessment_models import JourneyCommand
from .session_models import ApiModel
from .visualization_models import VisualType

GenerationStatus = Literal["queued", "preparing", "streaming", "finalizing", "completed", "cancel_requested", "cancelled", "failed", "interrupted"]
GenerationEventType = Literal[
    "generation.started",
    "generation.context_ready",
    "text.delta",
    "lesson.block_started",
    "visualization.planning",
    "visualization.ready",
    "visualization.skipped",
    "lesson.block_completed",
    "source.added",
    "tool.started",
    "tool.completed",
    "generation.completed",
    "generation.cancelled",
    "generation.error",
]


class GenerationRequest(JourneyCommand):
    """A message-producing Journey command observed through the generation API."""
    action: Literal["message", "start", "next", "repair"] = "message"
    selected_span_ids: list[str] = Field(default_factory=list, max_length=6)
    selected_text: str | None = Field(default=None, max_length=2000)
    selected_lesson_id: str | None = Field(default=None, max_length=160)
    selected_block_id: str | None = Field(default=None, max_length=160)
    visual_type: VisualType | Literal["auto"] = "auto"


class GenerationDescriptor(ApiModel):
    id: str
    session_id: str
    mode: Literal["ask", "learn"]
    status: GenerationStatus
    sequence: int = 0
    provider: str
    model: str
    journey_revision: int | None = None
    final_revision: int | None = None
    error_code: str | None = None
    metrics: dict[str, float | int | bool | str | None] = Field(default_factory=dict)


class GenerationEvent(ApiModel):
    generation_id: str
    sequence: int
    type: GenerationEventType
    data: dict[str, Any] = Field(default_factory=dict)
