"""Unit tests for review-scheduler-v1."""

from datetime import datetime, timezone

from backend.app.review.scheduler import (
    MemorySnapshot,
    PriorityInputs,
    estimate_minutes,
    priority_score,
    schedule_after_outcome,
    schedule_initial,
)


NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def test_new_concept_gets_short_initial_interval():
    decision = schedule_initial(now=NOW)
    assert decision.interval_days == 1.0
    assert decision.mastery_estimate == "recently_learned"
    assert (decision.due_at - NOW).days == 1


def test_correct_high_confidence_lengthens():
    memory = MemorySnapshot(last_interval_days=2.0, consecutive_successes=1)
    decision = schedule_after_outcome(
        outcome="correct", confidence="very", condition="independent", memory=memory, now=NOW,
    )
    assert decision.interval_days > 2.0
    assert decision.consecutive_successes == 2
    assert decision.needs_remediation is False


def test_correct_low_confidence_increases_conservatively():
    memory = MemorySnapshot(last_interval_days=3.0)
    high = schedule_after_outcome(outcome="correct", confidence="very", condition="independent", memory=memory, now=NOW)
    low = schedule_after_outcome(outcome="correct", confidence="guessing", condition="independent", memory=memory, now=NOW)
    assert low.interval_days < high.interval_days
    assert low.mastery_estimate == "developing"


def test_partial_shortens():
    memory = MemorySnapshot(last_interval_days=7.0)
    decision = schedule_after_outcome(
        outcome="partial", confidence="somewhat", condition="independent", memory=memory, now=NOW,
    )
    assert decision.interval_days < 7.0
    assert decision.mastery_estimate == "needs_reinforcement"


def test_incorrect_brings_back_soon():
    memory = MemorySnapshot(last_interval_days=7.0)
    decision = schedule_after_outcome(
        outcome="incorrect", confidence="somewhat", condition="independent", memory=memory, now=NOW,
    )
    assert decision.interval_days <= 2.0
    assert decision.consecutive_failures == 1


def test_repeated_failure_triggers_remediation():
    memory = MemorySnapshot(last_interval_days=2.0, consecutive_failures=1)
    decision = schedule_after_outcome(
        outcome="incorrect", confidence="somewhat", condition="independent", memory=memory, now=NOW,
    )
    assert decision.needs_remediation is True
    assert decision.consecutive_failures == 2


def test_high_confidence_incorrect_is_urgent():
    memory = MemorySnapshot(last_interval_days=10.0)
    decision = schedule_after_outcome(
        outcome="incorrect", confidence="very", condition="independent", memory=memory, now=NOW,
    )
    assert decision.interval_days <= 2.0
    assert "confidence" in decision.due_reason.lower() or "sooner" in decision.due_reason.lower()


def test_skip_does_not_count_as_outcome():
    memory = MemorySnapshot(consecutive_successes=3, consecutive_failures=0, last_interval_days=5.0)
    decision = schedule_after_outcome(
        outcome="skip", confidence=None, condition="independent", memory=memory, now=NOW,
    )
    assert decision.consecutive_successes == 3
    assert decision.consecutive_failures == 0


def test_assisted_correct_is_more_conservative():
    memory = MemorySnapshot(last_interval_days=2.0)
    independent = schedule_after_outcome(outcome="correct", confidence="confident", condition="independent", memory=memory, now=NOW)
    assisted = schedule_after_outcome(outcome="correct", confidence="confident", condition="assisted", memory=memory, now=NOW)
    assert assisted.interval_days <= independent.interval_days


def test_priority_overdue_and_weak_rank_high():
    overdue = priority_score(PriorityInputs(overdue_hours=48, mastery="needs_reinforcement", consecutive_failures=2))
    strong = priority_score(PriorityInputs(overdue_hours=0, mastery="strong", days_since_review=2))
    assert overdue > strong


def test_estimate_minutes_scales():
    assert estimate_minutes(5) >= 5
    assert estimate_minutes(8) > estimate_minutes(4)
