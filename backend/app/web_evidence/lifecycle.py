"""Tool-call lifecycle state machine. Model output never implies success."""

from __future__ import annotations

from enum import StrEnum


class ToolCallState(StrEnum):
    proposed = "proposed"
    schema_rejected = "schema_rejected"
    policy_denied = "policy_denied"
    rate_limited = "rate_limited"
    authorized = "authorized"
    running = "running"
    succeeded = "succeeded"
    no_reliable_evidence = "no_reliable_evidence"
    timed_out = "timed_out"
    provider_failed = "provider_failed"
    cancelled = "cancelled"
    response_completed = "response_completed"


class EvidenceOutcome(StrEnum):
    none = "none"
    no_reliable_evidence = "no_reliable_evidence"
    limited_evidence = "limited_evidence"
    conflicting_evidence = "conflicting_evidence"
    outdated_evidence = "outdated_evidence"
    sufficient_evidence = "sufficient_evidence"


_ALLOWED: dict[ToolCallState, set[ToolCallState]] = {
    ToolCallState.proposed: {
        ToolCallState.schema_rejected,
        ToolCallState.policy_denied,
        ToolCallState.rate_limited,
        ToolCallState.authorized,
        ToolCallState.cancelled,
    },
    ToolCallState.authorized: {
        ToolCallState.running,
        ToolCallState.cancelled,
        ToolCallState.provider_failed,
    },
    ToolCallState.running: {
        ToolCallState.succeeded,
        ToolCallState.no_reliable_evidence,
        ToolCallState.timed_out,
        ToolCallState.provider_failed,
        ToolCallState.policy_denied,
        ToolCallState.cancelled,
    },
    ToolCallState.succeeded: {ToolCallState.response_completed},
    ToolCallState.no_reliable_evidence: {ToolCallState.response_completed},
    ToolCallState.timed_out: {ToolCallState.response_completed},
    ToolCallState.provider_failed: {ToolCallState.response_completed},
    ToolCallState.schema_rejected: {ToolCallState.response_completed},
    ToolCallState.policy_denied: {ToolCallState.response_completed},
    ToolCallState.rate_limited: {ToolCallState.response_completed},
    ToolCallState.cancelled: {ToolCallState.response_completed},
    ToolCallState.response_completed: set(),
}


TERMINAL_FAILURE = {
    ToolCallState.schema_rejected,
    ToolCallState.policy_denied,
    ToolCallState.rate_limited,
    ToolCallState.timed_out,
    ToolCallState.provider_failed,
    ToolCallState.cancelled,
    ToolCallState.no_reliable_evidence,
}


def can_transition(current: ToolCallState, nxt: ToolCallState) -> bool:
    if current == nxt:
        return True
    return nxt in _ALLOWED.get(current, set())


def transition(current: ToolCallState, nxt: ToolCallState) -> ToolCallState:
    if not can_transition(current, nxt):
        raise ValueError(f"illegal tool-call transition {current.value} -> {nxt.value}")
    return nxt


def classify_evidence_outcome(excerpts: list[str], *, max_age_days_hint: int | None = None) -> EvidenceOutcome:
    if not excerpts:
        return EvidenceOutcome.no_reliable_evidence
    if len(excerpts) == 1:
        return EvidenceOutcome.limited_evidence
    # Lightweight conflict heuristic: opposing polarity tokens across excerpts.
    positive = sum(1 for e in excerpts if any(t in e.lower() for t in ("supports", "confirmed", "true")))
    negative = sum(1 for e in excerpts if any(t in e.lower() for t in ("refutes", "false", "debunked")))
    if positive and negative:
        return EvidenceOutcome.conflicting_evidence
    if max_age_days_hint is not None and max_age_days_hint > 365 * 5:
        return EvidenceOutcome.outdated_evidence
    if len(excerpts) < 2:
        return EvidenceOutcome.limited_evidence
    return EvidenceOutcome.sufficient_evidence
