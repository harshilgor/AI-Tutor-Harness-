from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class TopicScopeCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    objective: str | None = Field(default=None, max_length=500)
    depth: Literal["overview", "introductory", "deep"] = "introductory"

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("topic must contain at least one non-whitespace character")
        return value

    @field_validator("objective")
    @classmethod
    def normalize_objective(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return value or None


class TopicScope(BaseModel):
    id: str
    topic: str
    resolved_meaning: str
    objective: str
    depth: str
    revision: int = 1
    created_at: datetime


class SourceReference(BaseModel):
    id: str
    title: str
    url: str | None = None
    support_status: Literal["supported", "partial", "unverified"]
    locator: str | None = None


class Concept(BaseModel):
    id: str
    title: str
    label: str
    summary: str
    objective: str
    source_ids: list[str] = Field(default_factory=list)
    support_status: Literal["supported", "partial", "unverified"] = "unverified"


class Edge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["requires", "part_of", "related_to"]
    justification: str
    support_status: Literal["supported", "partial", "inferred", "unverified"]


class GraphVersion(BaseModel):
    id: str
    scope_id: str
    title: str
    description: str
    version: int = 1
    publication_state: Literal["limited_unverified", "published", "draft"]
    trust_summary: str
    concepts: list[Concept]
    edges: list[Edge]
    sources: list[SourceReference] = Field(default_factory=list)
    generated_by: str
    created_at: datetime


class GraphJob(BaseModel):
    id: str
    scope_id: str
    status: JobStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    graph_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateGraphJobResponse(BaseModel):
    job: GraphJob
    graph: GraphVersion | None = None

