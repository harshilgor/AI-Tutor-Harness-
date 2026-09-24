"""Structured answer evaluation for Review free-response items."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from ..model_provider import ModelProviderError
from ..json_context_prompt import bounded_json_prompt
from .models import ReviewEvaluationResult
from .prompts import ANSWER_EVALUATE_V1


class _EvalSchema(BaseModel):
    correctness: str
    score: float = Field(ge=0, le=1)
    confidence_assessment: str = "medium"
    missing_concepts: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    feedback: str = Field(min_length=5, max_length=3000)
    ideal_answer: str = ""
    needs_remediation: bool = False
    certain: bool = True
    prerequisite_gap: str | None = None


def evaluate_answer(
    provider: Any | None,
    *,
    concept_title: str,
    source_excerpt: str,
    prompt: str,
    expected_answer: str,
    response: str,
    selected_ids: list[str] | None = None,
    correct_option_ids: list[str] | None = None,
) -> ReviewEvaluationResult | None:
    """Return structured evaluation, or None when evaluation is uncertain/unavailable.

    None means: do not admit evidence and do not mutate memory correctness.
    """
    if selected_ids and correct_option_ids is not None:
        score = float(set(selected_ids) == set(correct_option_ids))
        correctness = "correct" if score == 1 else "incorrect"
        return ReviewEvaluationResult(
            correctness=correctness,  # type: ignore[arg-type]
            score=score,
            feedback="Your selection is correct." if score else "That selection does not match the supported answer.",
            ideal_answer=expected_answer,
            certain=True,
            needs_remediation=score < 1,
        )
    text = (response or "").strip()
    if not text:
        return ReviewEvaluationResult(
            correctness="incorrect",
            score=0.0,
            feedback="No answer was submitted. Try retrieving what you remember before continuing.",
            ideal_answer=expected_answer,
            certain=True,
            needs_remediation=True,
        )
    if provider is None:
        return _heuristic(text, expected_answer, concept_title)
    try:
        raw = provider.complete_json(
            bounded_json_prompt(provider, ANSWER_EVALUATE_V1, {
                "schema": _EvalSchema.model_json_schema(),
                "concept": concept_title,
                "source_excerpt": source_excerpt[:4000],
                "question": prompt,
                "expected_answer": expected_answer,
                "learner_response": text,
            }, required={"schema", "concept", "source_excerpt", "question", "expected_answer", "learner_response"}),
            1600,
        )
        parsed = _EvalSchema.model_validate(raw)
        if parsed.correctness not in {"correct", "partial", "incorrect"}:
            return None
        if not parsed.certain:
            return None
        if not (source_excerpt or expected_answer).strip():
            return None
        return ReviewEvaluationResult(
            correctness=parsed.correctness,  # type: ignore[arg-type]
            score=parsed.score,
            confidence_assessment=parsed.confidence_assessment if parsed.confidence_assessment in {"low", "medium", "high"} else "medium",  # type: ignore[arg-type]
            missing_concepts=parsed.missing_concepts[:8],
            misconceptions=parsed.misconceptions[:8],
            feedback=parsed.feedback,
            ideal_answer=parsed.ideal_answer or expected_answer,
            needs_remediation=parsed.needs_remediation or parsed.correctness == "incorrect",
            certain=True,
            prerequisite_gap=parsed.prerequisite_gap,
        )
    except (ModelProviderError, Exception):
        return None


def _heuristic(response: str, expected: str, title: str) -> ReviewEvaluationResult:
    tokens = {t.lower() for t in expected.replace(".", " ").split() if len(t) > 3}
    hit = sum(1 for t in tokens if t in response.lower())
    if not tokens:
        ratio = 0.5 if title.lower().split()[0] in response.lower() else 0.2
    else:
        ratio = hit / max(1, len(tokens))
    if ratio >= 0.55:
        correctness, score = "correct", min(1.0, 0.6 + ratio * 0.4)
        feedback = "Your answer covers the main idea."
    elif ratio >= 0.25:
        correctness, score = "partial", ratio
        feedback = "Partially correct — some key pieces are missing."
    else:
        correctness, score = "incorrect", max(0.0, ratio)
        feedback = "This recall missed important parts of the concept."
    return ReviewEvaluationResult(
        correctness=correctness,  # type: ignore[arg-type]
        score=score,
        feedback=feedback,
        ideal_answer=expected or f"A clear explanation of {title}.",
        certain=True,
        needs_remediation=correctness != "correct",
    )
