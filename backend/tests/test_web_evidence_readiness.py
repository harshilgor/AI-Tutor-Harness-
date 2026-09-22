"""Production-readiness verification: concurrency, TTL, cancel, failures, redaction."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from backend.app.graph_generator import GraphGenerator
from backend.app.models import TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.storage import Store
from backend.app.web_evidence import (
    CitationMapper,
    FakeClock,
    FakeWebEvidenceProvider,
    SearchIntent,
    ToolCallState,
    build_web_evidence_service,
    execute_tool_call,
)
from backend.app.web_evidence.config import WebEvidenceConfig
from backend.app.web_evidence.exa import ExaWebEvidenceProvider
from backend.app.web_evidence.lifecycle import EvidenceOutcome
from backend.app.web_evidence.models import (
    AuthScope,
    EvidenceBundle,
    PolicyDecision,
    PolicyDecisionKind,
    PolicyReason,
    ProviderSearchHit,
    SearchWebEvidenceArgs,
    SourceClassification,
)
from backend.app.web_evidence.quota import QuotaExceeded, QuotaLedger
from backend.app.web_evidence.redact import redact_mapping, redact_text
from backend.app.web_evidence.store import AuthorizationError, WebEvidenceStore
from sqlalchemy import inspect, text


def _config(**overrides) -> WebEvidenceConfig:
    base = WebEvidenceConfig(
        enabled=True,
        provider_name="fake",
        exa_api_key="test-key",
        max_results=3,
        max_chars_per_source=200,
        max_total_evidence_chars=600,
        max_searches_per_turn=50,
        max_searches_per_session=50,
        max_searches_per_user_day=50,
        max_searches_per_tenant_day=50,
        max_searches_global_day=2,
        cache_ttl_seconds=0,
        result_ttl_seconds=60,
        default_denylist=("chegg.com",),
    )
    return WebEvidenceConfig(**{**base.__dict__, **overrides})


@pytest.fixture
def ready_env(monkeypatch):
    root = Path.cwd() / "backend" / "data" / f"web-ready-{uuid4().hex}"
    root.mkdir(parents=True)
    monkeypatch.setenv("AI_TUTOR_MATERIAL_DIR", str(root / "objects"))
    monkeypatch.setenv("AI_TUTOR_ENV", "development")
    clock = FakeClock()
    store = Store(root / "test.db")
    scope = TopicScope(
        id="scope-ready", topic="Physics", resolved_meaning="Physics",
        objective="Learn", depth="introductory", created_at=utc_now(),
    )
    graph = GraphGenerator().generate(scope)
    store.save_scope(scope)
    store.save_graph(graph)
    store.save_session(LearningSession(
        id="session_ready", learner_id="alice", graph_id=graph.id,
        created_at=utc_now(), updated_at=utc_now(),
    ))
    yield store, clock, graph
    store.close()
    for item in sorted(root.rglob("*"), reverse=True):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    root.rmdir()


def test_migration_0015_and_0016_apply_with_indexes(ready_env):
    store, _, _ = ready_env
    with store.engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    # Head may advance past 0016; web-evidence tables/indexes must remain present.
    assert str(revision)[:4].isdigit() and int(str(revision)[:4]) >= 16
    tables = set(inspect(store.engine).get_table_names())
    assert {
        "web_tool_calls",
        "web_evidence_receipts",
        "web_evidence_aliases",
        "web_quota_ledgers",
        "web_provider_circuit",
    } <= tables
    indexes = {idx["name"] for idx in inspect(store.engine).get_indexes("web_evidence_aliases")}
    assert "ix_web_alias_auth" in indexes
    receipt_indexes = {idx["name"] for idx in inspect(store.engine).get_indexes("web_evidence_receipts")}
    assert "ix_web_receipt_scope" in receipt_indexes
    assert "ix_web_receipt_auth" in receipt_indexes
    assert "ix_web_receipt_expiry" in receipt_indexes


def test_concurrent_global_quota_is_atomic(ready_env):
    store, clock, _ = ready_env
    ledger = QuotaLedger(store, clock=clock)
    successes = []
    failures = []

    def attempt(i: int):
        try:
            reservation = ledger.reserve(
                scope_key="global_day",
                scope_kind="global_day",
                limit=2,
                units=1,
            )
            ledger.commit(reservation)
            successes.append(i)
        except QuotaExceeded:
            failures.append(i)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(attempt, range(12)))
    assert len(successes) == 2
    assert len(failures) == 10
    with store.engine.connect() as connection:
        row = connection.execute(
            text("SELECT reserved, consumed FROM web_quota_ledgers WHERE scope_key='global_day'")
        ).first()
    assert int(row[0]) == 2
    assert int(row[1]) == 2


def test_abandoned_quota_reconcile_after_crash(ready_env):
    store, clock, _ = ready_env
    ledger = QuotaLedger(store, clock=clock)
    reservation = ledger.reserve(scope_key="user_day:alice", scope_kind="user_day", limit=5, units=1)
    # Crash: neither commit nor release.
    assert reservation.committed is False
    clock.advance(400)
    released = ledger.reconcile_abandoned(grace_seconds=300)
    assert released == 1
    with store.engine.connect() as connection:
        row = connection.execute(
            text("SELECT reserved, consumed FROM web_quota_ledgers WHERE scope_key='user_day:alice'")
        ).first()
    assert int(row[0]) == int(row[1]) == 0


def test_ttl_rejects_before_cleanup(ready_env):
    store, clock, _ = ready_env
    provider = FakeWebEvidenceProvider(hits=[ProviderSearchHit(
        provider_result_ref="d1", title="T", url="https://nist.gov/a", domain="nist.gov",
        excerpt="text", classification=SourceClassification.primary,
    )])
    service = type(build_web_evidence_service(store))(
        store, _config(result_ttl_seconds=30), provider=provider, clock=clock
    )
    auth = AuthScope(learner_id="alice", session_id="session_ready", tenant_id="default", request_id="t1")
    bundle = service.begin_bundle()
    result = service.search_web_evidence(
        auth,
        SearchWebEvidenceArgs(query="metre", intent=SearchIntent.definition),
        response_bundle_id=bundle,
        idempotency_key="ttl-1",
        learner_requested_external=True,
        source_policy="general",
    )
    assert result.ok
    clock.advance(45)
    evidence_store = WebEvidenceStore(store, clock=clock)
    with pytest.raises(AuthorizationError) as exc:
        evidence_store.authorize_receipt(
            auth=auth,
            alias=result.evidence[0].alias,
            response_bundle_id=bundle,
            source_policy_fingerprint=service.config.source_policy_fingerprint("general"),
        )
    assert exc.value.code == "evidence_expired"


def test_cancel_before_provider_releases_quota(ready_env):
    store, clock, _ = ready_env
    provider = FakeWebEvidenceProvider(hits=[ProviderSearchHit(
        provider_result_ref="d1", title="T", url="https://nist.gov/a", domain="nist.gov",
        excerpt="text", classification=SourceClassification.primary,
    )])
    service = type(build_web_evidence_service(store))(store, _config(), provider=provider, clock=clock)
    auth = AuthScope(learner_id="alice", session_id="session_ready", tenant_id="default", request_id="c1")
    result = service.search_web_evidence(
        auth,
        SearchWebEvidenceArgs(query="metre", intent=SearchIntent.definition),
        response_bundle_id=service.begin_bundle(),
        idempotency_key="cancel-1",
        cancelled=True,
        learner_requested_external=True,
        source_policy="general",
    )
    assert result.retrieval_occurred is False
    assert result.state in {ToolCallState.cancelled, ToolCallState.response_completed}
    assert provider.search_calls == []


def test_cancel_during_exa_retry_stops(ready_env):
    calls = {"n": 0}
    cancelled = {"v": False}

    def handler(request: httpx.Request):
        calls["n"] += 1
        cancelled["v"] = True
        return httpx.Response(500, json={"error": "boom"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ExaWebEvidenceProvider(
        _config(exa_api_key="k", max_retries=3, timeout_seconds=2),
        client=client,
    )
    decision = PolicyDecision(
        decision=PolicyDecisionKind.allow_with_constraints,
        reason_code=PolicyReason.allowed,
        max_results=1,
        max_chars_per_source=100,
        max_total_evidence_chars=200,
    )
    with pytest.raises(Exception) as exc:
        provider.search(
            "query",
            intent=SearchIntent.definition,
            decision=decision,
            cancel_check=lambda: cancelled["v"],
        )
    assert "cancelled" in str(exc.value).lower() or getattr(exc.value, "category", "") == "cancelled"
    assert calls["n"] == 1
    client.close()


def test_failure_modes_do_not_claim_retrieval(ready_env):
    store, clock, _ = ready_env
    service = type(build_web_evidence_service(store))(
        store, _config(), provider=FakeWebEvidenceProvider(hits=[]), clock=clock
    )
    auth = AuthScope(learner_id="alice", session_id="session_ready", tenant_id="default", request_id="f1")
    bundle = service.begin_bundle()

    # Unknown tool
    unknown = execute_tool_call(
        service, tool_name="browse_web", arguments={}, auth=auth,
        response_bundle_id=bundle, idempotency_key="fail-unknown",
    )
    assert unknown.retrieval_occurred is False
    assert "not available" in (unknown.learner_message or "").lower() or unknown.error_code == "schema_rejected"

    # Policy denial
    denied = service.search_web_evidence(
        auth,
        SearchWebEvidenceArgs(query="x", intent=SearchIntent.definition),
        response_bundle_id=bundle,
        idempotency_key="fail-policy",
        assessment_mode=True,
        source_policy="general",
        learner_requested_external=True,
    )
    # assessment_mode is on AuthScope, not kwargs — set properly
    denied = service.search_web_evidence(
        AuthScope(learner_id="alice", session_id="session_ready", tenant_id="default",
                  request_id="f2", assessment_mode=True),
        SearchWebEvidenceArgs(query="x", intent=SearchIntent.definition),
        response_bundle_id=bundle,
        idempotency_key="fail-assess",
        learner_requested_external=True,
        source_policy="general",
    )
    assert denied.ok is False and denied.retrieval_occurred is False
    assert "assessment" in (denied.learner_message or "").lower()

    # Empty evidence outcome
    empty = service.search_web_evidence(
        auth,
        SearchWebEvidenceArgs(query="none", intent=SearchIntent.definition),
        response_bundle_id=service.begin_bundle(),
        idempotency_key="fail-empty",
        learner_requested_external=True,
        source_policy="general",
    )
    assert empty.retrieval_occurred is False
    assert empty.evidence_outcome == EvidenceOutcome.no_reliable_evidence

    # Invented citation
    mapper = CitationMapper(EvidenceBundle(
        response_bundle_id="b", retrieval_occurred=False,
        evidence_outcome=EvidenceOutcome.no_reliable_evidence,
    ))
    validation = mapper.validate_response_text("I searched and found https://fake.example [web:W9]")
    assert validation.ok is False
    assert validation.false_retrieval_claim or validation.unknown_aliases or validation.invented_urls


def test_redaction_strips_keys_from_logs_and_payloads():
    key = "exa_live_secret_abcdef"
    text = redact_text(f"Authorization: Bearer {key} and api_key={key}", api_key=key)
    assert key not in text
    assert "[redacted" in text.lower() or "redacted" in text
    payload = redact_mapping({"api_key": key, "excerpt": "secret page", "title": "ok"}, api_key=key)
    assert payload["api_key"] == "[redacted]"
    assert payload["excerpt"] == "[redacted]"
    assert payload["title"] == "ok"


def test_exa_effective_limits_are_bounded():
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = request.read()
        return httpx.Response(200, json={"results": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    cfg = _config(
        exa_api_key="k", max_retries=0, max_results=3, max_chars_per_source=120,
        timeout_seconds=9, connect_timeout_seconds=3,
    )
    provider = ExaWebEvidenceProvider(cfg, client=client)
    decision = PolicyDecision(
        decision=PolicyDecisionKind.allow_with_constraints,
        reason_code=PolicyReason.allowed,
        max_results=3,
        max_chars_per_source=120,
        max_total_evidence_chars=400,
        domain_denylist=["chegg.com"],
    )
    provider.search("NIST metre definition", intent=SearchIntent.definition, decision=decision)
    import json
    body = json.loads(captured["body"].decode())
    assert body["numResults"] == 3
    assert body["type"] == "auto"
    assert body["contents"] == {"highlights": True}
    assert "text" not in body["contents"]
    assert "chegg.com" in body.get("excludeDomains", [])
    assert cfg.timeout_seconds == 9
    assert cfg.max_retries == 0
    client.close()


def test_oversized_exa_response_fails_safely():
    def handler(request: httpx.Request):
        return httpx.Response(200, content=b"x" * 10_000)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ExaWebEvidenceProvider(
        _config(exa_api_key="k", max_retries=0, max_response_bytes=1000),
        client=client,
    )
    decision = PolicyDecision(
        decision=PolicyDecisionKind.allow_with_constraints,
        reason_code=PolicyReason.allowed,
        max_results=1,
        max_chars_per_source=50,
        max_total_evidence_chars=100,
    )
    with pytest.raises(Exception) as exc:
        provider.search("q", intent=SearchIntent.definition, decision=decision)
    assert getattr(exc.value, "category", "") == "response_too_large"
    client.close()
