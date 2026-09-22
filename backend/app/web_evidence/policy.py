"""Least-privilege policy for materials and web evidence tools."""

from __future__ import annotations

import re

from .config import WebEvidenceConfig
from .models import (
    PolicyContext,
    PolicyDecision,
    PolicyDecisionKind,
    PolicyReason,
    SearchIntent,
    SourceClassification,
)

_UNSAFE_QUERY = re.compile(
    r"(?i)\b(ignore (previous|all) instructions|system prompt|api[_ ]?key|"
    r"password|credit card|ssn|social security)\b"
)

_INTENT_PREFERENCES: dict[SearchIntent, list[SourceClassification]] = {
    SearchIntent.definition: [
        SourceClassification.reference,
        SourceClassification.educational,
        SourceClassification.official_documentation,
    ],
    SearchIntent.current_fact: [
        SourceClassification.primary,
        SourceClassification.news,
        SourceClassification.official_documentation,
    ],
    SearchIntent.primary_source: [
        SourceClassification.primary,
        SourceClassification.official_documentation,
        SourceClassification.academic,
    ],
    SearchIntent.academic_reference: [
        SourceClassification.academic,
        SourceClassification.reference,
    ],
    SearchIntent.technical_documentation: [
        SourceClassification.official_documentation,
        SourceClassification.reference,
    ],
    SearchIntent.worked_example: [
        SourceClassification.educational,
        SourceClassification.reference,
    ],
    SearchIntent.contextual_background: [
        SourceClassification.educational,
        SourceClassification.reference,
        SourceClassification.news,
    ],
}

_DENY_MESSAGES = {
    PolicyReason.web_search_disabled: (
        "External-source retrieval is currently unavailable. "
        "I can still explain from your course materials."
    ),
    PolicyReason.provider_unavailable: (
        "I couldn't retrieve external sources right now. "
        "I can still explain from your course materials."
    ),
    PolicyReason.assessment_mode_restricted: (
        "External web sources are disabled in this assessment mode. "
        "I can help you reason through the relevant concepts."
    ),
    PolicyReason.budget_exceeded: (
        "We've reached the external-source limit for this session. "
        "Let's work from your provided materials."
    ),
    PolicyReason.source_policy_denied: (
        "External sources are not allowed for this course or session. "
        "I can work from authorized materials instead."
    ),
    PolicyReason.no_learning_relevance: (
        "I can search only when it supports the active learning goal. "
        "Share a bit more about what you need to learn."
    ),
    PolicyReason.no_authenticated_context: (
        "A verified learning session is required before retrieving sources."
    ),
    PolicyReason.open_not_permitted: (
        "That source cannot be opened in the current mode."
    ),
    PolicyReason.open_budget_exceeded: (
        "We've reached the limit for opening external sources in this session."
    ),
    PolicyReason.evidence_expired: (
        "That source reference expired. Ask me to search again if you still need it."
    ),
    PolicyReason.evidence_scope_mismatch: (
        "That source is not available in this session."
    ),
    PolicyReason.kill_switch: (
        "External-source retrieval is disabled for this workspace."
    ),
    PolicyReason.circuit_open: (
        "I couldn't retrieve external sources right now. "
        "I can still explain from your course materials."
    ),
}



class SearchPolicyEngine:
    def __init__(self, config: WebEvidenceConfig):
        self.config = config

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        if context.tool_name in {"search_materials", "get_source_blocks"}:
            return self._allow_materials(context)

        if context.tool_name == "open_web_evidence":
            return self._evaluate_open(context)

        if context.tool_name != "search_web_evidence":
            return self._deny(PolicyReason.unsupported_intent)

        return self._evaluate_search(context)

    def _allow_materials(self, context: PolicyContext) -> PolicyDecision:
        if not context.auth.learner_id or not context.auth.session_id:
            return self._deny(PolicyReason.no_authenticated_context)
        return PolicyDecision(
            decision=PolicyDecisionKind.allow,
            reason_code=PolicyReason.allowed,
            max_results=min(context.requested_result_count, 6),
            max_chars_per_source=4000,
            max_total_evidence_chars=16000,
            citation_required=True,
            open_allowed=False,
            remaining_budget={},
            preferred_classifications=[],
        )

    def _evaluate_search(self, context: PolicyContext) -> PolicyDecision:
        if not context.auth.learner_id or not context.auth.session_id:
            return self._deny(PolicyReason.no_authenticated_context)
        if not context.feature_web_evidence_enabled:
            return self._deny(PolicyReason.web_search_disabled)
        if not context.provider_available:
            return self._deny(PolicyReason.provider_unavailable)
        if context.auth.assessment_mode:
            return self._deny(PolicyReason.assessment_mode_restricted)
        if context.source_policy in {"attached_only", "available_graph_sources_only"}:
            return self._deny(PolicyReason.source_policy_denied)
        if context.intent is None:
            return self._deny(PolicyReason.unsupported_intent)
        if _UNSAFE_QUERY.search(context.query):
            return self._deny(PolicyReason.unsafe_query_pattern)
        if not self._learning_relevant(context):
            return self._deny(PolicyReason.no_learning_relevance)

        remaining = {
            "searches_turn": max(0, self.config.max_searches_per_turn - context.searches_this_turn),
            "searches_session": max(0, self.config.max_searches_per_session - context.searches_this_session),
            "searches_day": max(0, self.config.max_searches_per_user_day - context.searches_today),
            "opens_session": max(0, self.config.max_opens_per_session - context.opens_this_session),
        }
        if (
            remaining["searches_turn"] <= 0
            or remaining["searches_session"] <= 0
            or remaining["searches_day"] <= 0
        ):
            return self._deny(PolicyReason.budget_exceeded, remaining=remaining)

        allowlist = list(self.config.default_allowlist)
        denylist = list(self.config.default_denylist)
        if self.config.allow_model_domain_hints and context.requested_domains:
            # Model hints can only narrow further when an allowlist already exists,
            # or become the allowlist when none is configured.
            if allowlist:
                allowlist = [d for d in allowlist if d in set(context.requested_domains)]
                if not allowlist:
                    return self._deny(PolicyReason.domain_not_allowed, remaining=remaining)
            else:
                allowlist = list(context.requested_domains)

        max_results = min(
            context.requested_result_count,
            self.config.max_results,
            5 if not context.high_stakes_domain else 3,
        )
        return PolicyDecision(
            decision=PolicyDecisionKind.allow_with_constraints,
            reason_code=PolicyReason.allowed,
            max_results=max_results,
            max_chars_per_source=self.config.max_chars_per_source,
            max_total_evidence_chars=self.config.max_total_evidence_chars,
            domain_allowlist=allowlist,
            domain_denylist=denylist,
            citation_required=True,
            open_allowed=remaining["opens_session"] > 0,
            remaining_budget=remaining,
            preferred_classifications=_INTENT_PREFERENCES.get(context.intent, []),
        )

    def _evaluate_open(self, context: PolicyContext) -> PolicyDecision:
        if not context.auth.learner_id or not context.auth.session_id:
            return self._deny(PolicyReason.no_authenticated_context)
        if not context.feature_web_evidence_enabled or not context.provider_available:
            return self._deny(PolicyReason.web_search_disabled)
        if context.auth.assessment_mode:
            return self._deny(PolicyReason.assessment_mode_restricted)
        remaining = {
            "opens_session": max(0, self.config.max_opens_per_session - context.opens_this_session),
        }
        if remaining["opens_session"] <= 0:
            return self._deny(PolicyReason.open_budget_exceeded, remaining=remaining)
        return PolicyDecision(
            decision=PolicyDecisionKind.allow_with_constraints,
            reason_code=PolicyReason.allowed,
            max_results=1,
            max_chars_per_source=self.config.max_chars_per_source,
            max_total_evidence_chars=self.config.max_chars_per_source,
            citation_required=True,
            open_allowed=True,
            remaining_budget=remaining,
        )

    def _learning_relevant(self, context: PolicyContext) -> bool:
        if context.learner_requested_external:
            return True
        if context.materials_insufficient:
            return True
        if context.intent in {
            SearchIntent.current_fact,
            SearchIntent.primary_source,
            SearchIntent.academic_reference,
            SearchIntent.technical_documentation,
        }:
            return True
        if context.learning_objective.strip() or context.learner_request.strip():
            return True
        return False

    def _deny(
        self,
        reason: PolicyReason,
        *,
        remaining: dict[str, int] | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            decision=PolicyDecisionKind.deny,
            reason_code=reason,
            max_results=0,
            citation_required=True,
            open_allowed=False,
            remaining_budget=remaining or {},
            learner_message=_DENY_MESSAGES.get(reason),
        )
