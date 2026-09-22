"""Review question generation grounded in concept source material."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ..model_provider import ModelProviderError
from .models import QuestionType
from .prompts import QUESTION_GENERATE_V1

QUESTION_TYPES: list[QuestionType] = [
    "free_recall", "explain", "apply", "compare", "diagnose", "teach", "short_answer",
]


class GeneratedQuestion(BaseModel):
    question_type: QuestionType
    prompt: str = Field(min_length=8, max_length=2000)
    expected_answer: str = Field(default="", max_length=4000)
    options: list[dict[str, str]] = Field(default_factory=list)
    difficulty: str = "standard"


def _pick_type(memory: dict[str, Any] | None, recent_types: list[str]) -> QuestionType:
    mastery = (memory or {}).get("masteryEstimate") or "recently_learned"
    failures = int((memory or {}).get("consecutiveFailures") or 0)
    if failures > 0 or mastery == "needs_reinforcement":
        pool: list[QuestionType] = ["free_recall", "short_answer", "explain"]
    elif mastery == "strong":
        pool = ["apply", "compare", "diagnose", "teach", "explain"]
    else:
        pool = ["free_recall", "explain", "short_answer", "apply"]
    for candidate in pool:
        if candidate not in recent_types[-2:]:
            return candidate
    return pool[0]


def generate_question(
    provider: Any | None,
    *,
    concept_title: str,
    concept_summary: str,
    source_excerpt: str,
    memory: dict[str, Any] | None = None,
    recent_questions: list[str] | None = None,
    recent_types: list[str] | None = None,
) -> GeneratedQuestion:
    qtype = _pick_type(memory, recent_types or [])
    recent = recent_questions or []
    if provider is None:
        return _fallback_question(concept_title, concept_summary, qtype)
    schema = {
        "type": "object",
        "properties": {
            "question_type": {"type": "string", "enum": list(QUESTION_TYPES)},
            "prompt": {"type": "string"},
            "expected_answer": {"type": "string"},
            "options": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string"}}}},
            "difficulty": {"type": "string"},
        },
        "required": ["question_type", "prompt", "expected_answer"],
    }
    try:
        raw = provider.complete_json(
            QUESTION_GENERATE_V1 + "\n" + json.dumps({
                "schema": schema,
                "preferred_type": qtype,
                "concept": {"title": concept_title, "summary": concept_summary},
                "source_excerpt": source_excerpt[:4000],
                "recent_questions": recent[-5:],
            }, ensure_ascii=False),
            1200,
        )
        item = GeneratedQuestion.model_validate(raw)
        # Review does not yet have a validated private answer-key contract.
        # Fail closed by replacing provider-authored multiple choice with a
        # free-response item instead of inferring correctness from option order.
        if item.question_type == "multiple_choice":
            return _fallback_question(concept_title, concept_summary, "short_answer")
        if item.prompt.strip() in recent:
            item = _fallback_question(concept_title, concept_summary, qtype)
        return item
    except (ModelProviderError, Exception):
        return _fallback_question(concept_title, concept_summary, qtype)


def _fallback_question(title: str, summary: str, qtype: QuestionType) -> GeneratedQuestion:
    prompts = {
        "free_recall": f"Without looking at your lesson: What is {title}?",
        "explain": f"Explain {title} in your own words.",
        "apply": f"Describe a concrete situation where {title} matters and what you would do.",
        "compare": f"How does {title} relate to or differ from a closely connected idea you studied?",
        "diagnose": f"A learner is confused about {title}. What misconception might they have, and how would you correct it?",
        "teach": f"Teach {title} to someone new to the topic in a few clear sentences.",
        "short_answer": f"In one or two sentences, what is the core idea of {title}?",
        "multiple_choice": f"Which statement best captures {title}?",
    }
    expected = summary.strip() or f"A clear explanation of {title}."
    options = []
    if qtype == "multiple_choice":
        options = [
            {"id": "a", "label": expected[:180] or f"The core idea of {title}"},
            {"id": "b", "label": f"An unrelated idea that is not {title}"},
            {"id": "c", "label": f"A partial description that misses the point of {title}"},
        ]
    return GeneratedQuestion(
        question_type=qtype,
        prompt=prompts.get(qtype, prompts["free_recall"]),
        expected_answer=expected,
        options=options,
        difficulty="standard",
    )


def new_item_id() -> str:
    return f"review_item_{uuid4().hex}"
