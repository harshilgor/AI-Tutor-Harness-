"""Optional live Exa contract checks. Opt-in only.

RUN_LIVE_EXA_TESTS=true EXA_API_KEY=... pytest -m live_provider backend/tests/test_live_exa.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Local server keys live in backend/.env (gitignored). Load before config reads.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from backend.app.web_evidence.config import load_web_evidence_config
from backend.app.web_evidence.exa import ExaWebEvidenceProvider
from backend.app.web_evidence.models import PolicyDecision, PolicyDecisionKind, PolicyReason, SearchIntent


@pytest.mark.live_provider
def test_live_exa_search_contract():
    if os.getenv("RUN_LIVE_EXA_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_LIVE_EXA_TESTS=true to call the live Exa API.")
    config = load_web_evidence_config()
    if not config.exa_api_key:
        pytest.skip("EXA_API_KEY is required for live Exa tests.")
    # Force enabled for the live contract even if the feature flag is off locally.
    live = type(config)(**{**config.__dict__, "enabled": True, "max_retries": 0, "timeout_seconds": 20})
    provider = ExaWebEvidenceProvider(live)
    decision = PolicyDecision(
        decision=PolicyDecisionKind.allow_with_constraints,
        reason_code=PolicyReason.allowed,
        max_results=2,
        max_chars_per_source=400,
        max_total_evidence_chars=800,
    )
    hits = provider.search(
        "NIST definition of the metre",
        intent=SearchIntent.definition,
        decision=decision,
    )
    assert isinstance(hits, list)
    if hits:
        assert hits[0].url.startswith("http")
        assert hits[0].excerpt
        assert hits[0].provider_result_ref
    provider.close()
