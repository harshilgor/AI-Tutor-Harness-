"""Deterministic Teach / Check / Repair policy for the immediate tutor loop."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from .adaptive_observability import ImmediateAdaptationInput
from .session_models import ApiModel

IMMEDIATE_ADAPTATION_POLICY_VERSION = "immediate-adaptation-v1"
PedagogicalAction = Literal["teach", "check", "repair"]


class ImmediateAdaptationDecision(ApiModel):
    action: PedagogicalAction
    reason_code: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    policy_version: str = IMMEDIATE_ADAPTATION_POLICY_VERSION


def policy_input_digest(value: ImmediateAdaptationInput) -> str:
    stable = {
        "policyVersion": IMMEDIATE_ADAPTATION_POLICY_VERSION,
        "sessionRevision": value.session_revision,
        "conceptId": value.concept_id,
        "conceptStateVersion": value.concept_state_version or 0,
        "lessonCompletedAt": value.latest_lesson_completed_at.isoformat() if value.latest_lesson_completed_at else None,
        "evidence": [
            {
                "id": item.id,
                "outcome": item.outcome,
                "condition": item.condition,
                "itemFamily": item.item_family,
                "misconceptionCode": item.misconception_code,
                "assistanceExposed": item.assistance_exposed,
                "occurredAt": item.occurred_at.isoformat(),
            }
            for item in value.evidence
        ],
        "activeMisconceptions": value.active_misconception_codes,
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:40]


def decide_immediate_action(value: ImmediateAdaptationInput) -> ImmediateAdaptationDecision:
    """Choose one immediate action without changing learner state."""
    observations = [
        item for item in value.evidence
        if item.kind in {"assessment", "review"}
    ]
    if not observations:
        if value.lesson_exposed:
            return ImmediateAdaptationDecision(
                action="check",
                reason_code="taught_without_check",
                rationale="You have worked through this idea. A fresh check will show what to do next.",
            )
        return ImmediateAdaptationDecision(
            action="teach",
            reason_code="new_concept",
            rationale="Start with a clear explanation before checking your understanding.",
        )

    latest = observations[0]
    evidence_ids = [item.id for item in observations]
    if latest.outcome in {"correct", "partial"} and latest.assistance_exposed:
        return ImmediateAdaptationDecision(
            action="check",
            reason_code="assisted_success_needs_fresh_check",
            rationale="You succeeded with help. Try a fresh question without assistance before moving on.",
            evidence_ids=[latest.id],
        )

    misses = [
        item for item in observations
        if item.outcome == "incorrect" and item.condition == "independent"
    ]
    distinct_families = {item.item_family for item in misses if item.item_family}
    misconception_counts: dict[str, int] = {}
    for item in misses:
        if item.misconception_code:
            misconception_counts[item.misconception_code] = misconception_counts.get(item.misconception_code, 0) + 1
    repeated_misconception = any(count >= 2 for count in misconception_counts.values())
    if latest.outcome == "incorrect" and (
        len(distinct_families) >= 2
        or repeated_misconception
        or bool(value.active_misconception_codes)
    ):
        return ImmediateAdaptationDecision(
            action="repair",
            reason_code="repeated_distinct_miss",
            rationale="More than one fresh check found the same area of difficulty. Try a different explanation and guided practice.",
            evidence_ids=[item.id for item in misses],
        )

    if latest.outcome == "incorrect":
        return ImmediateAdaptationDecision(
            action="check",
            reason_code="first_independent_miss",
            rationale="One miss is not enough to diagnose a pattern. Try a different fresh question.",
            evidence_ids=[latest.id],
        )

    if latest.outcome == "correct" and latest.condition == "independent" and not latest.assistance_exposed:
        return ImmediateAdaptationDecision(
            action="teach",
            reason_code="fresh_independent_success",
            rationale="You answered a fresh question independently. Continue to the next idea.",
            evidence_ids=[latest.id],
        )

    return ImmediateAdaptationDecision(
        action="check",
        reason_code="more_evidence_needed",
        rationale="A fresh independent check will reduce uncertainty about what to do next.",
        evidence_ids=evidence_ids[:3],
    )
