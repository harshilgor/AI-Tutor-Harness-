"""Model-facing tool schemas and validated execution entrypoint."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .audit import attach_audit, emit_audit_event
from .models import (
    AuthScope,
    FORBIDDEN_MODEL_FIELDS,
    GetSourceBlocksArgs,
    OpenWebEvidenceArgs,
    PolicyDecision,
    PolicyDecisionKind,
    PolicyReason,
    SearchMaterialsArgs,
    SearchWebEvidenceArgs,
    ToolExecutionResult,
)
from .lifecycle import ToolCallState
from .service import WebEvidenceService

TOOL_CATALOG = (
    "search_materials",
    "get_source_blocks",
    "search_web_evidence",
    "open_web_evidence",
)


def tool_schemas_for_model() -> list[dict[str, Any]]:
    return [
        {
            "name": "search_materials",
            "description": "Search only materials the learner is permitted to access in this session.",
            "parameters": SearchMaterialsArgs.model_json_schema(),
        },
        {
            "name": "get_source_blocks",
            "description": "Return selected excerpts by per-response aliases such as M1 from this response bundle.",
            "parameters": GetSourceBlocksArgs.model_json_schema(),
        },
        {
            "name": "search_web_evidence",
            "description": (
                "Search bounded public web evidence for a learning-relevant intent. "
                "Cite returned aliases only (W1, W2). Do not invent URLs."
            ),
            "parameters": SearchWebEvidenceArgs.model_json_schema(),
        },
        {
            "name": "open_web_evidence",
            "description": (
                "Open a constrained excerpt from a web evidence alias returned earlier "
                "in this response bundle. Pass alias like W1, never a URL."
            ),
            "parameters": OpenWebEvidenceArgs.model_json_schema(),
        },
    ]


def execute_tool_call(
    service: WebEvidenceService,
    *,
    tool_name: str,
    arguments: dict[str, Any],
    auth: AuthScope,
    response_bundle_id: str,
    idempotency_key: str,
    policy_kwargs: dict[str, Any] | None = None,
    cancelled: bool = False,
) -> ToolExecutionResult:
    policy_kwargs = dict(policy_kwargs or {})
    if tool_name not in TOOL_CATALOG:
        return _schema_rejected(auth, tool_name, "unknown_tool")

    if not isinstance(arguments, dict):
        return _schema_rejected(auth, tool_name, "arguments_not_object")

    # Hard size limit on argument payload.
    encoded = json.dumps(arguments, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > service.config.max_request_bytes:
        return _schema_rejected(auth, tool_name, "request_too_large")

    leaked = FORBIDDEN_MODEL_FIELDS.intersection(arguments)
    if leaked:
        event_id = emit_audit_event(
            "tool_call_schema_rejected",
            correlation_id=auth.correlation_id,
            request_id=auth.request_id,
            learner_id=auth.learner_id,
            session_id=auth.session_id,
            tool_name=tool_name,
            error_category="forbidden_fields",
            extra={"fields": sorted(leaked)},
            policy_version=service.config.policy_version,
            feature_version=service.config.feature_version,
        )
        return attach_audit(
            ToolExecutionResult(
                ok=False,
                tool_name=tool_name,
                state=ToolCallState.schema_rejected,
                error_code="forbidden_fields",
                learner_message="I can only search within the active learning session.",
                retrieval_occurred=False,
                decision=PolicyDecision(
                    decision=PolicyDecisionKind.deny,
                    reason_code=PolicyReason.schema_rejected,
                ),
            ),
            event_id,
        )

    # Strip unknown top-level privilege attempts already caught; pydantic forbid handles the rest.
    try:
        if tool_name == "search_materials":
            args = SearchMaterialsArgs.model_validate(arguments)
            policy_kwargs.setdefault("query", args.query)
            policy_kwargs.setdefault("requested_result_count", args.requested_result_count)
            return service.search_materials(
                auth, args,
                response_bundle_id=response_bundle_id,
                idempotency_key=idempotency_key,
                cancelled=cancelled,
                **policy_kwargs,
            )
        if tool_name == "get_source_blocks":
            args = GetSourceBlocksArgs.model_validate(arguments)
            return service.get_source_blocks(
                auth, args,
                response_bundle_id=response_bundle_id,
                idempotency_key=idempotency_key,
                cancelled=cancelled,
                **policy_kwargs,
            )
        if tool_name == "search_web_evidence":
            args = SearchWebEvidenceArgs.model_validate(arguments)
            policy_kwargs.setdefault("intent", args.intent)
            policy_kwargs.setdefault("query", args.query)
            policy_kwargs.setdefault("requested_result_count", args.requested_result_count)
            policy_kwargs.setdefault("requested_domains", args.allowed_domains)
            return service.search_web_evidence(
                auth, args,
                response_bundle_id=response_bundle_id,
                idempotency_key=idempotency_key,
                cancelled=cancelled,
                **policy_kwargs,
            )
        if tool_name == "open_web_evidence":
            args = OpenWebEvidenceArgs.model_validate(arguments)
            return service.open_web_evidence(
                auth, args,
                response_bundle_id=response_bundle_id,
                idempotency_key=idempotency_key,
                cancelled=cancelled,
                **policy_kwargs,
            )
    except ValidationError:
        return _schema_rejected(auth, tool_name, "validation_error")

    return _schema_rejected(auth, tool_name, "unknown_tool")


def _schema_rejected(auth: AuthScope, tool_name: str, category: str) -> ToolExecutionResult:
    event_id = emit_audit_event(
        "tool_call_schema_rejected",
        correlation_id=auth.correlation_id,
        request_id=auth.request_id,
        learner_id=auth.learner_id,
        session_id=auth.session_id,
        tool_name=tool_name,
        error_category=category,
    )
    return attach_audit(
        ToolExecutionResult(
            ok=False,
            tool_name=tool_name,
            state=ToolCallState.schema_rejected,
            error_code=PolicyReason.schema_rejected.value,
            learner_message="That request was not valid for the available tools.",
            retrieval_occurred=False,
            decision=PolicyDecision(
                decision=PolicyDecisionKind.deny,
                reason_code=PolicyReason.schema_rejected,
            ),
        ),
        event_id,
    )
