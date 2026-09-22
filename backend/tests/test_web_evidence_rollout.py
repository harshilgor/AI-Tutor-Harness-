"""Rollout readiness: schema, postgres gate, retention heartbeat, defaults."""

from __future__ import annotations

import os

import pytest

from backend.app.web_evidence.config import load_web_evidence_config
from backend.app.web_evidence.readiness import (
    REQUIRED_TABLES,
    assert_deployed_enablement,
    check_schema,
    enforce_enablement_gate,
    evaluate_readiness,
)
from backend.app.web_evidence.retention import EvidenceRetention
from backend.app.web_evidence.service import build_web_evidence_service


def test_web_evidence_defaults_disabled(monkeypatch):
    monkeypatch.delenv("AI_TUTOR_WEB_EVIDENCE", raising=False)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    cfg = load_web_evidence_config()
    assert cfg.enabled is False


def test_schema_readiness_after_migrations(tmp_path):
    from backend.app.storage import Store

    db = tmp_path / "ready.db"
    store = Store(str(db))
    ok, missing_tables, missing_indexes = check_schema(store)
    assert ok is True
    assert missing_tables == ()
    assert missing_indexes == ()
    assert set(REQUIRED_TABLES) <= set(
        __import__("sqlalchemy").inspect(store.engine).get_table_names()
    )
    report = evaluate_readiness(store)
    assert report.schema_ok is True
    assert report.egress_ok is True
    store.close()


def test_deployed_enablement_requires_postgres(tmp_path, monkeypatch):
    from backend.app.storage import Store
    from backend.app.web_evidence.config import WebEvidenceConfig

    monkeypatch.setenv("AI_TUTOR_ENV", "production")
    monkeypatch.setenv("AI_TUTOR_WEB_EVIDENCE", "true")
    monkeypatch.setenv("EXA_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("AI_TUTOR_WEB_EGRESS_HOSTS", "api.exa.ai")
    db = tmp_path / "prod-sqlite.db"
    store = Store(str(db))
    cfg = WebEvidenceConfig(enabled=True, exa_api_key="k", allowed_egress_hosts=("api.exa.ai",))
    with pytest.raises(RuntimeError, match="postgresql|web_evidence_requires_postgresql"):
        assert_deployed_enablement(store, cfg)
    gated = enforce_enablement_gate(store, cfg)
    assert gated.enabled is False
    service = build_web_evidence_service(store)
    assert service.config.enabled is False
    store.close()


def test_retention_heartbeat_and_health_signal(tmp_path, monkeypatch):
    from backend.app.storage import Store

    monkeypatch.setenv("AI_TUTOR_WEB_RETENTION_INTERVAL_SECONDS", "900")
    store = Store(str(tmp_path / "ret.db"))
    retention = EvidenceRetention(store)
    before = evaluate_readiness(store)
    assert before.retention["stale"] is True
    stats = retention.purge_expired(limit=10, record_heartbeat=True)
    assert isinstance(stats, dict)
    after = evaluate_readiness(store)
    assert after.retention["ok"] is True
    assert after.retention["stale"] is False
    assert after.retention["lastSuccessAt"]
    store.close()


def test_deployed_egress_pinned_to_exa(monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ENV", "production")
    monkeypatch.setenv("AI_TUTOR_WEB_EGRESS_HOSTS", "evil.example,api.exa.ai")
    cfg = load_web_evidence_config()
    assert cfg.allowed_egress_hosts == ("api.exa.ai",)
