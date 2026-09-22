"""Structured audit events for web/materials evidence tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..material_service import uid
from .models import PolicyDecision, ToolExecutionResult
from .redact import redact_mapping, redact_text

logger = logging.getLogger("ai_tutor.web_evidence")

EVENT_TYPES = frozenset({
    "tool_call_proposed",
    "tool_call_schema_rejected",
    "tool_call_policy_denied",
    "tool_call_rate_limited",
    "web_search_started",
    "web_search_succeeded",
    "web_search_failed",
    "web_result_opened",
    "web_result_open_denied",
    "citation_rendered",
    "response_citation_validation_failed",
    "provider_fallback_used",
})


def emit_audit_event(
    event_type: str,
    *,
    correlation_id: str | None = None,
    request_id: str | None = None,
    conversation_id: str | None = None,
    trace_id: str | None = None,
    tool_call_id: str | None = None,
    learner_id: str | None = None,
    session_id: str | None = None,
    tenant_id: str | None = None,
    course_id: str | None = None,
    tool_name: str | None = None,
    decision: PolicyDecision | None = None,
    provider: str | None = None,
    latency_ms: float | None = None,
    result_count: int | None = None,
    error_category: str | None = None,
    policy_version: str | None = None,
    feature_version: str | None = None,
    evidence_outcome: str | None = None,
    citation_validation_ok: bool | None = None,
    extra: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> str:
    event_id = uid("webaudit")
    if event_type not in EVENT_TYPES:
        event_type = "web_search_failed"
    payload: dict[str, Any] = {
        "eventId": event_id,
        "eventType": event_type,
        "correlationId": correlation_id,
        "requestId": request_id,
        "conversationId": conversation_id,
        "traceId": trace_id,
        "toolCallId": tool_call_id,
        "learnerIdHash": _privacy_safe_id(learner_id),
        "sessionId": session_id,
        "tenantId": tenant_id,
        "courseId": course_id,
        "toolName": tool_name,
        "provider": provider,
        "latencyMs": latency_ms,
        "resultCount": result_count,
        "errorCategory": error_category,
        "policyVersion": policy_version,
        "featureVersion": feature_version,
        "evidenceOutcome": evidence_outcome,
        "citationValidationOk": citation_validation_ok,
    }
    if decision is not None:
        payload["policy"] = {
            "decision": decision.decision.value,
            "reasonCode": decision.reason_code.value,
            "maxResults": decision.max_results,
            "openAllowed": decision.open_allowed,
            "remainingBudget": decision.remaining_budget,
            "sourcePolicyFingerprint": decision.source_policy_fingerprint,
            "policyVersion": decision.policy_version,
            "featureVersion": decision.feature_version,
        }
    if extra:
        payload["extra"] = redact_mapping(extra, api_key=api_key)
    line = redact_text(json.dumps(payload, default=str, separators=(",", ":")), api_key=api_key)
    logger.info("web_evidence_audit %s", line)
    return event_id


def _privacy_safe_id(value: str | None) -> str | None:
    if not value:
        return None
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def attach_audit(result: ToolExecutionResult, event_id: str) -> ToolExecutionResult:
    return result.model_copy(update={"audit_event_id": event_id})
