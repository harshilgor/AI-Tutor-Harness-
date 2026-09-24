"""Short remediation mini-lessons for weak review concepts."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from ..model_provider import ModelProviderError
from ..json_context_prompt import bounded_json_prompt
from .prompts import REMEDIATION_V1


class RemediationLesson(BaseModel):
    heading: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=2000)
    follow_up_prompt: str = Field(min_length=8, max_length=500)


def generate_remediation(
    provider: Any | None,
    *,
    concept_title: str,
    source_excerpt: str,
    missing_concepts: list[str] | None = None,
    feedback: str | None = None,
) -> RemediationLesson:
    if provider is None:
        return _fallback(concept_title, source_excerpt, missing_concepts)
    try:
        raw = provider.complete_json(
            bounded_json_prompt(provider, REMEDIATION_V1, {
                "schema": RemediationLesson.model_json_schema(),
                "concept": concept_title,
                "source_excerpt": source_excerpt[:3000],
                "missing_concepts": missing_concepts or [],
                "prior_feedback": feedback or "",
            }, required={"schema", "concept", "source_excerpt"}),
            1000,
        )
        lesson = RemediationLesson.model_validate(raw)
        if len(lesson.body.split()) > 220:
            lesson.body = " ".join(lesson.body.split()[:180]) + "…"
        return lesson
    except (ModelProviderError, Exception):
        return _fallback(concept_title, source_excerpt, missing_concepts)


def _fallback(title: str, excerpt: str, missing: list[str] | None) -> RemediationLesson:
    focus = ", ".join((missing or [])[:3]) or "the core idea"
    body = (
        f"{title} is worth a short refresher.\n\n"
        f"Focus on {focus}. "
        f"{(excerpt or '').strip()[:500] or 'Return to the key definition and one concrete example from your lesson.'}\n\n"
        "Keep this short, then try retrieving it again."
    )
    return RemediationLesson(
        heading=f"2-minute refresher · {title}",
        body=body,
        follow_up_prompt=f"In your own words, what is the essential idea of {title}?",
    )
