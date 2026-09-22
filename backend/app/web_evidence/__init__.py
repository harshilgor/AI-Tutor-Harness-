"""Bounded, policy-gated evidence retrieval for the learning harness."""

from .citations import CitationMapper, CitationValidation
from .clock import FakeClock, SystemClock
from .config import WebEvidenceConfig, load_web_evidence_config
from .lifecycle import EvidenceOutcome, ToolCallState
from .loop import ToolLoopOrchestrator, maybe_run_tool_loop
from .readiness import evaluate_readiness, check_schema
from .retention import EvidenceRetention
from .models import (
    EvidenceBundle,
    EvidencePacket,
    EvidenceSourceKind,
    OpenWebEvidenceArgs,
    PolicyDecision,
    PolicyDecisionKind,
    SearchIntent,
    SearchMaterialsArgs,
    SearchWebEvidenceArgs,
    SourceClassification,
    ToolExecutionResult,
    TrustLabel,
)
from .policy import SearchPolicyEngine
from .provider import FakeWebEvidenceProvider, WebEvidenceProvider
from .service import WebEvidenceService, build_web_evidence_service
from .tools import TOOL_CATALOG, execute_tool_call, tool_schemas_for_model

__all__ = [
    "CitationMapper",
    "CitationValidation",
    "EvidenceBundle",
    "EvidenceOutcome",
    "EvidencePacket",
    "EvidenceRetention",
    "EvidenceSourceKind",
    "FakeClock",
    "FakeWebEvidenceProvider",
    "OpenWebEvidenceArgs",
    "PolicyDecision",
    "PolicyDecisionKind",
    "SearchIntent",
    "SearchMaterialsArgs",
    "SearchPolicyEngine",
    "SearchWebEvidenceArgs",
    "SourceClassification",
    "SystemClock",
    "TOOL_CATALOG",
    "ToolCallState",
    "ToolExecutionResult",
    "ToolLoopOrchestrator",
    "TrustLabel",
    "WebEvidenceConfig",
    "WebEvidenceProvider",
    "WebEvidenceService",
    "build_web_evidence_service",
    "check_schema",
    "evaluate_readiness",
    "execute_tool_call",
    "load_web_evidence_config",
    "maybe_run_tool_loop",
    "tool_schemas_for_model",
]
