"""Contracts for living study notes: session linkage, section provenance, proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import utc_now


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


class StudyApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


TutorUpdatesMode = Literal["ask", "auto", "never"]
SectionOwner = Literal["tutor", "user", "shared"]
ProposalStatus = Literal["proposed", "applied", "rejected"]
ProposalOrigin = Literal["turn", "quiz", "insight"]


class StudyNoteLink(StudyApiModel):
    note_id: str
    title: str
    revision: int
    tutor_updates: TutorUpdatesMode = "ask"
    session_ids: list[str] = Field(default_factory=list)


class SectionProvenance(StudyApiModel):
    id: str
    note_id: str
    section_id: str
    heading: str
    owner_kind: SectionOwner
    created_from: str
    revision: int
    content_hash: str
    concept_title: str | None = None
    graph_concept_id: str | None = None
    learner_concept_id: str | None = None
    tombstoned: bool = False


class ProposalCreate(StudyApiModel):
    origin: ProposalOrigin = "turn"
    turn_index: int | None = Field(default=None, ge=0)
    attempt_ids: list[str] = Field(default_factory=list, max_length=20)
    section_id: str | None = Field(default=None, max_length=160)
    source_text: str | None = Field(default=None, max_length=6000)
    source_label: str | None = Field(default=None, max_length=200)
    expected_note_revision: int | None = Field(default=None, ge=1)

    @field_validator("attempt_ids")
    @classmethod
    def unique_attempts(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate attempt IDs.")
        return value

    @field_validator("source_text", "source_label")
    @classmethod
    def strip_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split()) or None


class NoteProposal(StudyApiModel):
    id: str
    session_id: str
    note_id: str
    origin: ProposalOrigin
    status: ProposalStatus = "proposed"
    heading: str
    body: str
    section_id: str | None = None
    concept_title: str | None = None
    graph_concept_id: str | None = None
    learner_concept_id: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    revision: int = 1
    created_at: datetime = Field(default_factory=utc_now)


class ProposalAcceptInput(StudyApiModel):
    body: str | None = Field(default=None, max_length=12000)
    heading: str | None = Field(default=None, max_length=300)
    expected_revision: int | None = Field(default=None, ge=1)


class InsightInput(StudyApiModel):
    heading: str | None = Field(default=None, max_length=300)
    body: str = Field(min_length=1, max_length=12000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Insight text must not be blank.")
        return value


class StudySettingsInput(StudyApiModel):
    tutor_updates: TutorUpdatesMode
    expected_revision: int = Field(ge=1)
