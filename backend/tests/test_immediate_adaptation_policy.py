from datetime import datetime, timezone

from backend.app.adaptive_observability import (
    ImmediateAdaptationInput,
    PolicyEvidenceObservation,
)
from backend.app.immediate_adaptation_policy import (
    decide_immediate_action,
    policy_input_digest,
)

NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)


def _observation(
    id: str,
    outcome: str,
    *,
    assisted: bool = False,
    family: str | None = None,
    misconception: str | None = None,
) -> PolicyEvidenceObservation:
    return PolicyEvidenceObservation(
        id=id,
        kind="assessment",
        outcome=outcome,
        condition="assisted" if assisted else "independent",
        reliability=0.4,
        occurred_at=NOW,
        item_id=f"item-{id}",
        item_family=family,
        misconception_code=misconception,
        assistance_exposed=assisted,
    )


def _input(
    evidence: list[PolicyEvidenceObservation] | None = None,
    *,
    lesson_exposed: bool = False,
    active_misconceptions: list[str] | None = None,
) -> ImmediateAdaptationInput:
    return ImmediateAdaptationInput(
        learner_id="local",
        session_id="session-1",
        session_revision=1,
        graph_id="graph-1",
        graph_version=1,
        concept_id="concept-1",
        lesson_exposed=lesson_exposed,
        latest_lesson_completed_at=NOW if lesson_exposed else None,
        evidence=evidence or [],
        active_misconception_codes=active_misconceptions or [],
    )


def test_new_concept_is_taught_before_it_is_checked():
    decision = decide_immediate_action(_input())
    assert (decision.action, decision.reason_code) == ("teach", "new_concept")


def test_taught_concept_without_evidence_gets_a_check():
    decision = decide_immediate_action(_input(lesson_exposed=True))
    assert (decision.action, decision.reason_code) == ("check", "taught_without_check")


def test_single_independent_miss_gets_a_distinct_check_not_repair():
    decision = decide_immediate_action(_input([
        _observation("miss-1", "incorrect", family="family-a"),
    ]))
    assert (decision.action, decision.reason_code) == ("check", "first_independent_miss")


def test_repeated_distinct_misses_trigger_repair():
    decision = decide_immediate_action(_input([
        _observation("miss-2", "incorrect", family="family-b"),
        _observation("miss-1", "incorrect", family="family-a"),
    ]))
    assert (decision.action, decision.reason_code) == ("repair", "repeated_distinct_miss")


def test_assisted_success_requires_a_fresh_check():
    decision = decide_immediate_action(_input([
        _observation("assisted", "correct", assisted=True, family="family-a"),
    ]))
    assert (decision.action, decision.reason_code) == ("check", "assisted_success_needs_fresh_check")


def test_fresh_independent_success_continues_without_mastery_claim():
    decision = decide_immediate_action(_input([
        _observation("success", "correct", family="family-c"),
        _observation("miss", "incorrect", family="family-a"),
    ]))
    assert (decision.action, decision.reason_code) == ("teach", "fresh_independent_success")
    assert "master" not in decision.rationale.lower()


def test_policy_is_deterministic_and_digest_changes_with_evidence():
    empty = _input(lesson_exposed=True)
    with_evidence = _input([_observation("success", "correct", family="family-a")], lesson_exposed=True)
    assert decide_immediate_action(empty) == decide_immediate_action(empty)
    assert policy_input_digest(empty) != policy_input_digest(with_evidence)
