"""Weighted review session composition with interleaving."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .scheduler import (
    SESSION_SIZES,
    PriorityInputs,
    estimate_minutes,
    priority_score,
)


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo is not None else current.replace(tzinfo=timezone.utc)


def compose_session(
    memories: list[dict[str, Any]],
    *,
    length: str = "standard",
    concept_ids: list[str] | None = None,
    optional: bool = False,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return ordered concept picks for a review session and estimated minutes."""
    moment = _utc(now)
    size = SESSION_SIZES.get(length, SESSION_SIZES["standard"])
    candidates: list[dict[str, Any]] = []
    for memory in memories:
        if concept_ids and memory["conceptId"] not in concept_ids:
            continue
        next_at = memory["nextReviewAt"]
        if isinstance(next_at, str):
            next_at = datetime.fromisoformat(next_at)
        next_at = _utc(next_at)
        overdue_hours = max(0.0, (moment - next_at).total_seconds() / 3600.0)
        first = memory["firstLearnedAt"]
        if isinstance(first, str):
            first = datetime.fromisoformat(first)
        first = _utc(first)
        last = memory.get("lastReviewedAt")
        if isinstance(last, str):
            last = datetime.fromisoformat(last)
        days_since_review = ((moment - _utc(last)).total_seconds() / 86400.0) if last else ((moment - first).total_seconds() / 86400.0)
        days_since_learned = (moment - first).total_seconds() / 86400.0
        due = overdue_hours > 0 or memory["masteryEstimate"] in {"needs_reinforcement", "due", "recently_learned"}
        if not optional and not due and memory["masteryEstimate"] == "strong" and overdue_hours <= 0:
            # Still allow a few strong cumulative items later.
            pass
        confidence_mismatch = (
            memory.get("lastConfidence") in {"confident", "very"} and memory.get("lastOutcome") == "incorrect"
        )
        score = priority_score(PriorityInputs(
            overdue_hours=overdue_hours,
            mastery=memory["masteryEstimate"],
            consecutive_failures=int(memory["consecutiveFailures"]),
            last_outcome=memory.get("lastOutcome"),
            needs_remediation=bool(memory["needsRemediation"]),
            days_since_learned=days_since_learned,
            days_since_review=days_since_review,
            is_cumulative=days_since_learned >= 7 and memory["masteryEstimate"] == "strong",
            confidence_mismatch=confidence_mismatch,
        ))
        if optional or due or score >= 10 or (concept_ids and memory["conceptId"] in concept_ids):
            candidates.append({
                **memory,
                "priorityScore": score,
                "dueReason": (memory.get("provenance") or {}).get("dueReason") or _default_reason(memory, overdue_hours),
                "graphTopic": memory.get("graphId"),
            })
    candidates.sort(key=lambda item: (-item["priorityScore"], item["conceptId"]))
    if not candidates and optional and memories:
        # Mixed optional recall from anything learned.
        candidates = [{**m, "priorityScore": 1.0, "dueReason": "Optional mixed recall", "graphTopic": m.get("graphId")} for m in memories]
        candidates.sort(key=lambda item: item["conceptId"])
    selected = _interleave(candidates[: max(size * 2, size)], size)
    return selected, estimate_minutes(len(selected))


def _default_reason(memory: dict[str, Any], overdue_hours: float) -> str:
    if memory.get("needsRemediation"):
        return "Needs reinforcement"
    if memory.get("lastOutcome") == "partial":
        return "Reviewing sooner because your last recall was partial"
    if overdue_hours > 0:
        return "Due for review"
    if memory.get("masteryEstimate") == "recently_learned":
        return "Recently learned — first recall"
    if memory.get("masteryEstimate") == "needs_reinforcement":
        return "Needs reinforcement"
    return "Due for review"


def _interleave(candidates: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    """Avoid stacking the same graph/topic repeatedly when alternatives exist."""
    if len(candidates) <= size:
        return candidates[:size]
    selected: list[dict[str, Any]] = []
    remaining = candidates[:]
    last_topic: str | None = None
    while remaining and len(selected) < size:
        pick_index = 0
        for index, item in enumerate(remaining):
            topic = item.get("graphTopic") or item["conceptId"]
            if topic != last_topic:
                pick_index = index
                break
        chosen = remaining.pop(pick_index)
        selected.append(chosen)
        last_topic = chosen.get("graphTopic") or chosen["conceptId"]
    return selected
