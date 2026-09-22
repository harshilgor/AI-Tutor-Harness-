"""Environment-backed configuration for web evidence retrieval."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field


POLICY_VERSION = "web-evidence-policy-v2"
FEATURE_VERSION = "web-evidence-feature-v2"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class WebEvidenceConfig:
    enabled: bool = False
    kill_global: bool = False
    kill_tenants: tuple[str, ...] = field(default_factory=tuple)
    kill_courses: tuple[str, ...] = field(default_factory=tuple)
    provider_name: str = "exa"
    exa_api_key: str | None = None
    exa_base_url: str = "https://api.exa.ai"
    allowed_egress_hosts: tuple[str, ...] = ("api.exa.ai",)
    timeout_seconds: float = 12.0
    connect_timeout_seconds: float = 5.0
    max_retries: int = 1
    retry_backoff_seconds: float = 0.25
    max_results: int = 5
    max_chars_per_source: int = 1200
    max_total_evidence_chars: int = 6000
    max_request_bytes: int = 4096
    max_response_bytes: int = 512_000
    max_tool_rounds: int = 2
    max_tool_calls_per_round: int = 2
    max_searches_per_turn: int = 1
    max_searches_per_session: int = 8
    max_searches_per_user_day: int = 40
    max_searches_per_tenant_day: int = 500
    max_searches_global_day: int = 5000
    max_opens_per_session: int = 4
    max_concurrent_provider_calls: int = 8
    result_ttl_seconds: int = 1800
    cache_ttl_seconds: int = 600
    circuit_failure_threshold: int = 5
    circuit_open_seconds: int = 60
    retention_interval_seconds: int = 900
    default_denylist: tuple[str, ...] = field(default_factory=tuple)
    default_allowlist: tuple[str, ...] = field(default_factory=tuple)
    allow_model_domain_hints: bool = False
    policy_version: str = POLICY_VERSION
    feature_version: str = FEATURE_VERSION

    @property
    def provider_available(self) -> bool:
        return bool(
            self.enabled
            and not self.kill_global
            and self.exa_api_key
            and self.provider_name in {"exa", "fake"}
        )

    def tenant_killed(self, tenant_id: str | None) -> bool:
        if self.kill_global:
            return True
        if not tenant_id:
            return False
        return tenant_id.lower() in {t.lower() for t in self.kill_tenants}

    def course_killed(self, course_id: str | None) -> bool:
        if not course_id:
            return False
        return course_id.lower() in {c.lower() for c in self.kill_courses}

    def source_policy_fingerprint(self, source_policy: str) -> str:
        material = "|".join([
            self.policy_version,
            self.feature_version,
            source_policy,
            ",".join(self.default_allowlist),
            ",".join(self.default_denylist),
            str(self.allow_model_domain_hints),
            str(int(self.enabled)),
        ])
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _resolve_egress_hosts() -> tuple[str, ...]:
    """Outbound evidence-provider hosts. Deployed environments are pinned to api.exa.ai."""
    configured = tuple(_env_csv("AI_TUTOR_WEB_EGRESS_HOSTS") or ["api.exa.ai"])
    env = (os.getenv("AI_TUTOR_ENV", "development") or "development").strip().lower()
    if env in {"production", "deployed"}:
        return ("api.exa.ai",)
    return configured or ("api.exa.ai",)


def load_web_evidence_config() -> WebEvidenceConfig:
    denylist = tuple(_env_csv("AI_TUTOR_WEB_DENYLIST") or [
        "quora.com", "brainly.com", "coursehero.com", "chegg.com",
        "stackoverflow.com",
    ])
    allowlist = tuple(_env_csv("AI_TUTOR_WEB_ALLOWLIST"))
    egress = _resolve_egress_hosts()
    return WebEvidenceConfig(
        enabled=_env_bool("AI_TUTOR_WEB_EVIDENCE", False),
        kill_global=_env_bool("AI_TUTOR_WEB_KILL_GLOBAL", False),
        kill_tenants=tuple(_env_csv("AI_TUTOR_WEB_KILL_TENANTS")),
        kill_courses=tuple(_env_csv("AI_TUTOR_WEB_KILL_COURSES")),
        provider_name=os.getenv("AI_TUTOR_WEB_PROVIDER", "exa").strip().lower() or "exa",
        exa_api_key=(os.getenv("EXA_API_KEY") or "").strip() or None,
        exa_base_url=(os.getenv("EXA_BASE_URL") or "https://api.exa.ai").rstrip("/"),
        allowed_egress_hosts=egress,
        timeout_seconds=float(os.getenv("AI_TUTOR_WEB_TIMEOUT_SECONDS") or 12),
        connect_timeout_seconds=float(os.getenv("AI_TUTOR_WEB_CONNECT_TIMEOUT_SECONDS") or 5),
        max_retries=max(0, min(3, _env_int("AI_TUTOR_WEB_MAX_RETRIES", 1))),
        retry_backoff_seconds=float(os.getenv("AI_TUTOR_WEB_RETRY_BACKOFF_SECONDS") or 0.25),
        max_results=max(1, min(10, _env_int("AI_TUTOR_WEB_MAX_RESULTS", 5))),
        max_chars_per_source=max(200, _env_int("AI_TUTOR_WEB_MAX_CHARS", 1200)),
        max_total_evidence_chars=max(500, _env_int("AI_TUTOR_WEB_MAX_TOTAL_CHARS", 6000)),
        max_request_bytes=max(512, _env_int("AI_TUTOR_WEB_MAX_REQUEST_BYTES", 4096)),
        max_response_bytes=max(4096, _env_int("AI_TUTOR_WEB_MAX_RESPONSE_BYTES", 512_000)),
        max_tool_rounds=max(0, min(4, _env_int("AI_TUTOR_WEB_MAX_TOOL_ROUNDS", 2))),
        max_tool_calls_per_round=max(1, min(4, _env_int("AI_TUTOR_WEB_MAX_TOOL_CALLS_ROUND", 2))),
        max_searches_per_turn=max(0, _env_int("AI_TUTOR_WEB_MAX_SEARCHES_TURN", 1)),
        max_searches_per_session=max(0, _env_int("AI_TUTOR_WEB_MAX_SEARCHES_SESSION", 8)),
        max_searches_per_user_day=max(0, _env_int("AI_TUTOR_WEB_MAX_SEARCHES_DAY", 40)),
        max_searches_per_tenant_day=max(0, _env_int("AI_TUTOR_WEB_MAX_SEARCHES_TENANT_DAY", 500)),
        max_searches_global_day=max(0, _env_int("AI_TUTOR_WEB_MAX_SEARCHES_GLOBAL_DAY", 5000)),
        max_opens_per_session=max(0, _env_int("AI_TUTOR_WEB_MAX_OPENS_SESSION", 4)),
        max_concurrent_provider_calls=max(1, _env_int("AI_TUTOR_WEB_MAX_CONCURRENCY", 8)),
        result_ttl_seconds=max(60, _env_int("AI_TUTOR_WEB_RESULT_TTL_SECONDS", 1800)),
        cache_ttl_seconds=max(0, _env_int("AI_TUTOR_WEB_CACHE_TTL_SECONDS", 600)),
        circuit_failure_threshold=max(1, _env_int("AI_TUTOR_WEB_CIRCUIT_FAILURES", 5)),
        circuit_open_seconds=max(5, _env_int("AI_TUTOR_WEB_CIRCUIT_OPEN_SECONDS", 60)),
        retention_interval_seconds=max(60, _env_int("AI_TUTOR_WEB_RETENTION_INTERVAL_SECONDS", 900)),
        default_denylist=denylist,
        default_allowlist=allowlist,
        allow_model_domain_hints=_env_bool("AI_TUTOR_WEB_ALLOW_MODEL_DOMAINS", False),
        policy_version=os.getenv("AI_TUTOR_WEB_POLICY_VERSION", POLICY_VERSION),
        feature_version=os.getenv("AI_TUTOR_WEB_FEATURE_VERSION", FEATURE_VERSION),
    )
