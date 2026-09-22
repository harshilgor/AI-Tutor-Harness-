"""Materials search/read tools wrapping existing context_service.retrieve."""

from __future__ import annotations

from datetime import timedelta

from ..context_service import retrieve
from ..material_service import MaterialService, problem
from .clock import Clock, SystemClock
from .models import (
    AuthScope,
    EvidencePacket,
    EvidenceSourceKind,
    GetSourceBlocksArgs,
    PolicyDecision,
    SearchMaterialsArgs,
    StoredWebEvidence,
    ToolExecutionResult,
    TrustLabel,
    SourceClassification,
)
from .redact import truncate
from .store import AuthorizationError, WebEvidenceStore


def search_materials(
    store,
    auth: AuthScope,
    args: SearchMaterialsArgs,
    decision: PolicyDecision,
    *,
    evidence_store: WebEvidenceStore,
    response_bundle_id: str,
    tool_call_id: str,
    source_policy_fingerprint: str,
    clock: Clock | None = None,
    ttl_seconds: int = 1800,
) -> ToolExecutionResult:
    clock = clock or SystemClock()
    MaterialService(store).session(auth.learner_id, auth.session_id)
    sources = retrieve(
        store,
        auth.learner_id,
        auth.session_id,
        args.query,
        byte_budget=decision.max_total_evidence_chars,
    )
    sources = sources[: decision.max_results]
    packets: list[EvidencePacket] = []
    used = 0
    expires = clock.now() + timedelta(seconds=ttl_seconds)
    existing = evidence_store.list_bundle_packets(
        auth=auth,
        response_bundle_id=response_bundle_id,
        source_policy_fingerprint=source_policy_fingerprint,
    )
    material_index = sum(1 for p in existing if p.source_kind == EvidenceSourceKind.material)
    for source in sources:
        text = truncate(source["text"], decision.max_chars_per_source)
        if used + len(text) > decision.max_total_evidence_chars:
            break
        used += len(text)
        material_index += 1
        alias = f"M{material_index}"
        evidence_id = evidence_store.new_evidence_id()
        stored = StoredWebEvidence(
            evidence_id=evidence_id,
            response_bundle_id=response_bundle_id,
            tool_call_id=tool_call_id,
            retrieval_session_id=response_bundle_id,
            owner_id=auth.learner_id,
            tenant_id=auth.tenant_id,
            course_id=auth.course_id,
            session_id=auth.session_id,
            source_policy_fingerprint=source_policy_fingerprint,
            source_kind=EvidenceSourceKind.material,
            provider="materials",
            provider_result_ref=None,
            title=source["title"],
            canonical_url=None,
            domain=None,
            excerpt=text,
            source_classification=SourceClassification.educational,
            citation_label=alias,
            trust_label=TrustLabel.authorized_material,
            created_at=clock.now(),
            expires_at=expires,
            span_id=source["spanId"],
            version_id=source["versionId"],
            page_index=source.get("pageIndex"),
        )
        evidence_store.save_receipt(stored, alias=alias)
        packets.append(
            EvidencePacket(
                evidence_id=evidence_id,
                alias=alias,
                retrieval_session_id=response_bundle_id,
                response_bundle_id=response_bundle_id,
                tool_call_id=tool_call_id,
                source_kind=EvidenceSourceKind.material,
                provider="materials",
                title=source["title"],
                excerpt=text,
                citation_label=alias,
                trust_label=TrustLabel.authorized_material,
                source_classification=SourceClassification.educational,
                span_id=source["spanId"],
                version_id=source["versionId"],
                page_index=source.get("pageIndex"),
                source_policy_fingerprint=source_policy_fingerprint,
            )
        )
    return ToolExecutionResult(
        ok=True,
        tool_name="search_materials",
        decision=decision,
        evidence=packets,
        retrieval_session_id=response_bundle_id,
        learner_message=None if packets else "No matching passages were found in your attached materials.",
    )


def get_source_blocks(
    store,
    auth: AuthScope,
    args: GetSourceBlocksArgs,
    decision: PolicyDecision,
    *,
    evidence_store: WebEvidenceStore,
    response_bundle_id: str,
    tool_call_id: str,
    source_policy_fingerprint: str,
    clock: Clock | None = None,
) -> ToolExecutionResult:
    clock = clock or SystemClock()
    MaterialService(store).session(auth.learner_id, auth.session_id)
    span_ids = []
    for alias in args.aliases[: decision.max_results]:
        normalized = alias[0].upper() + alias[1:]
        try:
            stored = evidence_store.authorize_receipt(
                auth=auth,
                alias=normalized,
                response_bundle_id=response_bundle_id,
                source_policy_fingerprint=source_policy_fingerprint,
                now=clock.now(),
            )
        except AuthorizationError:
            continue
        if stored.span_id:
            span_ids.append(stored.span_id)
    if not span_ids:
        problem("source_not_found", "Those passages are not available in this session.", 404)
    sources = retrieve(
        store,
        auth.learner_id,
        auth.session_id,
        args.focus or "selected",
        byte_budget=decision.max_total_evidence_chars,
        selected_span_ids=span_ids,
    )
    packets = []
    for index, source in enumerate(sources, start=1):
        text = truncate(source["text"], decision.max_chars_per_source)
        alias = f"M{index}"
        # Reuse authorized span as the visible alias target for this refresh.
        packets.append(
            EvidencePacket(
                evidence_id=source["spanId"],
                alias=alias,
                retrieval_session_id=response_bundle_id,
                response_bundle_id=response_bundle_id,
                tool_call_id=tool_call_id,
                source_kind=EvidenceSourceKind.material,
                provider="materials",
                title=source["title"],
                excerpt=text,
                citation_label=alias,
                trust_label=TrustLabel.authorized_material,
                source_classification=SourceClassification.educational,
                span_id=source["spanId"],
                version_id=source["versionId"],
                page_index=source.get("pageIndex"),
                source_policy_fingerprint=source_policy_fingerprint,
            )
        )
    return ToolExecutionResult(
        ok=True,
        tool_name="get_source_blocks",
        decision=decision,
        evidence=packets,
        retrieval_session_id=response_bundle_id,
    )
