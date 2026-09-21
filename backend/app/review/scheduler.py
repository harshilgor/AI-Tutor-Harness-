"""Deterministic adaptive review scheduler (review-scheduler-v1).

No LLM involvement. Constants are centralized for tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

Outcome = Literal["correct", "partial", "incorrect", "skip"]
Confidence = Literal["guessing", "somewhat", "confident", "very"] | None
Condition = Literal["independent", "assisted"]

SCHEDULER_VERSION = "review-scheduler-v1"

# Interval bounds (days). Operational heuristics, not calibrated forgetting curves.
INITIAL_INTERVAL_DAYS = 1.0
MIN_INTERVAL_DAYS = 0.25  # ~6 hours
MAX_INTERVAL_DAYS = 45.0
SKIP_DELAY_DAYS = 0.5

# Multipliers applied to the previous interval.
CORRECT_HIGH_CONF = 2.2
CORRECT_MED_CONF = 1.7
CORRECT_LOW_CONF = 1.25
PARTIAL_MULT = 0.45
INCORRECT_MULT = 0.2
ASSISTED_PENALTY = 0.85
FALSE_CONFIDENCE_MULT = 0.15  # high confidence + incorrect
REPEATED_FAILURE_DAYS = 0.35
REMEDIATION_THRESHOLD = 2

# Priority weights for session composition (higher = sooner).
WEIGHT_OVERDUE = 40.0
WEIGHT_WEAK = 35.0
WEIGHT_RECENT_FAILURE = 30.0
WEIGHT_PARTIAL = 22.0
WEIGHT_NEW = 18.0
WEIGHT_CUMULATIVE = 10.0
WEIGHT_CONFIDENCE_MISMATCH = 15.0
WEIGHT_REMEDIATION = 28.0

SESSION_SIZES = {"quick": 4, "standard": 6, "deep": 10}
MINUTES_PER_ITEM = 1.2

MasteryLabel = Literal["recently_learned", "needs_reinforcement", "developing", "strong", "due"]


@dataclass(frozen=True)
class MemorySnapshot:
    review_count: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    last_interval_days: float = INITIAL_INTERVAL_DAYS
    difficulty_estimate: float = 0.5
    mastery_estimate: MasteryLabel = "recently_learned"
    needs_remediation: bool = False


@dataclass(frozen=True)
class ScheduleDecision:
    interval_days: float
    due_at: datetime
    due_reason: str
    mastery_estimate: MasteryLabel
    difficulty_estimate: float
    consecutive_successes: int
    consecutive_failures: int
    needs_remediation: bool
    scheduler_version: str = SCHEDULER_VERSION


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo is not None else current.replace(tzinfo=timezone.utc)


def _clamp(interval: float) -> float:
    return max(MIN_INTERVAL_DAYS, min(MAX_INTERVAL_DAYS, round(interval, 4)))


def _confidence_band(confidence: Confidence) -> Literal["low", "medium", "high"]:
    if confidence in {"guessing", "somewhat"}:
        return "low"
    if confidence == "confident":
        return "medium"
    if confidence == "very":
        return "high"
    return "medium"


def schedule_after_outcome(
    *,
    outcome: Outcome,
    confidence: Confidence,
    condition: Condition,
    memory: MemorySnapshot,
    now: datetime | None = None,
) -> ScheduleDecision:
    """Compute the next review interval from retrieval performance."""
    moment = _utc(now)
    previous = max(memory.last_interval_days, INITIAL_INTERVAL_DAYS)
    difficulty = memory.difficulty_estimate
    successes = memory.consecutive_successes
    failures = memory.consecutive_failures
    remediation = memory.needs_remediation
    band = _confidence_band(confidence)

    if outcome == "skip":
        interval = SKIP_DELAY_DAYS
        reason = "Skipped — kept on your review list"
        mastery: MasteryLabel = memory.mastery_estimate if memory.mastery_estimate != "strong" else "due"
        return ScheduleDecision(
            interval_days=interval,
            due_at=moment + timedelta(days=interval),
            due_reason=reason,
            mastery_estimate=mastery,
            difficulty_estimate=difficulty,
            consecutive_successes=successes,
            consecutive_failures=failures,
            needs_remediation=remediation,
        )

    if outcome == "incorrect":
        failures = failures + 1
        successes = 0
        difficulty = min(0.95, difficulty + 0.12)
        if band == "high":
            interval = MIN_INTERVAL_DAYS
            reason = "Reviewing sooner because confidence was high but the recall missed key ideas"
        elif failures >= REMEDIATION_THRESHOLD:
            interval = REPEATED_FAILURE_DAYS
            remediation = True
            reason = "Needs reinforcement after repeated difficulty"
        else:
            interval = _clamp(previous * INCORRECT_MULT)
            reason = "Due sooner after an incomplete recall"
        mastery = "needs_reinforcement"
    elif outcome == "partial":
        failures = 0
        successes = 0
        difficulty = min(0.9, difficulty + 0.06)
        interval = _clamp(previous * PARTIAL_MULT)
        reason = "Reviewing sooner because your last recall was partial"
        mastery = "needs_reinforcement"
        if failures + 1 >= REMEDIATION_THRESHOLD:  # noqa: keep remediation from prior failures
            remediation = memory.needs_remediation
    else:  # correct
        successes = successes + 1
        failures = 0
        remediation = False
        difficulty = max(0.15, difficulty - (0.08 if band == "high" else 0.04))
        if band == "high":
            mult = CORRECT_HIGH_CONF
            reason = "Strengthened — next review moved further out"
        elif band == "low":
            mult = CORRECT_LOW_CONF
            reason = "Correct, but reviewing again soon while confidence builds"
        else:
            mult = CORRECT_MED_CONF
            reason = "Successful recall — interval increased"
        if condition == "assisted":
            mult *= ASSISTED_PENALTY
            reason = "Successful with help — conservative next interval"
        # Gradual lengthening with streak
        streak_bonus = 1.0 + min(0.35, 0.05 * successes)
        interval = _clamp(previous * mult * streak_bonus)
        if successes >= 3 and band != "low" and condition == "independent":
            mastery = "strong"
        else:
            mastery = "developing"

    if outcome == "incorrect" and band == "high":
        interval = min(interval, _clamp(previous * FALSE_CONFIDENCE_MULT), MIN_INTERVAL_DAYS * 2)

    return ScheduleDecision(
        interval_days=interval,
        due_at=moment + timedelta(days=interval),
        due_reason=reason,
        mastery_estimate=mastery,
        difficulty_estimate=round(difficulty, 4),
        consecutive_successes=successes,
        consecutive_failures=failures,
        needs_remediation=remediation or (failures >= REMEDIATION_THRESHOLD and outcome == "incorrect"),
    )


def schedule_initial(*, now: datetime | None = None) -> ScheduleDecision:
    moment = _utc(now)
    return ScheduleDecision(
        interval_days=INITIAL_INTERVAL_DAYS,
        due_at=moment + timedelta(days=INITIAL_INTERVAL_DAYS),
        due_reason="Recently learned — first recall scheduled",
        mastery_estimate="recently_learned",
        difficulty_estimate=0.5,
        consecutive_successes=0,
        consecutive_failures=0,
        needs_remediation=False,
    )


@dataclass(frozen=True)
class PriorityInputs:
    overdue_hours: float = 0.0
    mastery: MasteryLabel = "recently_learned"
    consecutive_failures: int = 0
    last_outcome: str | None = None
    needs_remediation: bool = False
    days_since_learned: float = 0.0
    days_since_review: float = 0.0
    is_cumulative: bool = False
    confidence_mismatch: bool = False


def priority_score(inputs: PriorityInputs) -> float:
    """Higher score = earlier in today's review queue."""
    score = 0.0
    if inputs.overdue_hours > 0:
        score += WEIGHT_OVERDUE + min(20.0, inputs.overdue_hours / 24.0)
    if inputs.mastery == "needs_reinforcement" or inputs.needs_remediation:
        score += WEIGHT_WEAK
    if inputs.needs_remediation:
        score += WEIGHT_REMEDIATION
    if inputs.last_outcome == "incorrect" or inputs.consecutive_failures > 0:
        score += WEIGHT_RECENT_FAILURE + 5.0 * min(3, inputs.consecutive_failures)
    if inputs.last_outcome == "partial":
        score += WEIGHT_PARTIAL
    if inputs.mastery == "recently_learned" and inputs.days_since_learned <= 3:
        score += WEIGHT_NEW
    if inputs.is_cumulative and inputs.days_since_review >= 7:
        score += WEIGHT_CUMULATIVE
    if inputs.confidence_mismatch:
        score += WEIGHT_CONFIDENCE_MISMATCH
    return round(score, 4)


def estimate_minutes(item_count: int) -> int:
    return max(3, round(item_count * MINUTES_PER_ITEM))
